import streamlit as st
from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine

st.title("LearnMate Course Recommender System")

# Inject CSS to make input and button bigger
st.markdown(
    """
    <style>
        div[data-testid="stTable"] td, th {
            font-size: 18px !important;
            padding: 12px !important;
        }
        div[data-testid="stTextInput"] input {
            font-size: 18px !important;
        }
        button {
            font-size: 18px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

user_input = st.text_input("Enter your learning interest:", "I want to learn programming basics")

if st.button("Get Recommendations"):
    recommender = CourseRecommenderCosine()
    recommender.load_data()
    recommender.train()
    recommender.load_test_data()
    
    recommendations = recommender.predict(user_input)
    
    st.write("### Recommended Courses:")

    # ✅ Full-width table + Larger text
    st.dataframe(
        recommendations[['Name', 'University', 'Link', 'Category']]
        .style.set_properties(**{
            'font-size': '18px',  # Increase text size
            'padding': '10px',  # Add spacing
        }),
        use_container_width=True  # Make table as wide as the screen
    )
    