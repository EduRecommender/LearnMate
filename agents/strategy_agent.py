from typing import Dict, Any, List, Optional
import logging
import uuid

from agents.base import StrategyAgent, AgentResponse
from agents.schemas.messages import StudyMethod, StudyStrategy, StrategyQuery
from agents.utils.validation import validate_strategy_query, validate_study_strategy
from agents.utils.deepseek_local import DeepSeekLocal

logger = logging.getLogger(__name__)

class DeepSeekStrategyAgent(StrategyAgent):
    """Strategy Agent that uses the open-source DeepSeek model"""
    
    def __init__(self, agent_id: str = "deepseek-strategy-agent", model_name: Optional[str] = None):
        super().__init__(agent_id)
        self.model = DeepSeekLocal(model_name)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process the input data and return a response"""
        try:
            if not await self.validate_input(input_data):
                return self._create_error_response("Invalid input data")
            
            query = StrategyQuery(**input_data)
            return await self.recommend_strategy(query)
        except Exception as e:
            logger.error(f"Error processing strategy query: {str(e)}")
            return await self.handle_error(e)
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate the input data"""
        try:
            validate_strategy_query(input_data)
            return True
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False
    
    async def recommend_strategy(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend a study strategy based on the query"""
        try:
            # Extract content and preferences from the query
            content = query.get("content", {})
            user_preferences = query.get("user_preferences", {})
            session_preferences = query.get("session_preferences", {})
            
            # Extract learning styles and preferred methods
            learning_styles = user_preferences.get("learning_styles", [])
            preferred_methods = user_preferences.get("preferred_study_methods", [])
            
            # Extract session-specific information
            session_goal = session_preferences.get("session_goal", "")
            session_context = session_preferences.get("context", "")
            time_per_day = session_preferences.get("time_per_day", "")
            number_of_days = session_preferences.get("number_of_days", 7)
            
            # Create a rich context for strategy generation
            strategy_context = {
                "content": content,
                "learning_profile": {
                    "styles": learning_styles,
                    "preferred_methods": preferred_methods
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
            
            # Generate strategy using the local model
            strategy = await self.model.generate_strategy(strategy_context)
            
            # Map the method to a StudyMethod enum
            method = StudyMethod(strategy.get("method", "ACTIVE_RECALL"))
            
            # Create a StudyStrategy object
            study_strategy = StudyStrategy(
                strategy_id=str(uuid.uuid4()),
                method=method,
                description=strategy.get("description", ""),
                steps=strategy.get("steps", []),
                estimated_duration=strategy.get("estimated_duration", "1 hour"),
                difficulty_level=strategy.get("difficulty_level", "MEDIUM"),
                prerequisites=strategy.get("prerequisites", []),
                resources=strategy.get("resources", []),
                metadata={
                    "learning_styles": learning_styles,
                    "session_goal": session_goal,
                    "time_commitment": f"{time_per_day} for {number_of_days} days"
                }
            )
            
            # Validate the strategy
            if not await self.validate_strategy(study_strategy):
                return None
            
            return study_strategy.__dict__
        except Exception as e:
            logger.error(f"Error recommending strategy: {str(e)}")
            return None
    
    async def validate_strategy(self, strategy: Dict[str, Any]) -> bool:
        """Validate the recommended strategy"""
        try:
            validate_study_strategy(strategy)
            return True
        except Exception as e:
            logger.error(f"Strategy validation error: {str(e)}")
            return False 