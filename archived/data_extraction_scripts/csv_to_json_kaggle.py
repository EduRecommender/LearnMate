import os
import pandas as pd
import json

# Load dataset
COURSES_FILE = os.getenv("COURSES_FILE", "data/input_data/kaggle_filtered_courses.csv")

if not os.path.exists(COURSES_FILE):
    raise FileNotFoundError(f"Course file not found at: {COURSES_FILE}")

courses = pd.read_csv(COURSES_FILE)

# Convert dataset into fine-tuning format
training_data = []
for _, row in courses.iterrows():
    course_info = f"Course: {row['Name']} | University: {row['University']} | Difficulty: {row['Difficulty Level']} | Category: {row['Category']} | Link: {row['Link']}"

    training_data.append({
        "messages": [
            {"role": "system", "content": "You are an expert AI course recommendation assistant."},
            {"role": "user", "content": f"I want to learn about {row['Category']} at a {row['Difficulty Level']} level."},
            {"role": "assistant", "content": f"I recommend '{row['Name']}' from {row['University']}. More details: {row['Link']}"}
        ]
    })

# Save in JSONL format
jsonl_file = "training_data.jsonl"
with open(jsonl_file, "w") as f:
    for entry in training_data:
        json.dump(entry, f)
        f.write("\n")

print(f"Training data saved to {jsonl_file}")
