import pytest
from fastapi.testclient import TestClient
from app.services.user import UserService

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

def test_register_user(client):
    """Test user registration endpoint."""
    # Registration data
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
        "preferences": {"theme": "dark"}
    }
    
    # Register a new user
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = response.json()
    assert "id" in data
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert data["preferences"] == user_data["preferences"]
    
    # Check that the password is not returned
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_duplicate_username(client, test_user):
    """Test registering a user with a duplicate username."""
    # Registration data with existing username
    user_data = {
        "username": test_user.username,
        "email": "different@example.com",
        "password": "password123"
    }
    
    # Try to register with duplicate username
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Check that the request failed
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_register_duplicate_email(client, test_user):
    """Test registering a user with a duplicate email."""
    # Registration data with existing email
    user_data = {
        "username": "differentuser",
        "email": test_user.email,
        "password": "password123"
    }
    
    # Try to register with duplicate email
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Check that the request failed
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_login_success(client, test_user):
    """Test successful login."""
    # Login data
    login_data = {
        "username": test_user.username,
        "password": "testpassword"
    }
    
    # Login
    response = client.post("/api/v1/auth/login", json=login_data)
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["id"] == test_user.id
    assert data["user"]["username"] == test_user.username
    assert data["user"]["email"] == test_user.email

def test_login_invalid_username(client):
    """Test login with invalid username."""
    # Login data with non-existent username
    login_data = {
        "username": "nonexistentuser",
        "password": "testpassword"
    }
    
    # Try to login
    response = client.post("/api/v1/auth/login", json=login_data)
    
    # Check that the request failed
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_login_invalid_password(client, test_user):
    """Test login with invalid password."""
    # Login data with incorrect password
    login_data = {
        "username": test_user.username,
        "password": "wrongpassword"
    }
    
    # Try to login
    response = client.post("/api/v1/auth/login", json=login_data)
    
    # Check that the request failed
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_get_current_user(authenticated_client, test_user):
    """Test getting the current authenticated user."""
    # Get current user
    response = authenticated_client.get("/api/v1/auth/me")
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = response.json()
    assert data["id"] == test_user.id
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    
    # Check that sensitive information is not returned
    assert "password" not in data
    assert "hashed_password" not in data

def test_get_current_user_unauthenticated(client):
    """Test getting the current user without authentication."""
    # Try to get current user without auth token
    response = client.get("/api/v1/auth/me")
    
    # Check that the request failed
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_update_user(authenticated_client, test_user, test_db):
    """Test updating user information."""
    # Update data
    update_data = {
        "email": "updated@example.com",
        "preferences": {"theme": "light"}
    }
    
    # Update user
    response = authenticated_client.patch("/api/v1/auth/me", json=update_data)
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the updated data
    data = response.json()
    assert data["id"] == test_user.id
    assert data["username"] == test_user.username
    assert data["email"] == update_data["email"]
    assert data["preferences"] == update_data["preferences"]
    
    # Check that the user was actually updated in the database
    updated_user = UserService.get_user(test_db, test_user.id)
    assert updated_user.email == update_data["email"]
    assert updated_user.preferences == update_data["preferences"]

def test_update_user_password(authenticated_client, test_user, test_db):
    """Test updating user password."""
    # Update data with new password
    update_data = {
        "password": "newpassword"
    }
    
    # Update user
    response = authenticated_client.patch("/api/v1/auth/me", json=update_data)
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the password was actually updated in the database
    updated_user = UserService.get_user(test_db, test_user.id)
    assert UserService.verify_password(update_data["password"], updated_user.hashed_password)
    assert not UserService.verify_password("testpassword", updated_user.hashed_password)

def test_update_user_unauthenticated(client):
    """Test updating user without authentication."""
    # Update data
    update_data = {
        "email": "updated@example.com"
    }
    
    # Try to update user without auth token
    response = client.patch("/api/v1/auth/me", json=update_data)
    
    # Check that the request failed
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"] 