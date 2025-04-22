import os
import time
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

if not deepseek_api_key:
    raise ValueError("DeepSeek API key not found. Ensure your .env file is set up correctly.")

# Initialize DeepSeek API client
deepseek_client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

# File paths for datasets
COURSES_FILE = os.getenv("COURSES_FILE", "data/input_data/kaggle_filtered_courses.csv")
YOUTUBE_FILE = os.getenv("YOUTUBE_FILE", "data/input_data/youtube_videos.csv")

def load_courses():
    """Loads the course dataset and ensures required columns exist."""
    if not os.path.exists(COURSES_FILE):
        print(f"⚠️ Warning: Course file not found at {COURSES_FILE}. Using an empty dataset.")
        return pd.DataFrame(columns=["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"])

    df = pd.read_csv(COURSES_FILE)

    # Ensure required columns exist
    required_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"⚠️ Warning: Missing columns in courses dataset: {missing_columns}. Using an empty dataset.")
        return pd.DataFrame(columns=required_columns)

    return df

def load_youtube_videos():
    """Loads YouTube videos dataset and assigns categories dynamically if missing."""
    if not os.path.exists(YOUTUBE_FILE):
        print(f"⚠️ Warning: Video file not found at {YOUTUBE_FILE}. Using an empty dataset.")
        return pd.DataFrame(columns=["Title", "Channel", "Category", "URL"])

    df = pd.read_csv(YOUTUBE_FILE)

    # ✅ Rename alternative column names (if needed)
    column_mapping = {
        "title": "Title",
        "url": "URL",
        "channel": "Channel",
        "description": "Description"  # Useful for categorization
    }
    df.rename(columns=column_mapping, inplace=True)

    # ✅ Assign categories dynamically if "Category" is missing
    if "Category" not in df.columns:
        print("⚠️ 'Category' column missing. Assigning categories based on keywords.")
        def infer_category(title):
            title = str(title).lower()

            if any(word in title for word in ["python", "java", "programming", "coding", "software"]):
                return "Programming"
            elif any(word in title for word in ["finance", "economics", "stock", "investment"]):
                return "Finance"
            elif any(word in title for word in ["ai", "machine learning", "deep learning", "data science"]):
                return "Artificial Intelligence"
            elif any(word in title for word in ["math", "algebra", "calculus", "statistics"]):
                return "Mathematics"
            else:
                return "General"

        df["Category"] = df["Title"].apply(infer_category)

    # ✅ Ensure required columns exist
    required_columns = ["Title", "Channel", "Category", "URL"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"⚠️ Warning: Missing columns in YouTube dataset: {missing_columns}. Using an empty dataset.")
        return pd.DataFrame(columns=required_columns)

    return df

# Load datasets
courses = load_courses()
youtube_videos = load_youtube_videos()

def summarize_text(text, max_words=20):
    """Returns a shortened version of the text with max_words."""
    words = text.split()
    return " ".join(words[:max_words]) + "..." if len(words) > max_words else text

# Retry function / logic
def retry_request(func, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                return f"An error occurred after {max_retries} retries: {str(e)}"

def chat_with_bot(user_input, difficulty, category, chat_history):
    """
    Conversational chatbot using DeepSeek API that recommends both courses and YouTube videos.
    """
    # Ensure valid input
    if not user_input.strip():
        return "Please enter a valid question."

    # ✅ Initialize past_messages properly
    past_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]

    # ✅ Append current user message
    past_messages.append({"role": "user", "content": user_input})

    # Filter courses dataset
    if "Difficulty Level" in courses.columns and "Category" in courses.columns:
        filtered_courses = courses[
            (courses["Difficulty Level"].str.lower() == difficulty.lower()) & 
            (courses["Category"].str.lower() == category.lower())
        ]
    else:
        filtered_courses = pd.DataFrame(columns=["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"])

    # Filter YouTube videos dataset
    if "Category" in youtube_videos.columns:
        filtered_videos = youtube_videos[youtube_videos["Category"].str.lower() == category.lower()]
    else:
        filtered_videos = pd.DataFrame(columns=["Title", "Channel", "Category", "URL"])

    # ✅ If no exact course match is found, suggest courses from ANY category at the same difficulty level
    if filtered_courses.empty and "Difficulty Level" in courses.columns:
        filtered_courses = courses[courses["Difficulty Level"].str.lower() == difficulty.lower()].head(5)

    # ✅ If no YouTube videos are found, return an empty DataFrame
    if filtered_videos.empty:
        filtered_videos = pd.DataFrame(columns=["Title", "Channel", "Category", "URL"])

    # Select only relevant columns
    valid_course_columns = ["Name", "University", "Difficulty Level", "Link", "About", "Course Description", "Category"]
    valid_video_columns = ["Title", "Channel", "Category", "URL"]

    # Summarize descriptions to save tokens
    if "Course Description" in filtered_courses.columns:
        filtered_courses = filtered_courses.copy()
        filtered_courses["Course Description"] = filtered_courses["Course Description"].astype(str).apply(lambda x: summarize_text(x, max_words=20))

    # Select top recommendations (limit to 5 each to reduce token usage)
    filtered_courses = filtered_courses[valid_course_columns].head(5)
    filtered_videos = filtered_videos[valid_video_columns].head(5)

    # Format recommended courses
    course_list = "\n".join([
        f"**{row['Name']}** - {row['University']} ({row['Difficulty Level']})\n[Course Link]({row['Link']})"
        for _, row in filtered_courses.iterrows()
    ])

    # Format recommended YouTube videos
    video_list = "\n".join([
        f"**{row['Title']}** - {row['Channel']}\n[Watch Here]({row['URL']})"
        for _, row in filtered_videos.iterrows()
    ])

    # Construct prompt with both courses and YouTube videos
    prompt = f"""
    You are an AI assistant helping users find the best educational resources.

    User's selected filters:
    - Difficulty Level: {difficulty}
    - Category: {category}

    Recommended Courses:
    {course_list if not filtered_courses.empty else "No matching courses found."}

    Recommended YouTube Videos:
    {video_list if not filtered_videos.empty else "No matching videos found."}

    Keep the conversation natural and helpful.
    """

    # ✅ Append the system prompt to past messages
    past_messages.append({"role": "system", "content": prompt})

    # Query DeepSeek API with exception handling
#    try:
#        response = deepseek_client.chat.completions.create(
#            model="deepseek-chat",
#            messages=past_messages,
#            stream=False
#        )

#        return response.choices[0].message.content

#    except Exception as e:
#        return f"An error occurred while communicating with DeepSeek: {str(e)}"

    def send_chat_request():
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=past_messages,
            stream=False
        )
        return response.choices[0].message.content

    return retry_request(send_chat_request)

