import os
import sys
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add current directory to Python path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agent_test.log')
    ]
)
logger = logging.getLogger("agent_test")

# Load environment variables
load_dotenv()

async def test_assistant_agent():
    """Test the assistant agent directly"""
    try:
        from agents.assistant_agent import DeepSeekAssistantAgent
        from agents.schemas.messages import ChatMessage

        logger.info("Testing DeepSeekAssistantAgent")
        
        # Initialize the agent with a small model for fast testing
        agent = DeepSeekAssistantAgent(model_name="facebook/opt-125m")
        logger.info("Successfully initialized agent")
        
        # Create a test message
        message_content = "Can you help me with Python programming?"
        session_id = str(uuid.uuid4())
        user_id = "test_user_1"
        
        # Prepare chat history
        chat_history = [
            ChatMessage(
                message_id=str(uuid.uuid4()),
                role="user",
                content="I want to learn Python programming",
                timestamp=datetime.now()
            ).dict()
        ]
        
        # Prepare test context
        context = {
            "session_data": {
                "name": "Python Programming Session",
                "topics": ["Python", "Programming", "Computer Science"],
                "progress": "Just started",
                "preferences": {
                    "session_goal": "Learn Python basics",
                    "context": "Complete beginner",
                    "time_per_day": "1 hour",
                    "number_of_days": 7
                },
                "chat_history": chat_history
            },
            "user_preferences": {
                "learning_styles": ["visual", "hands-on"],
                "preferred_study_methods": ["active_recall", "practice"],
                "subject_interest": ["programming", "data science"]
            }
        }
        
        # Create the input data for the agent - using actual datetime object instead of isoformat string
        input_data = {
            "message_id": str(uuid.uuid4()),
            "content": message_content,
            "timestamp": datetime.now(),
            "user_id": user_id,
            "session_id": session_id,
            "context": context
        }
        
        logger.info(f"Sending message to agent: '{message_content}'")
        # Process the message
        response = await agent.process(input_data)
        
        logger.info("Agent response received")
        logger.info(f"Success: {response.success}")
        
        # Check response format properly
        if response.success:
            logger.info(f"Response data: {str(response.data)[:150]}...")
        else:
            logger.info(f"Error: {response.error}")
            
        return response
    except Exception as e:
        logger.error(f"Error testing assistant agent: {e}")
        logger.error(f"Exception details: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_orchestrator():
    """Test the orchestrator"""
    try:
        # Import instead of creating instance here
        from agents.orchestrator import AgentOrchestrator
        
        logger.info("Testing AgentOrchestrator")
        
        try:
            # Create the orchestrator with specific model names to avoid None errors
            orchestrator = AgentOrchestrator()
            logger.info("Successfully initialized orchestrator")
            
            # Create test message
            message_content = "Can you find resources on Python programming for beginners?"
            session_id = str(uuid.uuid4())
            user_id = "test_user_1"
            
            # Prepare test user preferences
            user_preferences = {
                "learning_styles": ["visual", "hands-on"],
                "preferred_study_methods": ["active_recall", "practice"],
                "subject_interest": ["programming", "data science"]
            }
            
            # Prepare test session data
            session_data = {
                "name": "Python Programming Session",
                "topics": ["Python", "Programming", "Computer Science"],
                "progress": "Just started",
                "preferences": {
                    "session_goal": "Learn Python basics",
                    "context": "Complete beginner",
                    "time_per_day": "1 hour",
                    "number_of_days": 7
                },
                "chat_history": []
            }
            
            logger.info(f"Sending message to orchestrator: '{message_content}'")
            # Process the message
            response = await orchestrator.process_message(
                user_id=user_id,
                session_id=session_id,
                message_content=message_content,
                user_preferences=user_preferences,
                session_data=session_data
            )
            
            logger.info("Orchestrator response received")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response: {str(response)[:150]}...")
            
            return response
        except ImportError as e:
            logger.error(f"Import error in orchestrator: {e}")
            # Continue with test even if orchestrator fails to initialize
            return None
        except Exception as e:
            logger.error(f"Error initializing orchestrator: {e}")
            # Continue with test even if orchestrator fails to initialize
            return None
            
    except Exception as e:
        logger.error(f"Error testing orchestrator: {e}")
        logger.error(f"Exception details: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_deepseek_local():
    """Test the DeepSeekLocal utility directly"""
    try:
        from agents.utils.deepseek_local import DeepSeekLocal
        
        logger.info("Testing DeepSeekLocal utility")
        
        # Initialize with a small model for fast testing
        model = DeepSeekLocal(model_name="facebook/opt-125m")
        logger.info("Successfully initialized DeepSeekLocal model")
        
        # Test text generation
        prompt = "What are some tips for learning Python programming?"
        logger.info(f"Testing text generation with prompt: '{prompt}'")
        
        response = await model.generate_text(prompt, max_length=200)
        
        logger.info("Text generation response received")
        logger.info(f"Response length: {len(response)} characters")
        logger.info(f"Response: {response[:150]}...")
        
        return response
    except Exception as e:
        logger.error(f"Error testing DeepSeekLocal: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def main():
    """Run all tests"""
    logger.info("====== Starting Agent Tests ======")
    
    # Test DeepSeek local utility
    logger.info("\n====== Testing DeepSeekLocal ======")
    deepseek_response = await test_deepseek_local()
    
    # Test assistant agent
    logger.info("\n====== Testing Assistant Agent ======")
    assistant_response = await test_assistant_agent()
    
    # Test orchestrator
    logger.info("\n====== Testing Orchestrator ======")
    orchestrator_response = await test_orchestrator()
    
    logger.info("\n====== All Tests Completed ======")
    
    # Report results
    logger.info("\n====== Test Results ======")
    logger.info(f"DeepSeekLocal: {'SUCCESS' if deepseek_response else 'FAILED'}")
    logger.info(f"Assistant Agent: {'SUCCESS' if assistant_response and assistant_response.success else 'FAILED'}")
    logger.info(f"Orchestrator: {'SUCCESS' if orchestrator_response else 'FAILED'}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 