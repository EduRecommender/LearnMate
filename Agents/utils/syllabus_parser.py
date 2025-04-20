"""
Syllabus parser utility to extract key information from course syllabi
"""

import re
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_syllabus(syllabus_text: str) -> Dict[str, Any]:
    """
    Parse a syllabus text to extract key information like topics,
    learning objectives, and assessment methods.
    
    Args:
        syllabus_text: The raw text of the syllabus to parse
        
    Returns:
        Dictionary containing structured syllabus information
    """
    if not syllabus_text or not isinstance(syllabus_text, str):
        logger.warning("Empty or invalid syllabus text provided")
        return {}
    
    try:
        # Initialize the result structure
        result = {
            "course_name": None,
            "topics": [],
            "learning_objectives": [],
            "assessments": [],
            "schedule": []
        }
        
        # Extract course name (usually at the beginning)
        course_name_match = re.search(r'(?i)(?:course|class|subject)(?:\s+title)?(?:\s*:|\s+is)?\s+([^\n\.]+)', syllabus_text)
        if course_name_match:
            result["course_name"] = course_name_match.group(1).strip()
        
        # Extract topics (looking for lists, bullet points, or sections)
        topic_section = re.search(r'(?i)(?:topics|content|curriculum|subject matter)(?:\s+covered)?(?:\s*:|\s+include)?\s+([^#]+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)', syllabus_text)
        if topic_section:
            topic_text = topic_section.group(1)
            # Look for numbered or bulleted lists
            topics = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-|\•)\s*([^\n]+)', topic_text)
            if topics:
                result["topics"] = [topic.strip() for topic in topics]
            else:
                # If no bullet points, try to split by newlines or semicolons
                topics = re.split(r'(?:;\s*|\n+\s*)', topic_text)
                result["topics"] = [topic.strip() for topic in topics if topic.strip()]
        
        # Extract learning objectives
        objective_section = re.search(r'(?i)(?:learning\s+objectives|objectives|goals|outcomes)(?:\s*:|\s+include)?\s+([^#]+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)', syllabus_text)
        if objective_section:
            objective_text = objective_section.group(1)
            objectives = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-|\•)\s*([^\n]+)', objective_text)
            if objectives:
                result["learning_objectives"] = [obj.strip() for obj in objectives]
            else:
                objectives = re.split(r'(?:;\s*|\n+\s*)', objective_text)
                result["learning_objectives"] = [obj.strip() for obj in objectives if obj.strip()]
        
        # Extract assessment methods
        assessment_section = re.search(r'(?i)(?:assessment|grading|evaluation|assignments)(?:\s*:|\s+include)?\s+([^#]+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)', syllabus_text)
        if assessment_section:
            assessment_text = assessment_section.group(1)
            assessments = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-|\•)\s*([^\n]+)', assessment_text)
            if assessments:
                result["assessments"] = [assessment.strip() for assessment in assessments]
            else:
                assessments = re.split(r'(?:;\s*|\n+\s*)', assessment_text)
                result["assessments"] = [assessment.strip() for assessment in assessments if assessment.strip()]
        
        # Extract schedule if available
        schedule_section = re.search(r'(?i)(?:schedule|timeline|course calendar|weekly outline)(?:\s*:|\s+include)?\s+([^#]+?)(?=\n\s*\n|\n\s*[A-Z]|\Z)', syllabus_text)
        if schedule_section:
            schedule_text = schedule_section.group(1)
            # Try to identify week or session patterns
            schedule_items = re.findall(r'(?:^|\n)\s*(?:Week|Session|Day|Class)?\s*\d+\s*[\.:]?\s*([^\n]+)', schedule_text)
            if schedule_items:
                result["schedule"] = [item.strip() for item in schedule_items]
        
        return result
    
    except Exception as e:
        logger.error(f"Error parsing syllabus: {e}")
        return {} 