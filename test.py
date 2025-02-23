from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine
import pandas as pd

# Initialize and train the recommender
recommender = CourseRecommenderCosine()
recommender.load_data()  # The model loads its own data
recommender.train()
recommender.load_test_data()

# Get recommendations
user_input = "I want to learn programming basics"
recommendations = recommender.predict(user_input)
print("Recommended Courses:", recommendations[['Name', 'University', 'Link']])

# Evaluate the model
evaluation_results = recommender.evaluate()
print("Evaluation Results:", evaluation_results)