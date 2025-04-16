import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_ID = os.environ.get("TWILIO_ACCOUNT_ID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_ID, TWILIO_AUTH_TOKEN)


def format_phone_number(phone_number):
    """
    Formats phone number to Twilio-compatible format (+1XXXXXXXXXX)
    """
    # Remove any non-digit characters first
    clean_phone = "".join(filter(str.isdigit, phone_number))

    # Add country code if not present
    if not clean_phone.startswith("1"):
        clean_phone = "1" + clean_phone

    # Add '+' prefix
    return "+" + clean_phone


def send_order_ready_sms(phone_number, order_id, restaurant_name=None):
    """
    Send an SMS notification to the customer when their order is ready for pickup.

    Args:
        phone_number (str): Customer's phone number
        order_id (int): Order ID
        restaurant_name (str, optional): Name of the restaurant

    Returns:
        dict: Twilio message SID or error message
    """
    try:
        formatted_phone = format_phone_number(phone_number)

        # Get restaurant name or use default
        restaurant = restaurant_name or "our restaurant"

        # Prepare the message
        message_body = f"Good news! Your order #{order_id} from {restaurant} is now ready for pickup. Thank you for your business!"

        # Send SMS
        message = client.messages.create(
            body=message_body, from_=TWILIO_PHONE_NUMBER, to=formatted_phone
        )

        print(f"SMS sent to {formatted_phone}: {message.sid}")
        return {"success": True, "message_sid": message.sid}

    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return {"success": False, "error": str(e)}


def send_order_confirmation_sms(
    phone_number, order_id, restaurant_name, restaurant_address, estimated_time
):
    """
    Send an SMS notification to the customer when their order is confirmed.

    Args:
        phone_number (str): Customer's phone number
        order_id (int): Order ID
        restaurant_name (str): Name of the restaurant
        restaurant_address (str): Restaurant address for pickup
        estimated_time (int): Estimated preparation time in minutes

    Returns:
        dict: Twilio message SID or error message
    """
    try:
        formatted_phone = format_phone_number(phone_number)

        # Prepare the message
        message_body = (
            f"Thank you for your order #{order_id} from {restaurant_name}!\n\n"
            f"Estimated preparation time: {estimated_time} minutes\n"
            f"Pickup location: {restaurant_address}\n\n"
            f"We'll notify you when your order is ready for pickup."
        )

        # Send SMS
        message = client.messages.create(
            body=message_body, from_=TWILIO_PHONE_NUMBER, to=formatted_phone
        )

        print(f"Order confirmation SMS sent to {formatted_phone}: {message.sid}")
        return {"success": True, "message_sid": message.sid}

    except Exception as e:
        print(f"Error sending order confirmation SMS: {str(e)}")
        return {"success": False, "error": str(e)}


def send_time_update_sms(phone_number, order_id, restaurant_name, new_time):
    """
    Send an apologetic SMS notification to the customer when order preparation time is updated.

    Args:
        phone_number (str): Customer's phone number
        order_id (int): Order ID
        restaurant_name (str): Name of the restaurant
        new_time (int): New estimated preparation time in minutes

    Returns:
        dict: Twilio message SID or error message
    """
    try:
        formatted_phone = format_phone_number(phone_number)

        # Prepare the message
        message_body = (
            f"Update on your order #{order_id} from {restaurant_name}:\n\n"
            f"We apologize, but we need to update the estimated preparation time "
            f"for your order to {new_time} minutes.\n\n"
            f"We appreciate your patience and understanding."
        )

        # Send SMS
        message = client.messages.create(
            body=message_body, from_=TWILIO_PHONE_NUMBER, to=formatted_phone
        )

        print(f"Time update SMS sent to {formatted_phone}: {message.sid}")
        return {"success": True, "message_sid": message.sid}

    except Exception as e:
        print(f"Error sending time update SMS: {str(e)}")
        return {"success": False, "error": str(e)}
