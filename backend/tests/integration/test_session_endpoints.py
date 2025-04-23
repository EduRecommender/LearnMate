import pytest
import os
from io import BytesIO
from app.models.user import DifficultyLevel
from app.services.session import SessionService

def test_create_session(authenticated_client, test_user):
    """Test creating a study session endpoint."""
    # Session data
    session_data = {
        "name": "Test Session",
        "field_of_study": "Computer Science",
        "study_goal": "Learn Python",
        "context": "For a college course",
        "time_commitment": 10.0,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "preferences": {"pacing": "steady"},
        "syllabus": {"topics": ["Variables", "Functions", "Classes"]},
        "progress": {"completed": 0},
        "session_metadata": {}
    }
    
    # Create a session
    response = authenticated_client.post("/api/v1/sessions/", json=session_data)
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = response.json()
    assert "id" in data
    assert data["name"] == session_data["name"]
    assert data["field_of_study"] == session_data["field_of_study"]
    assert data["study_goal"] == session_data["study_goal"]
    assert data["context"] == session_data["context"]
    assert data["time_commitment"] == session_data["time_commitment"]
    assert data["difficulty_level"] == session_data["difficulty_level"]
    assert data["preferences"] == session_data["preferences"]
    assert data["syllabus"] == session_data["syllabus"]
    assert data["progress"] == session_data["progress"]
    assert data["user_id"] == test_user.id
    assert "created_at" in data
    assert "updated_at" in data
    assert "resources" in data

def test_create_session_unauthenticated(client):
    """Test creating a session without authentication."""
    # Session data
    session_data = {
        "name": "Test Session",
        "field_of_study": "Computer Science",
        "study_goal": "Learn Python",
        "context": "For a college course",
        "time_commitment": 10.0,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    # Try to create a session without auth token
    response = client.post("/api/v1/sessions/", json=session_data)
    
    # Check that the request failed
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_get_sessions(authenticated_client, test_user, test_db):
    """Test getting all sessions for a user."""
    # Create two sessions for the user via the service
    session_data1 = {
        "name": "Test Session 1",
        "field_of_study": "Computer Science",
        "study_goal": "Learn Python",
        "context": "For a college course",
        "time_commitment": 10.0,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    session_data2 = {
        "name": "Test Session 2",
        "field_of_study": "Mathematics",
        "study_goal": "Learn Calculus",
        "context": "For a college course",
        "time_commitment": 15.0,
        "difficulty_level": DifficultyLevel.ADVANCED,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    SessionService.create_session(test_db, test_user.id, session_data1)
    SessionService.create_session(test_db, test_user.id, session_data2)
    
    # Get all sessions
    response = authenticated_client.get("/api/v1/sessions/")
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains both sessions
    data = response.json()
    assert len(data) == 2
    assert any(s["name"] == session_data1["name"] for s in data)
    assert any(s["name"] == session_data2["name"] for s in data)

def test_get_sessions_unauthenticated(client):
    """Test getting sessions without authentication."""
    # Try to get sessions without auth token
    response = client.get("/api/v1/sessions/")
    
    # Check that the request failed
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_get_session(authenticated_client, test_user, test_db):
    """Test getting a specific session."""
    # Create a session via the service
    session_data = {
        "name": "Test Session",
        "field_of_study": "Computer Science",
        "study_goal": "Learn Python",
        "context": "For a college course",
        "time_commitment": 10.0,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    session = SessionService.create_session(test_db, test_user.id, session_data)
    
    # Get the session
    response = authenticated_client.get(f"/api/v1/sessions/{session.id}")
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = response.json()
    assert data["id"] == session.id
    assert data["name"] == session_data["name"]
    assert data["field_of_study"] == session_data["field_of_study"]
    assert data["user_id"] == test_user.id

def test_get_session_not_found(authenticated_client):
    """Test getting a non-existent session."""
    # Try to get a non-existent session
    response = authenticated_client.get("/api/v1/sessions/999")
    
    # Check that the request failed
    assert response.status_code == 404

def test_get_session_unauthorized(authenticated_client, test_db):
    """Test getting a session that belongs to another user."""
    # Create another user and a session for them
    from app.services.user import UserService
    
    other_user = UserService.create_user(test_db, {
        "username": "otheruser",
        "email": "other@example.com",
        "password": "password123",
        "preferences": {}
    })
    
    session_data = {
        "name": "Other User's Session",
        "field_of_study": "History",
        "study_goal": "Learn World History",
        "context": "For personal interest",
        "time_commitment": 5.0,
        "difficulty_level": DifficultyLevel.BEGINNER,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    other_session = SessionService.create_session(test_db, other_user.id, session_data)
    
    # Try to get the session as the authenticated user
    response = authenticated_client.get(f"/api/v1/sessions/{other_session.id}")
    
    # Check that the request failed with appropriate status code
    assert response.status_code in [403, 404]

def test_update_session(authenticated_client, test_user, test_db):
    """Test updating a session."""
    # Create a session via the service
    session_data = {
        "name": "Test Session",
        "field_of_study": "Computer Science",
        "study_goal": "Learn Python",
        "context": "For a college course",
        "time_commitment": 10.0,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    session = SessionService.create_session(test_db, test_user.id, session_data)
    
    # Update data
    update_data = {
        "name": "Updated Session",
        "field_of_study": "Data Science",
        "progress": {"completed": 50}
    }
    
    # Update the session
    response = authenticated_client.patch(f"/api/v1/sessions/{session.id}", json=update_data)
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Check that the response contains the updated data
    data = response.json()
    assert data["id"] == session.id
    assert data["name"] == update_data["name"]
    assert data["field_of_study"] == update_data["field_of_study"]
    assert data["progress"] == update_data["progress"]
    
    # Check that attributes not in the update data were not changed
    assert data["study_goal"] == session_data["study_goal"]
    assert data["context"] == session_data["context"]
    assert data["time_commitment"] == session_data["time_commitment"]
    assert data["difficulty_level"] == session_data["difficulty_level"]

def test_delete_session(authenticated_client, test_user, test_db):
    """Test deleting a session."""
    # Create a session via the service
    session_data = {
        "name": "Test Session",
        "field_of_study": "Computer Science",
        "study_goal": "Learn Python",
        "context": "For a college course",
        "time_commitment": 10.0,
        "difficulty_level": DifficultyLevel.INTERMEDIATE,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    session = SessionService.create_session(test_db, test_user.id, session_data)
    
    # Delete the session
    response = authenticated_client.delete(f"/api/v1/sessions/{session.id}")
    
    # Check that the request was successful
    assert response.status_code == 200
    assert response.json() == {"success": True}
    
    # Check that the session can no longer be retrieved
    get_response = authenticated_client.get(f"/api/v1/sessions/{session.id}")
    assert get_response.status_code == 404 