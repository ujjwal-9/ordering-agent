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
import dotenv
from .user_model import User, Base as UserBase

dotenv.load_dotenv(dotenv_path="../.env")

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
        """Find a menu item with a similar name."""
        query = self.session.query(MenuItem)
        if category:
            query = query.filter(MenuItem.category == category)
        items = query.filter(MenuItem.is_available == 1).all()

        # Simple string matching for now
        item_name = item_name.lower()
        for item in items:
            if item_name in item.name.lower():
                return item
        return None

    def create_customer(self, name, phone, auto_commit=False, **kwargs):
        """Create a new customer."""
        try:
            customer = Customer(name=name, phone=phone, **kwargs)
            self.session.add(customer)
            if auto_commit:
                self.session.commit()
            return customer
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error creating customer: {e}")

    def get_customer_by_phone(self, phone):
        """Get a customer by phone number."""
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    def update_customer(self, phone, auto_commit=False, **kwargs):
        """Update customer information."""
        try:
            customer = self.get_customer_by_phone(phone)
            if not customer:
                raise Exception("Customer not found")

            # Update fields
            for key, value in kwargs.items():
                if hasattr(customer, key):
                    setattr(customer, key, value)

            if auto_commit:
                self.session.commit()
            return customer
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error updating customer: {e}")

    def get_customer_order_history(self, phone):
        """Get order history for a customer."""
        customer = self.get_customer_by_phone(phone)
        if not customer:
            return []
        return self.session.query(Order).filter(Order.customer_id == customer.id).all()

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
        """Create a new order."""
        try:
            # Get or create customer
            customer = self.get_customer_by_phone(customer_phone)
            if not customer:
                customer = self.create_customer(
                    name=customer_name, phone=customer_phone, auto_commit=True
                )

            # Calculate estimated preparation time
            estimated_time = self._calculate_preparation_time(order_items)

            # Create order
            order = Order(
                customer_id=customer.id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                order_items=order_items,
                total_amount=total_amount,
                payment_method=payment_method,
                special_instructions=special_instructions,
                estimated_preparation_time=estimated_time,
            )

            # Update customer information
            customer.last_order_date = datetime.utcnow()
            customer.total_orders += 1

            self.session.add(order)
            if auto_commit:
                self.session.commit()

            return order
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error creating order: {e}")

    def _calculate_preparation_time(self, order_items):
        """Calculate estimated preparation time based on order items."""
        # Simple implementation - can be made more sophisticated
        return len(order_items) * 5  # 5 minutes per item

    def get_order_status(self, order_id):
        """Get the status of an order."""
        order = self.session.query(Order).get(order_id)
        return order.status if order else None

    def update_order_status(self, order_id, status, estimated_preparation_time=None):
        """Update the status of an order."""
        try:
            order = self.session.query(Order).get(order_id)
            if not order:
                raise Exception("Order not found")

            order.status = status
            if estimated_preparation_time is not None:
                order.estimated_preparation_time = estimated_preparation_time

            self.session.commit()
            return order
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error updating order status: {e}")

    def safe_commit(self):
        """Safely commit changes to the database."""
        try:
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error committing changes: {e}")
            return False

    def begin_transaction(self):
        """Begin a new transaction."""
        try:
            self.session.begin()
        except Exception as e:
            print(f"Error beginning transaction: {e}")
            raise

    def commit(self):
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self):
        """Rollback the current transaction."""
        self.session.rollback()

    def _ensure_user_table(self):
        """Ensure the User table exists."""
        inspector = inspect(self.engine)
        if "users" not in inspector.get_table_names():
            UserBase.metadata.create_all(self.engine)
            print("Created users table.")
