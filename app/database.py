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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

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
    is_available = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    delivery_address = Column(String, nullable=False)
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
    address = Column(String, nullable=False)
    preferred_payment_method = Column(String)
    dietary_preferences = Column(String)  # e.g., "vegetarian", "no-pork", etc.
    last_order_date = Column(DateTime)
    total_orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with orders
    orders = relationship("Order", backref="customer", lazy=True)


class Database:
    def __init__(self):
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/tote",
        )
        self.engine = create_engine(database_url)

        # Create all tables
        Base.metadata.create_all(self.engine)

        # Initialize session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Ensure all required columns exist
        self._ensure_all_columns()

    def _ensure_all_columns(self):
        """Ensure all required columns exist in all tables."""
        inspector = inspect(self.engine)

        # Check and add columns for customers table
        customer_columns = {
            "name": "VARCHAR",
            "phone": "VARCHAR",
            "address": "VARCHAR",
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
            "delivery_address": "VARCHAR",
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
        # This is a simple implementation. In production, you might want to use
        # more sophisticated fuzzy matching or vector similarity search
        query = self.session.query(MenuItem)
        if category:
            query = query.filter(MenuItem.category == category)
        items = query.filter(MenuItem.is_available == 1).all()

        # Simple string matching - can be improved with better algorithms
        best_match = None
        highest_similarity = 0

        for item in items:
            similarity = self._calculate_similarity(
                item_name.lower(), item.name.lower()
            )
            if (
                similarity > highest_similarity and similarity > 0.6
            ):  # 60% similarity threshold
                highest_similarity = similarity
                best_match = item

        return best_match

    def _calculate_similarity(self, str1, str2):
        # Simple Levenshtein distance implementation
        # In production, use a proper string similarity library
        if len(str1) < len(str2):
            str1, str2 = str2, str1
        if len(str2) == 0:
            return 0

        previous_row = range(len(str2) + 1)
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        max_len = max(len(str1), len(str2))
        return 1 - (previous_row[-1] / max_len)

    def get_customer_by_phone(self, phone):
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    def create_customer(
        self,
        name,
        phone,
        address,
        preferred_payment_method=None,
        dietary_preferences=None,
    ):
        customer = Customer(
            name=name,
            phone=phone,
            address=address,
            preferred_payment_method=preferred_payment_method,
            dietary_preferences=dietary_preferences,
        )
        self.session.add(customer)
        self.session.commit()
        return customer

    def update_customer(self, phone, **kwargs):
        customer = self.get_customer_by_phone(phone)
        if customer:
            for key, value in kwargs.items():
                setattr(customer, key, value)
            self.session.commit()
            return customer
        return None

    def get_customer_order_history(self, phone):
        customer = self.get_customer_by_phone(phone)
        if customer:
            return (
                self.session.query(Order)
                .filter(Order.customer_phone == phone)
                .order_by(Order.created_at.desc())
                .all()
            )
        return []

    def create_order(
        self,
        customer_name,
        customer_phone,
        delivery_address,
        order_items,
        total_amount,
        payment_method=None,
        special_instructions=None,
    ):
        try:
            # Get or create customer
            customer = self.get_customer_by_phone(customer_phone)
            if not customer:
                customer = self.create_customer(
                    name=customer_name,
                    phone=customer_phone,
                    address=delivery_address,
                )

            # Create order
            order = Order(
                customer_id=customer.id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                delivery_address=delivery_address,
                order_items=order_items,
                total_amount=total_amount,
                payment_method=payment_method,
                special_instructions=special_instructions,
                estimated_preparation_time=self._calculate_preparation_time(
                    order_items
                ),
            )

            # Update customer stats
            customer.last_order_date = datetime.utcnow()
            customer.total_orders += 1

            self.session.add(order)
            self.session.commit()
            return order
        except Exception as e:
            self.session.rollback()
            print(f"Error creating order: {e}")
            raise

    def _calculate_preparation_time(self, order_items):
        # Simple implementation - can be made more sophisticated
        base_time = 20  # Base preparation time in minutes
        items_count = len(order_items)
        return base_time + (items_count * 5)  # 5 minutes per additional item

    def get_order_status(self, order_id):
        return self.session.query(Order).filter(Order.id == order_id).first()

    def update_order_status(self, order_id, status):
        order = self.session.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            self.session.commit()
            return order
        return None
