import pytest
from fastapi.testclient import TestClient
import json
from sqlalchemy.orm import Session

from app.models.user import User


def test_register_user(client: TestClient, test_db_session: Session):
    """Test user registration endpoint."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"

    # Check that the user was actually created in the database
    user = test_db_session.query(User).filter(User.username == "newuser").first()
    assert user is not None
    assert user.email == "newuser@example.com"


def test_register_existing_username(client: TestClient, test_user: User):
    """Test registration with an existing username."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",  # Same as the test_user fixture
            "email": "different@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_login_valid_credentials(client: TestClient, test_user: User):
    """Test login with valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "password"  # This matches the hashed password in the fixture
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_get_current_user(client: TestClient, test_user: User):
    """Test getting the current user with a valid token."""
    # Login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "password"
        }
    )
    token = login_response.json()["access_token"]
    
    # Use token to get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_get_current_user_invalid_token(client: TestClient):
    """Test getting the current user with an invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401 