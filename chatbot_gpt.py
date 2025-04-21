import os
import time
import random
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
gpt_api_key = os.getenv("OPENAI_API_KEY")

if not gpt_api_key:
    raise ValueError("OpenAI API key not found. Ensure your .env file is set up correctly.")

# Initialize OpenAI client
gpt_client = OpenAI(api_key=gpt_api_key)

# Load course dataset dynamically
COURSES_FILE = os.getenv("COURSES_FILE", os.path.join(os.path.dirname(__file__), "input_data", "kaggle_filtered_courses.csv"))

def load_courses():
    """Loads the course dataset dynamically."""
    if not os.path.exists(COURSES_FILE):
        raise FileNotFoundError(f"Course file not found at: {COURSES_FILE}")
    
    return pd.read_csv(COURSES_FILE)

courses = load_courses()

def summarize_text(text, max_words=20):
    """Returns a shorter version of the text with max_words."""
    words = text.split()
    return " ".join(words[:max_words]) + "..." if len(words) > max_words else text

# retry requesting / handling function
def retry_request(func, max_retries=3, backoff_factor=2, jitter=1.0):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = backoff_factor ** attempt + random.uniform(0, jitter)
                print(f"Retrying in {sleep_time:.2f} seconds due to error: {e}")
                time.sleep(sleep_time)
            else:
                raise e

def chat_with_bot(user_input, difficulty, category, chat_history):
    """
    Conversational chatbot using GPT-4 that remembers past interactions.
    """
    # Ensure valid inputs
    if not user_input.strip():
        return "Please enter a valid question."

    # Case-insensitive filtering for difficulty and category
    filtered_courses = courses[
        (courses["Difficulty Level"].str.lower() == difficulty.lower()) & 
        (courses["Category"].str.lower() == category.lower())
    ]

    # ✅ If no exact match is found, suggest courses from ANY category at the same difficulty level
    if filtered_courses.empty:
        filtered_courses = courses[courses["Difficulty Level"].str.lower() == difficulty.lower()].head(5)
        if filtered_courses.empty:
            return f"Sorry, no courses found for Difficulty Level: {difficulty} and Category: {category}."

    # Select only the most relevant columns
    valid_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]

    # Summarize descriptions to save tokens
    filtered_courses = filtered_courses.copy()
    filtered_courses.loc[:, "Course Description"] = filtered_courses["Course Description"].astype(str).apply(lambda x: summarize_text(x, max_words=20))

    # Select top 5 courses to reduce token usage
    filtered_courses = filtered_courses[valid_columns].head(5)

    # Format past messages for context
    past_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    past_messages.append({"role": "user", "content": user_input})

    # Format recommended courses
    course_list = "\n".join([
        f"**{row['Name']}** - {row['University']} ({row['Difficulty Level']})\n[Course Link]({row['Link']})"
        for _, row in filtered_courses.iterrows()
    ])

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

    # Query GPT-4 API with exception handling
#    try:
#        response = gpt_client.chat.completions.create(
#            model="gpt-4",
#            messages=past_messages,
#            stream=False
#        )
#
#        return response.choices[0].message.content
#
#    except Exception as e:
#        return f"An error occurred while communicating with GPT-4: {str(e)}"

    def gpt_call():
        return gpt_client.chat.completions.create(
            model="gpt-4",
            messages=past_messages,
            stream=False
        )
    try:
        response = retry_request(gpt_call)
        return response.choices[0].message.content
    except Exception as e:

        return f"An error occurred while communicating with GPT-4 {str(e)}"

