"""
Orchestrator Module

This module connects the conversational assistant agent with the content, strategy, and meta agents.
It handles routing messages between agents and managing the state of study sessions.
"""

import uuid
import logging
import json
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from agents.base import AgentResponse
from agents.assistant_agent import DeepSeekAssistantAgent
from agents.meta_agent import DeepSeekMetaAgent
from agents.content_agent import DeepSeekContentAgent
from agents.strategy_agent import DeepSeekStrategyAgent
from agents.schemas.messages import ChatMessage, AssistantMessage
from agents.schemas.sessions import StudySession
from agents.utils.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orchestrator.log')
    ]
)
logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates the interaction between the conversational assistant agent and other agents.
    Handles message routing, state management, and context injection.
    """
    
    def __init__(self):
        logger.info("Initializing AgentOrchestrator")
        
        # Initialize the agents
        self.assistant_agent = DeepSeekAssistantAgent()
        self.meta_agent = DeepSeekMetaAgent()
        self.content_agent = DeepSeekContentAgent()
        self.strategy_agent = DeepSeekStrategyAgent()
        
        # Initialize the session manager
        self.session_manager = SessionManager()
        
        logger.info("AgentOrchestrator initialization complete")
    
    async def process_message(self, 
                             user_id: str, 
                             session_id: str, 
                             message_content: str, 
                             user_preferences: Dict[str, Any] = None,
                             session_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user message through the agent system.
        
        Args:
            user_id: The user's ID
            session_id: The study session ID
            message_content: The message content from the user
            user_preferences: User preferences (optional)
            session_data: Session data (optional)
            
        Returns:
            The assistant's response
        """
        try:
            logger.info(f"Processing message for user: {user_id}, session: {session_id}")
            logger.debug(f"Message content: '{message_content[:100]}...'")
            
            # Create a message ID
            message_id = str(uuid.uuid4())
            
            # Get session data if not provided
            if not session_data:
                session = self.session_manager.get_session(user_id, session_id)
                if session:
                    session_data = session.__dict__
                else:
                    logger.warning(f"Session not found: {session_id} for user: {user_id}")
                    session_data = {}
            
            # Get user preferences if not provided
            if not user_preferences:
                # This would typically come from a user service
                user_preferences = {}
            
            # Get chat history
            chat_history = session_data.get("chat_history", [])
            
            # Determine if this is a command that needs to be routed to another agent
            agent_type, intent = self._analyze_intent(message_content, chat_history)
            
            # Build context
            context = self._build_context(user_id, session_id, session_data, user_preferences, chat_history)
            
            # Create the input message for the assistant
            input_message = AssistantMessage(
                message_id=message_id,
                user_id=user_id,
                session_id=session_id,
                content=message_content,
                timestamp=datetime.now(),
                context=context,
                metadata={
                    "intent": intent,
                    "agent_type": agent_type
                }
            )
            
            # Process the message based on the intent
            response = await self._route_message(input_message, agent_type, intent)
            
            if response.success:
                # Extract the response content
                response_data = response.data
                response_content = response_data.get("content", "I'm sorry, I couldn't process your request.")
                
                # Create a chat message
                chat_message = {
                    "message_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": response_content,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add message to chat history
                self.session_manager.add_chat_message(user_id, session_id, chat_message)
                
                # Return the response data
                return {
                    "message_id": chat_message["message_id"],
                    "content": response_content,
                    "timestamp": chat_message["timestamp"],
                    "metadata": response.metadata
                }
            else:
                # Handle error
                error_message = response.error or "An error occurred while processing your message."
                logger.error(f"Error processing message: {error_message}")
                
                # Create error chat message
                chat_message = {
                    "message_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": f"I'm sorry, I encountered an error: {error_message}",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add error message to chat history
                self.session_manager.add_chat_message(user_id, session_id, chat_message)
                
                # Return error response
                return {
                    "message_id": chat_message["message_id"],
                    "content": chat_message["content"],
                    "timestamp": chat_message["timestamp"],
                    "error": error_message
                }
        
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create fallback error response
            return {
                "message_id": str(uuid.uuid4()),
                "content": f"I'm sorry, an unexpected error occurred: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _build_context(self, 
                      user_id: str, 
                      session_id: str, 
                      session_data: Dict[str, Any],
                      user_preferences: Dict[str, Any],
                      chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build the context for the assistant agent.
        
        Args:
            user_id: The user's ID
            session_id: The study session ID
            session_data: The session data
            user_preferences: The user preferences
            chat_history: The chat history
            
        Returns:
            A context dictionary
        """
        # Extract relevant session information
        name = session_data.get("name", "Study Session")
        field_of_study = session_data.get("field_of_study", "")
        study_goal = session_data.get("study_goal", "")
        context_desc = session_data.get("context", "")
        time_commitment = session_data.get("time_commitment", "")
        difficulty_level = session_data.get("difficulty_level", "")
        resources = session_data.get("resources", [])
        progress = session_data.get("progress", {})
        
        # Extract preferences information
        preferences = session_data.get("preferences", {})
        syllabus = session_data.get("syllabus", {})
        
        # Build a rich context for the assistant
        return {
            "session_data": {
                "id": session_id,
                "name": name,
                "field_of_study": field_of_study,
                "study_goal": study_goal,
                "context": context_desc,
                "time_commitment": time_commitment,
                "difficulty_level": difficulty_level,
                "preferences": preferences,
                "syllabus": syllabus,
                "progress": progress,
                "resources": resources,
                "chat_history": chat_history
            },
            "user_preferences": user_preferences
        }
    
    def _analyze_intent(self, message: str, chat_history: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Analyze the user's message to determine the intent and which agent should handle it.
        
        Args:
            message: The user's message
            chat_history: The chat history
            
        Returns:
            A tuple of (agent_type, intent)
        """
        # Simplified intent analysis based on keywords
        message_lower = message.lower()
        
        # Check for content retrieval intents
        if any(keyword in message_lower for keyword in 
              ["find resource", "get resource", "find material", "find video", "find article", 
               "search for", "look up", "get information on", "find information"]):
            return "content", "retrieve_content"
        
        # Check for strategy intents
        elif any(keyword in message_lower for keyword in 
                ["how to study", "study method", "learning technique", "study technique", 
                 "study strategy", "how should i learn", "best way to learn", "how to learn"]):
            return "strategy", "recommend_strategy"
        
        # Check for plan modification intents
        elif any(keyword in message_lower for keyword in 
                ["create plan", "generate plan", "make plan", "develop plan", 
                 "update plan", "modify plan", "change plan", "reschedule"]):
            return "meta", "create_or_modify_plan"
        
        # Default to assistant for conversational responses
        return "assistant", "general_conversation"
    
    async def _route_message(self, 
                           message: AssistantMessage, 
                           agent_type: str, 
                           intent: str) -> AgentResponse:
        """
        Route the message to the appropriate agent based on intent.
        
        Args:
            message: The input message
            agent_type: The type of agent to handle the message
            intent: The detected intent
            
        Returns:
            The agent's response
        """
        logger.info(f"Routing message to agent: {agent_type}, intent: {intent}")
        
        try:
            if agent_type == "content":
                # Route to content agent
                logger.info("Routing to content agent")
                
                # Extract query parameters from message
                topic = self._extract_topic_from_message(message.content)
                difficulty = message.context.get("session_data", {}).get("difficulty_level", "intermediate")
                
                # Build content query
                content_query = {
                    "query_id": str(uuid.uuid4()),
                    "user_id": message.user_id,
                    "session_id": message.session_id,
                    "topic": topic,
                    "difficulty": difficulty,
                    "content_types": [],  # Could extract from message
                    "preferred_sources": [],  # Could extract from preferences
                    "excluded_sources": [],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Process with content agent
                content_response = await self.content_agent.process(content_query)
                
                # If successful, pass to assistant for explanation
                if content_response.success:
                    # Enhance message with content results
                    enhanced_message = message.__dict__.copy()
                    enhanced_message["context"]["content_results"] = content_response.data
                    enhanced_message["context"]["intent"] = "explain_content_results"
                    
                    # Have assistant explain the content results
                    return await self.assistant_agent.process(enhanced_message)
                else:
                    # Return the error from content agent
                    return content_response
                
            elif agent_type == "strategy":
                # Route to strategy agent
                logger.info("Routing to strategy agent")
                
                # Extract content topic from message
                topic = self._extract_topic_from_message(message.content)
                
                # Build mock content for strategy recommendation
                mock_content = {
                    "content_id": str(uuid.uuid4()),
                    "metadata": {
                        "title": topic,
                        "content_type": "ARTICLE",
                        "difficulty": message.context.get("session_data", {}).get("difficulty_level", "intermediate"),
                        "duration_minutes": 30,
                        "source": "User query",
                        "description": f"Content about {topic}"
                    }
                }
                
                # Build strategy query
                strategy_query = {
                    "query_id": str(uuid.uuid4()),
                    "user_id": message.user_id,
                    "session_id": message.session_id,
                    "content": mock_content,
                    "user_preferences": message.context.get("user_preferences", {}),
                    "session_preferences": message.context.get("session_data", {}).get("preferences", {}),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Process with strategy agent
                strategy_response = await self.strategy_agent.process(strategy_query)
                
                # If successful, pass to assistant for explanation
                if strategy_response.success:
                    # Enhance message with strategy results
                    enhanced_message = message.__dict__.copy()
                    enhanced_message["context"]["strategy_results"] = strategy_response.data
                    enhanced_message["context"]["intent"] = "explain_strategy_results"
                    
                    # Have assistant explain the strategy results
                    return await self.assistant_agent.process(enhanced_message)
                else:
                    # Return the error from strategy agent
                    return strategy_response
                
            elif agent_type == "meta":
                # Route to meta agent
                logger.info("Routing to meta agent")
                
                # Extract topics from message
                topics = self._extract_topics_from_message(message.content)
                
                # Build plan query
                plan_query = {
                    "query_id": str(uuid.uuid4()),
                    "user_id": message.user_id,
                    "session_id": message.session_id,
                    "topics": topics,
                    "user_preferences": message.context.get("user_preferences", {}),
                    "session_preferences": message.context.get("session_data", {}).get("preferences", {}),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Process with meta agent
                plan_response = await self.meta_agent.process(plan_query)
                
                # If successful, pass to assistant for explanation
                if plan_response.success:
                    # Enhance message with plan results
                    enhanced_message = message.__dict__.copy()
                    enhanced_message["context"]["plan_results"] = plan_response.data
                    enhanced_message["context"]["intent"] = "explain_plan_results"
                    
                    # Have assistant explain the plan results
                    return await self.assistant_agent.process(enhanced_message)
                else:
                    # Return the error from meta agent
                    return plan_response
            
            # Default: route to assistant agent
            logger.info("Routing to assistant agent")
            return await self.assistant_agent.process(message.__dict__)
            
        except Exception as e:
            logger.error(f"Error routing message: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create error response
            return AgentResponse(
                success=False,
                data=None,
                error=f"Error routing message: {str(e)}"
            )
    
    def _extract_topic_from_message(self, message: str) -> str:
        """
        Extract the main topic from a message.
        This is a simplified implementation - in a real system,
        this would use NLP to extract topics accurately.
        
        Args:
            message: The user's message
            
        Returns:
            The extracted topic
        """
        # Simple keyword extraction - could be replaced with NLP
        lower_message = message.lower()
        
        # Look for topic after specific phrases
        topic_markers = [
            "about ", "on ", "for ", "related to ", "concerning ",
            "information on ", "resources for ", "material on "
        ]
        
        for marker in topic_markers:
            if marker in lower_message:
                # Get everything after the marker
                start_index = lower_message.find(marker) + len(marker)
                # Look for a period, comma, or end of string
                end_index = next((i for i, char in enumerate(lower_message[start_index:], start_index) 
                                if char in ['.', ',', '?', '!', '\n']), len(lower_message))
                
                if end_index > start_index:
                    return message[start_index:end_index].strip()
        
        # If no topic found, return a generic topic
        return "general knowledge"
    
    def _extract_topics_from_message(self, message: str) -> List[str]:
        """
        Extract multiple topics from a message.
        This is a simplified implementation - in a real system,
        this would use NLP to extract topics accurately.
        
        Args:
            message: The user's message
            
        Returns:
            A list of extracted topics
        """
        # Get the main topic
        main_topic = self._extract_topic_from_message(message)
        
        # In a real implementation, we would extract multiple topics
        # Here we just return the main topic as a single-item list
        return [main_topic]

# Singleton instance
orchestrator = AgentOrchestrator() 