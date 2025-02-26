import requests
import csv
import re
from youtube_transcript_api import YouTubeTranscriptApi
from trusted_channels import trusted_channels
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_KEY = api_key


def fetch_videos_from_channel(channel_id, max_results=10):
    """Fetches latest videos from a YouTube channel using the YouTube Data API."""
    url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults={max_results}"
    
    response = requests.get(url)
    data = response.json()

    if "items" not in data:
        print(f"Error fetching videos from channel {channel_id}: {data}")
        return []

    videos = []
    for item in data["items"]:
        if item["id"]["kind"] != "youtube#video":
            continue  # Skip non-video results (like playlists or channels)

        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        videos.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": snippet.get("channelTitle", ""),
            "channel_id": channel_id,
            "description": snippet.get("description", ""),
            "upload_date": snippet.get("publishedAt", ""),
        })

    return videos

def is_educational(text):
    """Filters videos using NLP-based keyword matching."""
    keywords = ["tutorial", "lecture", "lesson", "course", "exam prep", "crash course", "learning"]
    return any(re.search(rf"\b{keyword}\b", text.lower()) for keyword in keywords)

def get_transcript(video_id):
    """Fetches the transcript of a YouTube video if available."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except:
        return ""

def calculate_engagement(views, likes, comments):
    """Computes an engagement score based on views, likes, and comments."""
    return (likes * 2 + comments * 3) / (views + 1)  # Avoid division by zero

def save_to_csv(data, filename="youtube_videos.csv"):
    """Saves the scraped video data to a CSV file."""
    keys = data[0].keys() if data else []
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    all_videos = []

    for channel_id in trusted_channels:
        print(f"Fetching videos from channel: {channel_id}")
        videos = fetch_videos_from_channel(channel_id, max_results=10)

        for video in videos:
            if not is_educational(video["title"] + " " + video["description"]):
                continue  # Skip non-educational videos

            transcript = get_transcript(video["video_id"])
            video["transcript"] = transcript
            all_videos.append(video)

    if all_videos:
        save_to_csv(all_videos)
        print(f"Scraped {len(all_videos)} videos from trusted channels and saved to CSV.")
    else:
        print("No videos found.")
