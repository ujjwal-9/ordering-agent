def prepare_tools():
    """Prepare the function definitions for the OpenAI API."""
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
                    "required": ["phone"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_customer",
                "description": "Create a new customer in the database.",
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
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "get_order_history",
        #         "description": "Get the customer's order history.",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "phone": {
        #                     "type": "integer",
        #                     "description": "The phone number of the customer (must be a number without spaces or special characters)",
        #                 },
        #             },
        #             "required": ["phone"],
        #         },
        #     },
        # },
        {
            "type": "function",
            "function": {
                "name": "verify_order_item",
                "description": "Verify if a order item exists and find similar items if it doesn't. It is used when customer has selected a menu item to order.",
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
                        "add_ons": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The customer selected add-ons for the menu item",
                        },
                    },
                    "required": ["item_name", "category"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_order",
                "description": "When the customer confirms the order is complete, use this function to create the order in the database.",
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
                            "description": "List of items in the order, if an item is ordered with different addons, then decouple the item and the addons into different objects in the array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_name": {"type": "string"},
                                    "quantity": {"type": "integer"},
                                    "add_ons": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "special_instructions": {
                                        "type": "string",
                                        "description": "Any special instructions for the item",
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
                "name": "fetch_menu_categories",
                "description": "Fetch all available menu categories. It is used when just starting to read through the menu. Customer will choose one or more categories to read through.",
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
                "name": "fetch_items_for_category",
                "description": "Fetch available menu items for a specific category. It is used when customer has chosen a category to read through.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "The category of the menu items to fetch",
                        },
                    },
                    "required": ["category"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_complete_menu",
                "description": "Fetch all available menu items organized by category. It is used when customer has chosen a category to read through.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "The category of the menu items to fetch",
                        },
                    },
                    "required": ["category"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_addons",
                "description": "Get available add-ons for a specific menu item. It is used when customer has chosen a menu item to order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "The category of the add-ons to fetch",
                        },
                    },
                    "required": ["category"],
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
                            "description": "The message you will say before ending the call with the customer."
                        }
                    },
                    "required": ["message"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "record_addons",
                "description": "Record customer's add-on selection during the add-on selection flow.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "addon_type": {
                            "type": "string",
                            "description": "The type/category of add-on being selected (size, sauce, topping, other)."
                        },
                        "selection": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The customer's selection(s) for this add-on type."
                        }
                    },
                    "required": ["addon_type", "selection"]
                }
            }
        }
    ]
    return functions
