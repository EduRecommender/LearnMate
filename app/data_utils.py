import os
import pandas as pd

def get_course_data():
    """Return the course dataset from a configurable path."""
    data_path = os.path.join("..", "input_data", "kaggle_filtered_courses.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Course file not found at: {data_path}")
    return pd.read_csv(data_path)