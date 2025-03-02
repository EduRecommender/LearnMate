import os
import pandas as pd
import json

# Load dataset
YOUTUBE_FILE = os.getenv("YOUTUBE_FILE", "input_data/youtube_videos.csv")

if not os.path.exists(YOUTUBE_FILE):
    raise FileNotFoundError(f"Video file not found at: {YOUTUBE_FILE}")

videos = pd.read_csv(YOUTUBE_FILE)

# Convert dataset into fine-tuning format
training_data = []
for _, row in videos.iterrows():
    video_info = f"Video: {row['Title']} | Channel: {row['Channel']} | Category: {row['Category']} | Link: {row['URL']}"

    training_data.append({
        "messages": [
            {"role": "system", "content": "You are an expert AI YouTube video recommendation assistant."},
            {"role": "user", "content": f"I want to watch videos about {row['Category']}."},
            {"role": "assistant", "content": f"I recommend '{row['Title']}' from {row['Channel']}. Watch here: {row['URL']}"}
        ]
    })

# Save in JSONL format
jsonl_file = "youtube_training_data.jsonl"
with open(jsonl_file, "w") as f:
    for entry in training_data:
        json.dump(entry, f)
        f.write("\n")

print(f"Training data saved to {jsonl_file}")
