from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
from typing import List, Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # In a real implementation, you would verify the JWT token here
    # For now, we'll just return a dummy user for testing
    user = get_user_by_username(db, "dummy_user")
    if not user:
        # Create a dummy user if it doesn't exist
        user = create_user(db, schemas.UserCreate(
            username="dummy_user",
            password="password123"
        ))
    return user

def create_study_session(db: Session, session: schemas.StudySessionCreate) -> models.StudySession:
    """Create a new study session."""
    db_session = models.StudySession(
        name=session.name,
        field_of_study=session.field_of_study,
        study_goal=session.study_goal,
        context=session.context,
        time_commitment=session.time_commitment,
        difficulty_level=session.difficulty_level,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_study_session(db: Session, session_id: int) -> Optional[models.StudySession]:
    """Get a study session by ID."""
    return db.query(models.StudySession).filter(models.StudySession.id == session_id).first()

def get_study_sessions(db: Session, skip: int = 0, limit: int = 100) -> List[models.StudySession]:
    """Get all study sessions."""
    return db.query(models.StudySession).offset(skip).limit(limit).all()

def update_study_session(db: Session, session_id: int, session: schemas.StudySessionCreate) -> Optional[models.StudySession]:
    """Update a study session."""
    db_session = get_study_session(db, session_id)
    if not db_session:
        return None
    
    for key, value in session.dict().items():
        if hasattr(db_session, key):
            setattr(db_session, key, value)
    
    db_session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_session)
    return db_session

def delete_study_session(db: Session, session_id: int) -> bool:
    """Delete a study session."""
    db_session = get_study_session(db, session_id)
    if not db_session:
        return False
    
    db.delete(db_session)
    db.commit()
    return True

def get_resource(db: Session, resource_id: int) -> Optional[models.Resource]:
    """Get a resource by ID."""
    return db.query(models.Resource).filter(models.Resource.id == resource_id).first()

def get_session_resources(db: Session, session_id: int, skip: int = 0, limit: int = 100) -> List[models.Resource]:
    """Get all resources for a study session."""
    return db.query(models.Resource).filter(models.Resource.session_id == session_id)\
        .offset(skip).limit(limit).all()

def create_resource(db: Session, resource: schemas.ResourceCreate, session_id: int) -> models.Resource:
    """Create a new resource."""
    db_resource = models.Resource(
        name=resource.name,
        url=resource.url,
        type=resource.type,
        content=resource.content,
        session_id=session_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource

def update_resource(db: Session, resource_id: int, resource: schemas.ResourceCreate) -> Optional[models.Resource]:
    """Update a resource."""
    db_resource = get_resource(db, resource_id)
    if not db_resource:
        return None
    
    for key, value in resource.dict().items():
        if hasattr(db_resource, key):
            setattr(db_resource, key, value)
    
    db_resource.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_resource)
    return db_resource

def delete_resource(db: Session, resource_id: int) -> bool:
    """Delete a resource."""
    db_resource = get_resource(db, resource_id)
    if not db_resource:
        return False
    
    db.delete(db_resource)
    db.commit()
    return True 