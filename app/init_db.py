from app.database import Database, MenuItem, AddOn, Customer


def init_database():
    db = Database()

    # Clear existing data
    db.session.query(MenuItem).delete()
    db.session.query(AddOn).delete()
    db.session.query(Customer).delete()

    # Add menu items
    menu_items = [
        MenuItem(
            name="Classic Burger",
            category="burger",
            base_price=8.99,
            description="Juicy beef patty with lettuce, tomato, and our special sauce",
        ),
        MenuItem(
            name="Cheeseburger",
            category="burger",
            base_price=9.99,
            description="Classic burger with melted cheddar cheese",
        ),
        MenuItem(
            name="Bacon Burger",
            category="burger",
            base_price=10.99,
            description="Classic burger with crispy bacon strips",
        ),
        MenuItem(
            name="Veggie Burger",
            category="burger",
            base_price=9.49,
            description="Plant-based patty with fresh vegetables",
        ),
        MenuItem(
            name="Margherita Pizza",
            category="pizza",
            base_price=12.99,
            description="Classic pizza with tomato sauce, mozzarella, and basil",
        ),
        MenuItem(
            name="Pepperoni Pizza",
            category="pizza",
            base_price=14.99,
            description="Traditional pizza with pepperoni and cheese",
        ),
        MenuItem(
            name="Veggie Supreme",
            category="pizza",
            base_price=13.99,
            description="Pizza loaded with fresh vegetables",
        ),
    ]

    # Add add-ons
    add_ons = [
        AddOn(name="Extra Cheese", category="burger", price=1.50),
        AddOn(name="Bacon", category="burger", price=2.00),
        AddOn(name="Avocado", category="burger", price=1.75),
        AddOn(name="Extra Cheese", category="pizza", price=2.00),
        AddOn(name="Mushrooms", category="pizza", price=1.50),
        AddOn(name="Olives", category="pizza", price=1.50),
    ]

    # Add sample customers
    customers = [
        Customer(
            name="John Smith",
            phone="5551234567",
            address="123 Main St, Anytown, CA 94105",
            email="john.smith@example.com",
            preferred_payment_method="credit card",
            dietary_preferences="no preferences",
            total_orders=5,
        ),
        Customer(
            name="Emily Johnson",
            phone="5559876543",
            address="456 Oak Ave, Somewhere, NY 10001",
            email="emily.j@example.com",
            preferred_payment_method="cash",
            dietary_preferences="vegetarian",
            total_orders=3,
        ),
        Customer(
            name="Michael Brown",
            phone="5552223333",
            address="789 Pine Rd, Elsewhere, TX 75001",
            email="mbrown@example.com",
            preferred_payment_method="digital payment",
            dietary_preferences="gluten-free",
            total_orders=7,
        ),
        Customer(
            name="Sarah Williams",
            phone="5554445555",
            address="321 Cedar Ln, Nowhere, FL 33101",
            email="sarahw@example.com",
            preferred_payment_method="credit card",
            dietary_preferences="dairy-free",
            total_orders=2,
        ),
        Customer(
            name="David Miller",
            phone="5556667777",
            address="654 Birch St, Anywhere, WA 98101",
            email="dmiller@example.com",
            preferred_payment_method="cash",
            dietary_preferences="no preferences",
            total_orders=0,
        ),
    ]

    # Add all items to database
    for item in menu_items:
        db.session.add(item)

    for addon in add_ons:
        db.session.add(addon)

    for customer in customers:
        db.session.add(customer)

    db.session.commit()
    print("Database initialized with menu items, add-ons, and customer details!")


if __name__ == "__main__":
    init_database()
