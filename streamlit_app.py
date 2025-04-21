import os
import streamlit as st
import subprocess
import sys

# Redirect to the main Streamlit EDA app
if __name__ == "__main__":
    # Check if we need to run setup first (only on first run)
    setup_file = "setup_completed.txt"
    
    if not os.path.exists(setup_file):
        st.info("First-time setup in progress, please wait...")
        
        # Install dependencies if needed
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        # Run setup script
        subprocess.run([sys.executable, "setup.py"])
        
        # Process initial data
        subprocess.run([sys.executable, "data_processing.py"])
        
        # Create file to indicate setup is complete
        with open(setup_file, "w") as f:
            f.write("Setup completed at " + str(st.session_state.get("last_refresh_time", "")))
    
    # Import and run the actual EDA app
    st.set_page_config(page_title="LearnMate EDA", page_icon="📊", layout="wide")
    
    # Import the main function from streamlit_eda.py
    from streamlit_eda import main
    
    # Run the main function
    main() 