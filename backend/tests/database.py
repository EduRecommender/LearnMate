import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base  # This absolute import is still valid since app is in the Python path

# Get database URL from environment variable, default to a local SQLite file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test_local.db")

engine = create_async_engine(DATABASE_URL, echo=True) # echo=True for debugging SQL
TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def init_db():
    """Initializes the database by creating all tables."""
    async with engine.begin() as conn:
        # Drop all tables first (optional, for clean slate)
        # await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    """Drops all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def get_test_db() -> AsyncSession:
    """Dependency injector for test database sessions."""
    async with TestingSessionLocal() as session:
        yield session 