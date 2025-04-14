from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ContentType(Enum):
    VIDEO = "video"
    ARTICLE = "article"
    TEXTBOOK = "textbook"
    EXERCISE = "exercise"
    FLASHCARD = "flashcard"
    QUIZ = "quiz"
    OTHER = "other"

class StudyMethod(Enum):
    SPACED_REPETITION = "spaced_repetition"
    ACTIVE_RECALL = "active_recall"
    DUAL_CODING = "dual_coding"
    ELABORATIVE_INTERROGATION = "elaborative_interrogation"
    INTERLEAVED_PRACTICE = "interleaved_practice"
    OTHER = "other"

@dataclass
class ContentMetadata:
    """Metadata for study content"""
    title: str
    content_type: ContentType
    difficulty: str
    source: str
    duration_minutes: Optional[int] = None
    url: Optional[str] = None
    tags: List[str] = None
    description: Optional[str] = None

@dataclass
class StudyContent:
    """Study content with metadata"""
    content_id: str
    metadata: ContentMetadata
    content: Any
    created_at: datetime
    updated_at: datetime

@dataclass
class StudyStrategy:
    """Study strategy recommendation"""
    method: StudyMethod
    instructions: str
    estimated_duration: int
    prerequisites: List[str] = None
    expected_outcomes: List[str] = None
    tips: List[str] = None

@dataclass
class StudyTask:
    """Individual study task"""
    task_id: str
    content: StudyContent
    strategy: StudyStrategy
    duration_minutes: int
    order: int
    dependencies: List[str] = None

@dataclass
class StudyDay:
    """Study plan for a single day"""
    date: datetime
    tasks: List[StudyTask]
    total_duration: int
    breaks: List[Dict[str, Any]] = None

@dataclass
class StudyPlan:
    """Complete study plan"""
    plan_id: str
    user_id: str
    session_id: str
    title: str
    description: str
    days: List[StudyDay]
    total_duration: int
    created_at: datetime
    updated_at: datetime
    version: int
    metadata: Dict[str, Any] = None

@dataclass
class ContentQuery:
    """Query for content retrieval"""
    topic: str
    difficulty: str
    content_types: List[ContentType]
    max_duration: Optional[int] = None
    preferred_sources: List[str] = None
    excluded_sources: List[str] = None

@dataclass
class StrategyQuery:
    """Query for strategy recommendation"""
    content: StudyContent
    user_preferences: Dict[str, Any]
    time_constraints: Dict[str, Any]
    learning_goals: List[str]

@dataclass
class PlanQuery:
    """Query for plan generation"""
    user_id: str
    session_id: str
    topics: List[str]
    total_duration: int
    start_date: datetime
    end_date: datetime
    preferences: Dict[str, Any]
    constraints: Dict[str, Any]

@dataclass
class AssistantMessage:
    """Message for the assistant agent"""
    message_id: str
    content: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

@dataclass
class ChatMessage:
    """Message for chat history"""
    message_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def dict(self):
        """Convert to dictionary format"""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "metadata": self.metadata or {}
        } 