from typing import Optional
from sqlalchemy.orm import Session
from .models.user import User
from .services.user import UserService
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(db: Session, token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """Get current user from database using JWT token"""
    return await UserService.get_current_user(db, token) 