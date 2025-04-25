#!/usr/bin/env python
from app.db_operations import Database, Customer, Order, MenuItem, AddOn
import traceback


def test_database_operations():
    try:
        print("Initializing database connection...")
        db = Database()

        # Test basic database connectivity
        print("\n--- Testing Database Connectivity ---")
        menu_items = db.get_menu()
        print(f"Found {len(menu_items)} menu items")
        for item in menu_items[:3]:  # Show first 3 items
            print(f"- {item.name}: ${item.base_price}")

        # Test customer creation
        print("\n--- Testing Customer Creation ---")
        try:
            test_customer = db.create_customer(
                name="Test Customer",
                phone="1234567890",
                email="test@example.com",
                auto_commit=True,
            )
            # The customer is auto-committed now
            print(f"Created test customer with ID: {test_customer.id}")
        except Exception as e:
            print(f"Failed to create customer: {e}")
            print(traceback.format_exc())

        # Test customer retrieval
        print("\n--- Testing Customer Retrieval ---")
        try:
            found_customer = db.get_customer_by_phone("1234567890")
            if found_customer:
                print(
                    f"Found customer: {found_customer.name} (ID: {found_customer.id})"
                )
            else:
                print("Customer not found")
        except Exception as e:
            print(f"Failed to retrieve customer: {e}")
            print(traceback.format_exc())

        # Test order creation
        print("\n--- Testing Order Creation ---")
        try:
            test_order_items = [
                {
                    "item_name": "Classic Burger",
                    "quantity": 2,
                    "add_ons": ["Extra Cheese"],
                }
            ]

            test_order = db.create_order(
                customer_name="Test Customer",
                customer_phone="1234567890",
                order_items=test_order_items,
                total_amount=19.99,
                special_instructions="No onions please",
                auto_commit=True,
            )
            # The order is auto-committed now
            print(f"Created order with ID: {test_order.id}")
        except Exception as e:
            print(f"Failed to create order: {e}")
            print(traceback.format_exc())

        # Test order retrieval
        print("\n--- Testing Order Retrieval ---")
        try:
            customer_orders = db.get_customer_order_history("1234567890")
            print(f"Found {len(customer_orders)} orders for customer")
            for order in customer_orders:
                print(f"- Order #{order.id}, total: ${order.total_amount}")
        except Exception as e:
            print(f"Failed to retrieve orders: {e}")
            print(traceback.format_exc())

    except Exception as e:
        print(f"Test failed with error: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    test_database_operations()
