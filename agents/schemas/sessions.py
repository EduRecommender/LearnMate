from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """Schema for a chat message"""
    message_id: str = Field(..., description="Unique identifier for the message")
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the message")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the message")

class StudySession(BaseModel):
    """Schema for a study session"""
    session_id: str = Field(..., description="Unique identifier for the session")
    user_id: str = Field(..., description="ID of the user who owns this session")
    name: str = Field(..., description="Name of the study session")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Session-specific preferences")
    materials: List[Dict[str, Any]] = Field(default_factory=list, description="Learning materials for the session")
    notes: List[Dict[str, Any]] = Field(default_factory=list, description="User notes for the session")
    progress: Dict[str, Any] = Field(default_factory=dict, description="Session progress tracking")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="Chat history for the session")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the session") 