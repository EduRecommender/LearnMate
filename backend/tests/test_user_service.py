import pytest
from sqlalchemy.orm import Session

from app.services.user import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    authenticate_user,
    get_user_by_id
)
from app.models.user import User


def test_get_user_by_username(test_db_session: Session, test_user: User):
    """Test getting a user by username."""
    user = get_user_by_username(test_db_session, username=test_user.username)
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username


def test_get_user_by_username_nonexistent(test_db_session: Session):
    """Test getting a user by username that doesn't exist."""
    user = get_user_by_username(test_db_session, username="nonexistentuser")
    assert user is None


def test_get_user_by_email(test_db_session: Session, test_user: User):
    """Test getting a user by email."""
    user = get_user_by_email(test_db_session, email=test_user.email)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


def test_get_user_by_email_nonexistent(test_db_session: Session):
    """Test getting a user by email that doesn't exist."""
    user = get_user_by_email(test_db_session, email="nonexistent@example.com")
    assert user is None


def test_create_user(test_db_session: Session):
    """Test creating a new user."""
    username = "newserviceuser"
    email = "newserviceuser@example.com"
    password = "password123"
    
    user = create_user(test_db_session, username=username, email=email, password=password)
    assert user is not None
    assert user.username == username
    assert user.email == email
    # Password should be hashed
    assert user.hashed_password != password
    
    # Check that the user was added to the database
    created_user = test_db_session.query(User).filter(User.username == username).first()
    assert created_user is not None
    assert created_user.id == user.id


def test_authenticate_user_valid(test_db_session: Session, test_user: User):
    """Test authenticating a user with valid credentials."""
    user = authenticate_user(test_db_session, username=test_user.username, password="password")
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username


def test_authenticate_user_invalid_password(test_db_session: Session, test_user: User):
    """Test authenticating a user with invalid password."""
    user = authenticate_user(test_db_session, username=test_user.username, password="wrongpassword")
    assert user is None


def test_authenticate_user_nonexistent(test_db_session: Session):
    """Test authenticating a nonexistent user."""
    user = authenticate_user(test_db_session, username="nonexistentuser", password="password")
    assert user is None


def test_get_user_by_id(test_db_session: Session, test_user: User):
    """Test getting a user by ID."""
    user = get_user_by_id(test_db_session, user_id=test_user.id)
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username


def test_get_user_by_id_nonexistent(test_db_session: Session):
    """Test getting a user by ID that doesn't exist."""
    user = get_user_by_id(test_db_session, user_id=999)  # Assuming ID 999 doesn't exist
    assert user is None 