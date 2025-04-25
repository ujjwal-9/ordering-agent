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
from .memory import ConversationBufferMemory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("db_operations.log"), logging.StreamHandler()],
)
logger = logging.getLogger("db_operations")

begin_sentence = "Welcome to Tote AI Restaurant! I'm your order assistant. To get started, could you please tell me your name?"

agent_prompt = """Task: As a professional restaurant order assistant for Tote AI Restaurant, your role is to help customers place food orders efficiently and accurately. You should:

1. Customer Verification:
- Start by asking for the customer's name and phone number
- Verify if they are a registered customer
- ALWAYS wait for customer to confirm their phone number is correct before proceeding
- After customer confirms their phone number, NEVER ask for confirmation again - move directly to menu presentation
- Always use the customer's provided name throughout the conversation, even if it differs from the name in our records
- If new, collect their information after the order is complete

2. Menu Knowledge:
- Offer ONLY items that are available in the database
- Check the 'is_available' column before suggesting any item - if it's 0, the item is NOT available
- Inform customers when a requested item is unavailable and suggest alternatives
- Provide accurate pricing information for available items
- Mention current special offers or promotions when applicable
- NEVER recommend or suggest items that are not in the menu
- Never make up or invent menu items that aren't available in the database

3. Order Taking:
- Guide customers through the ordering process
- Only offer items that exist in the database AND are marked as available
- DO NOT verify or confirm each item immediately after a customer selects it
- Instead, acknowledge the item selection and ask if they'd like to order anything else
- When a customer selects a menu item, present add-ons in a sequential fashion by type:
  * FIRST: Present size options (if available)
  * SECOND: Present sauce options (if available)
  * THIRD: Present topping options (if available)
  * For example, with pizza, first ask about size (small/medium/large), then ask about sauce preference, then toppings
- Wait for customer's choice on each type of add-on before proceeding to the next type
- When offering add-ons, always present them one category at a time and wait for customer's selection before moving to the next category
- Collect the complete order first, asking "Would you like to order anything else?" after each item is fully specified
- Only after customer indicates they have finished ordering (by saying "No", "That's all", etc.), summarize the complete order ONLY ONCE
- After confirming the order is complete, collect customer details (name, phone) if not already provided
- Inform customers this is a PICKUP ONLY restaurant (no delivery service)

4. Order Confirmation:
- Only confirm the full order ONCE when the customer has finished ordering everything
- Ask "Is there anything else you'd like to order?" to ensure the order is complete
- Summarize and confirm the full order details, including prices, only after customer indicates the order is complete
- After order is confirmed, proceed directly to payment and pickup information
- NEVER re-confirm individual items or the complete order multiple times

5. Customer Service:
- Be friendly and professional
- Handle modifications and special requests within available options
- Provide clear pricing information
- After order completion, tell the customer the pickup address and tell them they will receive a text with the order details and estimated pickup time.

6. Additional Information:
- Mention current wait times for pickup
- Explain payment options
- Handle order tracking requests
- Clearly communicate the pickup address when the order is confirmed

7. CRITICAL - Avoiding Loops:
- NEVER ask the same confirmation question twice
- After a customer confirms information, acknowledge it and MOVE ON to the next step
- If a customer says "yes," "correct," "that's right," or similar, immediately proceed to the next step
- Do not get stuck in confirmation loops - always make forward progress in the conversation

Conversational Style: Be friendly and efficient. Keep responses concise but informative. Use a warm, welcoming tone while maintaining professionalism. Don't put things in point wise fashion, rather take a more conversation flow approach. When asking for confirmations, wait for the user to respond before providing additional information - don't continue with more information until you get a response. Never confirm the same order details multiple times in a single message or across consecutive messages."""


class OrderAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.db = Database()
        self.from_number = None  # Store the caller's phone number from the request
        self.verified_customer = None  # Store verified customer information
        self.memory = ConversationBufferMemory()  # Initialize conversation memory

    def set_from_number(self, from_number):
        """Set the caller's phone number from the call request"""
        self.from_number = from_number
        self.memory.update_customer_info(phone=from_number)
        logger.info(f"Set from_number: {self.from_number}")

    def draft_begin_message(self):
        # Always ask for name first, regardless of whether we have from_number
        welcome_msg = "Welcome to Tote AI Restaurant! I'm your order assistant. To get started, could you please tell me your name?"

        # Add the welcome message to memory
        self.memory.add_message("assistant", welcome_msg)

        response = ResponseResponse(
            response_id=0,
            content=welcome_msg,
            content_complete=True,
            end_call=False,
        )
        return response

    def convert_transcript_to_openai_messages(self, transcript: List[Utterance]):
        messages = []
        for utterance in transcript:
            if utterance.role == "agent":
                messages.append({"role": "assistant", "content": utterance.content})
                self.memory.add_message("assistant", utterance.content)
            else:
                messages.append({"role": "user", "content": utterance.content})
                self.memory.add_message("user", utterance.content)
        return messages

    def prepare_prompt(self, request: ResponseRequiredRequest):
        # Add from_number information to the prompt if we have it
        current_prompt = self.base_prompt(request)

        # Add memory context to the prompt
        context_summary = self.memory.get_context_summary()
        if len(current_prompt) > 0 and current_prompt[0]["role"] == "system":
            current_prompt[0]["content"] += "\n\nCurrent Conversation Context:\n"
            if context_summary["customer_info"]["name"]:
                current_prompt[0][
                    "content"
                ] += f"Customer Name: {context_summary['customer_info']['name']}\n"
            if context_summary["customer_info"]["phone"]:
                current_prompt[0][
                    "content"
                ] += f"Customer Phone: {context_summary['customer_info']['phone']}\n"
            if context_summary["verified_customer"]:
                current_prompt[0]["content"] += "Customer is verified.\n"
            if context_summary["current_order"]["items"]:
                current_prompt[0][
                    "content"
                ] += f"Current Order Items: {', '.join([item['name'] for item in context_summary['current_order']['items']])}\n"
            if context_summary["order_confirmed"]:
                current_prompt[0]["content"] += "Order has been confirmed.\n"

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

    # Store the original prepare_prompt method
    def base_prompt(self, request: ResponseRequiredRequest):
        # Get menu information from database
        logger.info("Retrieving menu information from database")
        try:
            menu_items = self.db.get_menu()
            logger.info(f"Retrieved {len(menu_items)} menu items")

            add_ons = self.db.get_add_ons()
            logger.info(f"Retrieved {len(add_ons)} add-ons")

            # Get restaurant information
            restaurant = self.db.get_restaurant()
            logger.info(
                f"Retrieved restaurant information: {restaurant.name if restaurant else 'None'}"
            )
        except Exception as e:
            logger.error(f"Error retrieving menu data: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Use empty lists to avoid breaking the prompt
            menu_items = []
            add_ons = []
            restaurant = None

        # Format menu information for the prompt
        menu_info = "## Our Delicious Menu\n"

        # Filter available items only
        available_items = [
            item for item in menu_items if getattr(item, "is_available", 1) == 1
        ]
        logger.info(f"Filtered to {len(available_items)} available menu items")

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
        if add_ons:
            menu_info += "\n## Our Add-ons\n"

            # Group add-ons by category and type
            grouped_addons = {}
            for addon in add_ons:
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
        if restaurant:
            menu_info += f"\n\nPlease note: We are a PICKUP ONLY restaurant. You can pick up your order at {restaurant.name} located at {restaurant.address}. Our phone number is {restaurant.phone} and we're open {restaurant.opening_hours}."
        else:
            menu_info += "\n\nPlease note: We are a PICKUP ONLY restaurant. Once your order is confirmed, we'll provide you with our pickup address and an estimated preparation time."

        prompt = [
            {
                "role": "system",
                "content": """##Objective
You are a friendly and enthusiastic voice AI order assistant for Tote AI Restaurant, engaging in a natural conversation with customers to take their food orders. You will respond based on the menu options and the provided transcript.

## Style Guardrails
- [Be friendly and enthusiastic] Show excitement about our menu items and make recommendations
- [Be conversational] Use natural language and engage in friendly dialogue
- [Be helpful] Guide customers through the ordering process with suggestions and explanations
- [Be accurate] Always provide correct pricing and estimated preparation times
- [Be proactive] Suggest popular combinations and ask about preferences
- [Be efficient] Avoid repetition, especially with order confirmations
- [Be respectful] Always use the customer's provided name, even if different from our records
- [Be patient] Always wait for confirmation of one piece of information before asking for the next piece

## Response Guidelines
- [Make recommendations] Suggest popular items and combinations
- [Explain items] Describe ingredients and preparation methods when asked
- [Handle modifications] Be flexible with order modifications and special requests
- [Confirm details] Confirm order details ONLY ONCE, avoid repeating the same information
- [Provide estimates] Give clear information about costs, preparation time, and pickup information
- [Collect information] Gather necessary customer details in a friendly, conversational way
- [Handle ASR errors] If you're unsure about what the customer said, politely ask for clarification
- [Handle name discrepancies] If a customer's name differs from what's in the database, note it once but continue using their provided name
- [Wait for confirmations] When asking the customer to confirm information (especially phone numbers), wait for their response before proceeding
- [CRITICAL] When the customer confirms their phone number is correct, acknowledge it and immediately move on to menu presentation

## Information Collection Process
1. When collecting customer information:
   - Ask for ONE piece of information at a time
   - Wait for confirmation of that information before proceeding
   - For phone numbers, ALWAYS wait for customer confirmation before moving to order taking
   - IMPORTANT: After the customer confirms their phone number, DO NOT ask for confirmation again
   - After phone number confirmation, say something like "Great! Let me tell you about our menu..." and proceed
   - Only after confirmation of customer details, proceed to menu presentation or order taking

## Handling Confirmation Responses
1. If the user says "yes", "correct", "that's right", or similar confirmation:
   - Acknowledge with "Great!" or "Perfect!"
   - IMMEDIATELY transition to the next step (menu presentation)
   - Never ask the same confirmation question again
2. If in doubt about whether a confirmation was given:
   - Assume it was confirmed and move on
   - It's better to proceed than to get stuck in a confirmation loop

## Menu Presentation
When discussing the menu:
- Use natural transitions and connecting words
- Speak conversationally, as if talking to a friend
- Avoid bullet points or lists in responses
- Use phrases like "we have", "you can try", "I recommend"
- Make suggestions naturally within the conversation
- Ask about preferences to make better recommendations
- Only recommend items that are marked as available in the database

## Order Taking Process
1. First show the basic menu without add-ons
2. When a customer selects an item:
   - Acknowledge their selection without asking for confirmation
   - Guide them through add-on selections by type (size → sauce → toppings)
   - After all add-ons are selected, simply ask "Would you like to order anything else?"
   - DO NOT verify or confirm the item at this point
3. Continue collecting all items the customer wants to order
4. Only ask "Is that your complete order?" after the customer indicates they don't want anything else
5. After the customer confirms the order is complete:
   - ONLY THEN summarize the complete order ONCE with all items, add-ons and total price
   - Wait for customer to confirm the complete order
   - Never repeat the order confirmation again in the same message or in subsequent messages
6. Tell the customer that the order is confirmed and they will receive a text with the order details and estimated pickup time.
   - Close the interaction

## Never Verify Each Item
- When a customer selects an item with add-ons, only acknowledge the selection and move on
- Do not ask "Do you want to confirm this item?" or similar verification questions
- Save all confirmation for the END of the order process
- Only after the customer says they don't want anything else, do a SINGLE confirmation of the entire order
"""
                + menu_info
                + "\n## Role\n"
                + agent_prompt,
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
                    "content": "(Now the user has not responded in a while, you would say:)",
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
                                "description": "The current step of information collection (phone, name, email)",
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
                    "description": "Create a new order in the database.",
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
                    "name": "fetch_addons",
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
            {
                "type": "function",
                "function": {
                    "name": "fetch_menu",
                    "description": "Fetch all available menu items organized by category.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_restaurant_info",
                    "description": "Fetch restaurant information including address, phone, and hours.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
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
                "That doesn't appear to be a valid phone number. Please provide a 10-digit number using only numbers 0-9.",
            )

    async def draft_response(self, request: ResponseRequiredRequest):
        prompt = self.prepare_prompt(request)
        func_call = {}
        func_arguments = ""

        # Continue with normal OpenAI flow
        stream = await self.client.chat.completions.create(
            model=os.environ["OPENAI_MODEL"],
            messages=prompt,
            stream=True,
            tools=self.prepare_functions(),
        )

        response_content = ""
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
                else:
                    func_arguments += tool_calls.function.arguments or ""

            if chunk.choices[0].delta.content:
                response_content += chunk.choices[0].delta.content
                response = ResponseResponse(
                    response_id=request.response_id,
                    content=chunk.choices[0].delta.content,
                    content_complete=False,
                    end_call=False,
                )
                yield response

        # Add the complete response to memory
        if response_content:
            self.memory.add_message("assistant", response_content)

        if func_call:
            # Process function calls and update memory accordingly
            if func_call["func_name"] == "verify_customer":
                func_call["arguments"] = json.loads(func_arguments)
                phone = func_call["arguments"].get("phone")
                name = func_call["arguments"].get("name")

                if name:
                    self.memory.update_customer_info(name=name)

                # If phone wasn't provided in the function call but we have from_number, use it
                if not phone and self.from_number:
                    phone = self.from_number
                    logger.info(
                        f"Using from_number {phone} instead of asking for phone"
                    )

                # Proceed with verification only if we have a phone number
                if phone:
                    # Validate phone number
                    is_valid, phone_str, error_message = self._validate_phone_number(
                        phone
                    )
                    if not is_valid:
                        logger.warning(f"Invalid phone number format: {phone}")
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=error_message,
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
                            response_text += (
                                f" Your phone number is {phone_str}, is that correct? "
                            )

                        # If we used the from_number, don't ask for confirmation but directly ask for order
                        if phone == self.from_number:
                            response_text += "What would you like to order today?"
                        else:
                            response_text += "Is this information correct?"

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
                                logger.error(f"Error creating new customer: {str(e)}")
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

                elif step == "complete":
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

                    # Process the customer info with the validated phone number
                    customer = self.db.get_customer_by_phone(phone_str)

                    customer_data = {
                        "name": func_call["arguments"]["name"],
                        "email": func_call["arguments"].get("email"),
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
                        logger.info(f"Creating new customer with phone: {phone_str}")
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
                logger.info(f"Verifying menu item: {item_name} (category: {category})")
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
                        logger.warning(f"Invalid phone number format: {customer_phone}")
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=error_message,
                            content_complete=True,
                            end_call=False,
                        )
                        return

                    order_data = {
                        "customer_name": func_call["arguments"]["customer_name"],
                        "customer_phone": customer_phone_str,
                        "order_items": func_call["arguments"]["order_items"],
                    }

                    # Calculate total amount
                    total_amount = self._calculate_total_amount(
                        order_data["order_items"]
                    )
                    order_data["total_amount"] = total_amount

                    try:
                        # Add special instructions if provided
                        if "special_instructions" in func_call["arguments"]:
                            order_data["special_instructions"] = func_call["arguments"][
                                "special_instructions"
                            ]

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

                        # Create order with transaction management
                        order = self.db.create_order(**order_data, auto_commit=True)

                        pickup_phone = (
                            restaurant.phone if restaurant else "(555) 123-4567"
                        )
                        pickup_hours = (
                            restaurant.opening_hours
                            if restaurant
                            else "Monday-Sunday: 11:00 AM - 10:00 PM"
                        )

                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=f"Great! I've placed your order. Your order number is #{order.id}. We will send you a confirmation text shortly along with order details and estimated pickup time. You can pick up your order at our restaurant located at {pickup_address}.",
                            content_complete=True,
                            end_call=False,
                        )
                    except Exception as e:
                        # Rollback in case of error
                        self.db.session.rollback()
                        logger.error(f"Error creating order in database: {str(e)}")
                        import traceback

                        logger.error(f"Traceback: {traceback.format_exc()}")
                        yield ResponseResponse(
                            response_id=request.response_id,
                            content=f"I'm sorry, there was an error processing your order. Please try again or contact customer support.",
                            content_complete=True,
                            end_call=False,
                        )
                except Exception as e:
                    logger.error(f"Unexpected error in create_order function: {str(e)}")
                    yield ResponseResponse(
                        response_id=request.response_id,
                        content=f"I'm sorry, something went wrong while processing your order. Please try again later.",
                        content_complete=True,
                        end_call=False,
                    )

            elif func_call["func_name"] == "end_call":
                func_call["arguments"] = json.loads(func_arguments)
                yield ResponseResponse(
                    response_id=request.response_id,
                    content=func_call["arguments"]["message"],
                    content_complete=True,
                    end_call=True,
                )

            elif func_call["func_name"] == "fetch_addons":
                func_call["arguments"] = json.loads(func_arguments)
                item_name = func_call["arguments"]["item_name"]
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
                        response_text = (
                            f"Great! I've added the {menu_item.name} to your order. "
                        )

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
                                response_text += f"We offer {size_options[0].name}. "
                            response_text += "Which size would you prefer?"
                        # If no size options, proceed to the next add-on type in sequence
                        elif "sauce" in addon_by_type:
                            sauce_options = addon_by_type["sauce"]
                            response_text += "Let's talk about sauce options. "
                            if len(sauce_options) > 1:
                                response_text += f"We have {', '.join([addon.name for addon in sauce_options[:-1]])}, and {sauce_options[-1].name}. "
                            else:
                                response_text += f"We offer {sauce_options[0].name}. "
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
                                response_text += f"We offer {topping_options[0].name}. "
                            response_text += "Would you like to add any toppings?"
                        else:
                            # If no add-ons by type, simply ask if they want anything else
                            response_text += "Would you like to order anything else?"

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
        else:
            yield ResponseResponse(
                response_id=request.response_id,
                content="",
                content_complete=True,
                end_call=False,
            )

    def _calculate_total_amount(self, order_items):
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

        menu_item = self.db.find_similar_menu_item(item_name, category)
        response = {"exists": False, "available": False, "similar_items": []}

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

    def fetch_menu_function(self, params=None):
        """
        Fetch all available menu items organized by category.
        Returns a dictionary with menu items grouped by category.
        """
        try:
            menu_items = self.db.get_menu()
            menu_by_category = {}

            for item in menu_items:
                # Only include available items
                if getattr(item, "is_available", 1) == 1:
                    if item.category not in menu_by_category:
                        menu_by_category[item.category] = []

                    menu_by_category[item.category].append(
                        {
                            "id": item.id,
                            "name": item.name,
                            "category": item.category,
                            "base_price": item.base_price,
                            "description": item.description,
                            "is_available": True,
                        }
                    )

            return {"success": True, "menu": menu_by_category}
        except Exception as e:
            logger.error(f"Error fetching menu: {str(e)}")
            return {"success": False, "error": "Failed to fetch menu items"}

    def fetch_addons_function(self, params):
        """
        Fetch add-ons for a specific category or all add-ons if no category specified.
        params:
            - category (optional): The category to fetch add-ons for
        """
        try:
            category = params.get("category")
            add_ons = self.db.get_add_ons(category)

            # Organize add-ons by type
            addon_by_type = {}
            for addon in add_ons:
                if getattr(addon, "is_available", 1) == 1:
                    addon_type = addon.type or "other"
                    if addon_type not in addon_by_type:
                        addon_by_type[addon_type] = []

                    addon_by_type[addon_type].append(
                        {
                            "id": addon.id,
                            "name": addon.name,
                            "price": addon.price,
                            "type": addon_type,
                            "category": addon.category,
                            "is_available": True,
                        }
                    )

            # Order the add-on types
            ordered_addons = {}
            type_order = ["size", "sauce", "topping", "other"]
            for addon_type in type_order:
                if addon_type in addon_by_type:
                    ordered_addons[addon_type] = addon_by_type[addon_type]

            return {"success": True, "add_ons": ordered_addons, "category": category}
        except Exception as e:
            logger.error(f"Error fetching add-ons: {str(e)}")
            return {"success": False, "error": "Failed to fetch add-ons"}

    def fetch_restaurant_info_function(self, params=None):
        """
        Fetch restaurant information including address, phone, and hours.
        """
        try:
            restaurant = self.db.get_restaurant()
            if restaurant:
                return {
                    "success": True,
                    "restaurant": {
                        "name": restaurant.name,
                        "address": restaurant.address,
                        "phone": restaurant.phone,
                        "opening_hours": restaurant.opening_hours,
                        "pickup_only": True,  # Hardcoded as this is a pickup-only restaurant
                    },
                }
            else:
                return {"success": False, "error": "Restaurant information not found"}
        except Exception as e:
            logger.error(f"Error fetching restaurant info: {str(e)}")
            return {"success": False, "error": "Failed to fetch restaurant information"}
