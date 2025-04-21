from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StudySession(Base):
    """Model for study sessions."""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    field_of_study = Column(String)
    study_goal = Column(Text)
    context = Column(Text)
    time_commitment = Column(String)
    difficulty_level = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with resources
    resources = relationship("Resource", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "field_of_study": self.field_of_study,
            "study_goal": self.study_goal,
            "context": self.context,
            "time_commitment": self.time_commitment,
            "difficulty_level": self.difficulty_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resources": [resource.to_dict() for resource in self.resources]
        }

class Resource(Base):
    """Model for learning resources."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String, nullable=True)
    type = Column(String)
    content = Column(Text, nullable=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with study session
    session = relationship("StudySession", back_populates="resources")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "type": self.type,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 