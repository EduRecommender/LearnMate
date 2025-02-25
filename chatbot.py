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

def get_course_recommendations(user_input, difficulty, category):
    """
    Uses OpenAI to suggest courses based on user-selected difficulty and category.
    """
    # Filter dataset based on difficulty and category
    filtered_courses = courses[(courses["Difficulty Level"] == difficulty) & (courses["Category"] == category)]

    if filtered_courses.empty:
        return f"No courses found for Difficulty Level: {difficulty} and Category: {category}."

    # Select only the most relevant columns
    valid_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]

    # Summarize descriptions to save tokens
    filtered_courses["Course Description"] = filtered_courses["Course Description"].astype(str).apply(lambda x: summarize_text(x, max_words=20))

    # Select top 5 courses to reduce token usage
    filtered_courses = filtered_courses[valid_columns].head(5)

    prompt = f"""
    Based on the user's interest: '{user_input}', recommend the most relevant courses from the database.

    Selected Filters:
    - Difficulty Level: {difficulty}
    - Category: {category}

    Courses:
    {filtered_courses.to_string(index=False)}

    Provide the recommendations in the following structured format:
    Course Name | University | Difficulty Level | Category | Course Link
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI that recommends courses only from the given database."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
