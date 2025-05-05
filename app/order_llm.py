from openai import AsyncOpenAI
import os
import json
import logging
from .custom_types import (
    ResponseRequiredRequest,
    ResponseResponse,
    Utterance,
)
from typing import List, Tuple, Optional
from .database import Database
import time
from .prompts import begin_sentence, agent_prompt, system_prompt, reminder_message
from .tools import get_tool_definitions
from .handler import verify_menu_item_function, handle_function_call

# Ensure logs directory exists
logs_dir = "logs"
if not os.path.exists(logs_dir):
    print(f"Logs directory {logs_dir} does not exist. Creating it.")
    os.makedirs(logs_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "db_operations.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("db_operations")

# Create separate loggers for different components
conversation_logger = logging.getLogger("conversation")
conversation_logger.setLevel(logging.INFO)
conversation_handler = logging.FileHandler(os.path.join(logs_dir, "conversation.log"))
conversation_logger.addHandler(conversation_handler)

tool_logger = logging.getLogger("tool_calls")
tool_logger.setLevel(logging.INFO)
tool_handler = logging.FileHandler(os.path.join(logs_dir, "tool_calls.log"))
tool_logger.addHandler(tool_handler)

response_logger = logging.getLogger("responses")
response_logger.setLevel(logging.INFO)
response_handler = logging.FileHandler(os.path.join(logs_dir, "responses.log"))
response_logger.addHandler(response_handler)

# Format for specialized logs
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
conversation_handler.setFormatter(log_formatter)
tool_handler.setFormatter(log_formatter)
response_handler.setFormatter(log_formatter)


class OrderAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.db = Database()
        self.from_number = None  # Store the caller's phone number from the request
        self.verified_customer = None  # Store verified customer information
        self.current_order = None  # Store the current order information
        self.conversation_id = str(int(time.time()))  # Create unique conversation ID

        # Cache menu and restaurant information
        try:
            logger.info("Retrieving and caching menu information from database")
            self.menu_items = self.db.get_menu()
            logger.info(f"Cached {len(self.menu_items)} menu items")

            self.add_ons = self.db.get_add_ons()
            logger.info(f"Cached {len(self.add_ons)} add-ons")

            # Get restaurant information
            self.restaurant = self.db.get_restaurant()
            logger.info(
                f"Cached restaurant information: {self.restaurant.name if self.restaurant else 'None'}"
            )
        except Exception as e:
            logger.error(f"Error retrieving menu data during initialization: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Use empty lists to avoid breaking initialization
            self.menu_items = []
            self.add_ons = []
            self.restaurant = None

    def set_from_number(self, from_number):
        """Set the caller's phone number from the call request"""
        self.from_number = from_number
        logger.info(f"Set from_number: {self.from_number}")

    def draft_begin_message(self):
        # Always ask for name first, regardless of whether we have from_number
        welcome_msg = "Welcome to Tote AI Restaurant! I'm your order assistant. To get started, could you please tell me your name?"

        # Log the initial agent message
        conversation_logger.info(
            f"CONV_ID:{self.conversation_id} ROLE:agent MESSAGE:{welcome_msg}"
        )

        response = ResponseResponse(
            response_id=0,
            content=welcome_msg,
            content_complete=True,
            end_call=False,
        )
        return response

    def convert_transcript_to_openai_messages(self, transcript: List[Utterance]):
        # Log the current conversation transcript
        for utterance in transcript:
            conversation_logger.info(
                f"CONV_ID:{self.conversation_id} ROLE:{utterance.role} MESSAGE:{utterance.content}"
            )

        messages = []
        for utterance in transcript:
            if utterance.role == "agent":
                messages.append({"role": "assistant", "content": utterance.content})
            else:
                messages.append({"role": "user", "content": utterance.content})
        return messages

    def prepare_prompt(self, request: ResponseRequiredRequest):
        # Add from_number information to the prompt if we have it
        current_prompt = (
            super().prepare_prompt(request)
            if hasattr(super(), "prepare_prompt")
            else self.prepare_prompt_original(request)
        )

        # Inform the LLM about the from_number if available
        if (
            self.from_number
            and len(current_prompt) > 0
            and current_prompt[0]["role"] == "system"
        ):
            current_prompt[0][
                "content"
            ] += f"\n\nIMPORTANT: The caller's phone number is {self.from_number}. After asking for their name, use this number to check if they are an existing customer. Do not ask for their phone number unless explicitly instructed to do so."

        return current_prompt

    def prepare_prompt_original(self, request: ResponseRequiredRequest):
        # Format menu information for the prompt
        menu_info = "## Our Delicious Menu\n"

        # Filter available items only
        available_items = [
            item for item in self.menu_items if getattr(item, "is_available", 1) == 1
        ]
        logger.info(f"Using {len(available_items)} available menu items from cache")

        # Group items by category
        categories = {}
        for item in available_items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)

        # Add items to menu info with more engaging descriptions
        for category, items in categories.items():
            menu_info += f"\nLet me tell you about our {category.title()}s. "
            menu_info += f"We have several delicious options: "
            for i, item in enumerate(items):
                if i > 0:
                    menu_info += ", and "
                menu_info += f"our {item.name} for ${item.base_price:.2f}"
                if item.description:
                    menu_info += f" - {item.description}"
            menu_info += ".\n"

        # Add add-on information by category and type
        if self.add_ons:
            menu_info += "\n## Our Add-ons\n"

            # Group add-ons by category and type
            grouped_addons = {}
            for addon in self.add_ons:
                if addon.category not in grouped_addons:
                    grouped_addons[addon.category] = {}

                addon_type = addon.type or "other"
                if addon_type not in grouped_addons[addon.category]:
                    grouped_addons[addon.category][addon_type] = []

                grouped_addons[addon.category][addon_type].append(addon)

            # Add grouped add-ons to menu info
            for category, types in grouped_addons.items():
                menu_info += f"\nFor our {category}s, we offer:\n"

                # Order types: size first, then sauce, then toppings, then others
                type_order = ["size", "sauce", "topping", "other"]

                for addon_type in type_order:
                    if addon_type in types and types[addon_type]:
                        menu_info += f"- {addon_type.title()} options: "
                        type_addons = types[addon_type]
                        for i, addon in enumerate(type_addons):
                            price_text = (
                                f"${addon.price:.2f}"
                                if addon.price != 0
                                else "no extra charge"
                            )
                            if i > 0:
                                menu_info += ", "
                            menu_info += f"{addon.name} ({price_text})"
                        menu_info += "\n"

        menu_info += "\nEverything is prepared fresh to order for pickup at our restaurant. What would you like to try today?"

        # Add restaurant information
        if self.restaurant:
            menu_info += f"\n\nPlease note: We are a PICKUP ONLY restaurant. You can pick up your order at {self.restaurant.name} located at {self.restaurant.address}. Our phone number is {self.restaurant.phone} and we're open {self.restaurant.opening_hours}."
        else:
            menu_info += "\n\nPlease note: We are a PICKUP ONLY restaurant. Once your order is confirmed, we'll provide you with our pickup address and an estimated preparation time."

        prompt = [
            {
                "role": "system",
                "content": system_prompt + menu_info + "\n## Role\n" + agent_prompt,
            }
        ]

        transcript_messages = self.convert_transcript_to_openai_messages(
            request.transcript
        )
        for message in transcript_messages:
            prompt.append(message)

        if request.interaction_type == "reminder_required":
            prompt.append(
                {
                    "role": "user",
                    "content": reminder_message,
                }
            )
        return prompt

    def prepare_functions(self):
        return get_tool_definitions()

    def _validate_phone_number(self, phone) -> Tuple[bool, Optional[str], str]:
        """
        Validates a phone number.
        Returns a tuple of (is_valid, phone_str, error_message)
        """
        try:
            # Convert to string to handle if it's already an integer
            phone_str = str(phone)

            # Remove any non-digit characters for validation
            digits_only = "".join(c for c in phone_str if c.isdigit())

            # Check if it's exactly 10 digits
            if len(digits_only) != 10:
                return (
                    False,
                    None,
                    "Phone number must be exactly 10 digits long. Please try again.",
                )

            # Return the phone number as a string for database operations
            return True, digits_only, ""

        except (ValueError, TypeError):
            return (
                False,
                None,
                "That doesn't appear to be a valid phone number. Please provide a 10-digit number without spaces or special characters.",
            )

    def create_response(
        self, response_id, content, content_complete=True, end_call=False
    ):
        """Helper to create ResponseResponse objects"""
        return ResponseResponse(
            response_id=response_id,
            content=content,
            content_complete=content_complete,
            end_call=end_call,
        )

    async def draft_response(self, request: ResponseRequiredRequest):
        prompt = self.prepare_prompt(request)
        func_call = {}
        func_arguments = ""
        accumulated_content = ""  # Variable to accumulate content chunks

        # Log the prepared prompt
        prompt_str = json.dumps(prompt, indent=2)
        response_logger.info(f"CONV_ID:{self.conversation_id} PROMPT:{prompt_str}")

        # Continue with normal OpenAI flow
        try:
            stream = await self.client.chat.completions.create(
                model=os.environ["OPENAI_MODEL"],
                messages=prompt,
                stream=True,
                tools=self.prepare_functions(),
            )

            # Log the request to OpenAI
            tool_logger.info(
                f"CONV_ID:{self.conversation_id} REQUEST:OpenAI model={os.environ['OPENAI_MODEL']}"
            )

            async for chunk in stream:
                if len(chunk.choices) == 0:
                    continue
                if chunk.choices[0].delta.tool_calls:
                    tool_calls = chunk.choices[0].delta.tool_calls[0]
                    if tool_calls.id:
                        if func_call:
                            break
                        func_call = {
                            "id": tool_calls.id,
                            "func_name": tool_calls.function.name or "",
                            "arguments": {},
                        }
                        # Log tool call initialization
                        tool_logger.info(
                            f"CONV_ID:{self.conversation_id} TOOL_CALL_INIT:id={tool_calls.id} name={tool_calls.function.name}"
                        )
                    else:
                        func_arguments += tool_calls.function.arguments or ""

                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # Accumulate content chunks instead of logging each one
                    accumulated_content += content

                    response = ResponseResponse(
                        response_id=request.response_id,
                        content=content,
                        content_complete=False,
                        end_call=False,
                    )
                    yield response

            # Log the complete accumulated content after all chunks have been processed
            if accumulated_content:
                response_logger.info(
                    f"CONV_ID:{self.conversation_id} COMPLETE_CONTENT:{accumulated_content}"
                )

            if func_call:
                # Use the handle_function_call from handler.py
                async for response in handle_function_call(
                    self, request, func_call, func_arguments
                ):
                    yield response
        except Exception as e:
            # Log any exceptions during the API call
            error_msg = f"Error during OpenAI API call: {str(e)}"
            logger.error(error_msg)
            response_logger.error(
                f"CONV_ID:{self.conversation_id} API_ERROR:{error_msg}"
            )

            # Return a generic error response
            yield ResponseResponse(
                response_id=request.response_id,
                content="I'm sorry, but I'm having trouble processing your request right now. Please try again in a moment.",
                content_complete=True,
                end_call=False,
            )

    def _calculate_total_amount(self, order_items):
        """Calculate the total amount for an order based on the menu items and their add-ons."""
        # This is now handled directly in the create_order function
        # We'll keep this for backward compatibility
        if (
            order_items
            and isinstance(order_items[0], dict)
            and "total_price" in order_items[0]
        ):
            # If we have the new format with total_price already calculated
            return sum(item["total_price"] for item in order_items)

        # Legacy calculation for old format
        print(f"Calculating total amount for order: {order_items}")
        total = 0
        for item in order_items:
            menu_item = self.db.find_similar_menu_item(item["item_name"])
            if menu_item and getattr(menu_item, "is_available", 1) == 1:
                item_total = menu_item.base_price * item["quantity"]
                total += item_total

                for addon_name in item.get("add_ons", []):
                    addon = next(
                        (
                            a
                            for a in self.db.get_add_ons(menu_item.category)
                            if a.name == addon_name
                        ),
                        None,
                    )
                    if addon:
                        total += addon.price * item["quantity"]

        return total
