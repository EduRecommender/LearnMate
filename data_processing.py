import os
import json
import pandas as pd
import glob
from datetime import datetime
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import hashlib
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_processing.log'))
    ]
)
logger = logging.getLogger(__name__)

# Download necessary NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

def calculate_file_hash(file_path):
    """
    Calculate MD5 hash of a file to detect changes
    """
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_file_metadata(metadata_path):
    """
    Load file metadata tracking last processed state
    """
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_file_metadata(metadata, metadata_path):
    """
    Save file metadata tracking last processed state
    """
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_chat_requests(directory_path, metadata_path):
    """
    Load all chat request JSON files into a pandas DataFrame,
    with optimizations to only process new or changed files
    """
    all_requests = []
    metadata = load_file_metadata(metadata_path)
    current_metadata = {}
    files_processed = 0
    files_skipped = 0
    
    # Get all JSON files in the directory
    json_files = glob.glob(os.path.join(directory_path, "*.json"))
    
    start_time = time.time()
    logger.info(f"Processing {len(json_files)} chat request files")
    
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        modified_time = os.path.getmtime(file_path)
        file_size = os.path.getsize(file_path)
        
        # Create a simple metadata key
        current_meta = {
            'modified_time': modified_time,
            'size': file_size
        }
        current_metadata[file_name] = current_meta
        
        # Check if file has changed since last processing
        if file_name in metadata and \
           metadata[file_name]['modified_time'] == modified_time and \
           metadata[file_name]['size'] == file_size:
            # File hasn't changed, load from cache if available
            if 'data' in metadata[file_name]:
                all_requests.append(metadata[file_name]['data'])
                files_skipped += 1
                continue
        
        # File is new or changed, process it
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Add the file name as a field
                data['file_name'] = file_name
                all_requests.append(data)
                # Store processed data in metadata
                current_metadata[file_name]['data'] = data
                files_processed += 1
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_requests)
    
    # Extract additional information
    if not df.empty:
        df['request_id'] = df['file_name'].apply(lambda x: x.split('.')[0])
        
        # If 'result' is a dictionary, extract message content
        df['response_content'] = df.apply(
            lambda row: row['result'].get('content', '') if isinstance(row.get('result'), dict) else '', 
            axis=1
        )
        
        # Calculate response length
        df['response_length'] = df['response_content'].apply(len)
        
        # Extract timestamps and convert to datetime
        df['started_at_dt'] = pd.to_datetime(df['started_at'], errors='coerce')
        df['completed_at_dt'] = pd.to_datetime(df['completed_at'], errors='coerce')
    
    # Save updated metadata
    save_file_metadata(current_metadata, metadata_path)
    
    processing_time = time.time() - start_time
    logger.info(f"Processed {files_processed} files, skipped {files_skipped} unchanged files in {processing_time:.2f} seconds")
    
    return df

def load_processing_metrics(file_path, last_processed_line=0):
    """
    Load the processing metrics JSONL file into a pandas DataFrame,
    with support for incremental processing
    """
    metrics = []
    lines_processed = 0
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            # Skip already processed lines
            if i < last_processed_line:
                continue
                
            try:
                data = json.loads(line.strip())
                metrics.append(data)
                lines_processed += 1
            except Exception as e:
                logger.error(f"Error parsing line {i} in metrics file: {e}")
    
    # Convert to DataFrame
    df = pd.DataFrame(metrics)
    
    # Convert timestamp to datetime if DataFrame is not empty
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    logger.info(f"Processed {lines_processed} new lines from metrics file")
    return df, last_processed_line + lines_processed

def extract_topics_from_content(text):
    """
    Extract important topics from text content
    """
    if not isinstance(text, str) or not text:
        return []
    
    # Tokenize text
    tokens = word_tokenize(text.lower())
    
    # Remove stopwords and non-alphabetic tokens
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [word for word in tokens if word.isalpha() and word not in stop_words]
    
    # Lemmatize words
    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered_tokens]
    
    # Count frequency of words
    word_freq = Counter(lemmatized)
    
    # Return top 10 most common words as topics
    return [word for word, _ in word_freq.most_common(10)]

def analyze_response_types(df):
    """
    Analyze and categorize responses based on content patterns
    """
    if df.empty or 'response_content' not in df.columns:
        return df
        
    # Define patterns for different response types
    patterns = {
        'study_plan': r'(study plan|daily activities|schedule)',
        'recommendation': r'(recommend|suggestion|advise)',
        'explanation': r'(explain|clarify|understand)',
        'summary': r'(summary|overview|recap)',
    }
    
    # Apply pattern matching to categorize responses
    for category, pattern in patterns.items():
        df[f'is_{category}'] = df['response_content'].str.contains(
            pattern, case=False, regex=True, na=False
        )
    
    return df

def merge_with_existing_data(new_df, existing_csv_path, key_column):
    """
    Merge new data with existing data, keeping the most recent version of each record
    """
    if os.path.exists(existing_csv_path):
        try:
            existing_df = pd.read_csv(existing_csv_path)
            
            # If the existing DataFrame is not empty and has the key column
            if not existing_df.empty and key_column in existing_df.columns and key_column in new_df.columns:
                # Get unique keys from both DataFrames
                existing_keys = set(existing_df[key_column])
                new_keys = set(new_df[key_column])
                
                # Find keys in both DataFrames
                common_keys = existing_keys.intersection(new_keys)
                
                # For common keys, use the data from new_df (more recent)
                if common_keys:
                    # Remove common keys from existing_df
                    existing_df = existing_df[~existing_df[key_column].isin(common_keys)]
                
                # Combine the filtered existing data with the new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                return combined_df
        except Exception as e:
            logger.error(f"Error merging with existing data: {e}")
            # If there's an error, just return the new data
            return new_df
    
    # If the file doesn't exist or there was an error, return just the new data
    return new_df

def main():
    start_time = time.time()
    logger.info("Starting data processing")
    
    # Base paths
    base_dir = "/home/sebas/Desktop/ie_dev/y3.2/reco/LearnMate"
    chat_requests_dir = os.path.join(base_dir, "backend/data/chat_requests")
    metrics_file = os.path.join(base_dir, "backend/data/metrics/processing_metrics.jsonl")
    
    # Create processed directory if it doesn't exist
    output_dir = os.path.join(base_dir, "backend/data/processed")
    os.makedirs(output_dir, exist_ok=True)
    
    # Metadata file paths for tracking processing state
    metadata_dir = os.path.join(output_dir, "metadata")
    os.makedirs(metadata_dir, exist_ok=True)
    
    chat_metadata_path = os.path.join(metadata_dir, "chat_metadata.json")
    metrics_state_path = os.path.join(metadata_dir, "metrics_state.json")
    
    # Get last processed metrics line
    last_processed_line = 0
    if os.path.exists(metrics_state_path):
        try:
            with open(metrics_state_path, 'r') as f:
                metrics_state = json.load(f)
                last_processed_line = metrics_state.get('last_processed_line', 0)
        except:
            pass
    
    # Load data
    chat_df = load_chat_requests(chat_requests_dir, chat_metadata_path)
    metrics_df, new_last_processed_line = load_processing_metrics(metrics_file, last_processed_line)
    
    # Save updated metrics state
    with open(metrics_state_path, 'w') as f:
        json.dump({'last_processed_line': new_last_processed_line}, f)
    
    # Process data if not empty
    if not chat_df.empty:
        # Analyze responses
        chat_df = analyze_response_types(chat_df)
        
        # Extract topics from responses
        chat_df['topics'] = chat_df['response_content'].apply(extract_topics_from_content)
        
        # Merge with existing processed data
        chat_csv_path = os.path.join(output_dir, "processed_chat_data.csv")
        merged_chat_df = merge_with_existing_data(chat_df, chat_csv_path, 'request_id')
        
        # Save processed DataFrame to CSV
        merged_chat_df.to_csv(chat_csv_path, index=False)
        logger.info(f"Saved processed chat data: {merged_chat_df.shape}")
    else:
        logger.info("No chat data to process")
    
    # Process metrics data if not empty
    if not metrics_df.empty:
        # Merge with existing processed data
        metrics_csv_path = os.path.join(output_dir, "processed_metrics_data.csv")
        merged_metrics_df = merge_with_existing_data(metrics_df, metrics_csv_path, 'request_id')
        
        # Save processed DataFrame to CSV
        merged_metrics_df.to_csv(metrics_csv_path, index=False)
        logger.info(f"Saved processed metrics data: {merged_metrics_df.shape}")
    else:
        logger.info("No metrics data to process")
    
    # Save processing timestamp
    timestamp_path = os.path.join(output_dir, "last_processed.txt")
    with open(timestamp_path, 'w') as f:
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    total_time = time.time() - start_time
    logger.info(f"Data processing completed in {total_time:.2f} seconds")

if __name__ == "__main__":
    main() 