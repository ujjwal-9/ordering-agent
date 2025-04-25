from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("db_operations.log"), logging.StreamHandler()],
)
logger = logging.getLogger("db_operations")


def validate_phone_number(phone) -> Tuple[bool, Optional[str], str]:
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
            "That doesn't appear to be a valid phone number. Please provide a 10-digit number using only numbers 0 to 9.",
        )


def calculate_total_amount(order_items, db):
    """
    Calculate the total amount for an order including add-ons.
    """
    total = 0
    for item in order_items:
        menu_item = db.find_similar_menu_item(item["item_name"])
        if menu_item and getattr(menu_item, "is_available", 1) == 1:
            item_total = menu_item.base_price * item["quantity"]
            total += item_total

            for addon_name in item.get("add_ons", []):
                addon = next(
                    (
                        a
                        for a in db.get_add_ons(menu_item.category)
                        if a.name == addon_name
                    ),
                    None,
                )
                if addon:
                    total += addon.price * item["quantity"]

    return total


def format_addon_response(result):
    """Format the add-on response in a user-friendly way."""
    response = []
    type_order = ["size", "sauce", "topping", "other"]

    for addon_type in type_order:
        if addon_type in result["add_ons"]:
            addons = result["add_ons"][addon_type]
            if addons:
                response.append(f"{addon_type.title()} options:")
                for addon in addons:
                    price_text = (
                        f"(${addon['price']:.2f})"
                        if addon["price"] > 0
                        else "(no extra charge)"
                    )
                    response.append(f"- {addon['name']} {price_text}")
                response.append("")

    return "\n".join(response) if response else "No add-ons available for this item."
