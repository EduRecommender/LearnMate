import pytest
from sqlalchemy.orm import Session

from app.services.session import (
    get_study_sessions,
    get_study_session,
    create_study_session,
    update_study_session,
    delete_study_session,
    create_resource,
    get_resources
)
from app.models.user import StudySession, Resource


def test_get_study_sessions(test_db_session: Session, test_study_session: StudySession):
    """Test getting all study sessions."""
    sessions = get_study_sessions(test_db_session)
    assert len(sessions) >= 1
    assert any(session.id == test_study_session.id for session in sessions)


def test_get_study_session(test_db_session: Session, test_study_session: StudySession):
    """Test getting a specific study session by ID."""
    session = get_study_session(test_db_session, session_id=test_study_session.id)
    assert session is not None
    assert session.id == test_study_session.id
    assert session.name == test_study_session.name


def test_get_study_session_nonexistent(test_db_session: Session):
    """Test getting a study session that doesn't exist."""
    session = get_study_session(test_db_session, session_id=9999)  # Assuming ID 9999 doesn't exist
    assert session is None


def test_create_study_session(test_db_session: Session):
    """Test creating a new study session."""
    session_data = {
        "name": "New Service Session",
        "field_of_study": "History",
        "study_goal": "Learn about World War II",
        "context": "For a history essay",
        "time_commitment": "4 hours",
        "difficulty_level": "Intermediate"
    }
    
    session = create_study_session(test_db_session, **session_data)
    assert session is not None
    assert session.name == session_data["name"]
    assert session.field_of_study == session_data["field_of_study"]
    assert session.study_goal == session_data["study_goal"]
    
    # Check that the session was added to the database
    created_session = test_db_session.query(StudySession).filter(
        StudySession.name == session_data["name"]
    ).first()
    assert created_session is not None
    assert created_session.id == session.id


def test_update_study_session(test_db_session: Session, test_study_session: StudySession):
    """Test updating a study session."""
    updated_data = {
        "name": "Updated Service Session",
        "field_of_study": test_study_session.field_of_study,
        "study_goal": "New study goal for testing",
        "context": test_study_session.context,
        "time_commitment": "1 hour",  # Changed
        "difficulty_level": test_study_session.difficulty_level
    }
    
    updated_session = update_study_session(
        test_db_session, 
        session_id=test_study_session.id, 
        **updated_data
    )
    
    assert updated_session is not None
    assert updated_session.id == test_study_session.id
    assert updated_session.name == updated_data["name"]
    assert updated_session.study_goal == updated_data["study_goal"]
    assert updated_session.time_commitment == updated_data["time_commitment"]
    
    # Check that the session was updated in the database
    test_db_session.refresh(test_study_session)
    assert test_study_session.name == updated_data["name"]
    assert test_study_session.study_goal == updated_data["study_goal"]


def test_update_nonexistent_study_session(test_db_session: Session):
    """Test updating a study session that doesn't exist."""
    updated_data = {
        "name": "This Should Fail",
        "field_of_study": "Test",
        "study_goal": "Test",
        "context": "Test",
        "time_commitment": "Test",
        "difficulty_level": "Test"
    }
    
    # Assuming ID 9999 doesn't exist
    updated_session = update_study_session(test_db_session, session_id=9999, **updated_data)
    assert updated_session is None


def test_delete_study_session(test_db_session: Session, test_study_session: StudySession):
    """Test deleting a study session."""
    session_id = test_study_session.id
    deleted = delete_study_session(test_db_session, session_id=session_id)
    
    assert deleted is True
    
    # Check that the session was deleted from the database
    deleted_session = test_db_session.query(StudySession).filter(
        StudySession.id == session_id
    ).first()
    assert deleted_session is None


def test_delete_nonexistent_study_session(test_db_session: Session):
    """Test deleting a study session that doesn't exist."""
    # Assuming ID 9999 doesn't exist
    deleted = delete_study_session(test_db_session, session_id=9999)
    assert deleted is False


def test_create_resource(test_db_session: Session, test_study_session: StudySession):
    """Test creating a resource for a study session."""
    resource_data = {
        "name": "Service Test Resource",
        "url": "https://example.com/service-test",
        "type": "Podcast",
        "content": "This is content for testing the service"
    }
    
    resource = create_resource(
        test_db_session, 
        session_id=test_study_session.id, 
        **resource_data
    )
    
    assert resource is not None
    assert resource.name == resource_data["name"]
    assert resource.url == resource_data["url"]
    assert resource.type == resource_data["type"]
    assert resource.session_id == test_study_session.id
    
    # Check that the resource was added to the database
    created_resource = test_db_session.query(Resource).filter(
        Resource.name == resource_data["name"],
        Resource.session_id == test_study_session.id
    ).first()
    assert created_resource is not None
    assert created_resource.id == resource.id


def test_create_resource_nonexistent_session(test_db_session: Session):
    """Test creating a resource for a study session that doesn't exist."""
    resource_data = {
        "name": "This Should Fail",
        "url": "https://example.com/fail",
        "type": "Website",
        "content": "This resource creation should fail"
    }
    
    # Assuming ID 9999 doesn't exist
    try:
        resource = create_resource(test_db_session, session_id=9999, **resource_data)
        assert False, "Should have raised an error for nonexistent session"
    except Exception:
        pass


def test_get_resources(test_db_session: Session, test_study_session: StudySession, test_resource: Resource):
    """Test getting all resources for a study session."""
    resources = get_resources(test_db_session, session_id=test_study_session.id)
    
    assert len(resources) >= 1
    assert any(resource.id == test_resource.id for resource in resources)
    
    # Create additional resources to test
    additional_resources = [
        Resource(name="Service Resource 1", type="Video", session_id=test_study_session.id),
        Resource(name="Service Resource 2", type="Quiz", session_id=test_study_session.id)
    ]
    for resource in additional_resources:
        test_db_session.add(resource)
    test_db_session.commit()
    
    # Get updated list of resources
    updated_resources = get_resources(test_db_session, session_id=test_study_session.id)
    assert len(updated_resources) >= 3
    
    resource_names = [r.name for r in updated_resources]
    assert "Service Resource 1" in resource_names
    assert "Service Resource 2" in resource_names 