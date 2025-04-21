import os
import sys

def setup_project_structure():
    """
    Creates the necessary directory structure for the project
    """
    # Define base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths for all required directories
    chat_requests_dir = os.path.join(base_dir, "backend", "data", "chat_requests")
    metrics_dir = os.path.join(base_dir, "backend", "data", "metrics")
    processed_dir = os.path.join(base_dir, "backend", "data", "processed")
    metadata_dir = os.path.join(processed_dir, "metadata")
    
    # Create directories if they don't exist
    for directory in [chat_requests_dir, metrics_dir, processed_dir, metadata_dir]:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Create empty files if needed for Streamlit Cloud
    if os.getenv('STREAMLIT_SHARING'):
        # Create empty metrics file if it doesn't exist
        metrics_file = os.path.join(metrics_dir, "processing_metrics.jsonl")
        if not os.path.exists(metrics_file):
            with open(metrics_file, 'w') as f:
                pass
            print(f"Created empty file: {metrics_file}")
    
    print("Project structure setup complete!")

if __name__ == "__main__":
    setup_project_structure() 