import streamlit as st
import os
import sys
import subprocess

# Set up the page configuration
st.set_page_config(
    page_title="LearnMate EDA Dashboard",
    page_icon="📊",
    layout="wide"
)

# Display header
st.title("LearnMate EDA Dashboard")
st.markdown("---")

# Create project structure if it doesn't exist
try:
    # Make sure directories exist
    if not os.path.exists("backend/data/processed"):
        st.info("Setting up project structure...")
        subprocess.run([sys.executable, "setup.py"], check=True)
        st.success("Project structure created!")
except Exception as e:
    st.error(f"Error setting up project structure: {e}")

# Run the EDA dashboard
try:
    st.info("Loading EDA dashboard...")
    
    # Set environment variable to indicate we're running on Streamlit Cloud
    os.environ['STREAMLIT_SHARING'] = '1'
    
    # Import and run the main app
    from eda.streamlit_eda import main
    main()
    
except Exception as e:
    st.error(f"Error running the EDA dashboard: {e}")
    st.error("Please check the logs for more information.")
    
    # Display troubleshooting information
    with st.expander("Troubleshooting Information"):
        st.write("### Environment Information")
        st.write(f"Python version: {sys.version}")
        st.write(f"Current directory: {os.getcwd()}")
        st.write(f"Directory contents: {os.listdir('.')}")
        
        if os.path.exists("backend/data"):
            st.write(f"Data directory contents: {os.listdir('backend/data')}") 