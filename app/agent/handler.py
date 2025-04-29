import logging
from typing import Dict, Any, Generator, Optional
import json
import os
from openai import AsyncOpenAI
from .prompts import CONFIRMATION_AGENT_PROMPT, MENU_AGENT_PROMPT, SIMILAR_ITEMS_PROMPT
from ..custom_types import ResponseResponse
from .utils import validate_phone_number, calculate_total_amount, format_addon_response

logger = logging.getLogger("openai_tool_calls")

TOOL_PROMPT = {
    "verify_customer": CONFIRMATION_AGENT_PROMPT,
    "create_customer": CONFIRMATION_AGENT_PROMPT,
    "verify_order_item": MENU_AGENT_PROMPT,
    "fetch_menu_categories": MENU_AGENT_PROMPT,
    "fetch_items_for_category": MENU_AGENT_PROMPT,
    "fetch_complete_menu": MENU_AGENT_PROMPT,
    "fetch_addons": MENU_AGENT_PROMPT,
}


class ToolHandler:
    def __init__(self, db, memory):
        self.db = db
        self.memory = memory
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    async def _find_similar_items_with_openai(
        self, item_name: str, all_items: list
    ) -> list:
        """
        Use OpenAI to find similar menu items based on the item name.

        Args:
            item_name: The name of the item to match
            all_items: List of all menu items

        Returns:
            List of similar menu items with their details
        """
        try:
            # Convert menu items to a simple format for the prompt
            menu_items_str = "\n".join(
                [f"{item.name} ({item.category})" for item in all_items]
            )

            # Create the prompt for OpenAI
            prompt = SIMILAR_ITEMS_PROMPT(item_name, menu_items_str)
            print("********************* SIMILAR ITEMS PROMPT *********************")
            print(prompt)
            print("***************************************************************")
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL"),
                messages=[{"role": "assistant", "content": prompt}],
                temperature=0.2,
            )
            print("********************* SIMILAR ITEMS RESPONSE *********************")
            print(response.choices[0].message.content)
            print("***************************************************************")

            # Parse the JSON response
            response_content = response.choices[0].message.content
            similar_items_data = json.loads(response_content)

            # Map the similar items to our menu items
            similar_items = []
            for item_data in similar_items_data.get("similar_items", []):
                # Find the actual menu item object
                for menu_item in all_items:
                    if (
                        menu_item.name.lower() == item_data["name"].lower()
                        and menu_item.category.lower() == item_data["category"].lower()
                    ):
                        similar_items.append(
                            {
                                "id": menu_item.id,
                                "name": menu_item.name,
                                "category": menu_item.category,
                                "base_price": menu_item.base_price,
                                "description": menu_item.description,
                                "is_available": getattr(menu_item, "is_available", 1)
                                == 1,
                                "reason": item_data.get("reason", "Similar item"),
                            }
                        )
                        break

            return similar_items

        except Exception as e:
            logger.error(f"Error using OpenAI to find similar items: {str(e)}")
            return []

    def verify_customer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify if a customer exists and get their details.
        Does not create a new customer, only verifies if the phone number exists.
        """
        try:
            phone = params.get("phone")
            name = params.get("name")

            if not phone:
                return {
                    "success": False,
                    "error": "Phone number is required",
                    "exists": False,
                }

            customer = self.db.get_customer_by_phone(phone)

            if customer:
                return {
                    "success": True,
                    "exists": True,
                    "customer": {
                        "id": customer.id,
                        "name": customer.name,
                        "phone": customer.phone,
                    },
                }
            else:
                return {
                    "success": True,
                    "exists": False,
                    "phone": phone,
                }

        except Exception as e:
            logger.error(f"Error verifying customer: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to verify customer: {str(e)}",
                "exists": False,
            }

    def create_customer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new customer after phone verification.

        Args:
            params: Dictionary containing 'phone' and 'name'

        Returns:
            Dictionary with success status and customer details if successful
        """
        try:
            phone = params.get("phone")
            name = params.get("name")

            if not phone:
                return {
                    "success": False,
                    "error": "Phone number is required",
                }

            if not name:
                return {
                    "success": False,
                    "error": "Customer name is required",
                }

            # Check if customer already exists
            existing_customer = self.db.get_customer_by_phone(phone)
            if existing_customer:
                return {
                    "success": False,
                    "error": "Customer with this phone number already exists",
                    "customer": {
                        "id": existing_customer.id,
                        "name": existing_customer.name,
                        "phone": existing_customer.phone,
                    },
                }

            # Create the new customer
            customer_data = {"name": name, "phone": phone}
            new_customer = self.db.create_customer(**customer_data, auto_commit=True)

            return {
                "success": True,
                "customer": {
                    "id": new_customer.id,
                    "name": new_customer.name,
                    "phone": new_customer.phone,
                },
                "message": "Customer created successfully",
            }

        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create customer: {str(e)}",
            }

    async def verify_order_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify if a order item exists and get its details.
        """
        item_name = params.get("item_name", "")
        category = params.get("category", None)
        add_ons = params.get("add_ons", [])

        menu_item = self.db.find_similar_menu_item(item_name, category)
        response = {"exists": False, "available": False, "similar_items": []}

        # If exact match not found, use OpenAI to find similar items
        if not menu_item:
            # Get all menu items for comparison
            all_menu_items = self.db.get_menu()
            # Use OpenAI to find similar items
            similar_items = await self._find_similar_items_with_openai(
                item_name, all_menu_items
            )
            response["similar_items"] = similar_items
        else:
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

            # Get add-ons by category
            available_add_ons = self.db.get_add_ons(menu_item.category)

            for addon in add_ons:
                if addon in available_add_ons:
                    response["add_ons"].append(
                        {
                            "id": addon.id,
                            "name": addon.name,
                            "price": addon.price,
                            "type": addon.type,
                        }
                    )
        return response

    def fetch_menu_categories(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Fetch all available menu categories.
        """
        try:
            menu_items = self.db.get_menu()
            categories = set()

            for item in menu_items:
                # Only consider categories of available items
                if getattr(item, "is_available", 1) == 1:
                    categories.add(item.category)

            return {"success": True, "categories": sorted(list(categories))}
        except Exception as e:
            logger.error(f"Error fetching menu categories: {str(e)}")
            return {"success": False, "error": "Failed to fetch menu categories"}

    def fetch_items_for_category(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch all available menu items for a specific category.

        Args:
            params: Dictionary containing 'category'

        Returns:
            Dictionary with success status and menu items for the specified category
        """
        try:
            category = params.get("category")

            if not category:
                return {"success": False, "error": "Category is required", "items": []}

            # Get all menu items
            all_menu_items = self.db.get_menu()

            # Filter menu items by category
            category_items = [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "base_price": item.base_price,
                    "description": item.description,
                    "is_available": getattr(item, "is_available", 1) == 1,
                }
                for item in all_menu_items
                if item.category.lower() == category.lower()
                and getattr(item, "is_available", 1) == 1
            ]

            return {"success": True, "category": category, "items": category_items}

        except Exception as e:
            logger.error(f"Error fetching items for category: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch menu items: {str(e)}",
                "items": [],
            }

    def fetch_complete_menu(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Fetch all available menu items organized by category.
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

    def fetch_addons(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch add-ons for a specific category or all add-ons if no category specified.
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

    def fetch_restaurant_info(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
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

    def create_prompt(
        self,
        tool_call: Dict[str, Any],
        result: Dict[str, Any],
        agent_prompt: str,
    ) -> str:
        """
        Create a prompt for the OpenAI API.
        """
        prompt = f"""
        # GUIDELINES AND GUARDRAILS
        {agent_prompt}

        Here is the infomation, you have to make presentable for customer as per above guidelines and guardrails.
        {result}
        """
        return [{"role": "system", "content": prompt}]

    def specs_create_prompt(
        self,
        tool_call: Dict[str, Any],
        result: Dict[str, Any],
    ) -> str:
        """
        Create a prompt for the OpenAI API.
        """
        SKIP_NEXT = False
        prompt = []
        # Get messages from memory instead of iterating directly
        for i, conversation in enumerate(self.memory.get_conversation_history()):
            if SKIP_NEXT:
                SKIP_NEXT = False
                continue
            if conversation["tool_calls"] and self.memory.get_memory_size() > (i + 1):
                message_n = self.memory.get_nth_messages(i + 1)
                if (
                    message_n.role == "tool"
                    and message_n.tool_call_id == conversation.tool_calls[0]["id"]
                ):
                    prompt.append(
                        {
                            "role": conversation["role"],
                            "content": conversation["content"],
                            "tool_calls": conversation["tool_calls"],
                        }
                    )
                else:
                    SKIP_NEXT = True
                    del self.memory.messages[i]
            else:
                prompt.append(
                    {
                        "role": conversation["role"],
                        "content": conversation["content"],
                        "tool_calls": conversation["tool_calls"],
                    }
                )
        prompt.append(
            {"role": "tool", "tool_call_id": tool_call["id"], "content": str(result)}
        )
        print("********************* SPECS PROMPT *********************")
        print(prompt)
        print("*************************************************")
        return prompt

    async def process_function_call(
        self,
        tool_call: Dict[str, Any],
        response_id: int,
        from_number: Optional[str] = None,
        memory=None,
    ) -> Generator[ResponseResponse, None, None]:
        """
        Process a function call from the agent and yield appropriate responses.

        Args:
            func_call: Dictionary containing function call details and arguments
            response_id: The response ID to use in response objects
            from_number: The caller's phone number, if available
            memory: Optional memory instance to update with customer info

        Yields:
            ResponseResponse objects based on the function call

        Flow of execution when handling an OpenAI function call:
        1. OpenAI API identifies a function to call based on user input
        2. This method receives the function name and arguments from tool_call
        3. The appropriate handler method is called based on func_name
        4. The result from the handler method is processed into a response
        5. If RUN_TOOLS is True, results are added directly to memory and conversation
        6. If RUN_CLIENT["run"] is True (for certain tools), the response is formatted using the create_prompt method
        7. Otherwise, another OpenAI API call is made to generate a natural language response based on the tool result
        8. The response is added to memory and yielded back as a ResponseResponse
        9. For special cases like end_call, specific behavior is implemented
        """
        logger.info(f"Processing: {tool_call}")
        func_name = tool_call["func_name"]
        arguments = tool_call["arguments"]
        RUN_CLIENT = {
            "tool": func_name,
            "run": False,
        }
        self.memory.tool_chain.append(func_name)

        # Handle verify_customer function
        if func_name == "verify_customer":
            phone = arguments.get("phone", from_number)
            name = arguments.get("name")

            # Update memory with customer name if available
            self.memory.update_customer_info(name=name)

            if phone:
                is_valid, phone_str, error_message = validate_phone_number(phone)
                if not is_valid:
                    yield ResponseResponse(
                        response_id=response_id,
                        content=error_message,
                        content_complete=True,
                        end_call=False,
                    )

                result = self.verify_customer({"phone": phone_str, "name": name})

                if not result["success"]:
                    response_text = "I'm having trouble verifying your information. Could you please try again?"

                if result["exists"]:
                    # Customer exists - proceed with order
                    customer = result["customer"]
                    provided_name = name or customer["name"]

                    # Update memory with customer info if available
                    if self.memory and not self.memory.customer_info["name"]:
                        self.memory.update_customer_info(
                            name=provided_name, phone=phone_str
                        )
                    response_text = f"Welcome back, {provided_name}! What would you like to order today?"

                else:
                    # Customer doesn't exist - ask to verify number
                    # If name provided, store it in memory for later
                    if name and self.memory:
                        self.memory.update_customer_info(name=name)

                    phone_formatted = phone_str  # You may want to format the phone number for better readability
                    # Add the response text to memory
                    response_text = f"I don't see your number in our system. I have your phone number as {phone_formatted}, is that correct?"

        # Handle create_customer function
        elif func_name == "create_customer":
            phone = arguments.get("phone", from_number)
            name = arguments.get("name")

            # Validate phone number
            is_valid, phone_str, error_message = validate_phone_number(phone)
            if not is_valid:
                yield ResponseResponse(
                    response_id=response_id,
                    content=error_message,
                    content_complete=True,
                    end_call=False,
                )
                return

            # Update memory with customer info
            if self.memory:
                self.memory.update_customer_info(name=name, phone=phone_str)

            result = self.create_customer({"phone": phone_str, "name": name})

            if result["success"]:
                response_text = f"Thank you, {name}! I've registered you as a new customer. What would you like to order today?"
            else:
                if "customer" in result:
                    response_text = (
                        f"Thank you, {name}! What would you like to order today?"
                    )
                else:
                    # Error creating customer
                    response_text = "I'm having trouble registering your information. Could you please try again with your name and phone number?"

        # Handle verify_order_item function
        elif func_name == "verify_order_item":
            result = await self.verify_order_item(arguments)
            if result["exists"] and result["available"]:
                response_text = f"I found {result['menu_item']['name']}. Would you like to order this?"
            elif result["similar_items"]:
                response_text = str(result["similar_items"])
            else:
                response_text = "I couldn't find that item on our menu. Would you like to see our available options?"

        # Handle create_order function
        elif func_name == "create_order":
            try:
                customer_phone = self.memory.customer_info["phone"]
                order_data = {
                    "customer_name": arguments["customer_name"],
                    "customer_phone": customer_phone,
                    "order_items": arguments["order_items"],
                    "total_amount": calculate_total_amount(
                        arguments["order_items"], self.db
                    ),
                }

                if "special_instructions" in arguments:
                    order_data["special_instructions"] = arguments[
                        "special_instructions"
                    ]

                order = self.db.create_order(**order_data, auto_commit=True)
                restaurant = self.db.get_restaurant()
                pickup_address = restaurant.address if restaurant else "our restaurant"
                response_text = f"Great! I've placed your order. Your order number is #{order.id}. We will send you a confirmation text shortly along with order details and estimated pickup time. You can pick up your order at {pickup_address}."
            except Exception as e:
                logger.error(f"Error creating order: {str(e)}")
                response_text = "I'm sorry, there was an error processing your order. Please try again or contact customer support."

        # Handle fetch_menu_categories function
        elif func_name == "fetch_menu_categories":
            result = self.fetch_menu_categories()
            if result["success"]:
                prompt = [
                    {
                        "role": "system",
                        "content": f"""
## Style Guardrails
- [Be friendly and enthusiastic] Show excitement about our menu items and make recommendations
- [Be conversational] Use natural language and engage in friendly dialogue, Dont use any special characters or markdown
- [Be helpful] Guide customers through the ordering process with suggestions and explanations]
- [Be concise] Dont use long sentences, use short and concise sentences, but still keep it engaging and friendly

## Conversation History
{self.memory.get_conversation_history()}

## Instructions
You are given a list of categories and you have to present them in a way that is easy to understand for a customer.

## Here is the list of categories:
{result["categories"]}
                """,
                    }
                ]
                print("********************* CATEGORIES PROMPT *********************")
                print(prompt)
                print("*************************************************")
                response = await self.client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL"),
                    messages=prompt,
                    temperature=0.2,
                )
                response_text = response.choices[0].message.content
                print("********************* CATEGORIES *********************")
                print(response_text)
                print("*************************************************")
                RUN_CLIENT["run"] = True
            else:
                response_text = "I'm having trouble accessing our menu categories right now. Please try again in a moment."

        # Handle fetch_items_for_category function
        elif func_name == "fetch_items_for_category":
            result = self.fetch_items_for_category(arguments)
            if result["success"]:
                category_name = result["category"].title()
                menu_items = result["items"]

                if menu_items:
                    prompt = [
                        {
                            "role": "system",
                            "content": f"""
## Style Guardrails
- [Be friendly and enthusiastic] Show excitement about our menu items and make recommendations
- [Be conversational] Use natural language and engage in friendly dialogue, Dont use any special characters or markdown
- [Be helpful] Guide customers through the ordering process with suggestions and explanations]
- [Be concise] Dont use long sentences, use short and concise sentences, but still keep it engaging and friendly

## Conversation History
{self.memory.get_conversation_history()}

## Instructions
You are given a list of menu items and you have to present them in a way that is easy to understand for a customer.

## Here is the list of menu items:
{menu_items}
                    """,
                        }
                    ]
                    response = await self.client.chat.completions.create(
                        model=os.environ.get("OPENAI_MODEL"),
                        messages=prompt,
                        temperature=0.2,
                    )
                    response_text = response.choices[0].message.content
                else:
                    response_text = f"I don't see any items available in the {category_name} category right now."

                RUN_CLIENT["run"] = True
            else:
                response_text = "I'm having trouble accessing the menu items for that category. Please try again in a moment."

        # Handle fetch_complete_menu function
        elif func_name == "fetch_complete_menu":
            result = self.fetch_complete_menu()
            if result["success"]:
                menu_text = "Here's our current menu:\n\n"
                for category, items in result["menu"].items():
                    menu_text += f"{category.title()}:\n"
                    for item in items:
                        menu_text += f"- {item['name']} (${item['base_price']:.2f})\n"
                    menu_text += "\n"
                response_text = menu_text
                RUN_CLIENT["run"] = True
            else:
                response_text = "I'm having trouble accessing our menu right now. Please try again in a moment."

        # Handle fetch_addons function
        elif func_name == "fetch_addons":
            result = self.fetch_addons(arguments)
            if result["success"]:
                # Check if we're in the middle of add-on selection
                current_addon_type = None
                for msg in reversed(self.memory.get_conversation_history()):
                    if msg["role"] == "assistant" and "size" in msg["content"].lower():
                        current_addon_type = "size"
                        break
                    elif (
                        msg["role"] == "assistant" and "sauce" in msg["content"].lower()
                    ):
                        current_addon_type = "sauce"
                        break
                    elif (
                        msg["role"] == "assistant"
                        and "topping" in msg["content"].lower()
                    ):
                        current_addon_type = "topping"
                        break
                    elif msg["role"] == "user" and any(
                        word in msg["content"].lower()
                        for word in ["small", "medium", "large"]
                    ):
                        current_addon_type = "sauce"
                        break
                    elif msg["role"] == "user" and any(
                        word in msg["content"].lower()
                        for word in ["tomato", "white", "spicy"]
                    ):
                        current_addon_type = "topping"
                        break

                prompt = [
                    {
                        "role": "system",
                        "content": f"""
## Style Guardrails
- [Be friendly and enthusiastic] Show excitement about our menu items and make recommendations
- [Be conversational] Use natural language and engage in friendly dialogue, Dont use any special characters or markdown
- [Be helpful] Guide customers through the ordering process with suggestions and explanations
- [Be concise] Dont use long sentences, use short and concise sentences, but still keep it engaging and friendly
- [Be sequential] Present add-ons one category at a time and wait for user response before moving to the next category
- [Be context-aware] Use the conversation history to determine which add-on category to present next

## Conversation History
{self.memory.get_conversation_history()}

## Current Add-on Context
Current add-on type being presented: {current_addon_type or "starting add-on selection"}

## Instructions
You are given a list of add-ons organized by type (size, sauce, topping, other). You must present them one category at a time in a conversational manner:

1. If no current_addon_type is set, start with size options
2. If current_addon_type is "size" and user has responded, move to sauce options
3. If current_addon_type is "sauce" and user has responded, move to topping options
4. If current_addon_type is "topping" and user has responded, present any other add-ons if available

For each category:
- Present options in a friendly, conversational way
- Mention prices naturally within the conversation
- Make recommendations if appropriate
- Wait for user response before moving to next category
- Acknowledge the user's previous selection when moving to the next category

## Here is the list of add-ons:
{result["add_ons"]}
                    """,
                    }
                ]
                response = await self.client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL"),
                    messages=prompt,
                    temperature=0.2,
                )
                response_text = response.choices[0].message.content
                RUN_CLIENT["run"] = True
            else:
                response_text = "I'm having trouble getting the add-on options. Would you like to try something else?"

        # Handle fetch_restaurant_info function
        elif func_name == "fetch_restaurant_info":
            result = self.fetch_restaurant_info()
            if result["success"]:
                restaurant = result["restaurant"]
                response_text = (
                    f"We are {restaurant['name']}, located at {restaurant['address']}. "
                )
                response_text += f"Our phone number is {restaurant['phone']}. "
                response_text += f"We are open {restaurant['opening_hours']}. "
                if restaurant.get("pickup_only"):
                    response_text += "Please note that we are a pickup-only restaurant."
            else:
                response_text = "I'm sorry, I'm having trouble accessing our restaurant information. Is there something else I can help you with?"

        # Handle end_call function
        elif func_name == "end_call":
            yield ResponseResponse(
                response_id=response_id,
                content=arguments["message"],
                content_complete=True,
                end_call=True,
            )

        # Handle unknown function
        else:
            response_text = (
                "I'm not sure how to handle that request. Can you try something else?"
            )

        # if os.environ.get("RUN_TOOLS") == "True":
        #     prompt = self.specs_create_prompt(
        #         tool_call=tool_call,
        #         result=response_text,
        #     )
        # else:
        #     if RUN_CLIENT["run"]:
        #         prompt = self.create_prompt(
        #             tool_call=tool_call,
        #             result=response_text,
        #             agent_prompt=TOOL_PROMPT[func_name],
        #         )
        #     else:
        #         pass

        # if not RUN_CLIENT["run"]:
        #     print("********************* AFTER TOOL SELECTION *********************")
        #     print(prompt)
        #     print("***************************************************************")
        #     response = await self.client.chat.completions.create(
        #         model=os.environ.get("OPENAI_MODEL"), messages=prompt, temperature=0.2
        #     )
        #     response_text = response.choices[0].message.content

        # if os.environ.get("RUN_TOOLS") == "True":
        #     response = await self.client.chat.completions.create(
        #         model=os.environ.get("OPENAI_MODEL"), messages=prompt, temperature=0.2
        #     )
        #     response_text = response.choices[0].message.content
        #     self.memory.add_message(role="assistant", content=response_text)
        # else:
        #     self.memory.add_message(
        #         role="tool", content=response_text, tool_call_id=tool_call["id"]
        #     )

        self.memory.add_message(
            role="tool", content=response_text, tool_call_id=tool_call["id"]
        )

        yield ResponseResponse(
            response_id=response_id,
            content=response_text,
            content_complete=True,
            end_call=False,
        )
