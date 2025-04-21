# agents/chat_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from Agents.llm_config import llama_llm
from typing import Type
from pydantic import BaseModel, Field
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Study plan placeholder - this will be replaced at runtime
current_study_plan = "No study plan has been generated yet."
current_user_context = {}

# Tool call tracking to prevent repetitive calls
previous_tool_calls = {
    "explain_plan": {"input": None, "result": None, "count": 0},
    "recommend_resources": {"input": None, "result": None, "count": 0},
    "adjust_schedule": {"input": None, "result": None, "count": 0}
}

# Helper function to extract string values from complex objects
def extract_string_value(obj, default_key=None):
    """Extract a simple string value from potentially complex input objects"""
    
    # Handle direct string case
    if isinstance(obj, str):
        # Try to parse JSON string
        try:
            if obj.strip().startswith("{") and obj.strip().endswith("}"):
                import json
                parsed = json.loads(obj)
                if isinstance(parsed, dict):
                    # If parsed, extract from dict
                    if default_key and default_key in parsed:
                        return extract_string_value(parsed[default_key])
                    # Try common keys
                    for key in ["value", "input", "text", "query", "topic", "request", "description"]:
                        if key in parsed:
                            return extract_string_value(parsed[key])
                    # If no keys matched, convert the first value to string
                    if parsed:
                        return str(next(iter(parsed.values())))
                return obj
        except:
            # Not JSON, return as is
            return obj
        return obj
        
    # Handle dict case
    if isinstance(obj, dict):
        # Try with the default key first
        if default_key and default_key in obj:
            return extract_string_value(obj[default_key])
            
        # Try with common parameter names
        for key in ["value", "input", "text", "query", "topic", "request", "description"]:
            if key in obj:
                return extract_string_value(obj[key])
                
        # If no keys matched, convert the first value to string
        if obj:
            return str(next(iter(obj.values())))
            
    # For any other type, convert to string
    return str(obj)

def study_plan_explainer(query):
    """Explain aspects of the study plan in more detail."""
    global previous_tool_calls
    
    # Use the helper function to get a string value
    query_str = extract_string_value(query, "query")
    
    # Check for repetitive calls
    if previous_tool_calls["explain_plan"]["input"] == query_str:
        previous_tool_calls["explain_plan"]["count"] += 1
        if previous_tool_calls["explain_plan"]["count"] >= 2:
            logger.warning(f"Detected repetitive call to explain_plan: '{query_str}' (count: {previous_tool_calls['explain_plan']['count']})")
            return previous_tool_calls["explain_plan"]["result"] + "\n\nNOTE: I notice you've asked this same question multiple times. Let me know if you'd like more specific details or have a different question."
    else:
        # Reset counter for new query
        previous_tool_calls["explain_plan"]["count"] = 1
    
    # This accesses the study plan that was saved
    if not current_study_plan or current_study_plan == "No study plan has been generated yet.":
        result = "I don't have access to your study plan yet. Please generate a plan first."
    else:
        subject = current_user_context.get('subject', 'your subject')
        days = current_user_context.get('days_until_exam', '2')
        hours = current_user_context.get('hours_per_day', '2')
        learning_style = current_user_context.get('learning_style', 'visual')
        
        # Include additional context info if available
        context_info = ""
        if 'difficult_topics' in current_user_context and current_user_context['difficult_topics']:
            if isinstance(current_user_context['difficult_topics'], list):
                topics = ", ".join(current_user_context['difficult_topics'])
            else:
                topics = current_user_context['difficult_topics']
            context_info += f" I know you find {topics} particularly challenging, so I'll focus on explaining that aspect."
        
        if 'previous_knowledge' in current_user_context and current_user_context['previous_knowledge']:
            context_info += f" Given your {current_user_context['previous_knowledge']} background in the subject,"
        
        result = f"Regarding '{query_str}' in your {days}-day study plan for {subject} ({hours} hours/day with a {learning_style} learning style):{context_info}\n\nBased on the plan, I can explain that this relates to the following sections: [Analysis would be performed on actual plan]"
    
    # Store the result and input for future comparison
    previous_tool_calls["explain_plan"]["input"] = query_str
    previous_tool_calls["explain_plan"]["result"] = result
    
    return result

def recommend_resources(topic):
    """Recommend additional resources for a specific topic."""
    global previous_tool_calls
    
    # Use the helper function to get a string value
    topic_str = extract_string_value(topic, "topic")
    
    # Check for repetitive calls
    if previous_tool_calls["recommend_resources"]["input"] == topic_str:
        previous_tool_calls["recommend_resources"]["count"] += 1
        if previous_tool_calls["recommend_resources"]["count"] >= 2:
            logger.warning(f"Detected repetitive call to recommend_resources: '{topic_str}' (count: {previous_tool_calls['recommend_resources']['count']})")
            return previous_tool_calls["recommend_resources"]["result"] + "\n\nNOTE: I notice you've asked for resources on this same topic multiple times. Would you like me to recommend different types of resources, or do you need more specific information about these resources?"
    else:
        # Reset counter for new topic
        previous_tool_calls["recommend_resources"]["count"] = 1
    
    if not current_study_plan or current_study_plan == "No study plan has been generated yet.":
        result = "I don't have access to your resource list yet. Please generate a plan first."
    else:
        subject = current_user_context.get('subject', 'your subject')
        
        # Include preferred resources if available
        resource_preferences = ""
        if 'preferred_resources' in current_user_context and current_user_context['preferred_resources']:
            if isinstance(current_user_context['preferred_resources'], list):
                resources = ", ".join(current_user_context['preferred_resources'])
            else:
                resources = current_user_context['preferred_resources']
            resource_preferences = f" I'll prioritize {resources} resources since those are your preference."
        
        result = f"For learning more about '{topic_str}' within {subject}, here are additional resources that complement your existing plan:{resource_preferences}\n\n[Recommendations would be based on actual plan]"
    
    # Store the result and input for future comparison
    previous_tool_calls["recommend_resources"]["input"] = topic_str
    previous_tool_calls["recommend_resources"]["result"] = result
    
    return result

def adjust_schedule(request):
    """Allow the user to adjust their schedule or request modifications."""
    global previous_tool_calls
    
    # Use the helper function to get a string value
    request_str = extract_string_value(request, "request")
    
    # Check for repetitive calls
    if previous_tool_calls["adjust_schedule"]["input"] == request_str:
        previous_tool_calls["adjust_schedule"]["count"] += 1
        if previous_tool_calls["adjust_schedule"]["count"] >= 2:
            logger.warning(f"Detected repetitive call to adjust_schedule: '{request_str}' (count: {previous_tool_calls['adjust_schedule']['count']})")
            return previous_tool_calls["adjust_schedule"]["result"] + "\n\nNOTE: I notice you've made this same schedule adjustment request multiple times. Is there something specific about the adjustment that you'd like me to explain or modify further?"
    else:
        # Reset counter for new request
        previous_tool_calls["adjust_schedule"]["count"] = 1
    
    if not current_study_plan or current_study_plan == "No study plan has been generated yet.":
        result = "I don't have access to your schedule yet. Please generate a plan first."
    else:
        subject = current_user_context.get('subject', 'your subject')
        days = current_user_context.get('days_until_exam', '2')
        hours = current_user_context.get('hours_per_day', '2')
        
        # Include time preferences if available
        time_preferences = ""
        if 'preferred_time_of_day' in current_user_context and current_user_context['preferred_time_of_day']:
            time_preferences = f" I'll make sure to prioritize {current_user_context['preferred_time_of_day']} study sessions since that's your preferred time."
        
        # Include difficult topics if available
        difficult_topics = ""
        if 'difficult_topics' in current_user_context and current_user_context['difficult_topics']:
            if isinstance(current_user_context['difficult_topics'], list):
                topics = ", ".join(current_user_context['difficult_topics'])
            else:
                topics = current_user_context['difficult_topics']
            difficult_topics = f" I'll allocate more time for {topics} since you find these topics challenging."
        
        result = f"I understand you want to adjust your schedule to {request_str}. Based on your {days}-day plan ({hours} hours/day) for {subject}, here's how I suggest modifying it:{time_preferences}{difficult_topics}\n\n[Adjustments would be based on actual plan]"
    
    # Store the result and input for future comparison
    previous_tool_calls["adjust_schedule"]["input"] = request_str
    previous_tool_calls["adjust_schedule"]["result"] = result
    
    return result

# Update study plan context - this function will be called from main.py
def update_context(study_plan, user_context):
    """Update the global context with the study plan and user information."""
    global current_study_plan, current_user_context
    
    # Apply formatting fix to ensure consistent format
    
    # Fix day headers format if needed
    day_header_pattern = r'(\*\*)?(?:Day|DAY)\s+(\d+)(?:\*\*)?:?'
    if re.search(day_header_pattern, study_plan):
        study_plan = re.sub(day_header_pattern, r'DAY \2:', study_plan)
    
    # Fix resource section header if needed
    if "RECOMMENDED RESOURCES:" not in study_plan and re.search(r'(?:Resources|RESOURCES):', study_plan):
        study_plan = re.sub(r'(?:Resources|RESOURCES):', "RECOMMENDED RESOURCES:", study_plan)
    
    current_study_plan = study_plan
    current_user_context = user_context
    return "Context updated successfully."

# Define schemas for the tools
class ExplainerSchema(BaseModel):
    query: object = Field(..., description="Query about the study plan to explain")

    class Config:
        # Allow extra fields to handle different CrewAI versions
        extra = "allow"
        # Allow arbitrary types
        arbitrary_types_allowed = True

class ResourceSchema(BaseModel):
    topic: object = Field(..., description="Topic to recommend resources for")

    class Config:
        # Allow extra fields to handle different CrewAI versions
        extra = "allow"
        # Allow arbitrary types
        arbitrary_types_allowed = True

class ScheduleSchema(BaseModel):
    request: object = Field(..., description="Request for schedule adjustment")

    class Config:
        # Allow extra fields to handle different CrewAI versions
        extra = "allow"
        # Allow arbitrary types
        arbitrary_types_allowed = True

# Create BaseTool classes for each tool
class ExplainerTool(BaseTool):
    name: str = "explain_plan"
    description: str = "Explain any aspect of the study plan in more detail"
    args_schema: Type[BaseModel] = ExplainerSchema
    
    def _run(self, query: str) -> str:
        # Pass the entire input to the function to handle various formats
        return study_plan_explainer(query)

class ResourceTool(BaseTool):
    name: str = "recommend_resources"
    description: str = "Recommend additional resources for a specific topic"
    args_schema: Type[BaseModel] = ResourceSchema
    
    def _run(self, topic: str) -> str:
        # Pass the entire input to the function to handle various formats
        return recommend_resources(topic)

class ScheduleTool(BaseTool):
    name: str = "adjust_schedule"
    description: str = "Make adjustments to the study schedule"
    args_schema: Type[BaseModel] = ScheduleSchema
    
    def _run(self, request: str) -> str:
        # Pass the entire input to the function to handle various formats
        return adjust_schedule(request)

# Instantiate the tool classes
explainer_tool = ExplainerTool()
resource_tool = ResourceTool()
schedule_tool = ScheduleTool()

chat_agent = Agent(
    role="Study Assistant Chatbot",
    goal="Answer the user's study-related questions using the strategy, plan, and resources.",
    backstory=(
        "You are a helpful and knowledgeable study chatbot. You understand the user's full plan — "
        "including their learning preferences, study strategies, schedule, and resource list. "
        "You provide clear, accurate answers and allow the user to explore or adjust their plan. "
        "You can explain complicated concepts in simple terms, recommend additional resources, "
        "and help the user modify their schedule if needed. Your main objective is to help the "
        "user implement their study plan effectively and address any questions or concerns."
    ),
    llm=llama_llm,
    verbose=True,
    tools=[explainer_tool, resource_tool, schedule_tool],
    tools_metadata={
        "study_plan": current_study_plan,
        "user_context": current_user_context
    }
)
