import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import json

from agents.base import MetaAgent, AgentResponse
from agents.schemas.messages import StudyPlan, PlanQuery, StudyDay, StudyTask
from agents.utils.validation import validate_plan_query, validate_study_plan
from agents.utils.deepseek_local import DeepSeekLocal

logger = logging.getLogger(__name__)

class DeepSeekMetaAgent(MetaAgent):
    """Meta Agent that orchestrates other agents using the open-source DeepSeek model"""
    
    def __init__(self, agent_id: str = "deepseek-meta-agent", model_name: Optional[str] = None):
        super().__init__(agent_id)
        self.model = DeepSeekLocal(model_name)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process the input data and return a response"""
        try:
            if not await self.validate_input(input_data):
                return self._create_error_response("Invalid input data")
            
            query = PlanQuery(**input_data)
            return await self.orchestrate(query)
        except Exception as e:
            logger.error(f"Error processing plan query: {str(e)}")
            return await self.handle_error(e)
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate the input data"""
        try:
            validate_plan_query(input_data)
            return True
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False
    
    async def orchestrate(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate the generation of a study plan"""
        try:
            # Extract topics and preferences from the query
            topics = query.get("topics", [])
            user_preferences = query.get("user_preferences", {})
            session_preferences = query.get("session_preferences", {})
            
            # Extract user learning profile
            learning_styles = user_preferences.get("learning_styles", [])
            preferred_methods = user_preferences.get("preferred_study_methods", [])
            subject_interest = user_preferences.get("subject_interest", [])
            
            # Extract session context
            session_goal = session_preferences.get("session_goal", "")
            session_context = session_preferences.get("context", "")
            time_per_day = session_preferences.get("time_per_day", "")
            number_of_days = session_preferences.get("number_of_days", 7)
            
            # Create a rich context for plan generation
            plan_context = {
                "topics": topics,
                "learning_profile": {
                    "styles": learning_styles,
                    "preferred_methods": preferred_methods,
                    "interests": subject_interest
                },
                "session_context": {
                    "goal": session_goal,
                    "context": session_context,
                    "time_commitment": {
                        "time_per_day": time_per_day,
                        "number_of_days": number_of_days
                    }
                }
            }
            
            # Generate high-level study plan using the local model
            plan_data = await self.model.generate_study_plan(plan_context)
            
            # Create a structured study plan
            study_plan = await self.create_structured_plan(plan_data, topics, number_of_days)
            
            # Validate the plan
            if not await self.validate_plan(study_plan):
                return None
            
            return study_plan
        except Exception as e:
            logger.error(f"Error orchestrating plan: {str(e)}")
            return None
    
    async def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """Validate the generated study plan"""
        try:
            validate_study_plan(plan)
            return True
        except Exception as e:
            logger.error(f"Plan validation error: {str(e)}")
            return False
    
    async def _create_structured_plan(self, plan_data: Dict[str, Any], query: PlanQuery) -> StudyPlan:
        """Create a structured study plan from the generated data"""
        # Extract data from the generated plan
        topics = plan_data.get("topics", query.topics)
        subtopics = plan_data.get("subtopics", {})
        resources = plan_data.get("resources", {})
        methods = plan_data.get("methods", {})
        time_allocation = plan_data.get("time_allocation", {})
        schedule = plan_data.get("schedule", [])
        
        # Create study days
        study_days = []
        current_date = query.start_date
        
        # If no schedule was generated, create a simple one
        if not schedule:
            # Calculate days needed
            total_days = (query.end_date - query.start_date).days
            if total_days <= 0:
                total_days = 1
            
            # Distribute topics across days
            for i, topic in enumerate(topics):
                day_index = i % total_days
                if day_index >= len(study_days):
                    study_days.append({
                        "date": current_date,
                        "tasks": [],
                        "total_duration": 0
                    })
                    current_date = current_date.replace(day=current_date.day + 1)
                
                # Create a task for this topic
                task = {
                    "task_id": str(uuid.uuid4()),
                    "content": {
                        "content_id": str(uuid.uuid4()),
                        "metadata": {
                            "title": topic,
                            "content_type": "ARTICLE",
                            "difficulty": query.preferences.get("difficulty", "intermediate"),
                            "source": "Generated",
                            "description": f"Study material for {topic}"
                        },
                        "content": f"Study material for {topic}",
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    },
                    "strategy": {
                        "method": "ACTIVE_RECALL",
                        "instructions": f"Study {topic} using active recall techniques",
                        "estimated_duration": 30
                    },
                    "duration_minutes": 30,
                    "order": i
                }
                
                study_days[day_index]["tasks"].append(task)
                study_days[day_index]["total_duration"] += 30
        
        # Create the study plan
        return StudyPlan(
            plan_id=str(uuid.uuid4()),
            user_id=query.user_id,
            session_id=query.session_id,
            title=f"Study Plan for {', '.join(topics[:2])}{' and more' if len(topics) > 2 else ''}",
            description=f"A personalized study plan for {', '.join(topics[:3])}{' and more' if len(topics) > 3 else ''}",
            days=[StudyDay(**day) for day in study_days],
            total_duration=query.total_duration,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1,
            metadata={
                "topics": topics,
                "subtopics": subtopics,
                "resources": resources,
                "methods": methods,
                "time_allocation": time_allocation
            }
        ) 