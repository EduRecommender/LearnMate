import os
import sys

def setup_project_structure():
    """
    Creates the necessary directory structure for the project
    """
    # Define base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths for processed data
    processed_dir = os.path.join(base_dir, "backend", "data", "processed")
    
    # Create directories if they don't exist
    os.makedirs(processed_dir, exist_ok=True)
    
    print(f"Created directory: {processed_dir}")
    print("Project structure setup complete!")

if __name__ == "__main__":
    setup_project_structure() 