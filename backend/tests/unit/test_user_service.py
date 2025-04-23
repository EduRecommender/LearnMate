import pytest
from datetime import datetime, timedelta
from jose import jwt
from app.services.user import UserService
from app.models.user import User
from app.core.config import settings

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

def test_get_password_hash():
    """Test that password hashing works correctly."""
    password = "testpassword"
    hashed_password = UserService.get_password_hash(password)
    
    # Check that the hashed password is not the same as the original
    assert hashed_password != password
    
    # Check that the hashed password can be verified
    assert UserService.verify_password(password, hashed_password)
    
    # Check that incorrect passwords don't verify
    assert not UserService.verify_password("wrongpassword", hashed_password)

def test_create_access_token():
    """Test creating JWT access tokens."""
    data = {"sub": "testuser"}
    
    # Test with default expiration
    token = UserService.create_access_token(data)
    assert token is not None
    
    # Decode the token and verify its contents
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "testuser"
    assert "exp" in payload
    
    # Test with custom expiration
    expires_delta = timedelta(minutes=30)
    token = UserService.create_access_token(data, expires_delta)
    
    # Decode the token and verify its contents
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "testuser"
    assert "exp" in payload

def test_get_user(test_db, test_user):
    """Test retrieving a user by ID."""
    # Get the user by ID
    user = UserService.get_user(test_db, test_user.id)
    
    # Check that the correct user was retrieved
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username
    
    # Check that non-existent users return None
    assert UserService.get_user(test_db, 999) is None

def test_get_user_by_username(test_db, test_user):
    """Test retrieving a user by username."""
    # Get the user by username
    user = UserService.get_user_by_username(test_db, test_user.username)
    
    # Check that the correct user was retrieved
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username
    
    # Check that non-existent users return None
    assert UserService.get_user_by_username(test_db, "nonexistentuser") is None

def test_get_user_by_email(test_db, test_user):
    """Test retrieving a user by email."""
    # Get the user by email
    user = UserService.get_user_by_email(test_db, test_user.email)
    
    # Check that the correct user was retrieved
    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email
    
    # Check that non-existent users return None
    assert UserService.get_user_by_email(test_db, "nonexistent@example.com") is None

def test_authenticate_user(test_db, test_user):
    """Test user authentication."""
    # Authenticate with correct credentials
    user = UserService.authenticate_user(test_db, test_user.username, "testpassword")
    
    # Check that the correct user was authenticated
    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username
    
    # Check that authentication fails with incorrect username
    assert UserService.authenticate_user(test_db, "nonexistentuser", "testpassword") is None
    
    # Check that authentication fails with incorrect password
    assert UserService.authenticate_user(test_db, test_user.username, "wrongpassword") is None

def test_create_user(test_db):
    """Test creating a new user."""
    # Create a user
    user_create = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword",
        "preferences": {"theme": "dark"}
    }
    
    user = UserService.create_user(test_db, user_create)
    
    # Check that the user was created with the correct attributes
    assert user is not None
    assert user.username == user_create["username"]
    assert user.email == user_create["email"]
    assert user.preferences == user_create["preferences"]
    
    # Check that the password was hashed
    assert user.hashed_password != user_create["password"]
    
    # Check that the user can be retrieved from the database
    db_user = UserService.get_user_by_username(test_db, user_create["username"])
    assert db_user is not None
    assert db_user.id == user.id

def test_update_user(test_db, test_user):
    """Test updating a user."""
    # Create update data
    user_update = {
        "email": "updated@example.com",
        "preferences": {"theme": "light"}
    }
    
    # Update the user
    updated_user = UserService.update_user(test_db, test_user.id, user_update)
    
    # Check that the user was updated with the correct attributes
    assert updated_user is not None
    assert updated_user.id == test_user.id
    assert updated_user.email == user_update["email"]
    assert updated_user.preferences == user_update["preferences"]
    
    # Check that the username was not changed
    assert updated_user.username == test_user.username
    
    # Test updating with a password
    user_update = {
        "password": "newpassword"
    }
    
    updated_user = UserService.update_user(test_db, test_user.id, user_update)
    
    # Check that the password was updated and hashed
    assert updated_user is not None
    assert updated_user.hashed_password != user_update["password"]
    assert UserService.verify_password(user_update["password"], updated_user.hashed_password)
    
    # Check that updating a non-existent user returns None
    assert UserService.update_user(test_db, 999, user_update) is None

def test_delete_user(test_db, test_user):
    """Test deleting a user."""
    # Delete the user
    result = UserService.delete_user(test_db, test_user.id)
    
    # Check that the operation was successful
    assert result is True
    
    # Check that the user can no longer be retrieved from the database
    assert UserService.get_user(test_db, test_user.id) is None
    
    # Check that deleting a non-existent user returns False
    assert UserService.delete_user(test_db, 999) is False 