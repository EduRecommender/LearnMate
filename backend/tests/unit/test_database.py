import pytest
from sqlalchemy.sql import text
from app.database import Base
from app.models.user import User

def test_database_connection(test_db):
    """Test that the database connection is working"""
    # Check that we can execute a simple query
    result = test_db.execute(text("SELECT 1")).fetchone()
    assert result[0] == 1
    
def test_users_table_exists(test_db):
    """Test that the users table exists"""
    # Check if User model is mapped correctly
    assert User.__tablename__ == "users"
    
    # Check if we can create a user and query it back
    test_db.add(User(
        username="testdbuser",
        email="testdb@example.com",
        hashed_password="fakehash",
        is_active=True
    ))
    test_db.commit()
    
    # Query the user back
    user = test_db.query(User).filter(User.username == "testdbuser").first()
    assert user is not None
    assert user.email == "testdb@example.com"
    
def test_all_tables_created(test_db):
    """Test that all tables defined in models are created"""
    # This test verifies that all tables defined in models are created
    engine = test_db.get_bind()
    inspector = engine.dialect.inspector
    
    # Get all table names from the database
    table_names = inspector.get_table_names()
    
    # Check that all mapped tables are in the database
    for mapper in Base.registry.mappers:
        table_name = mapper.class_.__tablename__
        assert table_name in table_names, f"Table '{table_name}' not found in the database" 