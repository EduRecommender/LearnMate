import sys
import os
import pandas as pd

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set pandas display options to show full tables
pd.set_option('display.max_columns', None)  # Show all columns
pd.set_option('display.width', 1000)        # Wide display
pd.set_option('display.max_colwidth', 200)  # Show more text in each column
pd.set_option('display.expand_frame_repr', False)  # Don't wrap to multiple lines

from recommendation.models.team_models.Isma.CourseRecommender042025 import HybridRecommender

# Initialize the recommender
recommender = HybridRecommender(similarity_method="ensemble")
print("Loading data...")
recommender.load_data()
print("Training model...")
recommender.train()
recommender.load_test_data()

# Get user input for recommendations
user_input = input("What do you want to learn?\n")
print()

# Optional: Ask for difficulty level preference
difficulty_input = input("Preferred difficulty level (Beginner/Intermediate/Advanced) or press Enter to skip: ")
difficulty_level = None if difficulty_input.strip() == "" else difficulty_input

# Generate recommendations
recommendations = recommender.predict(user_input, difficulty_level=difficulty_level)

# Evaluate the model
print("\nEvaluating model...")
evaluation_results = recommender.evaluate()
print("Evaluation Results:", evaluation_results)