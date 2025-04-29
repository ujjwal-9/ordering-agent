import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    Body,
)
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import TimeoutError as ConnectionTimeoutError
from retell import Retell
from app.custom_types import (
    ConfigResponse,
    ResponseRequiredRequest,
)
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

from app.order_llm import OrderAgent
from app.auth_api import router as auth_router, get_current_user
from app.user_model import User, UserManager
from app.database import Database, MenuItem, AddOn, Restaurant, Order, Customer

load_dotenv(override=True)
app = FastAPI()
retell = Retell(api_key=os.environ["RETELL_API_KEY"])

# Initialize database and ensure all tables are created
db = Database()
print("Database initialized and tables created")

# List of allowed ports for frontend dev
ports = [3000]
allow_origins = [f"http://0.0.0.0:{port}" for port in ports] + [
    f"http://34.44.106.200:{port}" for port in ports
]

# Configure CORS middleware for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the authentication router
app.include_router(auth_router)


# Handle webhook from Retell server. This is used to receive events from Retell server.
# Including call_started, call_ended, call_analyzed
@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        post_data = await request.json()
        valid_signature = retell.verify(
            json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
            api_key=str(os.environ["RETELL_API_KEY"]),
            signature=str(request.headers.get("X-Retell-Signature")),
        )
        if not valid_signature:
            print(
                "Received Unauthorized",
                post_data["event"],
                post_data["data"]["call_id"],
            )
            return JSONResponse(status_code=401, content={"message": "Unauthorized"})
        if post_data["event"] == "call_started":
            print("Call started event", post_data["data"]["call_id"])
        elif post_data["event"] == "call_ended":
            print("Call ended event", post_data["data"]["call_id"])
        elif post_data["event"] == "call_analyzed":
            print("Call analyzed event", post_data["data"]["call_id"])
        else:
            print("Unknown event", post_data["event"])
        return JSONResponse(status_code=200, content={"received": True})
    except Exception as err:
        print(f"Error in webhook: {err}")
        return JSONResponse(
            status_code=500, content={"message": "Internal Server Error"}
        )


# Start a websocket server to exchange text input and output with Retell server. Retell server
# will send over transcriptions and other information. This server here will be responsible for
# generating responses with LLM and send back to Retell server.
@app.websocket("/llm-websocket/{call_id}")
async def websocket_handler(websocket: WebSocket, call_id: str):
    try:
        await websocket.accept()
        llm_client = OrderAgent()  # Comment out the original LlmClient

        # Send optional config to Retell server
        config = ConfigResponse(
            response_type="config",
            config={
                "auto_reconnect": True,
                "call_details": True,
            },
            response_id=1,
        )
        await websocket.send_json(config.__dict__)

        # Send first message to signal ready of server
        response_id = 0
        first_event = llm_client.draft_begin_message()
        await websocket.send_json(first_event.__dict__)

        async def handle_message(request_json):
            nonlocal response_id

            # There are 5 types of interaction_type: call_details, pingpong, update_only, response_required, and reminder_required.
            # Not all of them need to be handled, only response_required and reminder_required.
            if request_json["interaction_type"] == "call_details":
                print(json.dumps(request_json, indent=2))

                # Extract from_number from call_details if present
                if "call" in request_json and "from_number" in request_json["call"]:
                    from_number = request_json["call"]["from_number"]
                    print(f"Incoming call from: {from_number}")

                    # Format phone number (remove + and country code for 10-digit number)
                    formatted_number = "".join(filter(str.isdigit, from_number))
                    if len(formatted_number) > 10:
                        formatted_number = formatted_number[-10:]

                    # Store the formatted number in OrderAgent but don't verify yet
                    llm_client.set_from_number(formatted_number)

                return

            if request_json["interaction_type"] == "ping_pong":
                await websocket.send_json(
                    {
                        "response_type": "ping_pong",
                        "timestamp": request_json["timestamp"],
                    }
                )
                return
            if request_json["interaction_type"] == "update_only":
                return
            if (
                request_json["interaction_type"] == "response_required"
                or request_json["interaction_type"] == "reminder_required"
            ):
                response_id = request_json["response_id"]
                request = ResponseRequiredRequest(
                    interaction_type=request_json["interaction_type"],
                    response_id=response_id,
                    transcript=request_json["transcript"],
                )
                print(
                    f"""Received interaction_type={request_json['interaction_type']}, response_id={response_id}, last_transcript={request_json['transcript'][-1]['content']}"""
                )

                async for event in llm_client.draft_response(request):
                    await websocket.send_json(event.__dict__)
                    if request.response_id < response_id:
                        break  # new response needed, abandon this one

        async for data in websocket.iter_json():
            asyncio.create_task(handle_message(data))

    except WebSocketDisconnect:
        print(f"LLM WebSocket disconnected for {call_id}")
    except ConnectionTimeoutError as e:
        print("Connection timeout error for {call_id}")
    except Exception as e:
        print(f"Error in LLM WebSocket: {e} for {call_id}")
        await websocket.close(1011, "Server error")
    finally:
        print(f"LLM WebSocket connection closed for {call_id}")


# API endpoints for menu items
@app.get("/menu")
async def get_menu_items(
    category: str = None, current_user: User = Depends(get_current_user)
):
    db = Database()
    menu_items = db.get_menu(category)
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "base_price": item.base_price,
            "description": item.description,
            "is_available": item.is_available == 1,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in menu_items
    ]


# Models for request validation
class MenuItemCreate(BaseModel):
    name: str
    category: str
    base_price: float
    description: Optional[str] = None
    is_available: Optional[bool] = True


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    base_price: Optional[float] = None
    description: Optional[str] = None
    is_available: Optional[bool] = None


# Create new menu item
@app.post("/menu")
async def create_menu_item(
    item: MenuItemCreate, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        new_item = MenuItem(
            name=item.name,
            category=item.category,
            base_price=item.base_price,
            description=item.description,
            is_available=1 if item.is_available else 0,
        )
        db.session.add(new_item)
        db.safe_commit()
        return {
            "id": new_item.id,
            "name": new_item.name,
            "category": new_item.category,
            "base_price": new_item.base_price,
            "description": new_item.description,
            "is_available": new_item.is_available == 1,
            "created_at": new_item.created_at,
            "updated_at": new_item.updated_at,
        }
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to create menu item: {str(e)}"
        )


# Update menu item
@app.put("/menu/{item_id}")
async def update_menu_item(
    item_id: int, item: MenuItemUpdate, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        existing_item = (
            db.session.query(MenuItem).filter(MenuItem.id == item_id).first()
        )
        if not existing_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        if item.name is not None:
            existing_item.name = item.name
        if item.category is not None:
            existing_item.category = item.category
        if item.base_price is not None:
            existing_item.base_price = item.base_price
        if item.description is not None:
            existing_item.description = item.description
        if item.is_available is not None:
            existing_item.is_available = 1 if item.is_available else 0

        db.safe_commit()
        return {
            "id": existing_item.id,
            "name": existing_item.name,
            "category": existing_item.category,
            "base_price": existing_item.base_price,
            "description": existing_item.description,
            "is_available": existing_item.is_available == 1,
            "created_at": existing_item.created_at,
            "updated_at": existing_item.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to update menu item: {str(e)}"
        )


# Delete menu item
@app.delete("/menu/{item_id}")
async def delete_menu_item(
    item_id: int, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        existing_item = (
            db.session.query(MenuItem).filter(MenuItem.id == item_id).first()
        )
        if not existing_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        db.session.delete(existing_item)
        db.safe_commit()
        return {"message": f"Menu item with ID {item_id} has been deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to delete menu item: {str(e)}"
        )


# API endpoint for add-ons
@app.get("/addons")
async def get_addons(
    category: str = None, current_user: User = Depends(get_current_user)
):
    db = Database()
    addons = db.get_add_ons(category)
    return [
        {
            "id": addon.id,
            "name": addon.name,
            "category": addon.category,
            "type": addon.type,
            "price": addon.price,
            "is_available": addon.is_available == 1,
            "created_at": addon.created_at,
            "updated_at": addon.updated_at,
        }
        for addon in addons
    ]


# Models for AddOn requests
class AddOnCreate(BaseModel):
    name: str
    category: str
    type: Optional[str] = None
    price: float
    is_available: Optional[bool] = True


class AddOnUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None


# Create add-on
@app.post("/addons")
async def create_addon(
    addon: AddOnCreate, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        new_addon = AddOn(
            name=addon.name,
            category=addon.category,
            type=addon.type,
            price=addon.price,
            is_available=1 if addon.is_available else 0,
        )
        db.session.add(new_addon)
        db.safe_commit()
        return {
            "id": new_addon.id,
            "name": new_addon.name,
            "category": new_addon.category,
            "type": new_addon.type,
            "price": new_addon.price,
            "is_available": new_addon.is_available == 1,
            "created_at": new_addon.created_at,
            "updated_at": new_addon.updated_at,
        }
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to create add-on: {str(e)}"
        )


# Update add-on
@app.put("/addons/{addon_id}")
async def update_addon(
    addon_id: int, addon: AddOnUpdate, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        existing_addon = db.session.query(AddOn).filter(AddOn.id == addon_id).first()
        if not existing_addon:
            raise HTTPException(status_code=404, detail="Add-on not found")

        if addon.name is not None:
            existing_addon.name = addon.name
        if addon.category is not None:
            existing_addon.category = addon.category
        if addon.type is not None:
            existing_addon.type = addon.type
        if addon.price is not None:
            existing_addon.price = addon.price
        if addon.is_available is not None:
            existing_addon.is_available = 1 if addon.is_available else 0

        db.safe_commit()
        return {
            "id": existing_addon.id,
            "name": existing_addon.name,
            "category": existing_addon.category,
            "type": existing_addon.type,
            "price": existing_addon.price,
            "is_available": existing_addon.is_available == 1,
            "created_at": existing_addon.created_at,
            "updated_at": existing_addon.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to update add-on: {str(e)}"
        )


# Delete add-on
@app.delete("/addons/{addon_id}")
async def delete_addon(addon_id: int, current_user: User = Depends(get_current_user)):
    db = Database()
    try:
        existing_addon = db.session.query(AddOn).filter(AddOn.id == addon_id).first()
        if not existing_addon:
            raise HTTPException(status_code=404, detail="Add-on not found")

        db.session.delete(existing_addon)
        db.safe_commit()
        return {"message": f"Add-on with ID {addon_id} has been deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to delete add-on: {str(e)}"
        )


# API endpoint for orders
@app.get("/orders")
async def get_orders(
    status: str = None, current_user: User = Depends(get_current_user)
):
    db = Database()
    query = db.session.query(Order)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.created_at.desc()).all()
    return [
        {
            "id": order.id,
            "customer_id": order.customer_id,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "order_items": order.order_items,
            "total_amount": order.total_amount,
            "status": order.status,
            "estimated_preparation_time": order.estimated_preparation_time,
            "payment_method": order.payment_method,
            "special_instructions": order.special_instructions,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }
        for order in orders
    ]


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    order_items: list
    total_amount: float
    payment_method: Optional[str] = None
    special_instructions: Optional[str] = None


# Create a new order
@app.post("/orders")
async def create_order(
    order_data: OrderCreate, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        new_order = db.create_order(
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            order_items=order_data.order_items,
            total_amount=order_data.total_amount,
            payment_method=order_data.payment_method,
            special_instructions=order_data.special_instructions,
            auto_commit=True,
        )

        return {
            "id": new_order.id,
            "customer_id": new_order.customer_id,
            "customer_name": new_order.customer_name,
            "customer_phone": new_order.customer_phone,
            "order_items": new_order.order_items,
            "total_amount": new_order.total_amount,
            "status": new_order.status,
            "estimated_preparation_time": new_order.estimated_preparation_time,
            "payment_method": new_order.payment_method,
            "special_instructions": new_order.special_instructions,
            "created_at": new_order.created_at,
            "updated_at": new_order.updated_at,
        }
    except Exception as e:
        db.session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create order: {str(e)}")


# Get order by ID
@app.get("/orders/{order_id}")
async def get_order_by_id(
    order_id: int, current_user: User = Depends(get_current_user)
):
    db = Database()
    order = db.session.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "order_items": order.order_items,
        "total_amount": order.total_amount,
        "status": order.status,
        "estimated_preparation_time": order.estimated_preparation_time,
        "payment_method": order.payment_method,
        "special_instructions": order.special_instructions,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


class OrderStatusUpdate(BaseModel):
    status: str
    estimated_preparation_time: Optional[int] = None


# Update order status
@app.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    update: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
):
    db = Database()
    try:
        # Pass both status and estimated_preparation_time to the database method
        updated_order = db.update_order_status(
            order_id, update.status, update.estimated_preparation_time
        )

        if not updated_order:
            raise HTTPException(status_code=404, detail="Order not found")

        message = f"Order status updated to {update.status}"
        if update.estimated_preparation_time is not None:
            message += (
                f" with {update.estimated_preparation_time} minutes preparation time"
            )

        # Get restaurant info for notifications
        restaurant = db.get_restaurant()
        restaurant_name = restaurant.name if restaurant else "Our Restaurant"
        restaurant_address = restaurant.address if restaurant else "Our Location"

        # Send SMS notification based on order status
        if update.status == "ready":
            try:
                from app.twilio_service import send_order_ready_sms

                # Send SMS notification
                sms_result = send_order_ready_sms(
                    updated_order.customer_phone, updated_order.id, restaurant_name
                )

                if sms_result["success"]:
                    message += f" - SMS notification sent to customer"
                else:
                    print(f"SMS notification failed: {sms_result.get('error')}")
            except Exception as sms_error:
                # Log the error but don't fail the status update
                print(f"Error sending SMS notification: {str(sms_error)}")

        # Send SMS notification when order is confirmed
        elif update.status == "confirmed":
            try:
                from app.twilio_service import send_order_confirmation_sms

                # Only send if we have an estimated preparation time
                if updated_order.estimated_preparation_time:
                    # Send SMS notification
                    sms_result = send_order_confirmation_sms(
                        updated_order.customer_phone,
                        updated_order.id,
                        restaurant_name,
                        restaurant_address,
                        updated_order.estimated_preparation_time,
                    )

                    if sms_result["success"]:
                        message += f" - Confirmation SMS sent to customer"
                    else:
                        print(f"Confirmation SMS failed: {sms_result.get('error')}")
            except Exception as sms_error:
                # Log the error but don't fail the status update
                print(f"Error sending confirmation SMS: {str(sms_error)}")

        return {"message": message}
    except Exception as e:
        db.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# API endpoint for customers
@app.get("/customers")
async def get_customers(current_user: User = Depends(get_current_user)):
    db = Database()
    # This is a simplified approach - in a real app, you'd implement pagination
    # and more sophisticated querying
    customers = db.session.query(Customer).limit(100).all()
    return [
        {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "preferred_payment_method": customer.preferred_payment_method,
            "dietary_preferences": customer.dietary_preferences,
            "last_order_date": customer.last_order_date,
            "total_orders": customer.total_orders,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
        }
        for customer in customers
    ]


# Get customer by phone number
@app.get("/customers/{phone}")
async def get_customer_by_phone(
    phone: str, current_user: User = Depends(get_current_user)
):
    db = Database()
    customer = db.get_customer_by_phone(phone)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    preferred_payment_method: Optional[str] = None
    dietary_preferences: Optional[str] = None


# Update customer information
@app.put("/customers/{phone}")
async def update_customer(
    phone: str, customer: CustomerUpdate, current_user: User = Depends(get_current_user)
):
    db = Database()
    update_data = {k: v for k, v in customer.dict().items() if v is not None}
    updated_customer = db.update_customer(phone, auto_commit=True, **update_data)
    if not updated_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated_customer


# Get restaurant information
@app.get("/restaurant")
async def get_restaurant(current_user: User = Depends(get_current_user)):
    db = Database()
    restaurant = db.get_restaurant()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant information not found")
    return restaurant


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: Optional[str] = None
    is_active: Optional[bool] = None


# Update restaurant information
@app.put("/restaurant/{restaurant_id}")
async def update_restaurant(
    restaurant_id: int,
    data: RestaurantUpdate,
    current_user: User = Depends(get_current_user),
):
    db = Database()
    try:
        restaurant = (
            db.session.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        )
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        if data.name is not None:
            restaurant.name = data.name
        if data.address is not None:
            restaurant.address = data.address
        if data.phone is not None:
            restaurant.phone = data.phone
        if data.email is not None:
            restaurant.email = data.email
        if data.opening_hours is not None:
            restaurant.opening_hours = data.opening_hours
        if data.is_active is not None:
            restaurant.is_active = data.is_active

        db.safe_commit()
        return restaurant
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to update restaurant information: {str(e)}"
        )


class TimeUpdate(BaseModel):
    minutes: int


@app.post("/set-time/{order_id}")
async def set_order_time(
    order_id: int, time_data: TimeUpdate, current_user: User = Depends(get_current_user)
):
    db = Database()
    try:
        order = db.session.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order.estimated_preparation_time = time_data.minutes
        db.safe_commit()

        # Get restaurant info for notifications
        restaurant = db.get_restaurant()
        restaurant_name = restaurant.name if restaurant else "Our Restaurant"

        # Send SMS notification about time update
        try:
            from app.twilio_service import send_time_update_sms

            # Send SMS notification
            sms_result = send_time_update_sms(
                order.customer_phone, order.id, restaurant_name, time_data.minutes
            )

            message = f"Order time set to {time_data.minutes} minutes"
            if sms_result["success"]:
                message += f" - Time update SMS sent to customer"
            else:
                print(f"Time update SMS failed: {sms_result.get('error')}")

            return {"success": True, "message": message}
        except Exception as sms_error:
            # Log the error but don't fail the update
            print(f"Error sending time update SMS: {str(sms_error)}")
            return {
                "success": True,
                "message": f"Order time set to {time_data.minutes} minutes",
            }
    except Exception as e:
        db.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
