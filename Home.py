import streamlit as st
from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine

st.title("LearnMate Course Recommender System")

user_input = st.text_input("Enter your learning interest:", "I want to learn programming basics")

if st.button("Get Recommendations"):
    recommender = CourseRecommenderCosine()
    recommender.load_data()
    recommender.train()
    recommender.load_test_data()
    
    recommendations = recommender.predict(user_input)
    st.write("Recommended Courses:")
    st.dataframe(recommendations[['Name', 'University', 'Link']])
    
    # evaluation_results = recommender.evaluate()
    # st.write("Evaluation Results:", evaluation_zresults)