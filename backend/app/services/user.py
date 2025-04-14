from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from datetime import datetime, timedelta
from jose import jwt
from ..core.config import settings
from fastapi import Depends
from jose.exceptions import JWTError
from fastapi.security import OAuth2PasswordBearer
from ..database import get_db
import logging

# Configure logging
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a stored password against one provided by user."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get a list of users."""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create a new user."""
        logger.debug(f"Starting user creation process for username: {user.username}")
        
        # Check if username exists
        if UserService.get_user_by_username(db, username=user.username):
            logger.debug(f"Username already exists: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email exists
        if user.email and UserService.get_user_by_email(db, email=user.email):
            logger.debug(f"Email already exists: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        logger.debug(f"Creating user object for: {user.username}")
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=UserService.get_password_hash(user.password),
            preferences=user.preferences
        )
        
        try:
            logger.debug("Adding user to database")
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.debug(f"User created successfully: {user.username}")
            return db_user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user"
            )

    @staticmethod
    def update_user(db: Session, user_id: int, user: UserUpdate) -> Optional[User]:
        """Update a user's information."""
        db_user = UserService.get_user(db, user_id=user_id)
        if not db_user:
            return None
        
        update_data = user.model_dump(exclude_unset=True)
        
        if "password" in update_data:
            update_data["hashed_password"] = UserService.get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        logger.debug(f"Attempting to authenticate user: {username}")
        user = UserService.get_user_by_username(db, username=username)
        if not user:
            logger.debug(f"User not found: {username}")
            return None
        if not UserService.verify_password(password, user.hashed_password):
            logger.debug(f"Invalid password for user: {username}")
            return None
        logger.debug(f"User authenticated successfully: {username}")
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Delete a user."""
        user = UserService.get_user(db, user_id=user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True

    @staticmethod
    async def get_current_user(
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme)
    ) -> User:
        """Get current user from token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
            
        user = UserService.get_user_by_username(db, username=username)
        if user is None:
            raise credentials_exception
        return user 