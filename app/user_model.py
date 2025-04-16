from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    create_engine,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
import hashlib
import uuid
import jwt
from datetime import datetime, timedelta

# Create a Base for table definition
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def hash_password(password, salt=None):
        if salt is None:
            salt = uuid.uuid4().hex
        hash_obj = hashlib.sha256(password.encode() + salt.encode())
        password_hash = hash_obj.hexdigest()
        return password_hash, salt

    @staticmethod
    def verify_password(password, password_hash, salt):
        computed_hash, _ = User.hash_password(password, salt)
        return computed_hash == password_hash


class UserManager:
    def __init__(self, db_session, secret_key=None):
        self.db_session = db_session
        self.secret_key = secret_key or os.getenv(
            "JWT_SECRET_KEY", "default_secret_key"
        )

    def register_user(self, username, email, password):
        """
        Register a new user.
        Note: Transaction handling should be done by the caller.
        """
        # Check if user with username or email already exists
        existing_user = (
            self.db_session.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )

        if existing_user:
            raise ValueError("User with this username or email already exists")

        # Hash the password with a salt
        password_hash, salt = User.hash_password(password)

        # Create the new user
        new_user = User(
            username=username, email=email, password_hash=password_hash, salt=salt
        )

        # Add to database
        self.db_session.add(new_user)
        # Note: We don't commit here; the caller should handle the transaction.

        return new_user

    def authenticate_user(self, email, password):
        """
        Authenticate a user by email and password.
        This is a read-only operation that doesn't modify the database.
        """
        try:
            # Find user by email
            user = self.db_session.query(User).filter_by(email=email).first()

            if not user or not user.is_active:
                return None

            # Verify password
            if User.verify_password(password, user.password_hash, user.salt):
                return user

            return None
        except Exception as e:
            print(f"Error in authenticate_user: {str(e)}")
            return None

    def generate_token(
        self, user_id, expiration_minutes=60 * 24
    ):  # Default to 24 hours
        """Generate a JWT token for the user"""
        payload = {
            "sub": str(user_id),  # Convert user_id to string
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=expiration_minutes),
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        # If token is bytes, convert to string
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        print(f"Generated token for user {user_id}: {token[:10]}...")
        return token

    def verify_token(self, token):
        """Verify and decode a JWT token"""
        if not token:
            print("Empty token received")
            return None

        try:
            # Handle different token formats
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token.replace("Bearer ", "")

            print(f"Verifying token: {token[:10]}...")

            # Decode with HS256 algorithm
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Extract user_id from subject claim
            user_id = payload["sub"]
            print(f"Token verified successfully for user ID: {user_id}")
            return user_id
        except jwt.ExpiredSignatureError as e:
            print(f"Token expired: {str(e)}")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error verifying token: {str(e)}")
            return None

    def get_user_by_id(self, user_id):
        """Get a user by ID"""
        try:
            return self.db_session.query(User).filter_by(id=user_id).first()
        except Exception as e:
            print(f"Error in get_user_by_id: {str(e)}")
            return None

    def get_user_from_token(self, token):
        """Get a user from a token"""
        user_id = self.verify_token(token)
        if user_id:
            return self.get_user_by_id(user_id)
        return None

    def update_user(self, user_id, **kwargs):
        """Update user details"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # Update fields
        for key, value in kwargs.items():
            if key == "password":
                # Special handling for password updates
                password_hash, salt = User.hash_password(value)
                user.password_hash = password_hash
                user.salt = salt
            elif hasattr(user, key):
                setattr(user, key, value)

        self.db_session.commit()
        return user


# Initialize the database if this module is run directly
if __name__ == "__main__":
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/tote",
    )
    engine = create_engine(database_url)

    # Create all tables
    Base.metadata.create_all(engine)

    # Initialize session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create a user manager
    user_manager = UserManager(session)

    # Check if admin user exists
    admin_user = session.query(User).filter_by(username="admin").first()

    # Create admin user if it doesn't exist
    if not admin_user:
        try:
            admin_user = user_manager.register_user(
                username="admin",
                email="admin@example.com",
                password="admin123",  # This should be a secure password in production
            )
            admin_user.is_admin = True
            session.commit()
            print("Admin user created successfully")
        except Exception as e:
            print(f"Error creating admin user: {e}")
