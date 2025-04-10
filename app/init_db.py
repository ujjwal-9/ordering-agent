from database import Database, MenuItem, AddOn


def init_database():
    db = Database()

    # Clear existing data
    db.session.query(MenuItem).delete()
    db.session.query(AddOn).delete()

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

    # Add all items to database
    for item in menu_items:
        db.session.add(item)

    for addon in add_ons:
        db.session.add(addon)

    db.session.commit()
    print("Database initialized with menu items and add-ons!")


if __name__ == "__main__":
    init_database()
