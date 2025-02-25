import streamlit as st
import pandas as pd
from chatbot import get_course_recommendations
from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine

# Load dataset to get available categories and difficulty levels
@st.cache_data
def load_courses():
    return pd.read_csv("input_data/kaggle_filtered_courses.csv")

courses = load_courses()

st.title("LearnMate Course Recommender System")

# User input for learning interest
user_input = st.text_input("Enter your learning interest:", "I want to learn programming basics")

# Choose recommendation method
option = st.radio(
    "Choose Recommendation Method:",
    ("AI Chatbot (GPT-4) from Database", "Cosine Similarity Model"),
)

# If AI Chatbot is selected, require Difficulty Level & Category selection
if option == "AI Chatbot (GPT-4) from Database":
    # Ensure dropdowns only contain unique, sorted values from the dataset
    difficulty_levels = sorted(courses["Difficulty Level"].dropna().unique().tolist())
    categories = sorted(courses["Category"].dropna().unique().tolist())

    difficulty = st.selectbox("Select Course Difficulty Level (Required):", difficulty_levels)
    category = st.selectbox("Select Course Category (Required):", categories)

if st.button("Get Recommendations"):
    if option == "Cosine Similarity Model":
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

    else:
        st.write("### Recommended Courses (AI Chatbot from Database):")
        recommendations = get_course_recommendations(user_input, difficulty, category)
        st.write(recommendations)
