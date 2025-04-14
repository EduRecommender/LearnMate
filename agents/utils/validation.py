from typing import Any, Dict, List, Optional
from datetime import datetime
from agents.schemas.messages import (
    ContentType, StudyMethod, ContentMetadata, StudyContent,
    StudyStrategy, StudyTask, StudyDay, StudyPlan,
    ContentQuery, StrategyQuery, PlanQuery, AssistantMessage
)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(f"{field + ': ' if field else ''}{message}")

def validate_content_metadata(metadata: Dict[str, Any]) -> bool:
    """Validate content metadata"""
    required_fields = ['title', 'content_type', 'difficulty', 'source']
    for field in required_fields:
        if field not in metadata:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(metadata['content_type'], ContentType):
        raise ValidationError("Invalid content type", 'content_type')
    
    if metadata.get('duration_minutes') is not None:
        if not isinstance(metadata['duration_minutes'], int) or metadata['duration_minutes'] <= 0:
            raise ValidationError("Duration must be a positive integer", 'duration_minutes')
    
    return True

def validate_study_content(content: Dict[str, Any]) -> bool:
    """Validate study content"""
    required_fields = ['content_id', 'metadata', 'content', 'created_at', 'updated_at']
    for field in required_fields:
        if field not in content:
            raise ValidationError(f"Missing required field: {field}", field)
    
    validate_content_metadata(content['metadata'])
    
    if not isinstance(content['created_at'], datetime) or not isinstance(content['updated_at'], datetime):
        raise ValidationError("Invalid datetime format", 'timestamps')
    
    return True

def validate_study_strategy(strategy: Dict[str, Any]) -> bool:
    """Validate study strategy"""
    required_fields = ['method', 'instructions', 'estimated_duration']
    for field in required_fields:
        if field not in strategy:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(strategy['method'], StudyMethod):
        raise ValidationError("Invalid study method", 'method')
    
    if not isinstance(strategy['estimated_duration'], int) or strategy['estimated_duration'] <= 0:
        raise ValidationError("Estimated duration must be a positive integer", 'estimated_duration')
    
    return True

def validate_study_task(task: Dict[str, Any]) -> bool:
    """Validate study task"""
    required_fields = ['task_id', 'content', 'strategy', 'duration_minutes', 'order']
    for field in required_fields:
        if field not in task:
            raise ValidationError(f"Missing required field: {field}", field)
    
    validate_study_content(task['content'])
    validate_study_strategy(task['strategy'])
    
    if not isinstance(task['duration_minutes'], int) or task['duration_minutes'] <= 0:
        raise ValidationError("Duration must be a positive integer", 'duration_minutes')
    
    if not isinstance(task['order'], int) or task['order'] < 0:
        raise ValidationError("Order must be a non-negative integer", 'order')
    
    return True

def validate_study_day(day: Dict[str, Any]) -> bool:
    """Validate study day"""
    required_fields = ['date', 'tasks', 'total_duration']
    for field in required_fields:
        if field not in day:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(day['date'], datetime):
        raise ValidationError("Invalid date format", 'date')
    
    if not isinstance(day['tasks'], list):
        raise ValidationError("Tasks must be a list", 'tasks')
    
    for task in day['tasks']:
        validate_study_task(task)
    
    if not isinstance(day['total_duration'], int) or day['total_duration'] <= 0:
        raise ValidationError("Total duration must be a positive integer", 'total_duration')
    
    return True

def validate_study_plan(plan: Dict[str, Any]) -> bool:
    """Validate study plan"""
    required_fields = [
        'plan_id', 'user_id', 'session_id', 'title', 'description',
        'days', 'total_duration', 'created_at', 'updated_at', 'version'
    ]
    for field in required_fields:
        if field not in plan:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(plan['days'], list):
        raise ValidationError("Days must be a list", 'days')
    
    for day in plan['days']:
        validate_study_day(day)
    
    if not isinstance(plan['version'], int) or plan['version'] < 0:
        raise ValidationError("Version must be a non-negative integer", 'version')
    
    if not isinstance(plan['created_at'], datetime) or not isinstance(plan['updated_at'], datetime):
        raise ValidationError("Invalid datetime format", 'timestamps')
    
    return True

def validate_content_query(query: Dict[str, Any]) -> bool:
    """Validate content query"""
    required_fields = ['topic', 'difficulty', 'content_types']
    for field in required_fields:
        if field not in query:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(query['content_types'], list):
        raise ValidationError("Content types must be a list", 'content_types')
    
    for content_type in query['content_types']:
        if not isinstance(content_type, ContentType):
            raise ValidationError("Invalid content type", 'content_types')
    
    if query.get('max_duration') is not None:
        if not isinstance(query['max_duration'], int) or query['max_duration'] <= 0:
            raise ValidationError("Max duration must be a positive integer", 'max_duration')
    
    return True

def validate_strategy_query(query: Dict[str, Any]) -> bool:
    """Validate strategy query"""
    required_fields = ['content', 'user_preferences', 'time_constraints', 'learning_goals']
    for field in required_fields:
        if field not in query:
            raise ValidationError(f"Missing required field: {field}", field)
    
    validate_study_content(query['content'])
    
    if not isinstance(query['learning_goals'], list):
        raise ValidationError("Learning goals must be a list", 'learning_goals')
    
    return True

def validate_plan_query(query: Dict[str, Any]) -> bool:
    """Validate plan query"""
    required_fields = [
        'user_id', 'session_id', 'topics', 'total_duration',
        'start_date', 'end_date', 'preferences', 'constraints'
    ]
    for field in required_fields:
        if field not in query:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(query['topics'], list):
        raise ValidationError("Topics must be a list", 'topics')
    
    if not isinstance(query['total_duration'], int) or query['total_duration'] <= 0:
        raise ValidationError("Total duration must be a positive integer", 'total_duration')
    
    if not isinstance(query['start_date'], datetime) or not isinstance(query['end_date'], datetime):
        raise ValidationError("Invalid datetime format", 'dates')
    
    if query['start_date'] >= query['end_date']:
        raise ValidationError("Start date must be before end date", 'dates')
    
    return True

def validate_assistant_message(message: Dict[str, Any]) -> bool:
    """Validate assistant message"""
    required_fields = ['message_id', 'user_id', 'session_id', 'content', 'timestamp']
    for field in required_fields:
        if field not in message:
            raise ValidationError(f"Missing required field: {field}", field)
    
    if not isinstance(message['timestamp'], datetime):
        raise ValidationError("Invalid datetime format", 'timestamp')
    
    if not message['content'].strip():
        raise ValidationError("Content cannot be empty", 'content')
    
    return True 