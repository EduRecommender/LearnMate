import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")  # Using DeepSeek API key from .env

if not deepseek_api_key:
    raise ValueError("DeepSeek API key not found. Ensure your .env file is set up correctly.")

# Initialize DeepSeek API client
deepseek_client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

# Load course dataset
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

def chat_with_bot(user_input, difficulty, category, chat_history):
    """
    Conversational chatbot that remembers past interactions using DeepSeek API.
    """
    # Ensure valid inputs
    if not user_input.strip():
        return "Please enter a valid question."

    # Filter dataset based on difficulty and category
    filtered_courses = courses[
        (courses["Difficulty Level"].str.lower() == difficulty.lower()) & 
        (courses["Category"].str.lower() == category.lower())
    ]

    if filtered_courses.empty:
        return f"Sorry, no courses found for Difficulty Level: {difficulty} and Category: {category}."

    # Select only the most relevant columns
    valid_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]

    # Summarize descriptions to save tokens
    filtered_courses = filtered_courses.copy()
    filtered_courses.loc[:, "Course Description"] = filtered_courses["Course Description"].astype(str).apply(lambda x: summarize_text(x, max_words=20))

    # Select top 5 courses to reduce token usage
    filtered_courses = filtered_courses[valid_columns].head(5)

    # Format chat history for context
    past_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    past_messages.append({"role": "user", "content": user_input})

    # Append recommended courses to the prompt
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

    # Query DeepSeek API
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=past_messages,
            stream=False
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"An error occurred while communicating with DeepSeek: {str(e)}"
