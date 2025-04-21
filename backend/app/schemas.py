from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Resource schemas
class ResourceBase(BaseModel):
    name: str
    url: Optional[str] = None
    type: str
    content: Optional[str] = None
    resource_metadata: Optional[Dict[str, Any]] = {}

class ResourceCreate(ResourceBase):
    pass

class Resource(ResourceBase):
    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            # Add custom encoder if needed for metadata
        }

# Study Session schemas
class StudySessionBase(BaseModel):
    name: str
    field_of_study: str
    study_goal: str
    context: str
    time_commitment: str
    difficulty_level: str

class StudySessionCreate(StudySessionBase):
    pass

class StudySession(StudySessionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    resources: List[Resource] = []

    class Config:
        orm_mode = True 