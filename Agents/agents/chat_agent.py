# agents/chat_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from llm_config import llama_llm
from typing import Type
from pydantic import BaseModel, Field

# Study plan placeholder - this will be replaced at runtime
current_study_plan = "No study plan has been generated yet."
current_user_context = {}

def study_plan_explainer(query):
    """Explain aspects of the study plan in more detail."""
    # This accesses the study plan that was saved
    if not current_study_plan or current_study_plan == "No study plan has been generated yet.":
        return "I don't have access to your study plan yet. Please generate a plan first."
    
    return f"Regarding '{query}' in your study plan for {current_user_context.get('subject', 'your subject')}:\n\nBased on the plan, I can explain that this relates to the following sections: [Analysis would be performed on actual plan]"

def recommend_resources(topic):
    """Recommend additional resources for a specific topic."""
    if not current_study_plan or current_study_plan == "No study plan has been generated yet.":
        return "I don't have access to your resource list yet. Please generate a plan first."
    
    return f"For learning more about '{topic}' within {current_user_context.get('subject', 'your subject')}, here are additional resources that complement your existing plan: [Recommendations would be based on actual plan]"

def adjust_schedule(request):
    """Allow the user to adjust their schedule or request modifications."""
    if not current_study_plan or current_study_plan == "No study plan has been generated yet.":
        return "I don't have access to your schedule yet. Please generate a plan first."
    
    return f"I understand you want to adjust your schedule to {request}. Based on your {current_user_context.get('days_until_exam', '7')}-day plan for {current_user_context.get('subject', 'your subject')}, here's how I suggest modifying it: [Adjustments would be based on actual plan]"

# Update study plan context - this function will be called from main.py
def update_context(study_plan, user_context):
    """Update the global context with the study plan and user information."""
    global current_study_plan, current_user_context
    current_study_plan = study_plan
    current_user_context = user_context
    return "Context updated successfully."

# Define schemas for the tools
class ExplainerSchema(BaseModel):
    query: str = Field(..., description="Query about the study plan to explain")

class ResourceSchema(BaseModel):
    topic: str = Field(..., description="Topic to recommend resources for")

class ScheduleSchema(BaseModel):
    request: str = Field(..., description="Request for schedule adjustment")

# Create BaseTool classes for each tool
class ExplainerTool(BaseTool):
    name: str = "explain_plan"
    description: str = "Explain any aspect of the study plan in more detail"
    args_schema: Type[BaseModel] = ExplainerSchema
    
    def _run(self, query: str) -> str:
        return study_plan_explainer(query)

class ResourceTool(BaseTool):
    name: str = "recommend_resources"
    description: str = "Recommend additional resources for a specific topic"
    args_schema: Type[BaseModel] = ResourceSchema
    
    def _run(self, topic: str) -> str:
        return recommend_resources(topic)

class ScheduleTool(BaseTool):
    name: str = "adjust_schedule"
    description: str = "Make adjustments to the study schedule"
    args_schema: Type[BaseModel] = ScheduleSchema
    
    def _run(self, request: str) -> str:
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
