from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.user_model import UserManager, User
from app.database import Database
import os
from fastapi import Header

# Initialize router
router = APIRouter(
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


class AdminUserCreate(BaseModel):
    username: str
    email: str
    password: str
    is_admin: Optional[bool] = False


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool


# Full user response including all fields
class FullUserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Dependency to get the current user
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


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


# Dependency to check if user is admin
def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this endpoint",
        )
    return current_user


# User registration endpoint
@router.post("/users/register", response_model=UserResponse)
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
@router.post("/users/login", response_model=TokenResponse)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}",
        )


# Form-based login for compatibility
@router.post("/users/token", include_in_schema=False)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = user_manager.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = user_manager.generate_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


# Get current user info
@router.get("/users/me", response_model=UserResponse)
async def get_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
    )


# Update current user's info
@router.put("/users/me", response_model=UserResponse)
async def update_user_info(
    user_update: dict, current_user: User = Depends(get_current_user)
):
    # Remove sensitive fields that shouldn't be updated directly
    if "is_admin" in user_update:
        del user_update["is_admin"]
    if "password" in user_update:
        del user_update["password"]

    try:
        db.begin_transaction()
        updated_user = user_manager.update_user(current_user.id, **user_update)
        db.commit()

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
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}",
        )


# Change password endpoint
@router.post("/users/change-password")
async def change_password(
    password_change: dict, current_user: User = Depends(get_current_user)
):
    if (
        "current_password" not in password_change
        or "new_password" not in password_change
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both current_password and new_password are required",
        )

    # Verify current password
    user = user_manager.authenticate_user(
        current_user.email, password_change["current_password"]
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    try:
        db.begin_transaction()
        user_manager.update_user(
            current_user.id, password=password_change["new_password"]
        )
        db.commit()
        return {"message": "Password changed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}",
        )


# --- ADMIN ENDPOINTS ---


# Get all users (admin only)
@router.get("/admin/users", response_model=List[FullUserResponse])
async def admin_get_all_users(current_user: User = Depends(get_admin_user)):
    try:
        users = db.session.query(User).all()
        return [
            FullUserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else "",
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}",
        )


# Create new user (admin only)
@router.post("/admin/users", response_model=FullUserResponse)
async def admin_create_user(
    user_data: AdminUserCreate, current_user: User = Depends(get_admin_user)
):
    try:
        db.begin_transaction()

        new_user = user_manager.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )

        if user_data.is_admin:
            new_user.is_admin = True
            db.session.commit()

        if not db.commit():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to commit the transaction",
            )

        return FullUserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            is_admin=new_user.is_admin,
            is_active=new_user.is_active,
            created_at=new_user.created_at.isoformat() if new_user.created_at else "",
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}",
        )


# Get user by ID (admin only)
@router.get("/admin/users/{user_id}", response_model=FullUserResponse)
async def admin_get_user(user_id: int, current_user: User = Depends(get_admin_user)):
    user = user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return FullUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


# Update user by ID (admin only)
@router.patch("/admin/users/{user_id}", response_model=FullUserResponse)
async def admin_update_user(
    user_id: int, user_data: UserUpdate, current_user: User = Depends(get_admin_user)
):
    # Don't allow updating own admin status
    if str(user_id) == str(current_user.id) and user_data.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges",
        )

    try:
        db.begin_transaction()

        # Convert to dict and remove None values
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}

        # Update user
        updated_user = user_manager.update_user(user_id, **update_data)

        if not updated_user:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        db.commit()

        return FullUserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            is_admin=updated_user.is_admin,
            is_active=updated_user.is_active,
            created_at=(
                updated_user.created_at.isoformat() if updated_user.created_at else ""
            ),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}",
        )


# Delete user by ID (admin only)
@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, current_user: User = Depends(get_admin_user)):
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    try:
        user = user_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Deactivate the user instead of hard delete
        db.begin_transaction()
        user.is_active = False
        db.session.commit()
        db.commit()

        return {"message": "User deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}",
        )
