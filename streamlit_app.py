import os
import streamlit as st
import subprocess
import sys

# Set the environment variable for Streamlit Cloud
os.environ['STREAMLIT_SHARING'] = '1'

# Create necessary directories
def setup_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths for all required directories
    chat_requests_dir = os.path.join(base_dir, "backend", "data", "chat_requests")
    metrics_dir = os.path.join(base_dir, "backend", "data", "metrics")
    processed_dir = os.path.join(base_dir, "backend", "data", "processed")
    metadata_dir = os.path.join(processed_dir, "metadata")
    
    # Create directories if they don't exist
    for directory in [chat_requests_dir, metrics_dir, processed_dir, metadata_dir]:
        os.makedirs(directory, exist_ok=True)
    
    # Create empty metrics file if it doesn't exist
    metrics_file = os.path.join(metrics_dir, "processing_metrics.jsonl")
    if not os.path.exists(metrics_file):
        with open(metrics_file, 'w') as f:
            pass

# Run setup
setup_directories()

# Simply import and run the original app
from streamlit_eda import main

# Call the main function from streamlit_eda.py
main() 