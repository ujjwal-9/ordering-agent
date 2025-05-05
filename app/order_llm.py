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
        functions = [
            {
                "type": "function",
                "function": {
                    "name": "verify_customer",
                    "description": "Verify if a customer exists by phone number.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the customer",
                            },
                            "phone": {
                                "type": "integer",
                                "description": "The phone number of the customer (must be a number without spaces or special characters)",
                            },
                        },
                        "required": ["name", "phone"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "collect_customer_info",
                    "description": "Collect customer information step by step.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "step": {
                                "type": "string",
                                "description": "The current step of information collection (phone, name, email, payment_method)",
                            },
                            "phone": {
                                "type": "integer",
                                "description": "The phone number of the customer (must be a number without spaces or special characters)",
                            },
                            "name": {
                                "type": "string",
                                "description": "The name of the customer",
                            },
                            "email": {
                                "type": "string",
                                "description": "The customer's email address",
                            },
                            "preferred_payment_method": {
                                "type": "string",
                                "description": "The customer's preferred payment method",
                            },
                        },
                        "required": ["step"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_order_history",
                    "description": "Get the customer's order history.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone": {
                                "type": "integer",
                                "description": "The phone number of the customer (must be a number without spaces or special characters)",
                            },
                        },
                        "required": ["phone"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_menu_item",
                    "description": "Verify if a menu item exists and find similar items if it doesn't.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_name": {
                                "type": "string",
                                "description": "The name of the menu item to verify",
                            },
                            "category": {
                                "type": "string",
                                "description": "The category of the menu item (burger, pizza, etc.)",
                            },
                        },
                        "required": ["item_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_order",
                    "description": "Create a new order or update existing order in the database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {
                                "type": "string",
                                "description": "The name of the customer",
                            },
                            "customer_phone": {
                                "type": "integer",
                                "description": "The phone number of the customer (must be a number without spaces or special characters)",
                            },
                            "order_items": {
                                "type": "array",
                                "description": "List of items in the order",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item_name": {"type": "string"},
                                        "quantity": {"type": "integer"},
                                        "add_ons": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                },
                            },
                            "is_update": {
                                "type": "boolean",
                                "description": "Whether this is an update to an existing order",
                            },
                        },
                        "required": [
                            "customer_name",
                            "customer_phone",
                            "order_items",
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "end_call",
                    "description": "End the call only when user explicitly requests it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message you will say before ending the call with the customer.",
                            },
                        },
                        "required": ["message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_item_addons",
                    "description": "Get available add-ons for a specific menu item.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_name": {
                                "type": "string",
                                "description": "The name of the menu item",
                            },
                        },
                        "required": ["item_name"],
                    },
                },
            },
        ]
        return functions

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
                # Log complete function call
                func_call["arguments"] = json.loads(func_arguments)
                tool_logger.info(
                    f"CONV_ID:{self.conversation_id} TOOL_CALL_COMPLETE:func={func_call['func_name']} args={json.dumps(func_call['arguments'])}"
                )

                if func_call["func_name"] == "verify_customer":
                    func_call["arguments"] = json.loads(func_arguments)
                    name = func_call["arguments"]["name"]
                    phone = func_call["arguments"].get("phone")

                    # If phone wasn't provided in the function call but we have from_number, use it
                    if not phone and self.from_number:
                        phone = self.from_number
                        logger.info(
                            f"Using from_number {phone} instead of asking for phone"
                        )

                    # Proceed with verification only if we have a phone number
                    if phone:
                        # Validate phone number
                        is_valid, phone_str, error_message = (
                            self._validate_phone_number(phone)
                        )
                        if not is_valid:
                            logger.warning(f"Invalid phone number format: {phone}")
                            response_content = error_message
                            # Log invalid phone number response
                            response_logger.warning(
                                f"CONV_ID:{self.conversation_id} INVALID_PHONE:{phone} RESPONSE:{response_content}"
                            )

                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=response_content,
                                content_complete=True,
                                end_call=False,
                            )
                            return

                        logger.info(f"Verifying customer with phone: {phone_str}")
                        customer = self.db.get_customer_by_phone(phone_str)

                        if customer:
                            logger.info(f"Found existing customer: {customer.name}")
                            self.verified_customer = customer

                            # Compare provided name with name in database
                            provided_name = name
                            db_name = customer.name

                            # Prepare response based on whether names match
                            if provided_name.lower() == db_name.lower():
                                response_text = f"Welcome back, {provided_name}! I found your information in our records. "
                            else:
                                # Note the discrepancy but continue using the customer's provided name
                                response_text = f"Welcome back, {provided_name}! I have you in our records as {db_name}."

                            # If we're using the from_number (not explicitly provided by customer), don't ask for confirmation
                            if phone == self.from_number:
                                response_text += " "
                            else:
                                response_text += f" Your phone number is {phone_str}, is that correct? "

                            # Only include optional fields if they exist and have values
                            if (
                                hasattr(customer, "preferred_payment_method")
                                and customer.preferred_payment_method
                            ):
                                response_text += f"Your preferred payment method is {customer.preferred_payment_method}. "

                            if hasattr(customer, "total_orders"):
                                response_text += f"\nYou've placed {customer.total_orders} orders with us. "

                            # If we used the from_number, don't ask for confirmation but directly ask for order
                            if phone == self.from_number:
                                response_text += "What would you like to order today?"
                            else:
                                response_text += "Is this information correct?"

                            # Log the response being sent to customer
                            conversation_logger.info(
                                f"CONV_ID:{self.conversation_id} ROLE:agent MESSAGE:{response_text}"
                            )
                            response_logger.info(
                                f"CONV_ID:{self.conversation_id} CUSTOMER_VERIFIED:true NAME:{provided_name} RESPONSE:{response_text}"
                            )

                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=response_text,
                                content_complete=True,
                                end_call=False,
                            )
                        else:
                            logger.info(
                                f"No existing customer found for phone: {phone_str}"
                            )

                            # If we're using from_number that's not in the database, we can register the customer
                            if phone == self.from_number:
                                # Register the new customer with the from_number
                                try:
                                    customer_data = {
                                        "name": name,
                                        "phone": phone_str,
                                    }
                                    new_customer = self.db.create_customer(
                                        **customer_data, auto_commit=True
                                    )
                                    logger.info(
                                        f"Created new customer: {name} with phone: {phone_str}"
                                    )

                                    # Skip phone confirmation and go straight to menu
                                    restaurant = self.db.get_restaurant()
                                    pickup_address = (
                                        restaurant.address
                                        if restaurant
                                        else "our restaurant"
                                    )

                                    yield ResponseResponse(
                                        response_id=request.response_id,
                                        content=f"Thank you, {name}! I've registered you as a new customer. Let me tell you about our menu. We offer delicious burgers and pizzas, all available for pickup at {pickup_address}. What would you like to order today?",
                                        content_complete=True,
                                        end_call=False,
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Error creating new customer: {str(e)}"
                                    )
                                    yield ResponseResponse(
                                        response_id=request.response_id,
                                        content=f"Thank you, {name}. What would you like to order today?",
                                        content_complete=True,
                                        end_call=False,
                                    )
                            else:
                                # For manually entered phone numbers, verify with the customer
                                yield ResponseResponse(
                                    response_id=request.response_id,
                                    content=f"Nice to meet you, {name}! I've got your phone number as {phone_str}, is that correct?",
                                    content_complete=True,
                                    end_call=False,
                                )
                elif func_call["func_name"] == "collect_customer_info":
                    func_call["arguments"] = json.loads(func_arguments)
                    step = func_call["arguments"]["step"]

                    if step == "name":
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content="What is your name?",
                            content_complete=True,
                            end_call=False,
                        )

                    elif step == "email":
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content="Would you like to provide an email address for order updates? (optional)",
                            content_complete=True,
                            end_call=False,
                        )

                    elif step == "payment_method":
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content="What is your preferred payment method? (cash, credit card, or digital payment)",
                            content_complete=True,
                            end_call=False,
                        )

                    elif step == "complete":
                        # Validate phone number
                        is_valid, phone_str, error_message = (
                            self._validate_phone_number(func_call["arguments"]["phone"])
                        )
                        if not is_valid:
                            logger.warning(
                                f"Invalid phone number format: {func_call['arguments']['phone']}"
                            )
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=error_message,
                                content_complete=True,
                                end_call=False,
                            )
                            return

                        # Process the customer info with the validated phone number
                        customer = self.db.get_customer_by_phone(phone_str)

                        customer_data = {
                            "name": func_call["arguments"]["name"],
                            "email": func_call["arguments"].get("email"),
                            "preferred_payment_method": func_call["arguments"].get(
                                "preferred_payment_method"
                            ),
                        }

                        if customer:
                            logger.info(f"Updating existing customer: {customer.name}")
                            try:
                                customer = self.db.update_customer(
                                    phone_str, auto_commit=True, **customer_data
                                )
                                # Safe commit is no longer needed as auto_commit=True will handle it
                                # if not self.db.safe_commit():
                                #    logger.error(
                                #        "Failed to commit customer update after multiple retries"
                                #    )
                            except Exception as e:
                                self.db.session.rollback()
                                logger.error(f"Error updating customer: {str(e)}")
                                import traceback

                                logger.error(f"Traceback: {traceback.format_exc()}")
                        else:
                            logger.info(
                                f"Creating new customer with phone: {phone_str}"
                            )
                            customer_data["phone"] = phone_str
                            try:
                                customer = self.db.create_customer(
                                    **customer_data, auto_commit=True
                                )
                                # Use the safe commit method is no longer needed as auto_commit=True will handle it
                                # if not self.db.safe_commit():
                                #    logger.error(
                                #        "Failed to commit new customer creation after multiple retries"
                                #    )
                            except Exception as e:
                                self.db.session.rollback()
                                logger.error(f"Error creating customer: {str(e)}")
                                import traceback

                                logger.error(f"Traceback: {traceback.format_exc()}")

                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=f"Thank you for providing your information. I've added your phone number {phone_str} to our records. What would you like to order today?",
                            content_complete=True,
                            end_call=False,
                        )

                elif func_call["func_name"] == "get_order_history":
                    func_call["arguments"] = json.loads(func_arguments)
                    # Validate phone number
                    is_valid, phone_str, error_message = self._validate_phone_number(
                        func_call["arguments"]["phone"]
                    )
                    if not is_valid:
                        logger.warning(
                            f"Invalid phone number format: {func_call['arguments']['phone']}"
                        )
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=error_message,
                            content_complete=True,
                            end_call=False,
                        )
                        return

                    logger.info(
                        f"Retrieving order history for customer with phone: {phone_str}"
                    )
                    orders = self.db.get_customer_order_history(phone_str)
                    if orders:
                        logger.info(f"Found {len(orders)} orders for customer")
                        response_text = "Here's your order history:\n\n"
                        for order in orders[:5]:  # Show last 5 orders
                            response_text += f"Order #{order.id} ({order.created_at.strftime('%Y-%m-%d')}):\n"
                            response_text += f"- Status: {order.status}\n"
                            response_text += f"- Total: ${order.total_amount:.2f}\n"
                            response_text += f"- Items: {', '.join([item['item_name'] for item in order.order_items])}\n\n"
                        if len(orders) > 5:
                            response_text += f"... and {len(orders) - 5} more orders."

                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=response_text,
                            content_complete=True,
                            end_call=False,
                        )
                    else:
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content="I don't see any previous orders in your history. Would you like to place an order?",
                            content_complete=True,
                            end_call=False,
                        )

                elif func_call["func_name"] == "verify_menu_item":
                    func_call["arguments"] = json.loads(func_arguments)
                    item_name = func_call["arguments"]["item_name"]
                    category = func_call["arguments"].get("category")
                    logger.info(
                        f"Verifying menu item: {item_name} (category: {category})"
                    )
                    similar_item = self.db.find_similar_menu_item(item_name, category)

                    if similar_item:
                        # Check if the item is available
                        if getattr(similar_item, "is_available", 1) == 1:
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=f"I found {similar_item.name} (${similar_item.base_price:.2f}). Would you like to order this?",
                                content_complete=True,
                                end_call=False,
                            )
                        else:
                            # If the item exists but is unavailable
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=f"I'm sorry, but {similar_item.name} is currently unavailable. Would you like to see other options in our menu?",
                                content_complete=True,
                                end_call=False,
                            )
                    else:
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content="I couldn't find that item on our menu. Would you like to see our available options?",
                            content_complete=True,
                            end_call=False,
                        )

                elif func_call["func_name"] == "create_order":
                    func_call["arguments"] = json.loads(func_arguments)
                    try:
                        # Get customer phone with priority: 1) function argument, 2) verified customer, 3) from_number
                        customer_phone = func_call["arguments"].get("customer_phone")
                        if not customer_phone and self.verified_customer:
                            customer_phone = self.verified_customer.phone
                        elif not customer_phone and self.from_number:
                            customer_phone = self.from_number

                        # Validate phone number
                        is_valid, customer_phone_str, error_message = (
                            self._validate_phone_number(customer_phone)
                        )
                        if not is_valid:
                            logger.warning(
                                f"Invalid phone number format: {customer_phone}"
                            )
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=error_message,
                                content_complete=True,
                                end_call=False,
                            )
                            return

                        # Check if this is an update to an existing order
                        is_update = False
                        if self.current_order:
                            is_update = True
                            logger.info(
                                f"Updating existing order #{self.current_order.id}"
                            )

                        # Transform order items into the required format with database queries
                        raw_order_items = func_call["arguments"]["order_items"]
                        formatted_order_items = []

                        # Collect special instructions for the whole order
                        order_special_instructions = func_call["arguments"].get(
                            "special_instructions", ""
                        )

                        for item in raw_order_items:
                            # Get menu item details including ID from database
                            menu_item = self.db.find_similar_menu_item(
                                item["item_name"]
                            )

                            if (
                                not menu_item
                                or getattr(menu_item, "is_available", 1) == 0
                            ):
                                logger.warning(
                                    f"Menu item not found or unavailable: {item['item_name']}"
                                )
                                continue

                            quantity = item.get("quantity", 1)
                            base_price = menu_item.base_price

                            # Process add-ons and collect item-specific special instructions
                            formatted_add_ons = []
                            total_add_on_price = 0
                            item_special_instructions = item.get(
                                "special_instructions", ""
                            )

                            for addon_name in item.get("add_ons", []):
                                # Find add-on in database to get its ID and price
                                add_ons = self.db.get_add_ons(menu_item.category)

                                # First try exact match
                                addon = next(
                                    (
                                        a
                                        for a in add_ons
                                        if a.name.lower() == addon_name.lower()
                                    ),
                                    None,
                                )

                                # If no exact match, try to extract the core add-on name
                                # This handles cases like "extra bacon" -> "bacon"
                                if not addon:
                                    # Try to find a partial match
                                    matching_addons = [
                                        a
                                        for a in add_ons
                                        if a.name.lower() in addon_name.lower()
                                        or addon_name.lower() in a.name.lower()
                                    ]

                                    if matching_addons:
                                        # Use the first matching add-on
                                        addon = matching_addons[0]

                                        # Extract modifier words like "extra", "light", etc.
                                        modifier_words = (
                                            addon_name.lower()
                                            .replace(addon.name.lower(), "")
                                            .strip()
                                        )
                                        if modifier_words:
                                            # Add to item special instructions if not empty
                                            if item_special_instructions:
                                                item_special_instructions += (
                                                    f", {modifier_words} {addon.name}"
                                                )
                                            else:
                                                item_special_instructions = (
                                                    f"{modifier_words} {addon.name}"
                                                )

                                if addon:
                                    formatted_add_ons.append(
                                        {
                                            "add_on_id": addon.id,
                                            "add_on_name": addon.name,
                                            "price": addon.price,
                                        }
                                    )
                                    total_add_on_price += addon.price

                            # Calculate total price for this item
                            total_price = (base_price + total_add_on_price) * quantity

                            # Create the formatted order item
                            formatted_item = {
                                "menu_item_id": menu_item.id,
                                "menu_item_name": menu_item.name,
                                "quantity": quantity,
                                "base_price": base_price,
                                "total_price": total_price,
                                "add_ons": formatted_add_ons,
                            }

                            # Add item special instructions if any
                            if item_special_instructions:
                                formatted_item["special_instructions"] = (
                                    item_special_instructions
                                )

                            formatted_order_items.append(formatted_item)

                        # Calculate total amount for the entire order
                        total_amount = sum(
                            item["total_price"] for item in formatted_order_items
                        )

                        # Combine order-level and item-level special instructions
                        combined_special_instructions = order_special_instructions
                        for item in formatted_order_items:
                            if "special_instructions" in item:
                                if combined_special_instructions:
                                    combined_special_instructions += f"; {item['menu_item_name']}: {item['special_instructions']}"
                                else:
                                    combined_special_instructions = f"{item['menu_item_name']}: {item['special_instructions']}"
                                # Remove from item to avoid duplication
                                del item["special_instructions"]

                        order_data = {
                            "customer_name": func_call["arguments"]["customer_name"],
                            "customer_phone": customer_phone_str,
                            "order_items": formatted_order_items,
                            "total_amount": total_amount,
                        }

                        # Add the combined special instructions
                        if combined_special_instructions:
                            order_data["special_instructions"] = (
                                combined_special_instructions
                            )

                        try:
                            # Add payment method if provided
                            if "payment_method" in func_call["arguments"]:
                                order_data["payment_method"] = func_call["arguments"][
                                    "payment_method"
                                ]

                            # Get restaurant information for pickup address
                            restaurant = self.db.get_restaurant()
                            pickup_address = (
                                restaurant.address
                                if restaurant
                                else "123 Main Street, Downtown, CA 94123"
                            )

                            # Create a new order or update the existing one
                            if is_update:
                                # Update the existing order
                                order = self.db.update_order(
                                    self.current_order.id,
                                    order_items=formatted_order_items,
                                    total_amount=total_amount,
                                    special_instructions=order_data.get(
                                        "special_instructions"
                                    ),
                                    payment_method=order_data.get("payment_method"),
                                    auto_commit=True,
                                )
                                confirmation_message = f"I've updated your order. Your order number is still #{order.id}."
                            else:
                                # Create a new order
                                order = self.db.create_order(
                                    **order_data, auto_commit=True
                                )
                                self.current_order = order  # Store the current order
                                confirmation_message = f"Great! I've placed your order. Your order number is #{order.id}."

                            # Construct the confirmation message
                            confirmation_message += " We will send you a confirmation text shortly along with order details and estimated pickup time."
                            confirmation_message += f" You can pick up your order at our restaurant located at {pickup_address}."

                            # Add a note about being able to update the order
                            if not is_update:
                                confirmation_message += " If you need to make any changes to your order, just let me know and I can update it for you."

                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=confirmation_message,
                                content_complete=True,
                                end_call=False,
                            )
                        except Exception as e:
                            # Rollback in case of error
                            self.db.session.rollback()
                            logger.error(
                                f"Error creating/updating order in database: {str(e)}"
                            )
                            import traceback

                            logger.error(f"Traceback: {traceback.format_exc()}")
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=f"I'm sorry, there was an error processing your order. Please try again or contact customer support.",
                                content_complete=True,
                                end_call=False,
                            )
                    except Exception as e:
                        logger.error(
                            f"Unexpected error in create_order function: {str(e)}"
                        )
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=f"I'm sorry, something went wrong while processing your order. Please try again later.",
                            content_complete=True,
                            end_call=False,
                        )

                elif func_call["func_name"] == "end_call":
                    func_call["arguments"] = json.loads(func_arguments)
                    response_content = func_call["arguments"]["message"]

                    # Log the end call
                    conversation_logger.info(
                        f"CONV_ID:{self.conversation_id} ROLE:agent MESSAGE:{response_content}"
                    )
                    tool_logger.info(f"CONV_ID:{self.conversation_id} END_CALL:true")
                    response_logger.info(
                        f"CONV_ID:{self.conversation_id} CALL_ENDED:true FINAL_MESSAGE:{response_content}"
                    )

                    yield ResponseResponse(
                        response_id=request.response_id,
                        content=response_content,
                        content_complete=True,
                        end_call=True,
                    )

                elif func_call["func_name"] == "get_item_addons":
                    func_call["arguments"] = json.loads(func_arguments)
                    item_name = func_call["arguments"]["item_name"]

                    # Attempt to find the menu item with more flexible matching
                    menu_item = None
                    all_menu_items = self.menu_items

                    # First try exact match
                    for item in all_menu_items:
                        if (
                            item.name.lower() == item_name.lower()
                            and getattr(item, "is_available", 1) == 1
                        ):
                            menu_item = item
                            break

                    # If no exact match, try partial match
                    if not menu_item:
                        potential_matches = []
                        for item in all_menu_items:
                            if getattr(item, "is_available", 1) == 1 and (
                                item.name.lower() in item_name.lower()
                                or item_name.lower() in item.name.lower()
                            ):
                                potential_matches.append(item)

                        if potential_matches:
                            menu_item = potential_matches[0]

                    if not menu_item:
                        # Fall back to database search if still not found
                        menu_item = self.db.find_similar_menu_item(item_name)

                    if menu_item:
                        # Check if the item is available
                        if getattr(menu_item, "is_available", 1) == 0:
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=f"I'm sorry, but {menu_item.name} is currently unavailable. Would you like to see other options in our menu?",
                                content_complete=True,
                                end_call=False,
                            )
                            return

                        add_ons = self.db.get_add_ons(menu_item.category)
                        if add_ons:
                            response_text = f"Great! I've added the {menu_item.name} to your order. "

                            # Group add-ons by type
                            addon_by_type = {}
                            for addon in add_ons:
                                addon_type = addon.type or "other"
                                if addon_type not in addon_by_type:
                                    addon_by_type[addon_type] = []
                                addon_by_type[addon_type].append(addon)

                            # Start with asking about size if available
                            if "size" in addon_by_type:
                                size_options = addon_by_type["size"]
                                response_text += "First, let's choose a size. "
                                if len(size_options) > 1:
                                    response_text += f"We have {', '.join([addon.name for addon in size_options[:-1]])}, and {size_options[-1].name}. "
                                else:
                                    response_text += (
                                        f"We offer {size_options[0].name}. "
                                    )
                                response_text += "Which size would you prefer?"
                            # If no size options, proceed to the next add-on type in sequence
                            elif "sauce" in addon_by_type:
                                sauce_options = addon_by_type["sauce"]
                                response_text += "Let's talk about sauce options. "
                                if len(sauce_options) > 1:
                                    response_text += f"We have {', '.join([addon.name for addon in sauce_options[:-1]])}, and {sauce_options[-1].name}. "
                                else:
                                    response_text += (
                                        f"We offer {sauce_options[0].name}. "
                                    )
                                response_text += "Which sauce would you like?"
                            # If no size or sauce options, proceed to toppings
                            elif "topping" in addon_by_type:
                                topping_options = addon_by_type["topping"]
                                response_text += (
                                    "You can add delicious toppings to your order. "
                                )
                                if len(topping_options) > 1:
                                    response_text += f"We have {', '.join([addon.name for addon in topping_options[:-1]])}, and {topping_options[-1].name}. "
                                else:
                                    response_text += (
                                        f"We offer {topping_options[0].name}. "
                                    )
                                response_text += "Would you like to add any toppings?"
                            else:
                                # If no add-ons by type, simply ask if they want anything else
                                response_text += (
                                    "Would you like to order anything else?"
                                )

                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=response_text,
                                content_complete=True,
                                end_call=False,
                            )
                        else:
                            yield ResponseResponse(
                                response_id=request.response_id,
                                content=f"Great! I've added the {menu_item.name} to your order. Would you like to order anything else?",
                                content_complete=True,
                                end_call=False,
                            )
                    else:
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content="I'm not sure I found that item on our menu. Let me show you what we have available.",
                            content_complete=True,
                            end_call=False,
                        )
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

    def verify_menu_item_function(self, params):
        item_name = params.get("item_name", "")
        category = params.get("category", None)

        # First try exact match
        menu_item = self.db.find_similar_menu_item(item_name, category)
        response = {"exists": False, "available": False, "similar_items": []}

        # If no exact match, try fuzzy matching
        if not menu_item:
            # Get all menu items and find potential matches
            all_menu_items = self.menu_items
            potential_matches = []

            for item in all_menu_items:
                # Skip items that aren't available
                if getattr(item, "is_available", 1) == 0:
                    continue

                # Check if category matches (if specified)
                if category and item.category.lower() != category.lower():
                    continue

                # Check if item name is in the query or query is in the item name
                if (
                    item.name.lower() in item_name.lower()
                    or item_name.lower() in item.name.lower()
                ):
                    potential_matches.append(item)

            # If we found potential matches, use the first one
            if potential_matches:
                menu_item = potential_matches[0]
                # Also populate similar items for the response
                response["similar_items"] = [
                    {
                        "id": item.id,
                        "name": item.name,
                        "category": item.category,
                        "base_price": item.base_price,
                        "is_available": getattr(item, "is_available", 1) == 1,
                    }
                    for item in potential_matches[:5]  # Limit to 5 suggestions
                ]

        if menu_item:
            response["exists"] = True
            response["menu_item"] = {
                "id": menu_item.id,
                "name": menu_item.name,
                "category": menu_item.category,
                "base_price": menu_item.base_price,
                "description": menu_item.description,
                "is_available": getattr(menu_item, "is_available", 1) == 1,
            }
            response["available"] = getattr(menu_item, "is_available", 1) == 1

            # Get add-ons by category and organize by type
            add_ons = self.db.get_add_ons(menu_item.category)
            addon_by_type = {}

            for addon in add_ons:
                addon_type = addon.type or "other"
                if addon_type not in addon_by_type:
                    addon_by_type[addon_type] = []

                addon_by_type[addon_type].append(
                    {
                        "id": addon.id,
                        "name": addon.name,
                        "price": addon.price,
                        "type": addon_type,
                        "is_available": getattr(addon, "is_available", 1) == 1,
                    }
                )

            # Order the add-on types: size first, then sauce, then toppings
            response["add_ons"] = {}
            type_order = ["size", "sauce", "topping", "other"]

            for addon_type in type_order:
                if addon_type in addon_by_type:
                    response["add_ons"][addon_type] = addon_by_type[addon_type]

        return response
