from app.user_model import UserManager, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging

# Enable SQLAlchemy logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Connect to the database
engine = create_engine("postgresql://postgres:postgres@localhost:5432/tote")
Session = sessionmaker(bind=engine)
session = Session()

# Create a user manager
manager = UserManager(session)


def test_login():
    try:
        # Try to login with test user credentials
        user = manager.authenticate_user("test@example.com", "password123")

        if user:
            print(
                f"Login successful: User ID={user.id}, Username={user.username}, Email={user.email}"
            )

            # Generate a token
            token = manager.generate_token(user.id)
            print(f"Generated token (first 20 chars): {token[:20]}...")

            # Verify the token
            user_id = manager.verify_token(token)

            # Convert user_id to int for comparison (token verification returns a string)
            user_id_int = int(user_id) if user_id else None

            if user_id_int == user.id:
                print(f"Token verification successful: User ID={user_id}")
            else:
                print(f"Token verification failed: Expected {user.id}, got {user_id}")

        else:
            print("Login failed: Incorrect email or password")

    except Exception as e:
        print(f"Error during login: {e}")
        session.rollback()


if __name__ == "__main__":
    test_login()
