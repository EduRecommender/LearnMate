from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine
import pandas as pd

recommender = CourseRecommenderCosine()
recommender.load_data()
recommender.train()
recommender.load_test_data()

user_input = input("What do you want to learn?\n")
print()
recommendations = recommender.predict(user_input)
print("Recommended Courses:", recommendations[['Name', 'University', 'Link']])

evaluation_results = recommender.evaluate()
print("Evaluation Results:", evaluation_results)