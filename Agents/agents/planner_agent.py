# agents/planner_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from Agents.llm_config import llama_llm
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Type, Dict, Any, List, Union
from pydantic import BaseModel, Field
import math
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_schedule(days, hours_per_day, start_date=None):
    """Calculate a study schedule based on the number of days and hours per day"""
    # Handle dict input similar to other tools
    if isinstance(days, dict):
        # Extract parameters from dict if provided that way
        if "days" in days:
            hours_per_day = days.get("hours_per_day", 2)
            start_date = days.get("start_date")
            days = days.get("days")
    
    # Convert days and hours to appropriate types
    try:
        days = int(days)
        hours_per_day = float(hours_per_day)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid days or hours_per_day value: {e}")
        return f"Error: Please provide valid numbers for days and hours_per_day. Got days={days}, hours_per_day={hours_per_day}"
    
    # Validate inputs
    if days <= 0:
        return "Error: Days must be a positive number"
    if hours_per_day <= 0:
        return "Error: Hours per day must be a positive number"
    if hours_per_day > 12:
        logger.warning(f"Hours per day ({hours_per_day}) seems unrealistically high")
    
    # Handle start_date properly
    if start_date:
        try:
            # If it's a string, try to parse it as a date
            if isinstance(start_date, str):
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y']:
                    try:
                        start_date = datetime.strptime(start_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If none of the formats worked, use current date
                    logger.warning(f"Could not parse start_date: {start_date}, using current date")
                    start_date = datetime.now()
        except Exception as e:
            logger.error(f"Error parsing start_date: {e}")
            start_date = datetime.now()
    else:
        # Default to current date if not provided
        start_date = datetime.now()
    
    # Calculate total available study time
    total_hours = days * hours_per_day
    logger.info(f"Total study time: {total_hours} hours over {days} days")
    
    schedule = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_schedule = {
            'day_number': i + 1,
            'day_name': day.strftime('%A'),
            'date': day.strftime('%Y-%m-%d'),
            'formatted_date': day.strftime('%A, %B %d'),
            'hours': hours_per_day,
            'available_minutes': int(hours_per_day * 60),
            'sessions': []
        }
        schedule.append(day_schedule)
    
    return {
        'days': days,
        'hours_per_day': hours_per_day,
        'total_hours': total_hours,
        'total_minutes': int(total_hours * 60),
        'daily_schedule': schedule,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': (start_date + timedelta(days=days-1)).strftime('%Y-%m-%d')
    }

# Define schema for the scheduler tool
class SchedulerSchema(BaseModel):
    days: Union[int, str, Dict[str, Any]] = Field(..., description="Number of days to schedule")
    hours_per_day: float = Field(2.0, description="Hours per day to study")
    start_date: str = Field(None, description="Start date for the schedule (optional)")

# Create a function to optimize session distribution
def optimize_session_distribution(topic_list, schedule, min_session_minutes=20):
    """Optimize the distribution of topics across the schedule"""
    if not topic_list or not schedule:
        return "Error: Missing topic list or schedule"
    
    # Extract schedule details
    daily_schedule = schedule.get('daily_schedule', [])
    total_days = len(daily_schedule)
    total_minutes = schedule.get('total_minutes', 0)
    
    if not daily_schedule or total_minutes <= 0:
        return "Error: Invalid schedule data"
    
    # Count the total number of topics
    topic_count = len(topic_list)
    if topic_count == 0:
        return "Error: No topics provided"
    
    # Calculate minutes per topic, ensuring each gets at least min_session_minutes
    base_minutes_per_topic = max(min_session_minutes, total_minutes // topic_count)
    
    # Distribute topics based on days available and importance
    distribution_plan = []
    
    # If we have more topics than available sessions, we need to combine topics
    available_sessions = total_days * 2  # Assuming 2 sessions per day maximum
    
    if topic_count <= available_sessions:
        # Simple distribution - each topic gets its own session
        topic_minutes = {}
        remaining_minutes = total_minutes
        
        # First pass - allocate minimum minutes to each topic
        for topic in topic_list:
            topic_minutes[topic] = base_minutes_per_topic
            remaining_minutes -= base_minutes_per_topic
        
        # Second pass - distribute remaining minutes proportionally
        if remaining_minutes > 0 and topic_count > 0:
            extra_per_topic = remaining_minutes // topic_count
            for topic in topic_list:
                topic_minutes[topic] += extra_per_topic
        
        # Create distribution plan
        for day_idx, day in enumerate(daily_schedule):
            day_topics = []
            day_remaining = day.get('available_minutes', 0)
            
            # Assign topics until we run out of time or topics
            for topic in list(topic_minutes.keys()):
                if day_remaining >= topic_minutes[topic]:
                    day_topics.append({
                        'topic': topic,
                        'minutes': topic_minutes[topic]
                    })
                    day_remaining -= topic_minutes[topic]
                    del topic_minutes[topic]
                    
                    # If we've allocated all topics, break
                    if not topic_minutes:
                        break
            
            distribution_plan.append({
                'day': day.get('day_number'),
                'date': day.get('formatted_date'),
                'topics': day_topics,
                'unused_minutes': day_remaining
            })
            
            # If we've allocated all topics, we can stop
            if not topic_minutes:
                break
    else:
        # Complex distribution - need to combine topics into sessions
        topics_per_session = max(1, topic_count // available_sessions)
        if topics_per_session * available_sessions < topic_count:
            topics_per_session += 1
        
        # Group topics into sessions
        session_groups = []
        current_group = []
        
        for topic in topic_list:
            current_group.append(topic)
            if len(current_group) >= topics_per_session:
                session_groups.append(current_group)
                current_group = []
        
        # Add any remaining topics
        if current_group:
            session_groups.append(current_group)
        
        # Distribute session groups across days
        session_minutes = total_minutes // len(session_groups)
        
        for day_idx, day in enumerate(daily_schedule):
            day_sessions = []
            day_remaining = day.get('available_minutes', 0)
            
            # Calculate how many sessions we can fit in this day
            while day_remaining >= session_minutes and session_groups:
                next_session = session_groups.pop(0)
                day_sessions.append({
                    'topics': next_session,
                    'minutes': min(session_minutes, day_remaining)
                })
                day_remaining -= session_minutes
            
            distribution_plan.append({
                'day': day.get('day_number'),
                'date': day.get('formatted_date'),
                'sessions': day_sessions,
                'unused_minutes': day_remaining
            })
            
            # If we've allocated all sessions, we can stop
            if not session_groups:
                break
    
    return distribution_plan

# Define schema for session optimizer
class OptimizerSchema(BaseModel):
    topic_list: List[str] = Field(..., description="List of topics to schedule")
    schedule: Dict[str, Any] = Field(..., description="Schedule object from calculate_schedule")
    min_session_minutes: int = Field(20, description="Minimum session duration in minutes")

# Create a function to validate time constraints
def format_study_plan(study_plan_text):
    """
    Ensure the study plan follows a consistent format with proper day headers
    and resource sections.
    """
    formatted_plan = study_plan_text
    
    # Ensure study plan starts with a proper overview
    if not formatted_plan.startswith("STUDY PLAN OVERVIEW:"):
        # Find any overview section
        overview_match = re.search(r'(OVERVIEW|INTRODUCTION|SUMMARY).*?\n', formatted_plan, re.IGNORECASE)
        if overview_match:
            # Replace with proper heading
            formatted_plan = re.sub(overview_match.group(0), "STUDY PLAN OVERVIEW:\n", formatted_plan)
        else:
            # Add overview section if none exists
            formatted_plan = "STUDY PLAN OVERVIEW:\n" + formatted_plan
    
    # Fix day headers - replace any variant with the standardized format
    day_header_pattern = r'(\*\*)?(?:Day|DAY)\s+(\d+)(?:\*\*)?:?'
    formatted_plan = re.sub(day_header_pattern, r'DAY \2:', formatted_plan)
    
    # Ensure each day header is followed by double newline
    formatted_plan = re.sub(r'(DAY \d+:)\s*\n', r'\1\n\n', formatted_plan)
    
    # Fix resource section header
    if "RECOMMENDED RESOURCES:" not in formatted_plan:
        resource_pattern = r'(?:Resources|RESOURCES):'
        formatted_plan = re.sub(resource_pattern, "RECOMMENDED RESOURCES:", formatted_plan)
        
        # If no resource section exists, add one before implementation tips
        if "RECOMMENDED RESOURCES:" not in formatted_plan:
            implementation_match = re.search(r'IMPLEMENTATION TIPS:', formatted_plan)
            if implementation_match:
                formatted_plan = formatted_plan.replace(
                    implementation_match.group(0),
                    "RECOMMENDED RESOURCES:\n\nIMPLEMENTATION TIPS:"
                )
    
    # Ensure consistent formatting for activities
    formatted_plan = re.sub(r'Activities:', r'Activities:', formatted_plan)
    
    # Replace any "*Day X*" with "DAY X:" to catch any missed headers
    formatted_plan = re.sub(r'\*Day (\d+)\*', r'DAY \1:', formatted_plan)
    
    return formatted_plan

def validate_time_allocation(study_plan, days, hours_per_day):
    """
    Validate that a study plan respects time constraints
    and properly formats day headers
    """
    # Apply the formatting first to ensure consistent headers
    formatted_plan = format_study_plan(study_plan)
    
    # Then perform the regular validation
    expected_total_hours = days * hours_per_day
    expected_minutes = expected_total_hours * 60
    
    # Find all time allocations like "30 minutes", "1 hour", "45 min", etc.
    hour_pattern = re.compile(r'(\d+)\s*(?:hour|hr)s?', re.IGNORECASE)
    minute_pattern = re.compile(r'(\d+)\s*(?:minute|min)s?', re.IGNORECASE)
    
    hour_matches = hour_pattern.findall(formatted_plan)
    minute_matches = minute_pattern.findall(formatted_plan)
    
    # Calculate total minutes
    total_minutes = sum(int(h) * 60 for h in hour_matches) + sum(int(m) for m in minute_matches)
    
    # Check if we have day markers to validate days
    day_pattern = re.compile(r'day\s*(\d+)', re.IGNORECASE)
    day_matches = day_pattern.findall(formatted_plan)
    
    max_day = 0
    if day_matches:
        try:
            day_numbers = [int(d) for d in day_matches]
            max_day = max(day_numbers) if day_numbers else 0
        except ValueError:
            max_day = 0
    
    # Validate and return results
    validation_results = {
        "valid": True,
        "formatted_plan": formatted_plan,
        "feedback": []
    }
    
    # Generate warnings and suggestions
    warnings = []
    suggestions = []
    
    if max_day > days:
        warnings.append(f"Plan includes more than the specified {days} days (found up to Day {max_day})")
        suggestions.append(f"Reduce the number of days to {days}")
    
    if total_minutes > expected_minutes:
        diff_hours = (total_minutes - expected_minutes) / 60
        warnings.append(f"Plan exceeds the time limit by {round(diff_hours, 1)} hours ({total_minutes - expected_minutes} minutes)")
        suggestions.append("Reduce activities or time allocated to stay within constraints")
    elif total_minutes < expected_minutes * 0.9:  # Only flag if significantly under (less than 90%)
        diff_hours = (expected_minutes - total_minutes) / 60
        warnings.append(f"Plan uses less than the available time by {round(diff_hours, 1)} hours ({expected_minutes - total_minutes} minutes)")
        suggestions.append("Add more activities or increase time allocated to maximize learning")
    
    validation_results["warnings"] = warnings
    validation_results["suggestions"] = suggestions
    
    return validation_results

# Create a function to ensure topic coverage
def check_topic_coverage(study_plan, syllabus_topics):
    """Check if all syllabus topics are covered in the study plan"""
    
    if not syllabus_topics:
        return {"covered_all": True, "missing_topics": [], "covered_topics": []}
        
    covered_topics = []
    missing_topics = []
    
    for topic in syllabus_topics:
        # Try different variations of the topic name to handle formatting differences
        topic_variations = [
            topic,
            topic.lower(),
            topic.strip(),
            topic.replace("-", " "),
            topic.replace("_", " ")
        ]
        
        # Check if any variation appears in the study plan
        is_covered = any(var in study_plan.lower() for var in [v.lower() for v in topic_variations if v])
        
        if is_covered:
            covered_topics.append(topic)
        else:
            missing_topics.append(topic)
    
    return {
        "covered_all": len(missing_topics) == 0,
        "coverage_percentage": round((len(covered_topics) / len(syllabus_topics)) * 100, 2),
        "missing_topics": missing_topics,
        "covered_topics": covered_topics
    }

# Define schema for time validator
class TimeValidatorSchema(BaseModel):
    study_plan: str = Field(..., description="The complete study plan text")
    days: int = Field(..., description="Number of days available for studying")
    hours_per_day: float = Field(..., description="Hours per day available for studying")

# Define schema for topic coverage checker
class TopicCoverageSchema(BaseModel):
    study_plan: str = Field(..., description="The complete study plan text")
    syllabus_topics: List[str] = Field(..., description="List of syllabus topics that should be covered")

# Create proper CrewAI BaseTool classes
class SchedulerTool(BaseTool):
    name: str = "calculate_schedule"
    description: str = "Calculate a detailed study schedule based on the number of days and hours per day"
    args_schema: Type[BaseModel] = SchedulerSchema
    
    def _run(self, days, hours_per_day=2, start_date=None):
        return calculate_schedule(days, hours_per_day, start_date)

class SessionOptimizerTool(BaseTool):
    name: str = "optimize_sessions"
    description: str = "Optimize the distribution of topics across the schedule"
    args_schema: Type[BaseModel] = OptimizerSchema
    
    def _run(self, topic_list, schedule, min_session_minutes=20):
        return optimize_session_distribution(topic_list, schedule, min_session_minutes)

class TimeValidatorTool(BaseTool):
    name: str = "validate_time_allocation"
    description: str = "Validate that a study plan respects time constraints"
    args_schema: Type[BaseModel] = TimeValidatorSchema
    
    def _run(self, study_plan, days, hours_per_day):
        return validate_time_allocation(study_plan, days, hours_per_day)

class TopicCoverageTool(BaseTool):
    name: str = "check_topic_coverage"
    description: str = "Check if all syllabus topics are covered in the study plan"
    args_schema: Type[BaseModel] = TopicCoverageSchema
    
    def _run(self, study_plan, syllabus_topics):
        return check_topic_coverage(study_plan, syllabus_topics)

# Instantiate the tools
scheduler_tool = SchedulerTool()
optimizer_tool = SessionOptimizerTool()
time_validator_tool = TimeValidatorTool()
topic_coverage_tool = TopicCoverageTool()

def create_single_day_schedule(hours, start_time=None, break_frequency=45, break_duration=10):
    """
    Create a detailed single-day schedule with integrated breaks
    
    Args:
        hours: Total study hours for the day
        start_time: Start time in format "HH:MM" (24-hour), defaults to "09:00"
        break_frequency: Minutes of study before taking a break, defaults to 45
        break_duration: Duration of breaks in minutes, defaults to 10
        
    Returns:
        A detailed hour-by-hour schedule with breaks
    """
    try:
        # Handle dict input similar to other tools
        if isinstance(hours, dict):
            # Extract parameters from dict if provided that way
            start_time = hours.get("start_time", "09:00")
            break_frequency = hours.get("break_frequency", 45)
            break_duration = hours.get("break_duration", 10)
            hours = hours.get("hours", 6)
        
        # Convert hours to float
        hours = float(hours)
        
        # Validate inputs
        if hours <= 0:
            return "Error: Hours must be a positive number"
        if break_frequency <= 0:
            return "Error: Break frequency must be a positive number"
        if break_duration <= 0:
            return "Error: Break duration must be a positive number"
        
        # Set default start time if not provided
        if not start_time:
            start_time = "09:00"
        
        # Parse start time
        try:
            current_time = datetime.strptime(start_time, "%H:%M")
        except ValueError:
            logger.warning(f"Could not parse start_time: {start_time}, using 09:00")
            current_time = datetime.strptime("09:00", "%H:%M")
        
        # Calculate total minutes and number of breaks needed
        total_minutes = int(hours * 60)
        study_minutes = 0
        schedule = []
        
        while study_minutes < total_minutes:
            # Add a study session
            session_minutes = min(break_frequency, total_minutes - study_minutes)
            
            if session_minutes <= 0:
                break
                
            # Format times
            start_time_str = current_time.strftime("%I:%M %p")
            end_time = current_time + timedelta(minutes=session_minutes)
            end_time_str = end_time.strftime("%I:%M %p")
            
            schedule.append({
                'type': 'study',
                'start_time': start_time_str,
                'end_time': end_time_str,
                'duration': session_minutes,
                'timeframe': f"{start_time_str} - {end_time_str}"
            })
            
            study_minutes += session_minutes
            current_time = end_time
            
            # Add a break if we haven't reached the total study time
            if study_minutes < total_minutes:
                # Format times
                start_time_str = current_time.strftime("%I:%M %p")
                end_time = current_time + timedelta(minutes=break_duration)
                end_time_str = end_time.strftime("%I:%M %p")
                
                schedule.append({
                    'type': 'break',
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'duration': break_duration,
                    'timeframe': f"{start_time_str} - {end_time_str}"
                })
                
                current_time = end_time
        
        # Calculate statistics
        study_blocks = [session for session in schedule if session['type'] == 'study']
        break_blocks = [session for session in schedule if session['type'] == 'break']
        
        total_study_minutes = sum(session['duration'] for session in study_blocks)
        total_break_minutes = sum(session['duration'] for session in break_blocks)
        total_schedule_minutes = total_study_minutes + total_break_minutes
        
        return {
            'schedule': schedule,
            'study_blocks': len(study_blocks),
            'break_blocks': len(break_blocks),
            'total_study_hours': round(total_study_minutes / 60, 2),
            'total_break_minutes': total_break_minutes,
            'total_schedule_minutes': total_schedule_minutes,
            'formatted_timeframe': f"{schedule[0]['start_time']} - {schedule[-1]['end_time']}"
        }
        
    except Exception as e:
        logger.error(f"Error creating single day schedule: {e}")
        return f"Error creating schedule: {str(e)}"

# Define schema for the single day scheduler tool
class SingleDaySchedulerSchema(BaseModel):
    hours: Union[float, str, Dict[str, Any]] = Field(..., description="Total study hours for the day")
    start_time: str = Field("09:00", description="Start time in format 'HH:MM' (24-hour)")
    break_frequency: int = Field(45, description="Minutes of study before taking a break")
    break_duration: int = Field(10, description="Duration of breaks in minutes")

# Add a specialized tool for single day intensive scheduling
class SingleDaySchedulerTool(BaseTool):
    name: str = "create_single_day_schedule"
    description: str = "Create a detailed hour-by-hour schedule for a single intensive study day with integrated breaks"
    args_schema: Type[BaseModel] = SingleDaySchedulerSchema
    
    def _run(self, hours, start_time="09:00", break_frequency=45, break_duration=10):
        """Create a single day intensive study schedule"""
        return create_single_day_schedule(hours, start_time, break_frequency, break_duration)

# Instantiate the single day scheduler tool
single_day_scheduler_tool = SingleDaySchedulerTool()

# Define time management techniques based on research
TIME_MANAGEMENT_TECHNIQUES = {
    "pomodoro": {
        "name": "Pomodoro Technique",
        "description": "Work in 25-minute focused intervals with 5-minute breaks",
        "suitable_for": "Medium to long study sessions (>1 hour)",
        "implementation": "25 minutes focused study + 5 minute break, repeat 4 times, then take 15-30 minute break",
        "high_pressure_compatible": False
    },
    "timeboxing": {
        "name": "Timeboxing",
        "description": "Allocate fixed time blocks to specific tasks",
        "suitable_for": "Short study periods, high pressure situations",
        "implementation": "Set a timer for each specific topic/task with no interruptions",
        "high_pressure_compatible": True
    },
    "spaced_sessions": {
        "name": "Spaced Sessions",
        "description": "Distribute shorter sessions across the day rather than one long session",
        "suitable_for": "Difficult material, improving retention",
        "implementation": "3 x 30-minute sessions spread throughout the day instead of one 90-minute session",
        "high_pressure_compatible": True
    },
    "interleaved_practice": {
        "name": "Interleaved Practice",
        "description": "Mix different topic practice within a single study session",
        "suitable_for": "Related topics, problem-solving subjects",
        "implementation": "Alternate between 2-3 related topics every 20-30 minutes",
        "high_pressure_compatible": False
    }
}

def select_best_strategy(topic, available_time, user_preferences):
    """Dynamically select the best learning strategy based on topic, time and user preferences"""
    days_remaining = int(user_preferences.get('days_until_exam', 2))
    learning_style = user_preferences.get('learning_style', 'visual')
    
    # Define evidence-based strategy references
    strategy_references = {
        "visual": "based on dual coding theory (Clark & Paivio, 1991)",
        "active_recall": "based on retrieval practice research (Karpicke & Roediger, 2008)",
        "spaced_repetition": "based on spacing effect research (Ebbinghaus, 1885; Kornell, 2009)",
        "pomodoro": "based on attention span research (Cirillo, 2018)",
        "3R": "based on Read-Recite-Review method (McDaniel et al., 2009)",
        "interleaving": "based on interleaved practice studies (Rohrer & Taylor, 2007)"
    }
    
    # Time pressure adjustments
    if days_remaining <= 2:
        logger.info(f"High time pressure detected ({days_remaining} days remaining)")
        return {
            "name": "Time-Pressure Study",
            "description": f"Active recall with minimal breaks {strategy_references['active_recall']}",
            "technique": "No standard breaks, only micro-pauses",
            "reference": "Karpicke & Roediger (2008)",
            "evidence_based": True
        }
    
    # Learning style adaptations
    if learning_style.lower() == 'visual':
        return {
            "name": "Visual Mapping",
            "description": f"Mind maps and diagrams for visual learning {strategy_references['visual']}",
            "technique": "Standard Pomodoro with visual tools",
            "reference": "Clark & Paivio (1991)",
            "evidence_based": True
        }
    elif learning_style.lower() == 'auditory':
        return {
            "name": "Verbal Recitation",
            "description": f"Speaking and listening to reinforce concepts {strategy_references['active_recall']}",
            "technique": "Standard Pomodoro with verbal recall",
            "reference": "Karpicke & Roediger (2008)",
            "evidence_based": True
        }
    elif learning_style.lower() == 'kinesthetic':
        return {
            "name": "3R Method",
            "description": f"Read-Recite-Review {strategy_references['3R']}",
            "technique": "Read content, recite from memory, review to check accuracy",
            "reference": "McDaniel et al. (2009)",
            "evidence_based": True
        }
    
    # Default strategy
    return {
        "name": "Spaced Repetition",
        "description": f"Balanced study with regular review intervals {strategy_references['spaced_repetition']}",
        "technique": "Study with increasing intervals between reviews",
        "reference": "Kornell (2009)",
        "evidence_based": True
    }

def identify_relevant_resources(topic, available_resources, user_preferences):
    """Find the most relevant resources for a specific topic"""
    exclude_syllabus = True  # Always exclude syllabus
    
    # Match resources to topic
    matched_resources = []
    for resource in available_resources:
        # Skip syllabus
        if "syllabus" in resource.get('name', '').lower():
            continue
            
        # Check if resource matches the topic
        if topic.lower() in resource.get('name', '').lower():
            # Add specificity to the resource if needed
            resource_name = resource.get('name', '')
            resource_type = determine_resource_type(resource_name)
            
            # Add URL if missing
            if not resource.get('url'):
                resource['url'] = generate_resource_url(resource_name, topic, resource_type)
            
            # Add specificity if missing
            if not has_resource_specificity(resource):
                resource['specificity'] = generate_resource_specificity(resource_type)
            
            matched_resources.append(resource)
    
    return matched_resources

def determine_resource_type(resource_name):
    """Determine the type of resource based on its name"""
    resource_name = resource_name.lower()
    if any(term in resource_name for term in ['book', 'textbook', 'pdf']):
        return 'book'
    elif any(term in resource_name for term in ['video', 'lecture', 'youtube']):
        return 'video'
    elif any(term in resource_name for term in ['article', 'paper', 'journal']):
        return 'article'
    elif any(term in resource_name for term in ['website', 'site', 'http', 'www']):
        return 'website'
    else:
        return 'other'

def generate_resource_url(resource_name, topic, resource_type):
    """Generate a URL for a resource based on its type"""
    search_term = topic.replace(' ', '+')
    
    if resource_type == 'book':
        return f"https://books.google.com/books?q={search_term}"
    elif resource_type == 'video':
        return f"https://www.youtube.com/results?search_query={search_term}"
    elif resource_type == 'article':
        return f"https://scholar.google.com/scholar?q={search_term}"
    elif resource_type == 'website':
        return f"https://duckduckgo.com/?q={search_term}"
    else:
        return f"https://duckduckgo.com/?q={search_term}"

def has_resource_specificity(resource):
    """Check if a resource has specificity (chapter, page number, timestamp)"""
    resource_str = str(resource)
    return any(term in resource_str.lower() for term in ['chapter', 'page', 'section', 'timestamp', 'minute'])

def generate_resource_specificity(resource_type):
    """Generate a specificity string based on resource type"""
    if resource_type == 'book':
        return "Full book coverage"
    elif resource_type == 'video':
        return "Entire video content"
    elif resource_type == 'article':
        return "Entire article content"
    elif resource_type == 'website':
        return "Entire website content"
    else:
        return "General resource coverage"

def calculate_study_plan_parameters(user_context):
    """Calculate key parameters for the study plan based on user context"""
    try:
        days_until_exam = int(float(user_context.get('days_until_exam', 2)))
        
        # Log warning if we're using a default value instead of user-provided value
        if 'days_until_exam' not in user_context or not user_context['days_until_exam']:
            logger.warning(f"No 'days_until_exam' provided in user context, using default of 2 days")
        
        hours_per_day = float(user_context.get('hours_per_day', 2))
        total_available_hours = days_until_exam * hours_per_day
        
        return {
            'days_until_exam': days_until_exam,
            'hours_per_day': hours_per_day,
            'total_available_hours': total_available_hours
        }
    except Exception as e:
        logger.error(f"Error calculating study plan parameters: {e}")
        # Use sensible defaults rather than 30 days
        return {
            'days_until_exam': 2,
            'hours_per_day': 2,
            'total_available_hours': 4
        }

# Create class for planner agent
def create_planner_agent():
    """Create and return the planner agent"""
    agent = Agent(
        role="Study Plan Master Architect",
        goal="Create the most effective and time-efficient study plan tailored to the student's specific needs and constraints.",
    backstory=(
            "As a seasoned educational planner with expertise in instructional design, "
            "learning optimization, and time management, you excel at crafting detailed, "
            "actionable study plans. You understand the science of effective learning and "
            "know how to allocate time for different types of activities. You're skilled "
            "at balancing the need to cover all required topics while respecting strict "
            "time constraints. Your plans are renowned for being comprehensive yet realistic, "
            "with precise time allocations, specific resources, and clear instructions. "
            "Students find your study plans highly effective because they incorporate "
            "evidence-based learning strategies, properly timed breaks, and regular "
            "review sessions."
        ),
    verbose=True,
    allow_delegation=False,
        llm=llama_llm,
        tools=[scheduler_tool, optimizer_tool, time_validator_tool, topic_coverage_tool, single_day_scheduler_tool],
    tools_metadata={
            "dynamic_planning": {
                "select_strategy": "Select the optimal learning strategy based on topic, time constraints, and learning preferences",
                "identify_resources": "Find relevant resources for each topic based on content and user preferences",
                "calculate_parameters": "Determine key study plan parameters like time pressure and topic allocation"
            },
            "scheduling": {
                "strategic_approach": "Start by understanding the time available and topics to cover, then create a day-by-day plan with specific time allocations.",
                "task_allocation": "Assign specific tasks, resources, and strategies to each time block.",
                "evidence_based_techniques": "Include dedicated time for review sessions using spaced repetition."
            },
            "time_management": {
                "break_scheduling": "Always include 5-15 minute breaks every 25-50 minutes of studying using evidence-based techniques.",
                "daily_limits": "Never exceed the specified hours per day limit under any circumstances.",
                "variety": "Mix different types of learning activities to maintain engagement and effectiveness."
            },
            "resource_integration": {
                "specificity": "Always specify exact page numbers, chapters, or video timestamps for every resource.",
                "strategy_alignment": "For each activity, explicitly specify which learning strategy to use with which resource.",
                "formats": "Include a mix of reading, practice, visual learning, and self-testing in the study plan."
            },
            "exam_preparation": {
                "review_sessions": "Schedule regular review sessions that revisit earlier material using spaced repetition.",
                "practice_tests": "Include time for practice tests or self-quizzing sessions if applicable.",
                "final_review": "Plan a comprehensive but not overwhelming final review before the exam date."
            },
            "single_day_planning": {
                "intensive_approach": "For single-day plans, structure as hour-by-hour schedule with frequent breaks.",
                "prioritization": "Focus on highest-yield topics and most efficient learning strategies.",
                "energy_management": "Alternate between more and less demanding activities throughout the day.",
                "break_structure": "Include 5-10 minute breaks every 25-45 minutes, with a longer 20-30 minute break midday."
            }
        }
    )
    
    return agent

# Create the planner agent
planner_agent = create_planner_agent()

# Export the agent
__all__ = ['create_planner_agent', 'planner_agent', 'select_best_strategy', 
           'identify_relevant_resources', 'calculate_study_plan_parameters']
