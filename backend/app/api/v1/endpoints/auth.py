from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict
import logging
import json
from datetime import datetime, timedelta
from pydantic import BaseModel

from ....database import get_db
from ....services.user import UserService
from ....schemas.user import UserCreate, UserUpdate, UserLogin

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# Define simplified response models
class UserResponse(BaseModel):
    id: int
    username: str
    email: str = None
    preferences: Dict[str, Any] = {}

# Define response model for auth endpoints
class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Simplified auth endpoints
@router.post("/register", response_model=AuthResponse)
async def register(
    request: Request,
    *, 
    db: Session = Depends(get_db), 
    user_in: UserCreate
) -> Any:
    """Register new user."""
    # Log raw request body
    body = await request.body()
    logger.debug(f"Raw request body: {body.decode()}")
    
    logger.debug(f"Registration attempt received")
    logger.debug(f"Username: {user_in.username}")
    logger.debug(f"Email: {user_in.email}")
    logger.debug(f"Password length: {len(user_in.password)}")
    logger.debug(f"Is active: {user_in.is_active}")
    logger.debug(f"Preferences: {user_in.preferences}")
    
    # Check if username exists
    user = UserService.get_user_by_username(db, username=user_in.username)
    if user:
        logger.debug(f"Username already exists: {user_in.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    # Create user
    logger.debug("Attempting to create user")
    user = UserService.create_user(db, user_in)
    logger.debug("User created successfully")
    
    # Generate access token
    logger.debug("Generating access token")
    access_token = UserService.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=60 * 24)  # 24 hours
    )
    logger.debug("Access token generated successfully")
    
    # Return user data with access token
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "preferences": user.preferences or {}
        }
    }
    logger.debug(f"Registration response: {response_data}")
    
    return response_data

@router.post("/login")
async def login(
    *,
    db: Session = Depends(get_db),
    user_in: UserLogin
) -> Any:
    """Simple login endpoint."""
    # Log the request data
    logger.debug(f"Login attempt - Username: {user_in.username}")
    logger.debug(f"Login data: {user_in}")
    
    try:
        # Authenticate user
        logger.debug(f"Attempting to authenticate user: {user_in.username}")
        user = UserService.authenticate_user(db, user_in.username, user_in.password)
        if not user:
            logger.debug(f"Authentication failed for user: {user_in.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        
        logger.debug(f"Authentication successful for user: {user_in.username}")
        logger.debug(f"User data: id={user.id}, username={user.username}, email={user.email}")
        
        # Generate access token
        logger.debug("Generating access token")
        access_token = UserService.create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=60 * 24)  # 24 hours
        )
        logger.debug("Access token generated successfully")
        
        # Log the response data
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "preferences": user.preferences or {}
            }
        }
        logger.debug(f"Login response: {response_data}")
        
        return response_data
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.exception("Full traceback:")
        raise

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user = Depends(UserService.get_current_user)
) -> Any:
    """Get current user information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "preferences": current_user.preferences or {}
    }

@router.put("/preferences")
async def update_preferences(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(UserService.get_current_user),
    preferences: Dict[str, Any] = Body(...)
) -> Any:
    """Update user preferences."""
    logger.debug(f"Updating preferences for user {current_user.username}")
    logger.debug(f"New preferences: {preferences}")
    
    # Update preferences for current user
    user = UserService.update_user(
        db,
        user_id=current_user.id,
        user=UserUpdate(preferences=preferences)
    )
    logger.debug(f"Updated user preferences: {user.preferences}")
    return {"preferences": user.preferences} 