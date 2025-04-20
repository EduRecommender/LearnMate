from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, Text, Enum, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampedModel
from datetime import datetime
import enum
from typing import Dict

class User(Base, TimestampedModel):
    """User model for authentication and profile information."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Profile information
    preferences = Column(JSON, default={})
    
    # StudySession relationship will be set up after the class is defined
    
    def __repr__(self):
        return f"<User {self.username}>"

# Define enums here
class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class ResourceType(str, enum.Enum):
    URL = "url"
    FILE = "file"
    TEXT = "text"

class StudySession(Base):
    """Study session model."""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    field_of_study = Column(String, nullable=False)
    study_goal = Column(Text, nullable=False)
    context = Column(Text, nullable=False)
    time_commitment = Column(Float, nullable=False)  # in hours
    difficulty_level = Column(Enum(DifficultyLevel), nullable=False)
    
    # Additional metadata
    preferences = Column(JSON, default={})
    syllabus = Column(JSON, default={})
    progress = Column(JSON, default={})
    session_metadata = Column(JSON, default={})  # For storing chat history and other dynamic data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys - ensure the table name matches User.__tablename__
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Direct reference to User class - no import needed now
    user = relationship("User", back_populates="study_sessions")
    
    # Resources will be set up after the Resource class is defined
    
    def __repr__(self):
        return f"<StudySession {self.name}>"

    def to_dict(self) -> Dict:
        """Convert session to dictionary format."""
        # Ensure all resources have proper metadata dictionaries
        resources_list = []
        for resource in self.resources:
            # Ensure resource_metadata is a dictionary
            if hasattr(resource, 'resource_metadata') and resource.resource_metadata is not None:
                if not isinstance(resource.resource_metadata, dict):
                    try:
                        resource.resource_metadata = dict(resource.resource_metadata)
                    except (TypeError, ValueError):
                        resource.resource_metadata = {}
            resources_list.append(resource.to_dict())
            
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "field_of_study": self.field_of_study,
            "study_goal": self.study_goal,
            "context": self.context,
            "time_commitment": self.time_commitment,
            "difficulty_level": self.difficulty_level,
            "preferences": self.preferences,
            "syllabus": self.syllabus,
            "progress": self.progress,
            "metadata": self.session_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resources": resources_list
        }

class Resource(Base, TimestampedModel):
    """Resource model for study materials."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(ResourceType), nullable=False)
    content = Column(Text, nullable=True)  # URL or text content
    path = Column(String, nullable=True)   # File path for uploaded files
    resource_metadata = Column(JSON, nullable=True)  # Additional resource metadata
    
    # Foreign Keys
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=False)
    
    # This relationship will be set up below
    
    def __repr__(self):
        return f"<Resource {self.name}>"
        
    def to_dict(self):
        """Convert resource to dictionary format."""
        # Do not include the resource_metadata field at all
        return {
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, ResourceType) else self.type,
            "content": self.content,
            "path": self.path,
            # Explicitly omit resource_metadata/metadata
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class ChatMessage(Base, TimestampedModel):
    """Chat message model for storing chat history."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to study session
    study_session = relationship("StudySession", back_populates="chat_messages")
    
    def __repr__(self):
        return f"<ChatMessage {self.id} ({self.role})>"

# Set up relationships AFTER all classes are defined
User.study_sessions = relationship(
    StudySession, 
    back_populates="user", 
    cascade="all, delete-orphan"
)

StudySession.resources = relationship(
    Resource, 
    back_populates="study_session", 
    cascade="all, delete-orphan"
)

StudySession.chat_messages = relationship(
    ChatMessage,
    back_populates="study_session",
    cascade="all, delete-orphan",
    order_by=ChatMessage.timestamp
)

Resource.study_session = relationship(
    StudySession,
    back_populates="resources"
) 