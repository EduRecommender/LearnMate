import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, StudySession, Resource

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db_engine():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_db_session(test_db_engine):
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(test_db_session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_db_session):
    """Create a test user in the database."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$tT5wG5LMYWgPEzO0gTzMiOD9AJrWVjFjUPxWjBd1NoZ.s/MQsIa1K"  # 'password'
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user

@pytest.fixture
def test_study_session(test_db_session):
    """Create a test study session in the database."""
    study_session = StudySession(
        name="Test Session",
        field_of_study="Computer Science",
        study_goal="Learn Python",
        context="For a final project",
        time_commitment="2 hours",
        difficulty_level="Intermediate"
    )
    test_db_session.add(study_session)
    test_db_session.commit()
    test_db_session.refresh(study_session)
    return study_session

@pytest.fixture
def test_resource(test_db_session, test_study_session):
    """Create a test resource in the database."""
    resource = Resource(
        name="Test Resource",
        url="https://example.com/resource",
        type="Article",
        content="This is a test resource content",
        session_id=test_study_session.id
    )
    test_db_session.add(resource)
    test_db_session.commit()
    test_db_session.refresh(resource)
    return resource 