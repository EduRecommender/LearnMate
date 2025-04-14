from pydantic import BaseModel, constr, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from pydantic import model_validator

class ResourceType(str, Enum):
    URL = "url"
    FILE = "file"
    TEXT = "text"

class ResourceBase(BaseModel):
    """Base schema for study resources."""
    name: str
    type: ResourceType  # e.g., "url", "file", "text"
    content: Optional[str] = None  # URL or text content
    resource_metadata: Dict[str, Any] = Field(default_factory=dict)

class ResourceCreate(BaseModel):
    """Schema for creating a new resource."""
    session_id: int
    name: str
    type: str
    content: Optional[str] = None
    resource_metadata: Dict[str, Any] = Field(default_factory=dict)

class Resource(BaseModel):
    """Schema for resource response."""
    id: int
    session_id: int
    name: str
    type: str
    content: Optional[str] = None
    path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class StudySessionBase(BaseModel):
    """Base schema for study sessions."""
    name: constr(min_length=1, max_length=100)
    field_of_study: str
    study_goal: str
    context: str
    time_commitment: float
    difficulty_level: DifficultyLevel
    preferences: Dict[str, Any] = Field(default_factory=dict)
    syllabus: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)
    session_metadata: Dict[str, Any] = Field(default_factory=dict)

class StudySessionCreate(StudySessionBase):
    """Schema for creating a new study session."""
    pass

class StudySessionUpdate(BaseModel):
    """Schema for updating a study session."""
    name: Optional[str] = None
    field_of_study: Optional[str] = None
    study_goal: Optional[str] = None
    context: Optional[str] = None
    time_commitment: Optional[float] = None
    difficulty_level: Optional[DifficultyLevel] = None
    preferences: Optional[Dict[str, Any]] = None
    syllabus: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    session_metadata: Optional[Dict[str, Any]] = None
    chat_history: Optional[Dict[str, Any]] = None

class StudySession(StudySessionBase):
    """Schema for study session response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    resources: List[Resource] = []

    model_config = {
        "from_attributes": True
    }

class StudySessionWithDetails(StudySession):
    """Schema for study session response with additional details."""
    total_study_time: Optional[float] = None
    completion_rate: Optional[float] = None
    last_activity: Optional[datetime] = None

# User schemas
class UserBase(BaseModel):
    """Base user schema with common attributes."""
    username: constr(min_length=3, max_length=50)
    email: Optional[str] = None
    is_active: bool = True
    preferences: Dict[str, Any] = {}

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: constr(min_length=4)

class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str

class UserPreferences(BaseModel):
    """Schema for user preferences."""
    academic_level: Optional[str] = None
    field_of_study: Optional[str] = None
    learning_style: Optional[str] = None
    study_goals: Optional[Dict[str, Any]] = Field(default_factory=dict)
    time_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    notifications: Optional[Dict[str, bool]] = Field(default_factory=dict)

class UserUpdate(BaseModel):
    """Schema for updating user information."""
    email: Optional[str] = None
    password: Optional[constr(min_length=4)] = None
    preferences: Optional[Dict[str, Any]] = None

class UserInDBBase(UserBase):
    """Base schema for user in database."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class User(UserInDBBase):
    """Schema for user response."""
    pass

class UserInDB(UserInDBBase):
    """Schema for user in database with hashed password."""
    hashed_password: str

# Chat message schemas
class ChatMessageCreate(BaseModel):
    message_id: str = Field(..., description="Unique identifier for the message")
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the message")
    metadata: Optional[Dict[str, Any]] = None

class ChatMessage(ChatMessageCreate):
    model_config = {
        "from_attributes": True
    } 