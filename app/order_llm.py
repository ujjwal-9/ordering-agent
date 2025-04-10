from openai import AsyncOpenAI
import os
import json
from .custom_types import (
    ResponseRequiredRequest,
    ResponseResponse,
    Utterance,
)
from typing import List
from .database import Database

begin_sentence = "Welcome to Tote AI Restaurant! I'm your virtual order assistant. To get started, could you please tell me your name?"

agent_prompt = """Task: As a professional restaurant order assistant for Tote AI Restaurant, your role is to help customers place food orders efficiently and accurately. You should:

1. Customer Verification:
- Start by asking for the customer's name and phone number
- Verify if they are a registered customer
- If registered, confirm their information and proceed with ordering
- If new, collect their information after the order is complete

2. Menu Knowledge:
- Offer burgers and pizzas with their add-ons
- Provide accurate pricing information
- Mention current special offers or promotions

3. Order Taking:
- Guide customers through the ordering process
- Confirm item selections and add-ons
- Ask for any special instructions or preferences
- Collect customer details (name, phone, delivery address)
- Provide estimated preparation and delivery times

4. Customer Service:
- Be friendly and professional
- Handle modifications and special requests
- Provide clear pricing information
- Confirm order details before finalizing

5. Additional Information:
- Mention current wait times
- Inform about delivery radius and minimum order amounts
- Explain payment options
- Handle order tracking requests

Conversational Style: Be friendly and efficient. Keep responses concise but informative. Use a warm, welcoming tone while maintaining professionalism.

Personality: Be helpful and attentive, but also efficient in taking orders. Show enthusiasm about the menu items while maintaining a professional demeanor."""


class LlmClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.db = Database()

    def draft_begin_message(self):
        response = ResponseResponse(
            response_id=0,
            content=begin_sentence,
            content_complete=True,
            end_call=False,
        )
        return response

    def convert_transcript_to_openai_messages(self, transcript: List[Utterance]):
        messages = []
        for utterance in transcript:
            if utterance.role == "agent":
                messages.append({"role": "assistant", "content": utterance.content})
            else:
                messages.append({"role": "user", "content": utterance.content})
        return messages

    def prepare_prompt(self, request: ResponseRequiredRequest):
        # Get menu information from database
        menu_items = self.db.get_menu()
        add_ons = self.db.get_add_ons()

        # Format menu information for the prompt
        menu_info = "## Our Delicious Menu\n"

        # Group items by category
        categories = {}
        for item in menu_items:
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

        menu_info += (
            "\nEverything is prepared fresh to order. What would you like to try today?"
        )

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

## Response Guidelines
- [Make recommendations] Suggest popular items and combinations
- [Explain items] Describe ingredients and preparation methods when asked
- [Handle modifications] Be flexible with order modifications and special requests
- [Confirm details] Always confirm order details, including add-ons and special instructions
- [Provide estimates] Give clear information about costs, preparation time, and delivery estimates
- [Collect information] Gather necessary customer details in a friendly, conversational way
- [Handle ASR errors] If you're unsure about what the customer said, politely ask for clarification

## Menu Presentation
When discussing the menu:
- Use natural transitions and connecting words
- Speak conversationally, as if talking to a friend
- Avoid bullet points or lists in responses
- Use phrases like "we have", "you can try", "I recommend"
- Make suggestions naturally within the conversation
- Ask about preferences to make better recommendations

## Order Taking Process
1. First show the basic menu without add-ons
2. When a customer selects an item:
   - Confirm their selection enthusiastically
   - Naturally introduce available add-ons
   - Ask if they'd like any customizations
3. After add-ons are selected:
   - Confirm the complete item with add-ons
   - Ask if they'd like to order anything else
4. Repeat for each item in the order

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
                            "name": {
                                "type": "string",
                                "description": "The name of the customer",
                            },
                            "phone": {
                                "type": "string",
                                "description": "The phone number of the customer",
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
                                "description": "The current step of information collection (phone, name, address, email, payment_method, dietary_preferences)",
                            },
                            "phone": {
                                "type": "string",
                                "description": "The phone number of the customer",
                            },
                            "name": {
                                "type": "string",
                                "description": "The name of the customer",
                            },
                            "address": {
                                "type": "string",
                                "description": "The delivery address",
                            },
                            "email": {
                                "type": "string",
                                "description": "The customer's email address",
                            },
                            "preferred_payment_method": {
                                "type": "string",
                                "description": "The customer's preferred payment method",
                            },
                            "dietary_preferences": {
                                "type": "string",
                                "description": "Any dietary preferences or restrictions",
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
                                "type": "string",
                                "description": "The phone number of the customer",
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
                                "type": "string",
                                "description": "The phone number of the customer",
                            },
                            "delivery_address": {
                                "type": "string",
                                "description": "The delivery address",
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
                            "delivery_address",
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

    async def draft_response(self, request: ResponseRequiredRequest):
        prompt = self.prepare_prompt(request)
        func_call = {}
        func_arguments = ""
        stream = await self.client.chat.completions.create(
            model=os.environ["OPENAI_MODEL"],
            messages=prompt,
            stream=True,
            tools=self.prepare_functions(),
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
                else:
                    func_arguments += tool_calls.function.arguments or ""

            if chunk.choices[0].delta.content:
                response = ResponseResponse(
                    response_id=request.response_id,
                    content=chunk.choices[0].delta.content,
                    content_complete=False,
                    end_call=False,
                )
                yield response

        if func_call:
            if func_call["func_name"] == "verify_customer":
                func_call["arguments"] = json.loads(func_arguments)
                name = func_call["arguments"]["name"]
                phone = func_call["arguments"]["phone"]
                customer = self.db.get_customer_by_phone(phone)

                if customer:
                    response_text = f"Welcome back, {customer.name}! I found your information in our records. "
                    response_text += f"Your phone number is {customer.phone}, and your delivery address is {customer.address}. "

                    # Only include optional fields if they exist and have values
                    try:
                        if (
                            hasattr(customer, "preferred_payment_method")
                            and customer.preferred_payment_method
                        ):
                            response_text += f"Your preferred payment method is {customer.preferred_payment_method}. "
                    except:
                        pass

                    try:
                        if (
                            hasattr(customer, "dietary_preferences")
                            and customer.dietary_preferences
                        ):
                            response_text += f"Your dietary preferences are {customer.dietary_preferences}. "
                    except:
                        pass

                    try:
                        if hasattr(customer, "total_orders"):
                            response_text += f"\nYou've placed {customer.total_orders} orders with us. "
                    except:
                        pass

                    response_text += "Is this information correct?"

                    response = ResponseResponse(
                        response_id=request.response_id,
                        content=response_text,
                        content_complete=True,
                        end_call=False,
                    )
                    yield response
                else:
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content=f"Nice to meet you, {name}! I don't have your information in our records yet. Let's start with your order, and I'll collect your delivery address at the end. What would you like to order today?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

            elif func_call["func_name"] == "collect_customer_info":
                func_call["arguments"] = json.loads(func_arguments)
                step = func_call["arguments"]["step"]

                if step == "name":
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="What is your name?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

                elif step == "address":
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="What is your delivery address?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

                elif step == "email":
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="Would you like to provide an email address for order updates? (optional)",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

                elif step == "payment_method":
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="What is your preferred payment method? (cash, credit card, or digital payment)",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

                elif step == "dietary_preferences":
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="Do you have any dietary preferences or restrictions? (e.g., vegetarian, no-pork, etc.)",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

                elif step == "complete":
                    # Create or update customer with all collected information
                    customer = self.db.get_customer_by_phone(
                        func_call["arguments"]["phone"]
                    )
                    if customer:
                        customer = self.db.update_customer(
                            func_call["arguments"]["phone"],
                            name=func_call["arguments"]["name"],
                            address=func_call["arguments"]["address"],
                            email=func_call["arguments"].get("email"),
                            preferred_payment_method=func_call["arguments"].get(
                                "preferred_payment_method"
                            ),
                            dietary_preferences=func_call["arguments"].get(
                                "dietary_preferences"
                            ),
                        )
                    else:
                        customer = self.db.create_customer(
                            name=func_call["arguments"]["name"],
                            phone=func_call["arguments"]["phone"],
                            address=func_call["arguments"]["address"],
                            email=func_call["arguments"].get("email"),
                            preferred_payment_method=func_call["arguments"].get(
                                "preferred_payment_method"
                            ),
                            dietary_preferences=func_call["arguments"].get(
                                "dietary_preferences"
                            ),
                        )

                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="Thank you for providing your information. What would you like to order today?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

            elif func_call["func_name"] == "get_order_history":
                func_call["arguments"] = json.loads(func_arguments)
                phone = func_call["arguments"]["phone"]
                orders = self.db.get_customer_order_history(phone)
                if orders:
                    response_text = "Here's your order history:\n\n"
                    for order in orders[:5]:  # Show last 5 orders
                        response_text += f"Order #{order.id} ({order.created_at.strftime('%Y-%m-%d')}):\n"
                        response_text += f"- Status: {order.status}\n"
                        response_text += f"- Total: ${order.total_amount:.2f}\n"
                        response_text += f"- Items: {', '.join([item['item_name'] for item in order.order_items])}\n\n"
                    if len(orders) > 5:
                        response_text += f"... and {len(orders) - 5} more orders."

                    response = ResponseResponse(
                        response_id=request.response_id,
                        content=response_text,
                        content_complete=True,
                        end_call=False,
                    )
                    yield response
                else:
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="I don't see any previous orders in your history. Would you like to place an order?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

            elif func_call["func_name"] == "verify_menu_item":
                func_call["arguments"] = json.loads(func_arguments)
                item_name = func_call["arguments"]["item_name"]
                category = func_call["arguments"].get("category")
                similar_item = self.db.find_similar_menu_item(item_name, category)
                if similar_item:
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content=f"I found a similar item: {similar_item.name} (${similar_item.base_price:.2f}). Would you like to order this instead?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response
                else:
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="I couldn't find that item on our menu. Would you like to see our available options?",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response

            elif func_call["func_name"] == "create_order":
                func_call["arguments"] = json.loads(func_arguments)
                order = self.db.create_order(
                    customer_name=func_call["arguments"]["customer_name"],
                    customer_phone=func_call["arguments"]["customer_phone"],
                    delivery_address=func_call["arguments"]["delivery_address"],
                    order_items=func_call["arguments"]["order_items"],
                    total_amount=self._calculate_total_amount(
                        func_call["arguments"]["order_items"]
                    ),
                )
                response = ResponseResponse(
                    response_id=request.response_id,
                    content=f"Great! I've placed your order. Your order number is #{order.id}. Estimated preparation time is {order.estimated_preparation_time} minutes. Is there anything else you need?",
                    content_complete=True,
                    end_call=False,
                )
                yield response

            elif func_call["func_name"] == "end_call":
                func_call["arguments"] = json.loads(func_arguments)
                response = ResponseResponse(
                    response_id=request.response_id,
                    content=func_call["arguments"]["message"],
                    content_complete=True,
                    end_call=True,
                )
                yield response

            elif func_call["func_name"] == "get_item_addons":
                func_call["arguments"] = json.loads(func_arguments)
                item_name = func_call["arguments"]["item_name"]
                menu_item = self.db.find_similar_menu_item(item_name)
                if menu_item:
                    add_ons = self.db.get_add_ons(menu_item.category)
                    if add_ons:
                        response_text = f"Excellent choice! The {menu_item.name} is one of our favorites. "
                        response_text += (
                            "You can make it even better with some delicious add-ons. "
                        )
                        response_text += f"We have {', '.join([addon.name for addon in add_ons[:-1]])}, and {add_ons[-1].name}. "
                        response_text += f"Each add-on is just ${add_ons[0].price:.2f}. Would you like to add any of these to your order?"

                        response = ResponseResponse(
                            response_id=request.response_id,
                            content=response_text,
                            content_complete=True,
                            end_call=False,
                        )
                        yield response
                    else:
                        response = ResponseResponse(
                            response_id=request.response_id,
                            content=f"Perfect choice! The {menu_item.name} is delicious as is. Would you like to order anything else?",
                            content_complete=True,
                            end_call=False,
                        )
                        yield response
                else:
                    response = ResponseResponse(
                        response_id=request.response_id,
                        content="I'm not sure I found that item on our menu. Let me show you what we have available.",
                        content_complete=True,
                        end_call=False,
                    )
                    yield response
        else:
            response = ResponseResponse(
                response_id=request.response_id,
                content="",
                content_complete=True,
                end_call=False,
            )
            yield response

    def _calculate_total_amount(self, order_items):
        total = 0
        for item in order_items:
            menu_item = self.db.find_similar_menu_item(item["item_name"])
            if menu_item:
                total += menu_item.base_price * item["quantity"]
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
