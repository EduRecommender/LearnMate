import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OpenAI API key not found. Ensure your .env file is set up correctly.")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Dynamically locate the CSV file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
COURSES_FILE = os.path.join(BASE_DIR, "input_data", "kaggle_filtered_courses.csv")  

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
    Conversational chatbot that remembers past interactions.
    """
    # Filter dataset based on difficulty and category
    filtered_courses = courses[(courses["Difficulty Level"] == difficulty) & (courses["Category"] == category)]

    if filtered_courses.empty:
        return f"No courses found for Difficulty Level: {difficulty} and Category: {category}."

    # Select only the most relevant columns
    valid_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]

    # Summarize descriptions to save tokens
    filtered_courses = filtered_courses.copy()
    filtered_courses.loc[:, "Course Description"] = filtered_courses["Course Description"].astype(str).apply(lambda x: summarize_text(x, max_words=20))

    # Select top 5 courses to reduce token usage
    filtered_courses = filtered_courses[valid_columns].head(5)

    # Format past messages for context
    past_messages = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])

    prompt = f"""
    You are an AI assistant helping users find the best courses.

    User's selected filters:
    - Difficulty Level: {difficulty}
    - Category: {category}

    Previous conversation:
    {past_messages}

    Current User Message:
    {user_input}

    Relevant Courses:
    {filtered_courses.to_string(index=False)}

    Respond as a helpful chatbot, keeping the conversation natural.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI that recommends courses only from the given database."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
