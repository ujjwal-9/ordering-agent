from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.user_model import UserManager, User
from app.database import Database
import os
from fastapi import Header

# Initialize router
router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Initialize database connection
db = Database()

# Create UserManager
user_manager = UserManager(
    db.session, os.getenv("JWT_SECRET_KEY", "default_secret_key")
)


# Pydantic models for request and response
class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Dependency to get the current user
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


async def get_current_user(authorization: str = Header(None)):
    """
    Dependency to get the current user from the authorization token.
    """
    print(f"Authorization header received: {authorization}")
    if not authorization:
        print("No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from header
    try:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
        else:
            token = authorization

        print(f"Extracted token (first 10 chars): {token[:10]}...")

        # Verify token
        user_id = user_manager.verify_token(token)
        if not user_id:
            print("Token verification failed - no user_id returned")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        print(f"Token verified successfully. User ID: {user_id}")

        # Get user from database
        user = user_manager.get_user_by_id(user_id)
        if not user:
            print(f"User with ID {user_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        print(f"User authenticated: {user.username} (ID: {user.id})")
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# User registration endpoint
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    try:
        # Check if the database and user_manager are properly initialized
        if not db or not user_manager:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection not initialized",
            )

        # Explicitly begin a new transaction
        db.begin_transaction()

        new_user = user_manager.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )

        # Ensure the transaction is committed
        if not db.commit():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to commit the transaction",
            )

        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            is_admin=new_user.is_admin,
        )
    except ValueError as e:
        # For expected validation errors (like duplicate users)
        print(f"Validation error in register: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # For unexpected errors
        print(f"Error registering user: {str(e)}")
        # Ensure transaction is rolled back in the database connection
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}",
        )


# User login endpoint with direct JSON body
@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    try:
        print(f"Login attempt for email: {user_data.email}")
        user = user_manager.authenticate_user(user_data.email, user_data.password)
        if not user:
            print(f"Authentication failed for email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate token
        token = user_manager.generate_token(user.id)
        print(
            f"Token generated for user: {user.username} (ID: {user.id}), token starts with: {token[:10]}..."
        )

        # Verify the token works (debug only)
        verified_id = user_manager.verify_token(token)
        if verified_id != user.id:
            print(f"WARNING: Token verification failed immediately after generation!")

        response = TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_admin=user.is_admin,
            ),
        )
        print(f"Login successful for user: {user.username}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during login: {str(e)}")
        db.rollback()  # Ensure transaction is rolled back for any error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}",
        )


# OAuth compatible login endpoint for Swagger UI
@router.post("/token", include_in_schema=False)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # OAuth form expects username field, but we use email
        user = user_manager.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate token
        token = user_manager.generate_token(user.id)

        # Return token in the format expected by OAuth
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        print(f"Error during OAuth login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}",
        )


# Get current user info
@router.get("/me", response_model=UserResponse)
async def get_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
    )


# Update user info
@router.put("/me", response_model=UserResponse)
async def update_user_info(
    user_update: dict, current_user: User = Depends(get_current_user)
):
    # Remove sensitive fields that shouldn't be updated directly
    safe_update = {
        k: v
        for k, v in user_update.items()
        if k not in ["id", "password_hash", "salt", "is_admin"]
    }

    updated_user = user_manager.update_user(current_user.id, **safe_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        is_admin=updated_user.is_admin,
    )


# Change password
@router.post("/change-password")
async def change_password(
    password_change: dict, current_user: User = Depends(get_current_user)
):
    if "old_password" not in password_change or "new_password" not in password_change:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing old_password or new_password",
        )

    # Verify old password
    if not User.verify_password(
        password_change["old_password"], current_user.password_hash, current_user.salt
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password"
        )

    # Update password
    user_manager.update_user(current_user.id, password=password_change["new_password"])

    return {"message": "Password updated successfully"}
