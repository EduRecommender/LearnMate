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
api_key = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_KEY = api_key

# Function to fetch videos from a YouTube channel using the YouTube Data API
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

# Function to check if a video is educational based on keywords
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

# Function to search YouTube videos using yt-dlp and return video details
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
            video_id = item.get("id")  # Extract video ID directly
            video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else item.get("url")

            video_data.append({
                "Title": item.get("title"),
                "Channel": item.get("uploader"),
                "Published Date": item.get("upload_date"),
                "Video URL": video_url,
                "video_id": video_id,
            })
    
    return video_data

# Function to save the video data to a CSV file
def save_to_csv(video_data, filename="youtube_videos.csv", path="../input_data/youtube_videos.csv"):
    df = pd.DataFrame(video_data)
    if os.path.isfile(path):
        df.to_csv(path, mode='a', header=False, index=False)
    else:
        df.to_csv(path, index=False)
    
    print(f"Data saved to {path}")

# Function to generate queries based on category keywords
def generate_queries(topics):
    queries = []
    for topic in topics:
        queries.append(f"{topic} tutorial")
        queries.append(f"{topic} guide")
        queries.append(f"{topic} how to")
    return queries

def main():
    all_videos = []

    category_keywords = ["business", "finance", "entrepreneur", "management", "accounting", "economics", "project management", "leadership", "strategy", "investment", 
                     "math", "mathematics", "statistics", "calculus", "algebra", "geometry", "probability", "trigonometry", "differential equations", "linear algebra", "discrete math", "topology", "combinatorics", "set theory", "real analysis", "complex analysis", "abstract algebra", "number theory", "graph theory", "logic", "game theory", "measure theory", "mathematical modeling", "stochastic processes", "numerical analysis", "multivariable calculus", "optimization", "vector calculus", "applied mathematics",
                     "computer science", "programming", "software", "coding", "java", "python", "C++", "AI", "artificial intelligence", "web development", "cs50", "technology", "algorithms", "autonomous systems", "systems programming", "cybersecurity", "blockchain", "cloud computing", "machine learning", "deep learning", "neural networks", "operating systems", "computational thinking", "networking", "computer architecture", "embedded systems", "database systems", "theory of computation",
                     "data analytics", "big data", "SQL", "machine learning", "deep learning", "data science", "excel", "r programming", "data", "predictive modeling", "business intelligence", "data mining", "data visualization", "data engineering", "time series analysis", "ETL", "hadoop", "spark",
                     "design", "graphic design", "ux", "ui", "web design", "visual", "animation", "illustration", "motion graphics", "product design", "typography", "brand design", "3D modeling", "video editing", "industrial design", "color theory", "interaction design",
                     "marketing", "advertising", "seo", "branding", "digital marketing", "social media", "consumer behavior", "market research", "public relations", "copywriting", "growth hacking", "email marketing", "content marketing", "performance marketing"]

    # Fetch videos from trusted channels
    for channel_id in trusted_channels:
        print(f"Fetching videos from channel: {channel_id}")
        videos = fetch_videos_from_channel(channel_id, max_results=10)

        for video in videos:
            if not is_educational(video["title"] + " " + video["description"]):
                continue  # Skip non-educational videos

            transcript = get_transcript(video["video_id"])
            video["transcript"] = transcript
            all_videos.append(video)

    # Fetch videos based on category keywords
    for query in generate_queries(category_keywords):
        print(f"Fetching YouTube videos for query: {query}")
        video_results = search_youtube_videos(query, max_results=20)

        for video in video_results:
            if not is_educational(video["Title"]):
                continue  # Skip non-educational videos

            video_id = video.get("video_id")
            if not video_id:
                print(f"Skipping video without valid ID: {video}")
                continue  # Skip if we can't extract the video ID

            transcript = get_transcript(video_id)
            video["transcript"] = transcript
            all_videos.append(video)

    if all_videos:
        save_to_csv(all_videos)
        print(f"Scraped {len(all_videos)} videos and saved to CSV.")
    else:
        print("No videos found.")

if __name__ == "__main__":
    main()
