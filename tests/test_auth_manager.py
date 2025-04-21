import pytest
import os
import shutil

# Assuming AuthManager is in the root directory
from auth_manager import AuthManager

# Fixture to set up and tear down the test environment
@pytest.fixture(scope="function")
def manager():
    # Create a temporary data directory for tests
    test_data_dir = "test_data"
    os.makedirs(test_data_dir, exist_ok=True)

    # Backup original files if they exist (optional, good practice)
    # ... (consider adding backup logic if needed)

    # Point AuthManager to test files
    manager = AuthManager()
    original_users_file = manager.users_file
    original_sessions_file = manager.sessions_file
    manager.users_file = os.path.join(test_data_dir, "test_users.json")
    manager.sessions_file = os.path.join(test_data_dir, "test_sessions.json")

    # Ensure test files are created if they don't exist
    manager._ensure_data_directory() # This will create the files in test_data_dir

    yield manager # Provide the manager instance to the test

    # Teardown: Clean up the temporary directory
    shutil.rmtree(test_data_dir)

# --- Test Cases ---

def test_register_user_success(manager):
    success, message = manager.register_user("testuser", "password123", "test@example.com")
    assert success
    assert message == "User registered successfully"
    assert "testuser" in manager.users
    assert manager.users["testuser"]["email"] == "test@example.com"
    # Password should be hashed, not stored directly
    assert manager.users["testuser"]["password"] != "password123"

def test_register_user_existing(manager):
    manager.register_user("testuser", "password123") # First registration
    success, message = manager.register_user("testuser", "anotherpassword") # Second attempt
    assert not success
    assert message == "Username already exists"

def test_login_user_success(manager):
    manager.register_user("testuser", "password123")
    success, session_id_or_message = manager.login_user("testuser", "password123")
    assert success
    assert isinstance(session_id_or_message, str) # Should return a session ID
    assert session_id_or_message in manager.sessions
    assert manager.sessions[session_id_or_message]["username"] == "testuser"

def test_login_user_not_found(manager):
    success, message = manager.login_user("nonexistent", "password123")
    assert not success
    assert message == "User not found"

def test_login_user_invalid_password(manager):
    manager.register_user("testuser", "password123")
    success, message = manager.login_user("testuser", "wrongpassword")
    assert not success
    assert message == "Invalid password"

def test_check_session_valid(manager):
    manager.register_user("testuser", "password123")
    _, session_id = manager.login_user("testuser", "password123")
    is_valid, username = manager.check_session(session_id)
    assert is_valid
    assert username == "testuser"

def test_check_session_invalid(manager):
    is_valid, username = manager.check_session("invalid_session_id")
    assert not is_valid
    assert username is None

def test_update_user_preferences_success(manager):
    username = "prefuser"
    manager.register_user(username, "password123")
    new_prefs = {"level": "Intermediate", "subject_interest": ["Python", "AI"]}
    success = manager.update_user_preferences(username, new_prefs)
    assert success
    assert manager.users[username]["preferences"]["level"] == "Intermediate"
    assert manager.users[username]["preferences"]["subject_interest"] == ["Python", "AI"]
    # Ensure defaults are still there if not updated
    assert "name" in manager.users[username]["preferences"]

def test_update_user_preferences_non_existent_user(manager):
    new_prefs = {"level": "Beginner"}
    success = manager.update_user_preferences("nonexistent", new_prefs)
    assert not success

def test_get_user_preferences_success(manager):
    username = "getprefuser"
    initial_prefs = {"level": "Expert", "has_set_preferences": True}
    manager.register_user(username, "password123")
    manager.update_user_preferences(username, initial_prefs)

    retrieved_prefs = manager.get_user_preferences(username)
    assert retrieved_prefs["level"] == "Expert"
    assert retrieved_prefs["has_set_preferences"]
    # Check a default value that wasn't updated
    assert retrieved_prefs["grade_level"] == "Not Set"

def test_get_user_preferences_new_user_defaults(manager):
    username = "newprefuser"
    manager.register_user(username, "password123") # Register without setting prefs
    retrieved_prefs = manager.get_user_preferences(username)
    assert retrieved_prefs["level"] == "Not Set"
    assert not retrieved_prefs["has_set_preferences"]
    assert not retrieved_prefs["has_skipped_preferences"]
    assert isinstance(retrieved_prefs["subject_interest"], list)

def test_get_user_preferences_non_existent_user(manager):
    prefs = manager.get_user_preferences("nonexistent")
    assert prefs == {}
