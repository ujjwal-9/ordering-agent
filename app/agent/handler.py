"""
Function handlers for the OrderAgent class.
This file contains implementations of tool functions used by the restaurant order system.
"""

import json
import logging

# Get logger reference
logger = logging.getLogger("db_operations")
conversation_logger = logging.getLogger("conversation")
tool_logger = logging.getLogger("tool_calls")
response_logger = logging.getLogger("responses")


def verify_menu_item_function(agent, params):
    """
    Verify if a menu item exists and find similar items if it doesn't.

    Args:
        agent: The OrderAgent instance
        params: Dictionary with parameters (item_name, category)

    Returns:
        Dict with menu item information
    """
    item_name = params.get("item_name", "")
    category = params.get("category", None)

    # First try exact match
    menu_item = agent.db.find_similar_menu_item(item_name, category)
    response = {"exists": False, "available": False, "similar_items": []}

    # If no exact match, try fuzzy matching
    if not menu_item:
        # Get all menu items and find potential matches
        all_menu_items = agent.menu_items
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
        add_ons = agent.db.get_add_ons(menu_item.category)
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


async def handle_function_call(agent, request, func_call, func_arguments):
    """
    Process function calls from the LLM.

    Args:
        agent: The OrderAgent instance
        request: The original request
        func_call: Dict with function call details
        func_arguments: String with function arguments

    Yields:
        ResponseResponse objects
    """
    func_call["arguments"] = json.loads(func_arguments)
    func_name = func_call["func_name"]

    # Log complete function call
    tool_logger.info(
        f"CONV_ID:{agent.conversation_id} TOOL_CALL_COMPLETE:func={func_name} args={json.dumps(func_call['arguments'])}"
    )

    # Call the appropriate handler based on function name
    if func_name == "verify_customer":
        async for response in handle_verify_customer(
            agent, request, func_call["arguments"]
        ):
            yield response

    elif func_name == "collect_customer_info":
        async for response in handle_collect_customer_info(
            agent, request, func_call["arguments"]
        ):
            yield response

    elif func_name == "get_order_history":
        async for response in handle_get_order_history(
            agent, request, func_call["arguments"]
        ):
            yield response

    elif func_name == "verify_menu_item":
        async for response in handle_verify_menu_item(
            agent, request, func_call["arguments"]
        ):
            yield response

    elif func_name == "create_order":
        async for response in handle_create_order(
            agent, request, func_call["arguments"]
        ):
            yield response

    elif func_name == "end_call":
        async for response in handle_end_call(agent, request, func_call["arguments"]):
            yield response

    elif func_name == "get_item_addons":
        async for response in handle_get_item_addons(
            agent, request, func_call["arguments"]
        ):
            yield response


async def handle_verify_customer(agent, request, arguments):
    """Handle verify_customer function call"""
    name = arguments["name"]
    phone = arguments.get("phone")

    # If phone wasn't provided in the function call but we have from_number, use it
    if not phone and agent.from_number:
        phone = agent.from_number
        logger.info(f"Using from_number {phone} instead of asking for phone")

    # Proceed with verification only if we have a phone number
    if phone:
        # Validate phone number
        is_valid, phone_str, error_message = agent._validate_phone_number(phone)
        if not is_valid:
            logger.warning(f"Invalid phone number format: {phone}")
            response_content = error_message
            # Log invalid phone number response
            response_logger.warning(
                f"CONV_ID:{agent.conversation_id} INVALID_PHONE:{phone} RESPONSE:{response_content}"
            )

            yield agent.create_response(
                request.response_id,
                response_content,
                content_complete=True,
                end_call=False,
            )
            return

        logger.info(f"Verifying customer with phone: {phone_str}")
        customer = agent.db.get_customer_by_phone(phone_str)

        if customer:
            logger.info(f"Found existing customer: {customer.name}")
            agent.verified_customer = customer

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
            if phone == agent.from_number:
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
                response_text += (
                    f"\nYou've placed {customer.total_orders} orders with us. "
                )

            # If we used the from_number, don't ask for confirmation but directly ask for order
            if phone == agent.from_number:
                response_text += "What would you like to order today?"
            else:
                response_text += "Is this information correct?"

            # Log the response being sent to customer
            conversation_logger.info(
                f"CONV_ID:{agent.conversation_id} ROLE:agent MESSAGE:{response_text}"
            )
            response_logger.info(
                f"CONV_ID:{agent.conversation_id} CUSTOMER_VERIFIED:true NAME:{provided_name} RESPONSE:{response_text}"
            )

            yield agent.create_response(
                request.response_id,
                response_text,
                content_complete=True,
                end_call=False,
            )
        else:
            logger.info(f"No existing customer found for phone: {phone_str}")

            # If we're using from_number that's not in the database, we can register the customer
            if phone == agent.from_number:
                # Register the new customer with the from_number
                try:
                    customer_data = {
                        "name": name,
                        "phone": phone_str,
                    }
                    new_customer = agent.db.create_customer(
                        **customer_data, auto_commit=True
                    )
                    logger.info(f"Created new customer: {name} with phone: {phone_str}")

                    # Skip phone confirmation and go straight to menu
                    restaurant = agent.db.get_restaurant()
                    pickup_address = (
                        restaurant.address if restaurant else "our restaurant"
                    )

                    yield agent.create_response(
                        request.response_id,
                        f"Thank you, {name}! I've registered you as a new customer. Let me tell you about our menu. We offer delicious burgers and pizzas, all available for pickup at {pickup_address}. What would you like to order today?",
                        content_complete=True,
                        end_call=False,
                    )
                except Exception as e:
                    logger.error(f"Error creating new customer: {str(e)}")
                    yield agent.create_response(
                        request.response_id,
                        f"Thank you, {name}. What would you like to order today?",
                        content_complete=True,
                        end_call=False,
                    )
            else:
                # For manually entered phone numbers, verify with the customer
                yield agent.create_response(
                    request.response_id,
                    f"Nice to meet you, {name}! I've got your phone number as {phone_str}, is that correct?",
                    content_complete=True,
                    end_call=False,
                )


async def handle_collect_customer_info(agent, request, arguments):
    """Handle collect_customer_info function call"""
    step = arguments["step"]

    if step == "name":
        yield agent.create_response(
            request.response_id,
            "What is your name?",
            content_complete=True,
            end_call=False,
        )

    elif step == "email":
        yield agent.create_response(
            request.response_id,
            "Would you like to provide an email address for order updates? (optional)",
            content_complete=True,
            end_call=False,
        )

    elif step == "payment_method":
        yield agent.create_response(
            request.response_id,
            "What is your preferred payment method? (cash, credit card, or digital payment)",
            content_complete=True,
            end_call=False,
        )

    elif step == "complete":
        # Validate phone number
        is_valid, phone_str, error_message = agent._validate_phone_number(
            arguments["phone"]
        )
        if not is_valid:
            logger.warning(f"Invalid phone number format: {arguments['phone']}")
            yield agent.create_response(
                request.response_id,
                error_message,
                content_complete=True,
                end_call=False,
            )
            return

        # Process the customer info with the validated phone number
        customer = agent.db.get_customer_by_phone(phone_str)

        customer_data = {
            "name": arguments["name"],
            "email": arguments.get("email"),
            "preferred_payment_method": arguments.get("preferred_payment_method"),
        }

        if customer:
            logger.info(f"Updating existing customer: {customer.name}")
            try:
                customer = agent.db.update_customer(
                    phone_str, auto_commit=True, **customer_data
                )
            except Exception as e:
                agent.db.session.rollback()
                logger.error(f"Error updating customer: {str(e)}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            logger.info(f"Creating new customer with phone: {phone_str}")
            customer_data["phone"] = phone_str
            try:
                customer = agent.db.create_customer(**customer_data, auto_commit=True)
            except Exception as e:
                agent.db.session.rollback()
                logger.error(f"Error creating customer: {str(e)}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")

        yield agent.create_response(
            request.response_id,
            f"Thank you for providing your information. I've added your phone number {phone_str} to our records. What would you like to order today?",
            content_complete=True,
            end_call=False,
        )


async def handle_get_order_history(agent, request, arguments):
    """Handle get_order_history function call"""
    # Validate phone number
    is_valid, phone_str, error_message = agent._validate_phone_number(
        arguments["phone"]
    )
    if not is_valid:
        logger.warning(f"Invalid phone number format: {arguments['phone']}")
        yield agent.create_response(
            request.response_id,
            error_message,
            content_complete=True,
            end_call=False,
        )
        return

    logger.info(f"Retrieving order history for customer with phone: {phone_str}")
    orders = agent.db.get_customer_order_history(phone_str)
    if orders:
        logger.info(f"Found {len(orders)} orders for customer")
        response_text = "Here's your order history:\n\n"
        for order in orders[:5]:  # Show last 5 orders
            response_text += (
                f"Order #{order.id} ({order.created_at.strftime('%Y-%m-%d')}):\n"
            )
            response_text += f"- Status: {order.status}\n"
            response_text += f"- Total: ${order.total_amount:.2f}\n"
            response_text += f"- Items: {', '.join([item['item_name'] for item in order.order_items])}\n\n"
        if len(orders) > 5:
            response_text += f"... and {len(orders) - 5} more orders."

        yield agent.create_response(
            request.response_id,
            response_text,
            content_complete=True,
            end_call=False,
        )
    else:
        yield agent.create_response(
            request.response_id,
            "I don't see any previous orders in your history. Would you like to place an order?",
            content_complete=True,
            end_call=False,
        )


async def handle_verify_menu_item(agent, request, arguments):
    """Handle verify_menu_item function call"""
    item_name = arguments["item_name"]
    category = arguments.get("category")
    logger.info(f"Verifying menu item: {item_name} (category: {category})")
    similar_item = agent.db.find_similar_menu_item(item_name, category)

    if similar_item:
        # Check if the item is available
        if getattr(similar_item, "is_available", 1) == 1:
            yield agent.create_response(
                request.response_id,
                f"I found {similar_item.name} (${similar_item.base_price:.2f}). Would you like to order this?",
                content_complete=True,
                end_call=False,
            )
        else:
            # If the item exists but is unavailable
            yield agent.create_response(
                request.response_id,
                f"I'm sorry, but {similar_item.name} is currently unavailable. Would you like to see other options in our menu?",
                content_complete=True,
                end_call=False,
            )
    else:
        yield agent.create_response(
            request.response_id,
            "I couldn't find that item on our menu. Would you like to see our available options?",
            content_complete=True,
            end_call=False,
        )


async def handle_get_item_addons(agent, request, arguments):
    """Handle get_item_addons function call"""
    item_name = arguments["item_name"]

    # Attempt to find the menu item with more flexible matching
    menu_item = None
    all_menu_items = agent.menu_items

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
        menu_item = agent.db.find_similar_menu_item(item_name)

    if menu_item:
        # Check if the item is available
        if getattr(menu_item, "is_available", 1) == 0:
            yield agent.create_response(
                request.response_id,
                f"I'm sorry, but {menu_item.name} is currently unavailable. Would you like to see other options in our menu?",
                content_complete=True,
                end_call=False,
            )
            return

        add_ons = agent.db.get_add_ons(menu_item.category)
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
                response_text += "You can add delicious toppings to your order. "
                if len(topping_options) > 1:
                    response_text += f"We have {', '.join([addon.name for addon in topping_options[:-1]])}, and {topping_options[-1].name}. "
                else:
                    response_text += f"We offer {topping_options[0].name}. "
                response_text += "Would you like to add any toppings?"
            else:
                # If no add-ons by type, simply ask if they want anything else
                response_text += "Would you like to order anything else?"

            yield agent.create_response(
                request.response_id,
                response_text,
                content_complete=True,
                end_call=False,
            )
        else:
            yield agent.create_response(
                request.response_id,
                f"Great! I've added the {menu_item.name} to your order. Would you like to order anything else?",
                content_complete=True,
                end_call=False,
            )
    else:
        yield agent.create_response(
            request.response_id,
            "I'm not sure I found that item on our menu. Let me show you what we have available.",
            content_complete=True,
            end_call=False,
        )


async def handle_end_call(agent, request, arguments):
    """Handle end_call function call"""
    response_content = arguments["message"]

    # Log the end call
    conversation_logger.info(
        f"CONV_ID:{agent.conversation_id} ROLE:agent MESSAGE:{response_content}"
    )
    tool_logger.info(f"CONV_ID:{agent.conversation_id} END_CALL:true")
    response_logger.info(
        f"CONV_ID:{agent.conversation_id} CALL_ENDED:true FINAL_MESSAGE:{response_content}"
    )

    yield agent.create_response(
        request.response_id,
        response_content,
        content_complete=True,
        end_call=True,
    )


async def handle_create_order(agent, request, arguments):
    """Handle create_order function call"""
    try:
        # Get customer phone with priority: 1) function argument, 2) verified customer, 3) from_number
        customer_phone = arguments.get("customer_phone")
        if not customer_phone and agent.verified_customer:
            customer_phone = agent.verified_customer.phone
        elif not customer_phone and agent.from_number:
            customer_phone = agent.from_number

        # Validate phone number
        is_valid, customer_phone_str, error_message = agent._validate_phone_number(
            customer_phone
        )
        if not is_valid:
            logger.warning(f"Invalid phone number format: {customer_phone}")
            yield agent.create_response(
                request.response_id,
                error_message,
                content_complete=True,
                end_call=False,
            )
            return

        # Check if this is an update to an existing order
        is_update = False
        if agent.current_order:
            is_update = True
            logger.info(f"Updating existing order #{agent.current_order.id}")

        # Transform order items into the required format with database queries
        raw_order_items = arguments["order_items"]
        formatted_order_items = []

        # Collect special instructions for the whole order
        order_special_instructions = arguments.get("special_instructions", "")

        for item in raw_order_items:
            # Get menu item details including ID from database
            menu_item = agent.db.find_similar_menu_item(item["item_name"])

            if not menu_item or getattr(menu_item, "is_available", 1) == 0:
                logger.warning(
                    f"Menu item not found or unavailable: {item['item_name']}"
                )
                continue

            quantity = item.get("quantity", 1)
            base_price = menu_item.base_price

            # Process add-ons and collect item-specific special instructions
            formatted_add_ons = []
            total_add_on_price = 0
            item_special_instructions = item.get("special_instructions", "")

            for addon_name in item.get("add_ons", []):
                # Find add-on in database to get its ID and price
                add_ons = agent.db.get_add_ons(menu_item.category)

                # First try exact match
                addon = next(
                    (a for a in add_ons if a.name.lower() == addon_name.lower()),
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
                            addon_name.lower().replace(addon.name.lower(), "").strip()
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
                formatted_item["special_instructions"] = item_special_instructions

            formatted_order_items.append(formatted_item)

        # Calculate total amount for the entire order
        total_amount = sum(item["total_price"] for item in formatted_order_items)

        # Combine order-level and item-level special instructions
        combined_special_instructions = order_special_instructions
        for item in formatted_order_items:
            if "special_instructions" in item:
                if combined_special_instructions:
                    combined_special_instructions += (
                        f"; {item['menu_item_name']}: {item['special_instructions']}"
                    )
                else:
                    combined_special_instructions = (
                        f"{item['menu_item_name']}: {item['special_instructions']}"
                    )
                # Remove from item to avoid duplication
                del item["special_instructions"]

        order_data = {
            "customer_name": arguments["customer_name"],
            "customer_phone": customer_phone_str,
            "order_items": formatted_order_items,
            "total_amount": total_amount,
        }

        # Add the combined special instructions
        if combined_special_instructions:
            order_data["special_instructions"] = combined_special_instructions

        try:
            # Add payment method if provided
            if "payment_method" in arguments:
                order_data["payment_method"] = arguments["payment_method"]

            # Get restaurant information for pickup address
            restaurant = agent.db.get_restaurant()
            pickup_address = (
                restaurant.address
                if restaurant
                else "123 Main Street, Downtown, CA 94123"
            )

            # Create a new order or update the existing one
            if is_update:
                # Update the existing order
                order = agent.db.update_order(
                    agent.current_order.id,
                    order_items=formatted_order_items,
                    total_amount=total_amount,
                    special_instructions=order_data.get("special_instructions"),
                    payment_method=order_data.get("payment_method"),
                    auto_commit=True,
                )
                confirmation_message = (
                    f"I've updated your order. Your order number is still #{order.id}."
                )
            else:
                # Create a new order
                order = agent.db.create_order(**order_data, auto_commit=True)
                agent.current_order = order  # Store the current order
                confirmation_message = (
                    f"Great! I've placed your order. Your order number is #{order.id}."
                )

            # Construct the confirmation message
            confirmation_message += " We will send you a confirmation text shortly along with order details and estimated pickup time."
            confirmation_message += f" You can pick up your order at our restaurant located at {pickup_address}."

            # Add a note about being able to update the order
            if not is_update:
                confirmation_message += " If you need to make any changes to your order, just let me know and I can update it for you."

            yield agent.create_response(
                request.response_id,
                confirmation_message,
                content_complete=True,
                end_call=False,
            )
        except Exception as e:
            # Rollback in case of error
            agent.db.session.rollback()
            logger.error(f"Error creating/updating order in database: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            yield agent.create_response(
                request.response_id,
                f"I'm sorry, there was an error processing your order. Please try again or contact customer support.",
                content_complete=True,
                end_call=False,
            )
    except Exception as e:
        logger.error(f"Unexpected error in create_order function: {str(e)}")
        yield agent.create_response(
            request.response_id,
            f"I'm sorry, something went wrong while processing your order. Please try again later.",
            content_complete=True,
            end_call=False,
        )
