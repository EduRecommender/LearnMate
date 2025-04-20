#!/usr/bin/env python3
"""
Example usage script for the LearnMate CrewAI integration.
This script demonstrates how to use the CrewAI agents to generate study plans
with different data sources.
"""

import os
import sys
import json
from datetime import datetime

# Example usage for creating a mock session file for testing
def create_mock_session_data():
    """Create mock session data for testing"""
    # Mock user and session IDs
    user_id = "test_user"
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create a sample syllabus
    syllabus = {
        "course_name": "Introduction to Machine Learning",
        "session_content": [
            "Supervised Learning Basics",
            "Linear Regression",
            "Logistic Regression",
            "Decision Trees and Random Forests",
            "Support Vector Machines",
            "Neural Networks Fundamentals",
            "Convolutional Neural Networks",
            "Recurrent Neural Networks",
            "Unsupervised Learning",
            "Clustering Algorithms",
            "Dimensionality Reduction",
            "Reinforcement Learning",
            "Model Evaluation and Validation"
        ]
    }
    
    # Create a data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Create a sample session file
    sessions_file = "data/study_sessions.json"
    
    # Load existing sessions or create a new dictionary
    if os.path.exists(sessions_file):
        with open(sessions_file, 'r') as f:
            try:
                sessions = json.load(f)
            except json.JSONDecodeError:
                sessions = {}
    else:
        sessions = {}
    
    # Add the user if not exists
    if user_id not in sessions:
        sessions[user_id] = {}
    
    # Create a new session
    sessions[user_id][session_id] = {
        "name": "ML Study Session",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "preferences": {
            "subject": "Machine Learning",
            "exam_type": "Final Exam",
            "days_until_exam": "14",
            "hours_per_day": "3",
            "specific_challenges": "complex mathematical concepts"
        },
        "syllabus": syllabus,
        "materials": [],
        "notes": [],
        "progress": 0
    }
    
    # Save the updated sessions
    with open(sessions_file, 'w') as f:
        json.dump(sessions, f, indent=4)
    
    # Create a sample user preferences file
    prefs_file = "user_preferences.json"
    
    # Load existing preferences or create a new dictionary
    if os.path.exists(prefs_file):
        with open(prefs_file, 'r') as f:
            try:
                preferences = json.load(f)
            except json.JSONDecodeError:
                preferences = {}
    else:
        preferences = {}
    
    # Add preferences for the test user
    preferences[user_id] = {
        "name": "Test User",
        "level": "undergraduate",
        "grade_level": "Junior",
        "major": "Computer Science",
        "subject_interest": ["Machine Learning", "Artificial Intelligence", "Data Science"],
        "learning_styles": ["visual", "hands-on"],
        "preferred_study_methods": ["practice problems", "video lectures", "coding exercises"],
        "preferred_difficulty": "advanced",
        "time_available_per_week": "20 hours",
        "preferred_schedule": "evenings",
        "additional_notes": "Interested in ML applications to computer vision",
        "has_set_preferences": True
    }
    
    # Save the updated preferences
    with open(prefs_file, 'w') as f:
        json.dump(preferences, f, indent=4)
    
    print(f"Created mock user: {user_id}")
    print(f"Created mock session: {session_id}")
    print(f"Session data saved to: {sessions_file}")
    print(f"User preferences saved to: {prefs_file}")
    
    return user_id, session_id

def main():
    # Check if we should create mock data
    if "--create-mock" in sys.argv:
        user_id, session_id = create_mock_session_data()
        print("\nMock data created! You can now run with:")
        print(f"python main.py --user_id {user_id} --session_id {session_id}")
        return
    
    # Example command to run with backend data
    if "--run-example" in sys.argv:
        print("Running CrewAI with mock data...")
        # Get the most recent mock user and session
        if os.path.exists("data/study_sessions.json"):
            with open("data/study_sessions.json", 'r') as f:
                sessions = json.load(f)
                if sessions:
                    user_id = list(sessions.keys())[0]
                    session_id = list(sessions[user_id].keys())[0]
                    
                    # Run the main script with the mock data
                    os.system(f"python main.py --user_id {user_id} --session_id {session_id}")
                    return
        
        print("No mock data found. Please run with --create-mock first.")
        return
    
    # Display help information
    print("LearnMate CrewAI Example Usage")
    print("------------------------------")
    print("Options:")
    print("  --create-mock : Create mock user and session data for testing")
    print("  --run-example : Run the main script with the most recent mock data")
    print("\nExample commands:")
    print("  python example_usage.py --create-mock")
    print("  python example_usage.py --run-example")
    print("  python main.py --user_id test_user --session_id <session_id>")
    print("  python main.py --user_id test_user --session_id <session_id> --interactive")

if __name__ == "__main__":
    main() 