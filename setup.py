import os
import sys

def setup_project_structure():
    """
    Creates the necessary directory structure for the project
    """
    # Define base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define directory paths
    data_dir = os.path.join(base_dir, "backend", "data")
    processed_dir = os.path.join(data_dir, "processed")
    metadata_dir = os.path.join(processed_dir, "metadata")
    chat_requests_dir = os.path.join(data_dir, "chat_requests")
    metrics_dir = os.path.join(data_dir, "metrics")
    
    # Create directories if they don't exist
    for directory in [processed_dir, metadata_dir, chat_requests_dir, metrics_dir]:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    print("Project structure setup complete!")

if __name__ == "__main__":
    setup_project_structure() 