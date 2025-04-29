from app.database import Database, MenuItem, AddOn, Customer, Restaurant
from app.user_model import User, Base as UserBase
from sqlalchemy import inspect


def init_database():
    db = Database()

    # Ensure users table exists
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        print("Creating users table...")
        UserBase.metadata.create_all(db.engine)
        print("Users table created.")
    else:
        print("Users table already exists.")

    # Clear existing data
    # db.session.query(MenuItem).delete()
    # db.session.query(AddOn).delete()
    # db.session.query(Customer).delete()

    # Add menu items
    menu_items = [
        MenuItem(
            name="Classic Burger",
            category="burger",
            base_price=8.99,
            description="Juicy beef patty with lettuce, tomato, and our special sauce",
            is_available=1,
        ),
        MenuItem(
            name="Cheeseburger",
            category="burger",
            base_price=9.99,
            description="Classic burger with melted cheddar cheese",
            is_available=1,
        ),
        MenuItem(
            name="Bacon Burger",
            category="burger",
            base_price=10.99,
            description="Classic burger with crispy bacon strips",
            is_available=1,
        ),
        MenuItem(
            name="Veggie Burger",
            category="burger",
            base_price=9.49,
            description="Plant-based patty with fresh vegetables",
            is_available=1,
        ),
        MenuItem(
            name="Margherita Pizza",
            category="pizza",
            base_price=12.99,
            description="Classic pizza with tomato sauce, mozzarella, and basil",
            is_available=1,
        ),
        MenuItem(
            name="Pepperoni Pizza",
            category="pizza",
            base_price=14.99,
            description="Traditional pizza with pepperoni and cheese",
            is_available=1,
        ),
        MenuItem(
            name="Veggie Supreme",
            category="pizza",
            base_price=13.99,
            description="Pizza loaded with fresh vegetables",
            is_available=1,
        ),
        # Example of unavailable item
        MenuItem(
            name="BBQ Chicken Pizza",
            category="pizza",
            base_price=15.99,
            description="Pizza with BBQ sauce, chicken, and red onions",
            is_available=0,
        ),
    ]

    # Add add-ons
    add_ons = [
        AddOn(
            name="Extra Cheese",
            category="burger",
            price=1.50,
            type="topping",
            is_available=1,
        ),
        AddOn(
            name="Bacon", category="burger", price=2.00, type="topping", is_available=1
        ),
        AddOn(
            name="Avocado",
            category="burger",
            price=1.75,
            type="topping",
            is_available=1,
        ),
        AddOn(
            name="Regular", category="burger", price=0.00, type="size", is_available=1
        ),
        AddOn(
            name="Double Patty",
            category="burger",
            price=3.50,
            type="size",
            is_available=1,
        ),
        AddOn(
            name="Regular Ketchup",
            category="burger",
            price=0.00,
            type="sauce",
            is_available=1,
        ),
        AddOn(
            name="Spicy Mayo",
            category="burger",
            price=0.75,
            type="sauce",
            is_available=1,
        ),
        AddOn(
            name="BBQ Sauce",
            category="burger",
            price=0.75,
            type="sauce",
            is_available=1,
        ),
        AddOn(
            name="Extra Cheese",
            category="pizza",
            price=2.00,
            type="topping",
            is_available=1,
        ),
        AddOn(
            name="Mushrooms",
            category="pizza",
            price=1.50,
            type="topping",
            is_available=1,
        ),
        AddOn(
            name="Olives", category="pizza", price=1.50, type="topping", is_available=1
        ),
        AddOn(
            name="Peppers", category="pizza", price=1.50, type="topping", is_available=1
        ),
        AddOn(
            name='Small (8")',
            category="pizza",
            price=-2.00,
            type="size",
            is_available=1,
        ),
        AddOn(
            name='Medium (12")',
            category="pizza",
            price=0.00,
            type="size",
            is_available=1,
        ),
        AddOn(
            name='Large (16")',
            category="pizza",
            price=4.00,
            type="size",
            is_available=1,
        ),
        AddOn(
            name="Regular Tomato",
            category="pizza",
            price=0.00,
            type="sauce",
            is_available=1,
        ),
        AddOn(
            name="White Sauce",
            category="pizza",
            price=1.00,
            type="sauce",
            is_available=1,
        ),
        AddOn(
            name="Spicy Tomato",
            category="pizza",
            price=0.75,
            type="sauce",
            is_available=1,
        ),
    ]

    # Add sample customers
    # customers = [
    #     Customer(
    #         name="John Smith",
    #         phone="5551234567",
    #         email="john.smith@example.com",
    #         preferred_payment_method="credit card",
    #         dietary_preferences="no preferences",
    #         total_orders=5,
    #     ),
    #     Customer(
    #         name="Emily Johnson",
    #         phone="5559876543",
    #         email="emily.j@example.com",
    #         preferred_payment_method="cash",
    #         dietary_preferences="vegetarian",
    #         total_orders=3,
    #     ),
    #     Customer(
    #         name="Michael Brown",
    #         phone="5552223333",
    #         email="mbrown@example.com",
    #         preferred_payment_method="digital payment",
    #         dietary_preferences="gluten-free",
    #         total_orders=7,
    #     ),
    #     Customer(
    #         name="Sarah Williams",
    #         phone="5554445555",
    #         email="sarahw@example.com",
    #         preferred_payment_method="credit card",
    #         dietary_preferences="dairy-free",
    #         total_orders=2,
    #     ),
    #     Customer(
    #         name="David Miller",
    #         phone="5556667777",
    #         email="dmiller@example.com",
    #         preferred_payment_method="cash",
    #         dietary_preferences="no preferences",
    #         total_orders=0,
    #     ),
    # ]

    # Add restaurant data (will only be added if no restaurant exists)
    restaurant = Restaurant(
        name="Tote AI Restaurant",
        address="123 Main Street, Downtown, CA 94123",
        phone="(555) 123-4567",
        email="info@toteairestaurant.com",
        opening_hours="Monday-Sunday: 11:00 AM - 10:00 PM",
        is_active=True,
    )

    # Add all items to database
    for item in menu_items:
        db.session.add(item)

    for addon in add_ons:
        db.session.add(addon)

    # for customer in customers:
    #     db.session.add(customer)

    # Clear existing restaurants and add new one
    db.session.query(Restaurant).delete()
    db.session.add(restaurant)

    db.session.commit()
    print(
        "Database initialized with menu items, add-ons, customer details, and restaurant information!"
    )


if __name__ == "__main__":
    init_database()
