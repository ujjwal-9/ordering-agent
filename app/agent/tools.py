"""
Tools definitions for the OrderAgent class.
This file contains the tool definitions used by the OpenAI API to handle restaurant order interactions.
"""

from .handler import verify_menu_item_function


def get_tool_definitions():
    """Return the tool definitions for the OrderAgent class."""
    return [
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
