import os
import pandas as pd
import logging
import json
import time
import traceback
from openai import OpenAI
from dotenv import load_dotenv

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chatbot.log')
    ]
)
logger = logging.getLogger('chatbot_gpt')

# Load environment variables
load_dotenv()
gpt_api_key = os.getenv("OPENAI_API_KEY")

if not gpt_api_key:
    logger.error("OpenAI API key not found. Ensure your .env file is set up correctly.")
    raise ValueError("OpenAI API key not found. Ensure your .env file is set up correctly.")

# Initialize OpenAI client
try:
    gpt_client = OpenAI(api_key=gpt_api_key)
    logger.info("Successfully initialized OpenAI client")
except Exception as e:
    logger.critical(f"Failed to initialize OpenAI client: {str(e)}")
    logger.critical(traceback.format_exc())
    raise

# Load course dataset dynamically
COURSES_FILE = os.getenv("COURSES_FILE", os.path.join(os.path.dirname(__file__), "input_data", "kaggle_filtered_courses.csv"))

def load_courses():
    """Loads the course dataset dynamically."""
    logger.info(f"Attempting to load courses from: {COURSES_FILE}")
    if not os.path.exists(COURSES_FILE):
        logger.error(f"Course file not found at: {COURSES_FILE}")
        raise FileNotFoundError(f"Course file not found at: {COURSES_FILE}")
    
    try:
        df = pd.read_csv(COURSES_FILE)
        logger.info(f"Successfully loaded {len(df)} courses from {COURSES_FILE}")
        logger.debug(f"Course columns: {df.columns.tolist()}")
        logger.debug(f"Difficulty levels: {df['Difficulty Level'].unique()}")
        logger.debug(f"Categories: {df['Category'].unique()}")
        return df
    except Exception as e:
        logger.error(f"Error loading courses: {str(e)}")
        logger.error(traceback.format_exc())
        raise

try:
    courses = load_courses()
    logger.info(f"Courses loaded successfully with {len(courses)} entries")
except Exception as e:
    logger.critical(f"Failed to load courses: {str(e)}")
    courses = None  # Will be checked later

def summarize_text(text, max_words=20):
    """Returns a shorter version of the text with max_words."""
    if not text or not isinstance(text, str):
        logger.warning(f"Invalid text for summarization: {type(text)}")
        return str(text) if text is not None else ""
    
    words = text.split()
    return " ".join(words[:max_words]) + "..." if len(words) > max_words else text

def chat_with_bot(user_input, difficulty, category, chat_history):
    """
    Conversational chatbot using GPT-4 that remembers past interactions.
    """
    start_time = time.time()
    request_id = f"req_{int(start_time)}"
    
    logger.info(f"[{request_id}] Chat request received - Difficulty: {difficulty}, Category: {category}")
    logger.debug(f"[{request_id}] User input: {user_input}")
    logger.debug(f"[{request_id}] Chat history length: {len(chat_history)}")
    
    # Check if courses are loaded
    if courses is None:
        error_msg = "Course data is not available. Please check logs for details."
        logger.error(f"[{request_id}] {error_msg}")
        return error_msg
    
    # Ensure valid inputs
    if not user_input or not user_input.strip():
        logger.warning(f"[{request_id}] Empty user input received")
        return "Please enter a valid question."

    # Log input parameters
    logger.debug(f"[{request_id}] Difficulty: '{difficulty}', Category: '{category}'")
    
    # Case-insensitive filtering for difficulty and category
    try:
        logger.debug(f"[{request_id}] Filtering courses by difficulty='{difficulty}' and category='{category}'")
        
        # Check if the difficulty and category exist in the dataset
        if difficulty.lower() not in courses["Difficulty Level"].str.lower().unique():
            logger.warning(f"[{request_id}] Difficulty '{difficulty}' not found in dataset")
        
        if category.lower() not in courses["Category"].str.lower().unique():
            logger.warning(f"[{request_id}] Category '{category}' not found in dataset")
        
        # Filter courses
        filtered_courses = courses[
            (courses["Difficulty Level"].str.lower() == difficulty.lower()) & 
            (courses["Category"].str.lower() == category.lower())
        ]
        
        logger.info(f"[{request_id}] Found {len(filtered_courses)} courses matching exact criteria")

        # ✅ If no exact match is found, suggest courses from ANY category at the same difficulty level
        if filtered_courses.empty:
            logger.warning(f"[{request_id}] No exact matches found for difficulty='{difficulty}' and category='{category}'")
            filtered_courses = courses[courses["Difficulty Level"].str.lower() == difficulty.lower()].head(5)
            logger.info(f"[{request_id}] Using {len(filtered_courses)} courses with matching difficulty")
            
            if filtered_courses.empty:
                error_msg = f"Sorry, no courses found for Difficulty Level: {difficulty} and Category: {category}."
                logger.warning(f"[{request_id}] {error_msg}")
                return error_msg
    except Exception as e:
        error_msg = f"An error occurred while filtering courses: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        return error_msg

    # Select only the most relevant columns
    valid_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]
    logger.debug(f"[{request_id}] Selected columns: {valid_columns}")

    # Summarize descriptions to save tokens
    try:
        filtered_courses = filtered_courses.copy()
        logger.debug(f"[{request_id}] Summarizing course descriptions")
        filtered_courses.loc[:, "Course Description"] = filtered_courses["Course Description"].astype(str).apply(
            lambda x: summarize_text(x, max_words=20)
        )
    except Exception as e:
        logger.error(f"[{request_id}] Error summarizing descriptions: {str(e)}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        # Continue with original descriptions

    # Select top 5 courses to reduce token usage
    filtered_courses = filtered_courses[valid_columns].head(5)
    logger.info(f"[{request_id}] Selected top {len(filtered_courses)} courses for recommendation")

    # Format past messages for context
    try:
        past_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
        past_messages.append({"role": "user", "content": user_input})
        logger.debug(f"[{request_id}] Added {len(past_messages)} messages to context")
    except Exception as e:
        logger.error(f"[{request_id}] Error formatting chat history: {str(e)}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        past_messages = [{"role": "user", "content": user_input}]

    # Format recommended courses
    try:
        course_list = "\n".join([
            f"**{row['Name']}** - {row['University']} ({row['Difficulty Level']})\n[Course Link]({row['Link']})"
            for _, row in filtered_courses.iterrows()
        ])
        logger.debug(f"[{request_id}] Created course list with {len(filtered_courses)} courses")
    except Exception as e:
        logger.error(f"[{request_id}] Error formatting course list: {str(e)}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        course_list = "Error formatting course list"

    prompt = f"""
    You are an AI assistant helping users find the best courses.

    User's selected filters:
    - Difficulty Level: {difficulty}
    - Category: {category}

    Recommended Courses:
    {course_list}

    Keep the conversation natural and friendly.
    """

    past_messages.append({"role": "system", "content": prompt})
    logger.debug(f"[{request_id}] Constructed prompt with {len(past_messages)} messages")
    logger.debug(f"[{request_id}] Total prompt length: {sum(len(m['content']) for m in past_messages)} characters")

    # Query GPT-4 API with exception handling
    try:
        logger.info(f"[{request_id}] Sending request to OpenAI API")
        api_start_time = time.time()
        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=past_messages,
            stream=False
        )
        api_time = time.time() - api_start_time
        logger.info(f"[{request_id}] OpenAI API response time: {api_time:.2f} seconds")

        response_content = response.choices[0].message.content
        logger.info(f"[{request_id}] Successfully received response from OpenAI API")
        logger.debug(f"[{request_id}] Response length: {len(response_content)} characters")
        
        total_time = time.time() - start_time
        logger.info(f"[{request_id}] Total processing time: {total_time:.2f} seconds")
        
        return response_content

    except Exception as e:
        error_msg = f"An error occurred while communicating with GPT-4: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        return error_msg
