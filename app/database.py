from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    JSON,
    inspect,
    text,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import json
import time
from app.user_model import User, Base as UserBase

Base = declarative_base()


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # 'burger', 'pizza', etc.
    base_price = Column(Float, nullable=False)
    description = Column(String)
    is_available = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AddOn(Base):
    __tablename__ = "add_ons"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # 'burger', 'pizza', etc.
    type = Column(String, nullable=True)  # 'topping', 'size', 'drink', etc.
    is_available = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    order_items = Column(JSON, nullable=False)  # Store order items as JSON
    total_amount = Column(Float, nullable=False)
    status = Column(
        String, default="pending"
    )  # pending, confirmed, preparing, ready, delivered
    estimated_preparation_time = Column(Integer)  # in minutes
    payment_method = Column(String)
    special_instructions = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    email = Column(String)  # Add email field
    preferred_payment_method = Column(String)
    dietary_preferences = Column(String)  # e.g., "vegetarian", "no-pork", etc.
    last_order_date = Column(DateTime)
    total_orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with orders
    orders = relationship("Order", backref="customer", lazy=True)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String)
    opening_hours = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Database:
    def __init__(self):
        try:
            # Construct database URL from individual environment variables
            db_user = os.getenv("DATABASE_USER", "postgres")
            db_password = os.getenv("DATABASE_PASSWORD", "postgres")
            db_host = os.getenv("DATABASE_HOST", "localhost")
            db_port = os.getenv("DATABASE_PORT", "5432")
            db_name = os.getenv("DATABASE_NAME", "tote")

            # Build the connection string
            database_url = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )
            print(f"Using database URL: {database_url}")

            self.engine = create_engine(database_url)

            # Create all tables including User table from user_model
            Base.metadata.create_all(self.engine)
            UserBase.metadata.create_all(self.engine)

            # Initialize session
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

            # Ensure all required columns exist
            self._ensure_all_columns()

            # Initialize restaurant data if none exists
            self._initialize_restaurant()

            # Make sure User table exists
            self._ensure_user_table()

        except Exception as e:
            print(f"Error initializing database: {e}")
            raise

    def _ensure_all_columns(self):
        """Ensure all required columns exist in all tables."""
        inspector = inspect(self.engine)

        # Check and add columns for customers table
        customer_columns = {
            "name": "VARCHAR",
            "phone": "VARCHAR",
            "email": "VARCHAR",  # Add email field
            "preferred_payment_method": "VARCHAR",
            "dietary_preferences": "VARCHAR",
            "last_order_date": "TIMESTAMP",
            "total_orders": "INTEGER",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        # Check and add columns for orders table
        order_columns = {
            "customer_id": "INTEGER",
            "customer_name": "VARCHAR",
            "customer_phone": "VARCHAR",
            "order_items": "JSON",
            "total_amount": "FLOAT",
            "status": "VARCHAR",
            "estimated_preparation_time": "INTEGER",
            "payment_method": "VARCHAR",
            "special_instructions": "VARCHAR",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        # Add missing columns to customers table
        existing_customer_columns = [
            col["name"] for col in inspector.get_columns("customers")
        ]
        with self.engine.connect() as conn:
            for column, type_ in customer_columns.items():
                if column not in existing_customer_columns:
                    conn.execute(
                        text(f"ALTER TABLE customers ADD COLUMN {column} {type_}")
                    )

            # Add missing columns to orders table
            existing_order_columns = [
                col["name"] for col in inspector.get_columns("orders")
            ]
            for column, type_ in order_columns.items():
                if column not in existing_order_columns:
                    conn.execute(
                        text(f"ALTER TABLE orders ADD COLUMN {column} {type_}")
                    )

            # Add foreign key constraint if it doesn't exist
            try:
                conn.execute(
                    text(
                        """
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.table_constraints 
                            WHERE constraint_name = 'orders_customer_id_fkey'
                        ) THEN
                            ALTER TABLE orders 
                            ADD CONSTRAINT orders_customer_id_fkey 
                            FOREIGN KEY (customer_id) 
                            REFERENCES customers(id);
                        END IF;
                    END $$;
                """
                    )
                )
            except Exception as e:
                print(f"Warning: Could not add foreign key constraint: {e}")

            conn.commit()

    def _initialize_restaurant(self):
        """Initialize restaurant data if none exists."""
        restaurant_count = self.session.query(Restaurant).count()
        if restaurant_count == 0:
            restaurant = Restaurant(
                name="Tote AI Restaurant",
                address="123 Main Street, Downtown, CA 94123",
                phone="(555) 123-4567",
                email="info@toteairestaurant.com",
                opening_hours="Monday-Sunday: 11:00 AM - 10:00 PM",
            )
            self.session.add(restaurant)
            self.session.commit()
            print(f"Initialized restaurant data: {restaurant.name}")

    def get_restaurant(self):
        """Get the restaurant information."""
        return (
            self.session.query(Restaurant).filter(Restaurant.is_active == True).first()
        )

    def get_menu(self, category=None):
        query = self.session.query(MenuItem)
        if category:
            query = query.filter(MenuItem.category == category)
        return query.filter(MenuItem.is_available == 1).all()

    def get_add_ons(self, category=None):
        query = self.session.query(AddOn)
        if category:
            query = query.filter(AddOn.category == category)
        return query.filter(AddOn.is_available == 1).all()

    def find_similar_menu_item(self, item_name, category=None):
        if not item_name:
            return None

        item_name_lower = item_name.lower()
        query = self.session.query(MenuItem)

        if category:
            query = query.filter(MenuItem.category == category)

        # Try exact match first
        exact_match = query.filter(MenuItem.name.ilike(item_name_lower)).first()
        if exact_match:
            return exact_match

        # Try contains match
        for item in query.all():
            if (
                item_name_lower in item.name.lower()
                or item.name.lower() in item_name_lower
            ):
                return item

        return None

    def create_customer(self, name, phone, auto_commit=False, **kwargs):
        try:
            customer = Customer(
                name=name,
                phone=str(phone),  # Ensure phone is stored as string
                **kwargs,
            )
            self.session.add(customer)
            self.session.flush()  # Get ID without committing yet

            # Auto-commit if requested
            if auto_commit:
                if not self.safe_commit():
                    print("Failed to commit customer creation after multiple retries")
                    raise Exception("Failed to commit customer creation")

            return customer
        except Exception as e:
            import traceback

            print(f"Error creating customer: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            self.session.rollback()
            raise

    def get_customer_by_phone(self, phone):
        # Search by phone as string
        return self.session.query(Customer).filter(Customer.phone == str(phone)).first()

    def update_customer(self, phone, auto_commit=False, **kwargs):
        # Find customer by phone (as string)
        customer = self.get_customer_by_phone(str(phone))
        if not customer:
            return None

        try:
            # If phone is being updated, ensure it's stored as string
            if "phone" in kwargs:
                kwargs["phone"] = str(kwargs["phone"])

            for key, value in kwargs.items():
                setattr(customer, key, value)

            self.session.flush()  # Flush changes without committing yet

            # Auto-commit if requested
            if auto_commit:
                if not self.safe_commit():
                    print("Failed to commit customer update after multiple retries")
                    raise Exception("Failed to commit customer update")

            return customer
        except Exception as e:
            import traceback

            print(f"Error updating customer: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            self.session.rollback()
            raise

    def get_customer_order_history(self, phone):
        # Find orders by phone (as string)
        return (
            self.session.query(Order)
            .filter(Order.customer_phone == str(phone))
            .order_by(Order.created_at.desc())
            .all()
        )

    def create_order(
        self,
        customer_name,
        customer_phone,
        order_items,
        total_amount,
        payment_method=None,
        special_instructions=None,
        auto_commit=False,
    ):
        try:
            # Store customer_phone as string
            customer_phone_str = str(customer_phone)
            print(f"Creating order for: {customer_name}, phone: {customer_phone_str}")

            # Check if customer exists
            customer = self.get_customer_by_phone(customer_phone_str)
            if not customer:
                print(f"Customer not found, creating new customer: {customer_name}")
                # Create a new customer with minimal information
                try:
                    customer = Customer(
                        name=customer_name,
                        phone=customer_phone_str,
                    )
                    self.session.add(customer)
                    self.session.flush()  # Get ID without committing yet
                    print(f"New customer created with ID: {customer.id}")
                except Exception as e:
                    print(f"Error creating customer: {e}")
                    self.session.rollback()
                    raise

            # Update customer's last order date and total orders
            print(f"Updating customer data for ID: {customer.id}")
            customer.last_order_date = datetime.utcnow()
            customer.total_orders += 1

            # Calculate estimated preparation time
            estimated_preparation_time = self._calculate_preparation_time(order_items)
            print(f"Estimated preparation time: {estimated_preparation_time} minutes")

            # Create the order
            print(
                f"Creating order with: {len(order_items)} items, total: ${total_amount}"
            )

            # Ensure order_items is properly serialized as JSON
            order_items_json = order_items
            if not isinstance(order_items, str):
                try:
                    # Check if we can serialize and deserialize it
                    order_items_json = json.dumps(order_items)
                    json.loads(order_items_json)
                    print(
                        f"Successfully serialized order_items: {order_items_json[:100]}"
                    )
                except Exception as e:
                    print(f"Error serializing order_items: {e}")
                    print(f"Original order_items: {order_items}")
                    raise

            order = Order(
                customer_id=customer.id,
                customer_name=customer_name,
                customer_phone=customer_phone_str,
                order_items=order_items,  # SQLAlchemy should handle JSON serialization
                total_amount=total_amount,
                payment_method=payment_method,
                special_instructions=special_instructions,
                estimated_preparation_time=estimated_preparation_time,
            )
            self.session.add(order)

            # Flush to get the ID but don't commit yet
            self.session.flush()
            print(f"Order prepared with ID: {order.id}")

            # Auto-commit if requested
            if auto_commit:
                if not self.safe_commit():
                    print("Failed to commit order creation after multiple retries")
                    raise Exception("Failed to commit order creation")

            return order
        except Exception as e:
            import traceback

            print(f"Unexpected error in create_order: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            self.session.rollback()
            raise

    def _calculate_preparation_time(self, order_items):
        # Simple implementation - can be made more sophisticated
        base_time = 20  # Base preparation time in minutes
        items_count = len(order_items)
        return base_time + (items_count * 5)  # 5 minutes per additional item

    def get_order_status(self, order_id):
        return self.session.query(Order).filter(Order.id == order_id).first()

    def update_order_status(self, order_id, status, estimated_preparation_time=None):
        order = self.session.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status

            # Update estimated preparation time if provided
            if estimated_preparation_time is not None:
                print(
                    f"Updating order {order_id} estimated_preparation_time to {estimated_preparation_time}"
                )
                order.estimated_preparation_time = estimated_preparation_time

            self.session.commit()
            return order
        return None

    def safe_commit(self):
        """Safely commit changes to the database."""
        try:
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error committing changes: {e}")
            self.session.rollback()
            return False

    def begin_transaction(self):
        """Begin a new transaction."""
        # SQLAlchemy automatically starts a transaction when needed,
        # but this method is provided for clarity
        pass

    def commit(self):
        """Commit the current transaction."""
        return self.safe_commit()

    def rollback(self):
        """Roll back the current transaction."""
        try:
            self.session.rollback()
            return True
        except Exception as e:
            print(f"Error rolling back transaction: {e}")
            return False

    def _ensure_user_table(self):
        """Ensure the User table exists and has the correct schema."""
        inspector = inspect(self.engine)
        user_table_exists = "users" in inspector.get_table_names()

        if not user_table_exists:
            print("Creating users table...")
            UserBase.metadata.create_all(self.engine)

            # Verify table was created
            inspector = inspect(self.engine)
            if "users" in inspector.get_table_names():
                print("Users table created successfully")
            else:
                print("WARNING: Failed to create users table")
        else:
            print("Users table already exists")
