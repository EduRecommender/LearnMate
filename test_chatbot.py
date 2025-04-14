import os
import sys
import logging
from dotenv import load_dotenv
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    # Import the chat_with_bot function
    from chatbot_gpt import chat_with_bot

    # Test message
    test_message = "Tell me about Python programming courses"
    
    # Test difficulty and category
    difficulty = "beginner"
    category = "computer science"
    
    # Empty chat history for initial test
    chat_history = []
    
    logger.info(f"Testing chatbot with message: '{test_message}'")
    logger.info(f"Difficulty: {difficulty}, Category: {category}")
    
    # Call the chatbot function
    response = chat_with_bot(
        user_input=test_message,
        difficulty=difficulty,
        category=category,
        chat_history=chat_history
    )
    
    logger.info("Chatbot response:")
    logger.info(response)
    
    # Add this exchange to chat history
    chat_history.append({"role": "user", "content": test_message})
    chat_history.append({"role": "assistant", "content": response})
    
    # Test a follow-up message
    follow_up_message = "Can you recommend a more advanced course?"
    logger.info(f"\nTesting follow-up message: '{follow_up_message}'")
    
    # Update difficulty
    difficulty = "advanced"
    
    # Call the chatbot function again
    response = chat_with_bot(
        user_input=follow_up_message,
        difficulty=difficulty,
        category=category,
        chat_history=chat_history
    )
    
    logger.info("Chatbot response to follow-up:")
    logger.info(response)
    
except Exception as e:
    logger.error(f"Error testing chatbot: {e}")
    logger.error(traceback.format_exc()) 