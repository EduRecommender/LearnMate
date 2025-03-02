import yt_dlp
import os
import requests
import csv
import re
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from trusted_channels import trusted_channels
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Function to fetch videos from a YouTube channel
def fetch_videos_from_channel(channel_id, max_results=10):
    url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults={max_results}"
    
    response = requests.get(url)
    data = response.json()

    if "items" not in data:
        print(f"Error fetching videos from channel {channel_id}: {data}")
        return []

    videos = []
    for item in data["items"]:
        if item["id"]["kind"] != "youtube#video":
            continue  # Skip non-video results

        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        videos.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": snippet.get("channelTitle", ""),
            "upload_date": snippet.get("publishedAt", ""),
        })
    return videos

# Function to fetch video statistics
def fetch_video_statistics(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?key={YOUTUBE_API_KEY}&id={video_id}&part=statistics"
    
    response = requests.get(url)
    data = response.json()

    if "items" not in data or not data["items"]:
        print(f"Error fetching statistics for video {video_id}: {data}")
        return {}

    stats = data["items"][0]["statistics"]
    return {
        "view_count": stats.get("viewCount", 0),
        "like_count": stats.get("likeCount", 0),
        "dislike_count": stats.get("dislikeCount", 0)
    }

# Function to check if a video is educational
def is_educational(text):
    keywords = ["tutorial", "lecture", "lesson", "course", "exam prep", "crash course", "learning"]
    return any(re.search(rf"\b{keyword}\b", text.lower()) for keyword in keywords)

# Function to get the transcript of a YouTube video
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return ""

# Function to search YouTube videos
def search_youtube_videos(query, max_results=50):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_url = f"ytsearch{max_results}:{query}"
        info = ydl.extract_info(search_url, download=False)
    
    video_data = []
    if 'entries' in info:
        for item in info['entries']:
            video_id = item.get("id")
            video_data.append({
                "video_id": video_id,
                "title": item.get("title"),
                "channel": item.get("uploader"),
                "upload_date": item.get("upload_date"),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else item.get("url"),
            })
    
    return video_data

# Function to save video data to CSV
def save_to_csv(video_data, filename="youtube_videos.csv"):
    df = pd.DataFrame(video_data)
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

# Function to generate search queries
def generate_queries(topics):
    queries = []
    for topic in topics:
        queries.append(f"{topic} tutorial")
        queries.append(f"{topic} guide")
        queries.append(f"{topic} how to")
    return queries

# Main function
def main():
    all_videos = []

    # Fetch videos from trusted channels
    for channel_id in trusted_channels:
        print(f"Fetching videos from channel: {channel_id}")
        videos = fetch_videos_from_channel(channel_id, max_results=10)

        for video in videos:
            if not is_educational(video["title"]):
                continue

            video_stats = fetch_video_statistics(video["video_id"])
            transcript = get_transcript(video["video_id"])
            
            video.update(video_stats)
            video["transcript"] = transcript
            
            all_videos.append(video)

    # Fetch videos based on queries
    category_keywords = ["business", "finance", "entrepreneur", "math", "statistics", "computer science", "programming"]
    for query in generate_queries(category_keywords):
        print(f"Fetching YouTube videos for query: {query}")
        video_results = search_youtube_videos(query, max_results=20)
        
        for video in video_results:
            if not is_educational(video["title"]):
                continue
            
            video_stats = fetch_video_statistics(video["video_id"])
            transcript = get_transcript(video["video_id"])
            
            video.update(video_stats)
            video["transcript"] = transcript
            
            all_videos.append(video)

    if all_videos:
        save_to_csv(all_videos)
        print(f"Scraped {len(all_videos)} videos and saved to CSV.")
    else:
        print("No videos found.")

if __name__ == "__main__":
    main()
