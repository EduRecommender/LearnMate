from recommendation.models.team_models.Andres.CourseRecommender2 import CourseRecommender2
import pandas as pd

recommender = CourseRecommender2()
recommender.load_data()
recommender.train()
recommender.load_test_data()

user_input = input("What do you want to learn?\n")
print()
recommendations = recommender.predict(user_input)
#print("Recommended Courses:", recommendations[['Name', 'University', 'Link', 'Category']]) #moved to the model

evaluation_results = recommender.evaluate()
print("Evaluation Results:", evaluation_results)