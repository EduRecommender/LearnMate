import pytest
from app.services.session import SessionService
from app.services.user import UserService
from app.models.user import StudySession, DifficultyLevel, Resource, ResourceType
from app.schemas.user import StudySessionCreate, StudySessionUpdate

def test_create_session(test_db, test_user):
    """Test creating a new study session."""
    # Create session data
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
    
    # Create the session
    session = SessionService.create_session(test_db, test_user.id, session_data)
    
    # Check that the session was created with the correct attributes
    assert session is not None
    assert session.name == session_data["name"]
    assert session.user_id == test_user.id
    assert session.field_of_study == session_data["field_of_study"]
    assert session.study_goal == session_data["study_goal"]
    assert session.context == session_data["context"]
    assert session.time_commitment == session_data["time_commitment"]
    assert session.difficulty_level == session_data["difficulty_level"]
    assert session.preferences == session_data["preferences"]
    assert session.syllabus == session_data["syllabus"]
    assert session.progress == session_data["progress"]
    
    # Check that the session can be retrieved from the database
    db_session = SessionService.get_session(test_db, session.id)
    assert db_session is not None
    assert db_session.id == session.id

def test_get_session(test_db, test_user):
    """Test retrieving a study session by ID."""
    # Create a session first
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
    
    # Get the session by ID
    retrieved_session = SessionService.get_session(test_db, session.id)
    
    # Check that the correct session was retrieved
    assert retrieved_session is not None
    assert retrieved_session.id == session.id
    assert retrieved_session.name == session.name
    
    # Check that non-existent sessions return None
    assert SessionService.get_session(test_db, 999) is None

def test_get_user_sessions(test_db, test_user):
    """Test retrieving all study sessions for a user."""
    # Create two sessions for the user
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
    
    session1 = SessionService.create_session(test_db, test_user.id, session_data1)
    session2 = SessionService.create_session(test_db, test_user.id, session_data2)
    
    # Get all sessions for the user
    sessions = SessionService.get_user_sessions(test_db, test_user.id)
    
    # Check that both sessions were retrieved
    assert len(sessions) == 2
    session_ids = [s.id for s in sessions]
    assert session1.id in session_ids
    assert session2.id in session_ids
    
    # Create another user and check that their sessions aren't mixed
    new_user = UserService.create_user(test_db, {
        "username": "anotheruser",
        "email": "another@example.com",
        "password": "password123",
        "preferences": {}
    })
    
    # Create a session for the new user
    session_data3 = {
        "name": "Test Session 3",
        "field_of_study": "Physics",
        "study_goal": "Learn Mechanics",
        "context": "For a college course",
        "time_commitment": 20.0,
        "difficulty_level": DifficultyLevel.BEGINNER,
        "preferences": {},
        "syllabus": {},
        "progress": {},
        "session_metadata": {}
    }
    
    session3 = SessionService.create_session(test_db, new_user.id, session_data3)
    
    # Get sessions for the original user
    sessions = SessionService.get_user_sessions(test_db, test_user.id)
    
    # Check that only their sessions were retrieved
    assert len(sessions) == 2
    session_ids = [s.id for s in sessions]
    assert session3.id not in session_ids

def test_update_session(test_db, test_user):
    """Test updating a study session."""
    # Create a session first
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
    
    # Create update data
    update_data = {
        "name": "Updated Session",
        "field_of_study": "Data Science",
        "progress": {"completed": 50}
    }
    
    # Update the session
    updated_session = SessionService.update_session(test_db, session.id, update_data)
    
    # Check that the session was updated with the correct attributes
    assert updated_session is not None
    assert updated_session.id == session.id
    assert updated_session.name == update_data["name"]
    assert updated_session.field_of_study == update_data["field_of_study"]
    assert updated_session.progress == update_data["progress"]
    
    # Check that attributes not in the update data were not changed
    assert updated_session.study_goal == session.study_goal
    assert updated_session.context == session.context
    assert updated_session.time_commitment == session.time_commitment
    assert updated_session.difficulty_level == session.difficulty_level
    
    # Check that updating a non-existent session returns None
    assert SessionService.update_session(test_db, 999, update_data) is None

def test_delete_session(test_db, test_user):
    """Test deleting a study session."""
    # Create a session first
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
    result = SessionService.delete_session(test_db, session.id)
    
    # Check that the operation was successful
    assert result is True
    
    # Check that the session can no longer be retrieved from the database
    assert SessionService.get_session(test_db, session.id) is None
    
    # Check that deleting a non-existent session returns False
    assert SessionService.delete_session(test_db, 999) is False

def test_resource_management(test_db, test_user, tmp_path):
    """Test resource creation and retrieval."""
    # Create a session first
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
    
    # Create a text resource
    resource_data = {
        "session_id": session.id,
        "name": "Test Resource",
        "type": "text",
        "content": "This is a test resource",
        "resource_metadata": {"source": "test"}
    }
    
    # Add the resource to the database directly for testing
    resource = Resource(
        session_id=resource_data["session_id"],
        name=resource_data["name"],
        type=resource_data["type"],
        content=resource_data["content"],
        resource_metadata=resource_data["resource_metadata"]
    )
    
    test_db.add(resource)
    test_db.commit()
    test_db.refresh(resource)
    
    # Get the resource by ID
    retrieved_resource = SessionService.get_resource(test_db, resource.id)
    
    # Check that the correct resource was retrieved
    assert retrieved_resource is not None
    assert retrieved_resource.id == resource.id
    assert retrieved_resource.name == resource.name
    assert retrieved_resource.type == resource.type
    assert retrieved_resource.content == resource.content
    
    # Check that non-existent resources return None
    assert SessionService.get_resource(test_db, 999) is None 