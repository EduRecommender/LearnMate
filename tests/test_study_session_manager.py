import pytest
import os
import json
import shutil

# Assuming StudySessionManager is in the root directory
from study_session_manager import StudySessionManager

# Fixture to set up and tear down the test environment
@pytest.fixture(scope="function")
def manager():
    test_data_dir = "test_session_data"
    os.makedirs(test_data_dir, exist_ok=True)

    manager = StudySessionManager()
    original_sessions_file = manager.sessions_file
    manager.sessions_file = os.path.join(test_data_dir, "test_study_sessions.json")

    # Ensure the test file exists
    manager._ensure_sessions_file_exists() 

    yield manager

    # Teardown: Clean up the temporary directory
    shutil.rmtree(test_data_dir)

# --- Test Cases ---

def test_create_session_success(manager):
    username = "testuser"
    session_name = "Math Basics"
    prefs = {"difficulty": "Beginner"}
    session_id = manager.create_session(username, session_name, prefs)

    assert isinstance(session_id, str)
    # Verify by reading the file directly or using get_session
    session = manager.get_session(username, session_id)
    assert session is not None
    assert session["name"] == session_name
    assert session["preferences"]["difficulty"] == "Beginner"
    assert "created_at" in session
    assert session["materials"] == []
    assert session["notes"] == []
    assert session["progress"] == 0

def test_get_user_sessions(manager):
    username = "testuser"
    manager.create_session(username, "Session 1", {})
    manager.create_session(username, "Session 2", {})

    sessions = manager.get_user_sessions(username)
    assert len(sessions) == 2
    assert any(s["name"] == "Session 1" for s in sessions.values())
    assert any(s["name"] == "Session 2" for s in sessions.values())

def test_get_user_sessions_non_existent_user(manager):
    sessions = manager.get_user_sessions("nonexistent")
    assert sessions == {}

def test_get_session_success(manager):
    username = "testuser"
    session_name = "Specific Session"
    session_id = manager.create_session(username, session_name, {})

    session = manager.get_session(username, session_id)
    assert session is not None
    assert session["name"] == session_name

def test_get_session_non_existent(manager):
    username = "testuser"
    # User exists, but session doesn't
    manager.create_session(username, "Another Session", {})
    session = manager.get_session(username, "non_existent_session_id")
    assert session is None
    # User doesn't exist
    session = manager.get_session("nonexistent", "some_id")
    assert session is None

def test_update_session_success(manager):
    username = "testuser"
    session_id = manager.create_session(username, "Old Name", {"difficulty": "Easy"})
    updates = {
        "name": "New Name",
        "progress": 50,
        "preferences": {"difficulty": "Medium", "new_pref": True}
    }
    success, message = manager.update_session(username, session_id, updates)

    assert success
    assert message == "Session updated successfully"
    updated_session = manager.get_session(username, session_id)
    assert updated_session["name"] == "New Name"
    assert updated_session["progress"] == 50
    assert updated_session["preferences"]["difficulty"] == "Medium"
    assert updated_session["preferences"]["new_pref"] is True

def test_update_session_not_found(manager):
    success, message = manager.update_session("testuser", "nonexistent_id", {"name": "Fail"})
    assert not success
    assert message == "Session not found"

def test_add_material_success(manager):
    username = "testuser"
    session_id = manager.create_session(username, "Material Test", {})
    material = {"title": "Intro Video", "type": "video", "url": "http://example.com/video"}
    success, message = manager.add_material(username, session_id, material)

    assert success
    assert message == "Material added successfully"
    session = manager.get_session(username, session_id)
    assert len(session["materials"]) == 1
    added_material = session["materials"][0]
    assert added_material["title"] == "Intro Video"
    assert added_material["type"] == "video"
    assert added_material["url"] == "http://example.com/video"
    assert "added_at" in added_material

def test_add_material_session_not_found(manager):
    material = {"title": "Fail"}
    success, message = manager.add_material("testuser", "nonexistent_id", material)
    assert not success
    assert message == "Session not found"

def test_add_note_success(manager):
    username = "testuser"
    session_id = manager.create_session(username, "Note Test", {})
    note_content = "This is an important concept."
    success, message = manager.add_note(username, session_id, note_content)

    assert success
    assert message == "Note added successfully"
    session = manager.get_session(username, session_id)
    assert len(session["notes"]) == 1
    added_note = session["notes"][0]
    assert added_note["content"] == note_content
    assert "created_at" in added_note

def test_add_note_session_not_found(manager):
    success, message = manager.add_note("testuser", "nonexistent_id", "Fail note")
    assert not success
    assert message == "Session not found"

def test_update_progress_success(manager):
    username = "testuser"
    session_id = manager.create_session(username, "Progress Test", {})
    success, message = manager.update_progress(username, session_id, 75)

    assert success
    assert message == "Progress updated successfully"
    session = manager.get_session(username, session_id)
    assert session["progress"] == 75

def test_update_progress_session_not_found(manager):
    success, message = manager.update_progress("testuser", "nonexistent_id", 100)
    assert not success
    assert message == "Session not found"

def test_delete_session_success(manager):
    username = "testuser"
    session_id_to_delete = manager.create_session(username, "To Delete", {})
    session_id_to_keep = manager.create_session(username, "To Keep", {})

    success, message = manager.delete_session(username, session_id_to_delete)
    assert success
    assert message == "Session deleted successfully"

    # Verify deleted session is gone
    assert manager.get_session(username, session_id_to_delete) is None
    # Verify other session remains
    assert manager.get_session(username, session_id_to_keep) is not None
    # Verify user entry still exists if they have other sessions
    assert username in json.load(open(manager.sessions_file))

def test_delete_last_session_success(manager):
    username = "testuser_last"
    session_id = manager.create_session(username, "Last One", {})

    success, message = manager.delete_session(username, session_id)
    assert success
    assert message == "Session deleted successfully"
    assert manager.get_session(username, session_id) is None
    # Check if user entry might be removed if empty (depends on implementation, test assumes it might stay)
    all_sessions = manager.get_user_sessions(username)
    assert all_sessions == {}

def test_delete_session_not_found(manager):
    username = "testuser"
    manager.create_session(username, "Exists", {})
    success, message = manager.delete_session(username, "nonexistent_id")
    assert not success
    assert message == "Session not found" 