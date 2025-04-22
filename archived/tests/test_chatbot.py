import pytest
import pandas as pd
import os
from chatbot_gpt import load_courses, summarize_text, chat_with_bot

# Override the dataset path for testing
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    os.environ["COURSES_FILE"] = os.path.join(os.path.dirname(__file__), "test_data", "test_courses.csv")

def test_load_courses():
    """Ensure courses load correctly from the mock dataset."""
    courses_df = load_courses()
    assert isinstance(courses_df, pd.DataFrame)
    assert not courses_df.empty

def summarize_text(text, max_words=20):
    """Summarizes text to a fixed number of words, appending '...' when truncated."""
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return " ".join(words)

def test_chat_with_bot():
    """Test chatbot responses with mocked data."""
    user_input = "I want to learn Python."
    difficulty = "Beginner"
    category = "Programming"
    chat_history = [{"role": "user", "content": "I want to learn data science."}]
    
    response = chat_with_bot(user_input, difficulty, category, chat_history)
    
    assert isinstance(response, str)
    assert "No courses found" not in response  # Assuming test dataset contains relevant courses

if __name__ == "__main__":
    pytest.main()
