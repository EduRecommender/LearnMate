import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import json
import traceback

from agents.base import AssistantAgent, AgentResponse
from agents.schemas.messages import AssistantMessage
from agents.schemas.sessions import ChatMessage
from agents.utils.validation import validate_assistant_message
from agents.utils.deepseek_local import DeepSeekLocal

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deepseek_agent.log')
    ]
)
logger = logging.getLogger(__name__)

class DeepSeekAssistantAgent(AssistantAgent):
    """Assistant Agent that uses the open-source DeepSeek model"""
    
    def __init__(self, agent_id: str = "deepseek-assistant-agent", model_name: Optional[str] = None):
        super().__init__(agent_id)
        logger.info(f"Initializing DeepSeekAssistantAgent with ID: {agent_id}")
        
        # Use a smaller model by default if no model is specified
        if model_name is None:
            # This is a smaller model that doesn't require authentication
            model_name = "facebook/opt-125m"
            logger.info(f"No model specified, using default model: {model_name}")
        
        try:
            logger.info(f"Loading model: {model_name}")
            self.model = DeepSeekLocal(model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process the input data and return a response"""
        try:
            logger.info(f"Processing input data: {json.dumps(input_data, default=str)[:200]}...")
            
            if not await self.validate_input(input_data):
                logger.warning("Input validation failed")
                return self._create_error_response("Invalid input data")
            
            logger.info("Input validation successful")
            message = AssistantMessage(**input_data)
            
            logger.info(f"Processing message with ID: {message.message_id}")
            return await self.process_message(message)
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(traceback.format_exc())
            return await self.handle_error(e)
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate the input data"""
        try:
            logger.debug(f"Validating input: {json.dumps(input_data, default=str)[:200]}...")
            validate_assistant_message(input_data)
            logger.debug("Input validation successful")
            return True
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def process_message(self, message: AssistantMessage) -> AgentResponse:
        """Process a user message"""
        try:
            # Extract message content and context
            content = message.content
            context = message.context or {}
            session_id = message.session_id
            
            logger.info(f"Processing message: '{content[:50]}...' for session: {session_id}")
            
            # Get session data from context
            session_data = context.get("session_data", {})
            chat_history = session_data.get("chat_history", [])
            logger.info(f"Found {len(chat_history)} messages in chat history")
            
            # Create user message
            user_message = ChatMessage(
                message_id=str(uuid.uuid4()),
                role="user",
                content=content,
                timestamp=datetime.now()
            )
            
            # Add user message to chat history
            logger.debug(f"Adding user message to chat history: {user_message.message_id}")
            chat_history.append(user_message.dict())
            
            # Check for special intents from the orchestrator
            intent = context.get("intent", "general_conversation")
            logger.info(f"Detected intent: {intent}")
            
            # Generate response based on intent
            logger.info(f"Generating response using DeepSeek model for intent: {intent}")
            start_time = datetime.now()
            
            if intent == "explain_content_results":
                response = await self._generate_content_explanation(context, chat_history)
            elif intent == "explain_strategy_results":
                response = await self._generate_strategy_explanation(context, chat_history)
            elif intent == "explain_plan_results":
                response = await self._generate_plan_explanation(context, chat_history)
            else:
                # Default general conversation response
                response = await self.generate_response(context, chat_history)
                
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info(f"Response generated in {processing_time:.2f} seconds")
            logger.info(f"Response: '{response[:50]}...'")
            
            # Create assistant message
            assistant_message = ChatMessage(
                message_id=str(uuid.uuid4()),
                role="assistant",
                content=response,
                timestamp=datetime.now()
            )
            
            # Add assistant message to chat history
            logger.debug(f"Adding assistant message to chat history: {assistant_message.message_id}")
            chat_history.append(assistant_message.dict())
            
            # Update session data with new chat history
            session_data["chat_history"] = chat_history
            context["session_data"] = session_data
            
            logger.info("Creating response message")
            # Create a response message
            response_message = AssistantMessage(
                message_id=str(uuid.uuid4()),
                user_id=message.user_id,
                session_id=session_id,
                content=response,
                timestamp=datetime.now(),
                context=context,
                metadata={
                    "original_message_id": message.message_id,
                    "chat_history": chat_history,
                    "processing_time_seconds": processing_time,
                    "intent": intent
                }
            )
            
            logger.info(f"Successfully processed message for session: {session_id}")
            return self._create_success_response(
                data=response_message,
                metadata={
                    "original_message": message.__dict__,
                    "processing_time_seconds": processing_time,
                    "intent": intent
                }
            )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(traceback.format_exc())
            return await self.handle_error(e)
    
    async def _generate_content_explanation(self, context: Dict[str, Any], chat_history: List[Dict[str, Any]]) -> str:
        """Generate an explanation of content search results"""
        try:
            logger.info("Generating content explanation")
            
            # Get the content results from context
            content_results = context.get("content_results", [])
            if not content_results:
                logger.warning("No content results found in context")
                return "I'm sorry, I couldn't find any content results to explain."
            
            # Create a prompt for content explanation
            prompt = f"""
            You are an AI study assistant. Based on the user's message and the search results, provide a helpful response.
            
            User's latest message: {self._get_latest_user_message(chat_history)}
            
            Content search results:
            """
            
            # Add content results to prompt
            for i, content in enumerate(content_results[:5], 1):  # Limit to first 5 results
                metadata = content.get("metadata", {})
                prompt += f"""
                {i}. {metadata.get('title', 'Unknown')}
                   Type: {metadata.get('content_type', 'Unknown')}
                   Difficulty: {metadata.get('difficulty', 'Unknown')}
                   Duration: {metadata.get('duration_minutes', 'Unknown')} minutes
                   Source: {metadata.get('source', 'Unknown')}
                   Description: {metadata.get('description', 'No description available')}
                   URL: {metadata.get('url', 'No URL available')}
                """
            
            prompt += """
            Provide a helpful response that:
            1. Summarizes the most relevant resources found
            2. Explains why these resources are appropriate for the user's needs
            3. Suggests a logical order for consuming these resources
            4. Asks if the user would like more specific information about any of the resources
            
            Be conversational and helpful. Don't use phrases like "Based on the content results" or "According to the search". Just provide the information directly as if you found these resources yourself.
            """
            
            # Generate response
            return await self.model.generate_text(prompt)
        except Exception as e:
            logger.error(f"Error generating content explanation: {str(e)}")
            logger.error(traceback.format_exc())
            return "I apologize, but I encountered an error while explaining the content results. Let me try a different approach to help you find resources."
    
    async def _generate_strategy_explanation(self, context: Dict[str, Any], chat_history: List[Dict[str, Any]]) -> str:
        """Generate an explanation of study strategy results"""
        try:
            logger.info("Generating strategy explanation")
            
            # Get the strategy results from context
            strategy_results = context.get("strategy_results", {})
            if not strategy_results:
                logger.warning("No strategy results found in context")
                return "I'm sorry, I couldn't find any strategy results to explain."
            
            # Create a prompt for strategy explanation
            prompt = f"""
            You are an AI study assistant. Based on the user's message and the suggested study strategy, provide a helpful response.
            
            User's latest message: {self._get_latest_user_message(chat_history)}
            
            Recommended Study Strategy:
            Method: {strategy_results.get('method', 'Unknown')}
            Description: {strategy_results.get('description', 'No description available')}
            
            Steps:
            """
            
            # Add strategy steps to prompt
            steps = strategy_results.get("steps", [])
            for i, step in enumerate(steps, 1):
                prompt += f"{i}. {step}\n"
            
            prompt += f"""
            Estimated Duration: {strategy_results.get('estimated_duration', 'Unknown')}
            Difficulty Level: {strategy_results.get('difficulty_level', 'Unknown')}
            
            Prerequisites:
            """
            
            # Add prerequisites to prompt
            prerequisites = strategy_results.get("prerequisites", [])
            for prereq in prerequisites:
                prompt += f"- {prereq}\n"
            
            prompt += """
            Provide a helpful response that:
            1. Explains the recommended study method in a way that's easy to understand
            2. Highlights the benefits of this approach for the user's specific learning goals
            3. Offers tips for implementing the strategy effectively
            4. Asks if the user would like more details or has questions about the approach
            
            Be conversational and helpful. Don't use phrases like "Based on the strategy results" or "According to the algorithm". Just provide the information directly as if you came up with this strategy yourself.
            """
            
            # Generate response
            return await self.model.generate_text(prompt)
        except Exception as e:
            logger.error(f"Error generating strategy explanation: {str(e)}")
            logger.error(traceback.format_exc())
            return "I apologize, but I encountered an error while explaining the study strategy. Let me try a different approach to help you develop an effective study plan."
    
    async def _generate_plan_explanation(self, context: Dict[str, Any], chat_history: List[Dict[str, Any]]) -> str:
        """Generate an explanation of a study plan"""
        try:
            logger.info("Generating plan explanation")
            
            # Get the plan results from context
            plan_results = context.get("plan_results", {})
            if not plan_results:
                logger.warning("No plan results found in context")
                return "I'm sorry, I couldn't find any plan results to explain."
            
            # Create a prompt for plan explanation
            prompt = f"""
            You are an AI study assistant. Based on the user's message and the study plan, provide a helpful response.
            
            User's latest message: {self._get_latest_user_message(chat_history)}
            
            Study Plan:
            Title: {plan_results.get('title', 'Study Plan')}
            Description: {plan_results.get('description', 'No description available')}
            Total Duration: {plan_results.get('total_duration', 'Unknown')}
            
            Daily Breakdown:
            """
            
            # Add plan days to prompt
            days = plan_results.get("days", [])
            for i, day in enumerate(days, 1):
                prompt += f"\nDay {i}:"
                tasks = day.get("tasks", [])
                total_duration = day.get("total_duration", 0)
                
                for j, task in enumerate(tasks, 1):
                    content = task.get("content", {})
                    strategy = task.get("strategy", {})
                    
                    prompt += f"""
                    Task {j}: {content.get('metadata', {}).get('title', 'Unknown Task')}
                    - Type: {content.get('metadata', {}).get('content_type', 'Unknown')}
                    - Method: {strategy.get('method', 'Unknown')}
                    - Duration: {task.get('duration_minutes', 'Unknown')} minutes
                    - Instructions: {strategy.get('instructions', 'No instructions available')}
                    """
                
                prompt += f"\nTotal time for Day {i}: {total_duration} minutes\n"
            
            prompt += """
            Provide a helpful response that:
            1. Presents the study plan in a clear, easy-to-understand way
            2. Explains how the plan addresses the user's learning goals
            3. Offers suggestions for getting the most out of the plan
            4. Asks if the user would like to modify any aspects of the plan
            
            Be conversational and helpful. Don't use phrases like "Based on the plan results" or "According to the algorithm". Just present the plan as if you created it yourself specifically for this user.
            """
            
            # Generate response
            return await self.model.generate_text(prompt)
        except Exception as e:
            logger.error(f"Error generating plan explanation: {str(e)}")
            logger.error(traceback.format_exc())
            return "I apologize, but I encountered an error while explaining the study plan. Let me try a different approach to help you organize your studies."
    
    def _get_latest_user_message(self, chat_history: List[Dict[str, Any]]) -> str:
        """Get the latest user message from chat history"""
        for msg in reversed(chat_history):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""
    
    async def generate_response(self, context: Dict[str, Any], chat_history: List[Dict[str, Any]]) -> str:
        """Generate a response based on context and session history"""
        try:
            logger.info("Preparing context for response generation")
            # Extract relevant information from context
            session_data = context.get("session_data", {})
            session_name = session_data.get("name", "Unknown")
            topics = session_data.get("topics", [])
            progress = session_data.get("progress", "Not started")
            
            # Log detailed context information
            logger.debug(f"Session name: {session_name}")
            logger.debug(f"Topics: {topics}")
            logger.debug(f"Progress: {progress}")
            
            # Extract user preferences
            user_preferences = context.get("user_preferences", {})
            learning_styles = user_preferences.get("learning_styles", [])
            preferred_study_methods = user_preferences.get("preferred_study_methods", [])
            subject_interest = user_preferences.get("subject_interest", [])
            
            # Extract session preferences
            session_preferences = session_data.get("preferences", {})
            session_goal = session_preferences.get("session_goal", "")
            session_context = session_preferences.get("context", "")
            time_per_day = session_preferences.get("time_per_day", "")
            number_of_days = session_preferences.get("number_of_days", 7)
            
            # Extracting the latest user message
            latest_user_message = ""
            if chat_history and len(chat_history) > 0:
                for msg in reversed(chat_history):
                    if msg.get("role") == "user":
                        latest_user_message = msg.get("content", "")
                        break
            
            logger.debug(f"Latest user message: '{latest_user_message[:50]}...'")
            
            # Create a rich context for the model
            enhanced_context = {
                "user_message": latest_user_message,
                "session_info": {
                    "name": session_name,
                    "topics": topics,
                    "progress": progress,
                    "goal": session_goal,
                    "context": session_context,
                    "time_commitment": {
                        "time_per_day": time_per_day,
                        "number_of_days": number_of_days
                    }
                },
                "user_profile": {
                    "learning_styles": learning_styles,
                    "preferred_methods": preferred_study_methods,
                    "interests": subject_interest
                },
                "chat_history": chat_history
            }
            
            logger.info("Calling DeepSeek model to generate response")
            # Generate response using the local model with enhanced context
            response = await self.model.process_user_message(latest_user_message, enhanced_context)
            
            logger.info(f"Response generated: '{response[:50]}...'")
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            logger.error(traceback.format_exc())
            error_msg = "I'm sorry, I couldn't generate a response. Please try again."
            logger.info(f"Returning fallback response: '{error_msg}'")
            return error_msg 