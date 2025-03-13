import streamlit as st
from syllabus_processor import process_uploaded_syllabus
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

# Initialize session state for chat history & syllabus
if "messages" not in st.session_state:
    st.session_state.messages = []

if "syllabus_data" not in st.session_state:
    st.session_state.syllabus_data = None

# File uploader (PDF syllabus)
uploaded_file = st.file_uploader("Upload a Syllabus PDF", type=["pdf"])

if uploaded_file is not None:
    syllabus_data = process_uploaded_syllabus(uploaded_file)
    if syllabus_data:
        st.session_state.syllabus_data = syllabus_data
        st.write("✅ PDF Uploaded Successfully!")
        st.write(f"**Course Name:** {syllabus_data['course_name']}")
        st.write("**Program Content:**")
        st.text_area("Extracted Topics", "\n".join(syllabus_data["session_content"]), height=200)

# User selects recommendation method
option = st.radio(
    "Choose Recommendation Method:",
    ("Conversational AI Chatbot", "Cosine Similarity Model"),
)

# Conversational AI Chatbot
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
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Ensure syllabus content is available
        syllabus_content = "\n".join(st.session_state.syllabus_data["session_content"]) if st.session_state.syllabus_data else ""
        enriched_prompt = f"{user_input}\n\nCourse Syllabus:\n{syllabus_content}"

        if chatbot_option == "GPT-4":
            bot_response = chat_with_gpt(enriched_prompt, difficulty, category, st.session_state.messages)
        else:
            bot_response = chat_with_deepseek(enriched_prompt, difficulty, category, st.session_state.messages)

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

        # If syllabus exists, add it to recommendation query
        syllabus_content = "\n".join(st.session_state.syllabus_data["session_content"]) if st.session_state.syllabus_data else ""
        enriched_query = f"{user_input}\n\nCourse Topics: {syllabus_content}"

        recommendations = recommender.predict(enriched_query)

        st.write("### Recommended Courses (Cosine Similarity):")
        st.dataframe(
            recommendations[['Name', 'University', 'Link', 'Category']],
            use_container_width=True
        )
