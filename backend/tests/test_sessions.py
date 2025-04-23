import pytest
from fastapi.testclient import TestClient
import json
from sqlalchemy.orm import Session

from app.models.user import StudySession, Resource


def test_create_study_session(client: TestClient, test_db_session: Session):
    """Test creating a new study session."""
    response = client.post(
        "/api/v1/sessions",
        json={
            "name": "New Study Session",
            "field_of_study": "Machine Learning",
            "study_goal": "Learn neural networks",
            "context": "For a data science certification",
            "time_commitment": "5 hours",
            "difficulty_level": "Advanced"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Study Session"
    assert data["field_of_study"] == "Machine Learning"
    assert data["study_goal"] == "Learn neural networks"
    
    # Verify session was created in the database
    session = test_db_session.query(StudySession).filter(StudySession.name == "New Study Session").first()
    assert session is not None
    assert session.difficulty_level == "Advanced"


def test_get_all_study_sessions(client: TestClient, test_study_session: StudySession):
    """Test getting all study sessions."""
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check that our test session is in the list
    session_names = [session["name"] for session in data]
    assert test_study_session.name in session_names


def test_get_study_session_by_id(client: TestClient, test_study_session: StudySession):
    """Test getting a specific study session by ID."""
    response = client.get(f"/api/v1/sessions/{test_study_session.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_study_session.id
    assert data["name"] == test_study_session.name
    assert data["field_of_study"] == test_study_session.field_of_study


def test_get_nonexistent_study_session(client: TestClient):
    """Test getting a study session that doesn't exist."""
    response = client.get("/api/v1/sessions/9999")  # Assuming ID 9999 doesn't exist
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_study_session(client: TestClient, test_study_session: StudySession, test_db_session: Session):
    """Test updating a study session."""
    response = client.put(
        f"/api/v1/sessions/{test_study_session.id}",
        json={
            "name": "Updated Session Name",
            "field_of_study": test_study_session.field_of_study,
            "study_goal": test_study_session.study_goal,
            "context": test_study_session.context,
            "time_commitment": test_study_session.time_commitment,
            "difficulty_level": "Beginner"  # Changed from Intermediate
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Session Name"
    assert data["difficulty_level"] == "Beginner"
    
    # Verify changes in the database
    test_db_session.refresh(test_study_session)
    assert test_study_session.name == "Updated Session Name"
    assert test_study_session.difficulty_level == "Beginner"


def test_delete_study_session(client: TestClient, test_study_session: StudySession, test_db_session: Session):
    """Test deleting a study session."""
    response = client.delete(f"/api/v1/sessions/{test_study_session.id}")
    assert response.status_code == 200
    
    # Verify session was deleted from the database
    session = test_db_session.query(StudySession).filter(StudySession.id == test_study_session.id).first()
    assert session is None


def test_create_resource(client: TestClient, test_study_session: StudySession, test_db_session: Session):
    """Test creating a resource for a study session."""
    response = client.post(
        f"/api/v1/sessions/{test_study_session.id}/resources",
        json={
            "name": "New Resource",
            "url": "https://example.com/new-resource",
            "type": "Video",
            "content": "Content for the new resource"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Resource"
    assert data["type"] == "Video"
    
    # Verify resource was created in the database
    resource = test_db_session.query(Resource).filter(
        Resource.name == "New Resource",
        Resource.session_id == test_study_session.id
    ).first()
    assert resource is not None
    assert resource.url == "https://example.com/new-resource"


def test_get_resources_for_session(client: TestClient, test_study_session: StudySession, test_resource: Resource):
    """Test getting all resources for a study session."""
    response = client.get(f"/api/v1/sessions/{test_study_session.id}/resources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check that our test resource is in the list
    resource_names = [resource["name"] for resource in data]
    assert test_resource.name in resource_names 