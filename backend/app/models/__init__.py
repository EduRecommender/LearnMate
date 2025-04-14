"""Models package for the application."""
# Base models first
from .base import Base, TimestampedModel

# Import all models from user.py - now it contains all model classes
from .user import User, StudySession, Resource, DifficultyLevel, ResourceType

# All relationships are already defined directly in the model classes

__all__ = [
    'Base',
    'TimestampedModel',
    'User',
    'StudySession',
    'DifficultyLevel',
    'Resource',
    'ResourceType'
] 