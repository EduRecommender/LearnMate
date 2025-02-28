import os
import streamlit as st
import pandas as pd
from chatbot.chatbot import chat_with_bot
from recommendations.CourseRecommender import CourseRecommender2 as RecommenderModel

# Load dataset to get available categories and difficulty levels
@st.cache_data
def load_courses():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    COURSES_FILE = os.path.join(ROOT_DIR, "input_data", "kaggle_filtered_courses.csv")
    return pd.read_csv(COURSES_FILE)

courses = load_courses()

st.title("LearnMate Course Recommender System")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# User selects recommendation method
option = st.radio(
    "Choose Recommendation Method:",
    ("Conversational AI Chatbot (GPT-4)", "Cosine Similarity Model"),
)

if option == "Conversational AI Chatbot (GPT-4)":
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

        # Get chatbot response
        bot_response = chat_with_bot(user_input, difficulty, category, st.session_state.messages)

        # Add bot response to chat history
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

        # Display bot response
        with st.chat_message("assistant"):
            st.markdown(bot_response)

else:
    # Standard Cosine Similarity Model
    user_input = st.text_input("Enter your learning interest:", "I want to learn programming basics")

    if st.button("Get Recommendations"):
        recommender = RecommenderModel()

        recommender.load_data()
        recommender.train()
        recommender.load_test_data()
        recommendations = recommender.predict(user_input)

        st.write("### Recommended Courses (Cosine Similarity):")
        st.dataframe(
            recommendations[['Name', 'University', 'Link', 'Category']],
            use_container_width=True
        )
