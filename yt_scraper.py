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

# Path to save CSV
CSV_PATH = "input_data/youtube_videos.csv"

# Function to fetch videos from a YouTube channel
def fetch_videos_from_channel(channel_id, max_results=20):
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

# Function to fetch video statistics
def fetch_video_statistics(video_id):
    """Fetches video statistics like views, likes, and comments."""
    url = f"https://www.googleapis.com/youtube/v3/videos?key={YOUTUBE_API_KEY}&id={video_id}&part=statistics"
    
    response = requests.get(url)
    data = response.json()

    if "items" not in data or not data["items"]:
        print(f"Error fetching statistics for video {video_id}: {data}")
        return {}

    stats = data["items"][0]["statistics"]
    return {
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0))
    }

# Function to check if a video is educational
def is_educational(title, description):
    """Filters videos using NLP-based keyword matching."""
    keywords = ["tutorial", "lecture", "lesson", "course", "exam prep", "crash course", "learning", "workshop", "masterclass"]
    text = f"{title} {description}".lower()
    return any(re.search(rf"\b{keyword}\b", text) for keyword in keywords)

# Function to get the transcript of a YouTube video
def get_transcript(video_id):
    """Fetches the transcript of a YouTube video if available."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return ""

# Function to calculate engagement score
def calculate_engagement(views, likes, comments):
    """Computes an engagement score based on views, likes, and comments."""
    views, likes, comments = int(views), int(likes), int(comments)
    return round((likes * 2 + comments * 3) / (views + 1), 5)  # Avoid division by zero

# Function to search YouTube videos
def search_youtube_videos(query, max_results=50):
    """Searches for videos on YouTube matching a query."""
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
def save_to_csv(video_data, path=CSV_PATH):
    """Saves the scraped video data to a CSV file."""
    df = pd.DataFrame(video_data)
    if os.path.isfile(path):
        df.to_csv(path, mode='a', header=False, index=False)
    else:
        df.to_csv(path, index=False)

    print(f"✅ Data saved to {path}")

# Function to generate search queries
def generate_queries(topics):
    """Generates search queries for YouTube."""
    queries = []
    for topic in topics:
        queries.append(f"{topic} tutorial")
        queries.append(f"{topic} guide")
        queries.append(f"{topic} how to")
    return queries

# Main function to scrape YouTube videos
def main():
    all_videos = []

    # ✅ Fetch videos from trusted channels
    for channel_id in trusted_channels:
        print(f"📡 Fetching videos from channel: {channel_id}")
        videos = fetch_videos_from_channel(channel_id, max_results=15)

        for video in videos:
            if not is_educational(video["title"], video["description"]):
                continue  # Skip non-educational videos

            video_stats = fetch_video_statistics(video["video_id"])
            transcript = get_transcript(video["video_id"])

            video.update(video_stats)
            video["engagement_score"] = calculate_engagement(video["view_count"], video["like_count"], video["comment_count"])
            video["transcript"] = transcript

            all_videos.append(video)

    # ✅ Fetch videos using search queries
    category_keywords = ["business", "finance", "entrepreneur", "management", "accounting", "economics", "project management", "leadership", "strategy", "investment", 
                     "math", "mathematics", "statistics", "calculus", "algebra", "geometry", "probability", "trigonometry", "differential equations", "linear algebra", "discrete math", "topology", "combinatorics", "set theory", "real analysis", "complex analysis", "abstract algebra", "number theory", "graph theory", "logic", "game theory", "measure theory", "mathematical modeling", "stochastic processes", "numerical analysis", "multivariable calculus", "optimization", "vector calculus", "applied mathematics",
                     "computer science", "programming", "software", "coding", "java", "python", "C++", "AI", "artificial intelligence", "web development", "cs50", "technology", "algorithms", "autonomous systems", "systems programming", "cybersecurity", "blockchain", "cloud computing", "machine learning", "deep learning", "neural networks", "operating systems", "computational thinking", "networking", "computer architecture", "embedded systems", "database systems", "theory of computation",
                     "data analytics", "big data", "SQL", "machine learning", "deep learning", "data science", "excel", "r programming", "data", "predictive modeling", "business intelligence", "data mining", "data visualization", "data engineering", "time series analysis", "ETL", "hadoop", "spark",
                     "design", "graphic design", "ux", "ui", "web design", "visual", "animation", "illustration", "motion graphics", "product design", "typography", "brand design", "3D modeling", "video editing", "industrial design", "color theory", "interaction design",
                     "marketing", "advertising", "seo", "branding", "digital marketing", "social media", "consumer behavior", "market research", "public relations", "copywriting", "growth hacking", "email marketing", "content marketing", "performance marketing"]
    for query in generate_queries(category_keywords):
        print(f"🔍 Fetching YouTube videos for query: {query}")
        video_results = search_youtube_videos(query, max_results=30)
        
        for video in video_results:
            if not is_educational(video["title"], ""):
                continue  # Skip non-educational videos

            video_stats = fetch_video_statistics(video["video_id"])
            transcript = get_transcript(video["video_id"])

            video.update(video_stats)
            video["engagement_score"] = calculate_engagement(video["view_count"], video["like_count"], video["comment_count"])
            video["transcript"] = transcript

            all_videos.append(video)

    # ✅ Save results to CSV
    if all_videos:
        save_to_csv(all_videos)
        print(f"📊 Scraped {len(all_videos)} videos and saved to CSV.")
    else:
        print("❌ No videos found.")

if __name__ == "__main__":
    main()
