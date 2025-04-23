"""
Global pytest configuration and fixtures for the LearnMate backend tests.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path to import app modules
# This is no longer necessary with proper package structure
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Assuming your FastAPI app instance is here
from app.main import app
# Assuming your dependency injector for DB session is here
from app.database import get_db
# Assuming your SQLAlchemy models Base is defined here
# You might need to import specific models if Base isn't automatically populated
from app.models.base import Base
# Import the test database setup
from tests.database import TestingSessionLocal, init_db, drop_db, get_test_db

# Override the get_db dependency for the FastAPI app during tests
# This ensures API endpoints use the test database session
app.dependency_overrides[get_db] = get_test_db

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    logger.info("Setting up event loop for test session")
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
    logger.info("Closed event loop for test session")

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Set up the test database schema before tests run and tear down after."""
    logger.info("Initializing test database schema")
    await init_db()
    yield
    logger.info("Dropping test database schema")
    await drop_db()

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Provide a test database session scoped to each test function."""
    logger.debug("Creating test database session for function")
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit() # Commit changes made within a test if no exceptions
        except Exception:
            await session.rollback() # Rollback on error
            raise
        finally:
            await session.close()
    logger.debug("Closed test database session for function")


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncClient:
    """Provide an HTTP client for testing the FastAPI app.
    Ensures the client uses the overridden test DB session.
    """
    # The db_session fixture ensures the dependency override is active
    # for the duration of the client's use within a test function.
    logger.debug("Creating AsyncClient for function")
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    logger.debug("AsyncClient context closed")

# Add other fixtures if needed, for example, creating test users or other data
# @pytest_asyncio.fixture(scope="function")
# async def test_user(db_session: AsyncSession):
#     from app.models.user import User # Import User model here or globally
#     from app.services.user import UserService # Import UserService
#     user_data = {"username": "testuser", "email": f"test{hash(asyncio.current_task())}@example.com", "password": "password"}
#     user = await UserService.create_user(db=db_session, user_create=user_data) # Assuming an async create_user
#     return user

# Mark all tests as asyncio by default if preferred, or mark individual test files/functions
# pytestmark = pytest.mark.asyncio

# Mark all tests as asyncio
@pytest.mark.asyncio
async def test_example():
    # This is just to ensure pytest-asyncio is recognized.
    # Actual tests will be in other files.
    assert True 