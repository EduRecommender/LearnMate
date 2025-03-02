import streamlit as st
import pandas as pd
from chatbot_gpt import chat_with_bot as chat_with_gpt
from chatbot_deepseek import chat_with_bot as chat_with_deepseek
from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine

# Load dataset for available categories and difficulty levels
@st.cache_data
def load_courses():
    return pd.read_csv("input_data/kaggle_filtered_courses.csv")

courses = load_courses()

st.title("LearnMate Course Recommender System")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# User selects recommendation method
option = st.radio(
    "Choose Recommendation Method:",
    ("Conversational AI Chatbot", "Cosine Similarity Model"),
)

# If AI Chatbot is selected, allow users to choose between DeepSeek and GPT-4
if option == "Conversational AI Chatbot":
    chatbot_option = st.radio(
        "Choose AI Model:",
        ("DeepSeek API", "GPT-4"),
    )

    # Ensure dropdowns only contain unique, sorted values from the dataset
    difficulty_levels = sorted(courses["Difficulty Level"].dropna().unique().tolist())
    categories = sorted(courses["Category"].dropna().unique().tolist())

    difficulty = st.selectbox("Select Course Difficulty Level (Required):", difficulty_levels)
    category = st.selectbox("Select Course Category (Required):", categories)

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User inputs a new message
    user_input = st.chat_input("Ask me anything about courses...")

    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Use the selected chatbot
        if chatbot_option == "GPT-4":
            bot_response = chat_with_gpt(user_input, difficulty, category, st.session_state.messages)
        else:
            bot_response = chat_with_deepseek(user_input, difficulty, category, st.session_state.messages)

        # Add bot response to chat history
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

        # Display bot response
        with st.chat_message("assistant"):
            st.markdown(bot_response)

else:
    # Standard Cosine Similarity Model
    user_input = st.text_input("Enter your learning interest:", "I want to learn programming basics")

    if st.button("Get Recommendations"):
        recommender = CourseRecommenderCosine()
        recommender.load_data()
        recommender.train()
        recommender.load_test_data()
        recommendations = recommender.predict(user_input)

        st.write("### Recommended Courses (Cosine Similarity):")
        st.dataframe(
            recommendations[['Name', 'University', 'Link', 'Category']],
            use_container_width=True
        )
