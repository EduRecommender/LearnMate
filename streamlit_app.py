import os
import streamlit as st
import sys
import traceback

# Set the environment variable for Streamlit Cloud
os.environ['STREAMLIT_SHARING'] = '1'

# Configure page
st.set_page_config(page_title="LearnMate Chat Analysis", page_icon="📊", layout="wide")

# Create necessary directories
def setup_directories():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define paths for all required directories
        chat_requests_dir = os.path.join(base_dir, "backend", "data", "chat_requests")
        metrics_dir = os.path.join(base_dir, "backend", "data", "metrics")
        processed_dir = os.path.join(base_dir, "backend", "data", "processed")
        metadata_dir = os.path.join(processed_dir, "metadata")
        
        # Create directories if they don't exist
        for directory in [chat_requests_dir, metrics_dir, processed_dir, metadata_dir]:
            os.makedirs(directory, exist_ok=True)
            st.sidebar.write(f"Created directory: {directory}")
        
        # Create empty metrics file if it doesn't exist
        metrics_file = os.path.join(metrics_dir, "processing_metrics.jsonl")
        if not os.path.exists(metrics_file):
            with open(metrics_file, 'w') as f:
                pass
            st.sidebar.write(f"Created empty metrics file")
        
        return True
    except Exception as e:
        st.error(f"Error setting up directories: {str(e)}")
        return False

# Main app with error handling
def run_app():
    try:
        st.title("LearnMate Chat Response Analysis")
        st.markdown("""
        This dashboard provides insights into chat responses for improving chatbot and recommendation systems.
        """)
        
        # Setup directories first
        if not setup_directories():
            st.error("Failed to set up required directories. See error above.")
            return
        
        # Try to import and run the main app
        try:
            from streamlit_eda import main
            main()
        except ImportError as e:
            # If import fails, provide a simplified dashboard
            st.warning(f"Could not load full dashboard: {str(e)}")
            st.info("Displaying simplified dashboard instead")
            
            # Basic dashboard content
            st.header("Sample Data")
            st.write("This is a placeholder for the full dashboard. The actual data processing module could not be loaded.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Chat Requests", "0")
            with col2:
                st.metric("Unique Users", "0")
            
            st.subheader("Next Steps")
            st.write("""
            If you're seeing this message, there may be an issue with dependencies or file structure.
            
            Check the Streamlit Cloud logs for specific errors and try the following:
            1. Verify all required files are in the repository
            2. Check package compatibility in requirements-minimal.txt
            3. Check import statements in streamlit_eda.py
            """)
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    run_app() 