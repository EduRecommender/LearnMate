import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Assuming schemas are defined in app.schemas
from app import schemas
from app import crud
from app import models # Needed for querying/checking results

pytestmark = pytest.mark.asyncio

# --- User CRUD Tests --- 

async def test_create_user(db_session: AsyncSession):
    user_in = schemas.UserCreate(username="testuser_crud", email="test_crud@example.com", password="password123")
    
    # Use run_sync to call the synchronous CRUD function
    db_user = await db_session.run_sync(crud.create_user, user_in)
    
    assert db_user.username == user_in.username
    assert db_user.email == user_in.email
    assert hasattr(db_user, "hashed_password")
    assert db_user.id is not None

    # Verify it's in the database
    stmt = select(models.User).where(models.User.id == db_user.id)
    result = await db_session.execute(stmt)
    fetched_user = result.scalar_one_or_none()
    assert fetched_user is not None
    assert fetched_user.username == user_in.username

async def test_get_user(db_session: AsyncSession):
    user_in = schemas.UserCreate(username="getmeuser", email="getme@example.com", password="password123")
    created_user = await db_session.run_sync(crud.create_user, user_in)

    # Test get_user
    fetched_user = await db_session.run_sync(crud.get_user, created_user.id)
    assert fetched_user is not None
    assert fetched_user.id == created_user.id
    assert fetched_user.username == "getmeuser"

async def test_get_user_by_username(db_session: AsyncSession):
    user_in = schemas.UserCreate(username="getmebyname", email="getmebyname@example.com", password="password123")
    await db_session.run_sync(crud.create_user, user_in)

    # Test get_user_by_username
    fetched_user = await db_session.run_sync(crud.get_user_by_username, "getmebyname")
    assert fetched_user is not None
    assert fetched_user.username == "getmebyname"

# --- Study Session CRUD Tests --- 

async def test_create_study_session(db_session: AsyncSession):
    session_in = schemas.StudySessionCreate(
        name="Test Session",
        field_of_study="Testing",
        study_goal="Write CRUD tests",
        context="Testing context",
        time_commitment="1 hour",
        difficulty_level="Medium"
    )
    db_session_obj = await db_session.run_sync(crud.create_study_session, session_in)
    
    assert db_session_obj.name == session_in.name
    assert db_session_obj.field_of_study == session_in.field_of_study
    assert db_session_obj.id is not None

    # Verify in DB
    stmt = select(models.StudySession).where(models.StudySession.id == db_session_obj.id)
    result = await db_session.execute(stmt)
    fetched_session = result.scalar_one_or_none()
    assert fetched_session is not None
    assert fetched_session.name == "Test Session"

async def test_get_study_session(db_session: AsyncSession):
    session_in = schemas.StudySessionCreate(name="Get Session Test", field_of_study="Testing Get")
    created_session = await db_session.run_sync(crud.create_study_session, session_in)
    
    fetched_session = await db_session.run_sync(crud.get_study_session, created_session.id)
    assert fetched_session is not None
    assert fetched_session.id == created_session.id
    assert fetched_session.name == "Get Session Test"

# --- Resource CRUD Tests --- 

async def test_create_resource(db_session: AsyncSession):
    # First, create a session to link the resource to
    session_in = schemas.StudySessionCreate(name="Session For Resource", field_of_study="Resources")
    study_session = await db_session.run_sync(crud.create_study_session, session_in)
    
    resource_in = schemas.ResourceCreate(
        name="Test Resource",
        url="http://example.com/resource",
        type="URL",
        content="Test content"
    )
    db_resource = await db_session.run_sync(crud.create_resource, resource_in, study_session.id)
    
    assert db_resource.name == resource_in.name
    assert db_resource.url == resource_in.url
    assert db_resource.session_id == study_session.id
    assert db_resource.id is not None

    # Verify in DB
    stmt = select(models.Resource).where(models.Resource.id == db_resource.id)
    result = await db_session.execute(stmt)
    fetched_resource = result.scalar_one_or_none()
    assert fetched_resource is not None
    assert fetched_resource.name == "Test Resource"

async def test_get_resource(db_session: AsyncSession):
    session_in = schemas.StudySessionCreate(name="Session For Get Resource", field_of_study="Resources Get")
    study_session = await db_session.run_sync(crud.create_study_session, session_in)
    resource_in = schemas.ResourceCreate(name="Get Resource Test", url="http://example.com/get", type="URL")
    created_resource = await db_session.run_sync(crud.create_resource, resource_in, study_session.id)

    fetched_resource = await db_session.run_sync(crud.get_resource, created_resource.id)
    assert fetched_resource is not None
    assert fetched_resource.id == created_resource.id
    assert fetched_resource.name == "Get Resource Test"

# Add more tests for get_users, get_study_sessions, get_session_resources, 
# update operations, delete operations, authenticate_user etc. 