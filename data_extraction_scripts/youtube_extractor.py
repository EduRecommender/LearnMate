import yt_dlp
import os
import pandas as pd

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
            video_data.append({
                "Title": item.get("title"),
                "Channel": item.get("uploader"),
                "Published Date": item.get("upload_date"),
                "Video URL": item.get("url"),
            })
    
    return video_data

# Function to save the video data to a CSV file
def save_to_csv(video_data, filename="youtube_videos.csv", path="../input_data/youtube_videos.csv"):
    
    # Convert video data to DataFrame
    df = pd.DataFrame(video_data)
    
    # Check if the file exists
    if os.path.isfile(path):
        # If file exists, append without writing the header
        df.to_csv(path, mode='a', header=False, index=False)
    else:
        # If file does not exist, create it and write the header
        df.to_csv(path, index=False)
    
    print(f"Data saved to {path}")

category_keywords = ["business", "finance", "entrepreneur", "management", "accounting", "economics", "project management", "leadership", "strategy", "investment", 
                     "math", "mathematics", "statistics", "calculus", "algebra", "geometry", "probability", "trigonometry", "differential equations", "linear algebra", "discrete math", "topology", "combinatorics", "set theory", "real analysis", "complex analysis", "abstract algebra", "number theory", "graph theory", "logic", "game theory", "measure theory", "mathematical modeling", "stochastic processes", "numerical analysis", "multivariable calculus", "optimization", "vector calculus", "applied mathematics",
                     "computer science", "programming", "software", "coding", "java", "python", "C++", "AI", "artificial intelligence", "web development", "cs50", "technology", "algorithms", "autonomous systems", "systems programming", "cybersecurity", "blockchain", "cloud computing", "machine learning", "deep learning", "neural networks", "operating systems", "computational thinking", "networking", "computer architecture", "embedded systems", "database systems", "theory of computation",
                     "data analytics", "big data", "SQL", "machine learning", "deep learning", "data science", "excel", "r programming", "data", "predictive modeling", "business intelligence", "data mining", "data visualization", "data engineering", "time series analysis", "ETL", "hadoop", "spark",
                     "design", "graphic design", "ux", "ui", "web design", "visual", "animation", "illustration", "motion graphics", "product design", "typography", "brand design", "3D modeling", "video editing", "industrial design", "color theory", "interaction design",
                     "marketing", "advertising", "seo", "branding", "digital marketing", "social media", "consumer behavior", "market research", "public relations", "copywriting", "growth hacking", "email marketing", "content marketing", "performance marketing"]

# Function to go over the list of wanted topics and generate the query for each topic
def generate_queries(topics):
    queries = []
    for topic in topics:
        queries.append(f"{topic} tutorial")
        queries.append(f"{topic} guide")
        queries.append(f"{topic} how to")
    return queries

def main():
    for query in generate_queries(category_keywords):
        
        print("Fetching YouTube videos...")
        video_results = search_youtube_videos(query, max_results=20)
            
        if video_results:
            save_to_csv(video_results)
        else:
            print("No videos found.")

if __name__ == "__main__":
    main()
