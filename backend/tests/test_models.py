import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User, StudySession, Resource


def test_user_model(test_db_session: Session):
    """Test creating and retrieving a User model."""
    # Create a user
    user = User(
        username="modeluser",
        email="modeluser@example.com",
        hashed_password="hashedpassword123"
    )
    test_db_session.add(user)
    test_db_session.commit()
    
    # Retrieve the user
    retrieved_user = test_db_session.query(User).filter(User.username == "modeluser").first()
    
    # Assert user properties
    assert retrieved_user is not None
    assert retrieved_user.username == "modeluser"
    assert retrieved_user.email == "modeluser@example.com"
    assert retrieved_user.hashed_password == "hashedpassword123"
    assert isinstance(retrieved_user.created_at, datetime)
    assert isinstance(retrieved_user.updated_at, datetime)


def test_study_session_model(test_db_session: Session):
    """Test creating and retrieving a StudySession model."""
    # Create a study session
    session = StudySession(
        name="Model Test Session",
        field_of_study="Biology",
        study_goal="Learn about cells",
        context="For a science exam",
        time_commitment="3 hours",
        difficulty_level="Easy"
    )
    test_db_session.add(session)
    test_db_session.commit()
    
    # Retrieve the session
    retrieved_session = test_db_session.query(StudySession).filter(StudySession.name == "Model Test Session").first()
    
    # Assert session properties
    assert retrieved_session is not None
    assert retrieved_session.field_of_study == "Biology"
    assert retrieved_session.study_goal == "Learn about cells"
    assert retrieved_session.difficulty_level == "Easy"
    assert isinstance(retrieved_session.created_at, datetime)


def test_to_dict_method(test_study_session: StudySession):
    """Test the to_dict method of StudySession model."""
    session_dict = test_study_session.to_dict()
    
    # Check that the dictionary contains all expected keys
    expected_keys = ["id", "name", "field_of_study", "study_goal", "context", 
                     "time_commitment", "difficulty_level", "created_at", 
                     "updated_at", "resources"]
    
    for key in expected_keys:
        assert key in session_dict
    
    # Check that values match
    assert session_dict["id"] == test_study_session.id
    assert session_dict["name"] == test_study_session.name
    assert session_dict["field_of_study"] == test_study_session.field_of_study
    assert isinstance(session_dict["resources"], list)


def test_resource_model(test_db_session: Session, test_study_session: StudySession):
    """Test creating and retrieving a Resource model."""
    # Create a resource
    resource = Resource(
        name="Model Test Resource",
        url="https://example.com/test-resource",
        type="Book",
        content="This is content for testing the model",
        session_id=test_study_session.id
    )
    test_db_session.add(resource)
    test_db_session.commit()
    
    # Retrieve the resource
    retrieved_resource = test_db_session.query(Resource).filter(Resource.name == "Model Test Resource").first()
    
    # Assert resource properties
    assert retrieved_resource is not None
    assert retrieved_resource.type == "Book"
    assert retrieved_resource.url == "https://example.com/test-resource"
    assert retrieved_resource.session_id == test_study_session.id
    assert isinstance(retrieved_resource.created_at, datetime)


def test_session_resource_relationship(test_db_session: Session, test_study_session: StudySession):
    """Test the relationship between StudySession and Resource models."""
    # Create multiple resources for the session
    resources = [
        Resource(name="Resource 1", type="Video", session_id=test_study_session.id),
        Resource(name="Resource 2", type="Article", session_id=test_study_session.id),
        Resource(name="Resource 3", type="Book", session_id=test_study_session.id)
    ]
    
    for resource in resources:
        test_db_session.add(resource)
    test_db_session.commit()
    
    # Refresh the session to update its resources relationship
    test_db_session.refresh(test_study_session)
    
    # Assert the session has the correct resources
    assert len(test_study_session.resources) >= 3
    resource_names = [r.name for r in test_study_session.resources]
    assert "Resource 1" in resource_names
    assert "Resource 2" in resource_names
    assert "Resource 3" in resource_names
    
    # Test cascade delete
    # Delete the session
    test_db_session.delete(test_study_session)
    test_db_session.commit()
    
    # Check that all related resources were also deleted
    remaining_resources = test_db_session.query(Resource).filter(
        Resource.name.in_(["Resource 1", "Resource 2", "Resource 3"])
    ).all()
    assert len(remaining_resources) == 0 