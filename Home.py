import streamlit as st
from syllabus_processor import process_uploaded_syllabus
import pandas as pd
from chatbot_gpt import chat_with_bot as chat_with_gpt
from chatbot_deepseek import chat_with_bot as chat_with_deepseek
from recommendation.models.team_models.Andres.CourseRecommenderCosine import CourseRecommenderCosine
import os
from datetime import datetime
from agents.utils.session_manager import SessionManager
from auth_manager import AuthManager
from study_session_manager import StudySessionManager
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from user_preferences_manager import UserPreferencesManager
from agents.assistant_agent import DeepSeekAssistantAgent
from agents.schemas.sessions import ChatMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config and theme
st.set_page_config(
    page_title="LearnMate",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom theme to ensure text visibility
st.markdown("""
    <style>
        .stTextInput input, .stTextArea textarea {
            color: #000000 !important;
        }
        .stSelectbox select {
            color: #000000 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize managers
auth_manager = AuthManager()
session_manager = SessionManager()
user_preferences_manager = UserPreferencesManager()

# Lazy initialization of assistant agent
@st.cache_resource
def get_assistant_agent():
    """Lazy initialization of DeepSeekAssistantAgent"""
    return DeepSeekAssistantAgent()

# Initialize all session state variables
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "show_session_preferences" not in st.session_state:
    st.session_state.show_session_preferences = False

if "show_preferences_modal" not in st.session_state:
    st.session_state.show_preferences_modal = False

if "show_session_modal" not in st.session_state:
    st.session_state.show_session_modal = False

if "current_session" not in st.session_state:
    st.session_state.current_session = None

if "current_sessions" not in st.session_state:
    st.session_state.current_sessions = None

if "editing_session" not in st.session_state:
    st.session_state.editing_session = None

if "temp_resources" not in st.session_state:
    st.session_state.temp_resources = []

if "syllabus_data" not in st.session_state:
    st.session_state.syllabus_data = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "form_timestamp" not in st.session_state:
    st.session_state.form_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

if "preferences_source" not in st.session_state:
    st.session_state.preferences_source = None

# Initialize user preferences if not set
if "user_preferences" not in st.session_state:
    st.session_state.user_preferences = {
        "name": "",
        "level": "Not Set",  # undergraduate, high school, graduate, PhD
        "grade_level": "Not Set",
        "major": "Not Set",
        "subject_interest": [],
        "learning_styles": [],
        "preferred_study_methods": [],
        "preferred_difficulty": "Not Set",
        "time_available_per_week": "Not Set",
        "preferred_schedule": "Not Set",
        "additional_notes": "",
        "has_set_preferences": False,
        "has_skipped_preferences": False
    }

# Check for existing session
if st.session_state.session_id:
    is_valid, username = auth_manager.check_session(st.session_state.session_id)
    if is_valid:
        st.session_state.is_authenticated = True
        st.session_state.user = username
        st.session_state.user_preferences = auth_manager.get_user_preferences(username)

# Load dataset for available categories and difficulty levels
@st.cache_data
def load_courses():
    return pd.read_csv("input_data/kaggle_filtered_courses.csv")

courses = load_courses()

# Create a unique form key using timestamp
if "form_timestamp" not in st.session_state:
    st.session_state.form_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

def show_login_form():
    """Display the login form."""
    with st.form(f"login_form_{st.session_state.form_timestamp}"):
        st.subheader("Login to LearnMate")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            success, session_id = auth_manager.login_user(username, password)
            if success:
                st.session_state.session_id = session_id
                st.session_state.is_authenticated = True
                st.session_state.user = username
                st.session_state.user_preferences = auth_manager.get_user_preferences(username)
                st.success("Login successful!")
                st.rerun()
            else:
                st.error(session_id)  # session_id contains error message in this case
    
    st.markdown("---")
    with st.expander("Register New Account"):
        with st.form(f"register_form_{st.session_state.form_timestamp}"):
            st.subheader("Create Account")
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            email = st.text_input("Email (Optional)")
            submitted = st.form_submit_button("Register")
            
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = auth_manager.register_user(new_username, new_password, email)
                    if success:
                        st.success("✅ Account created successfully! You can now log in with your username and password.")
                        st.info("Please log in with your new account.")
                        st.rerun()
                    else:
                        st.error(message)

def show_logout_button():
    """Display the logout button in the sidebar."""
    if st.sidebar.button("Logout", key="logout_button_sidebar"):
        auth_manager.logout_user()
        st.rerun()

def show_general_preferences_modal():
    """Display the general preferences modal."""
    st.markdown("### General Learning Preferences")
    
    # Initialize preferences_source if not set
    if "preferences_source" not in st.session_state:
        st.session_state.preferences_source = "default"
    
    with st.form(key=f"general_preferences_form_{st.session_state.preferences_source}_{st.session_state.form_timestamp}", clear_on_submit=False):
        # Personal Information
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your Name (Optional)", value=st.session_state.user_preferences["name"])
            level = st.selectbox(
                "Academic Level",
                ["Not Set", "High School", "Undergraduate", "Graduate", "PhD", "Professional", "Other"],
                index=["Not Set", "High School", "Undergraduate", "Graduate", "PhD", "Professional", "Other"].index(st.session_state.user_preferences["level"])
            )
            grade_level = st.selectbox(
                "Grade Level",
                ["Not Set", "Freshman", "Sophomore", "Junior", "Senior", "Graduate Student", "PhD Candidate", "Other"],
                index=["Not Set", "Freshman", "Sophomore", "Junior", "Senior", "Graduate Student", "PhD Candidate", "Other"].index(st.session_state.user_preferences["grade_level"])
            )
            major = st.text_input("Major/Field of Study (Optional)", value=st.session_state.user_preferences["major"])
        
        with col2:
            subject_interest = st.multiselect(
                "Subject Interests",
                ["Computer Science", "Mathematics", "Physics", "Chemistry", "Biology", "Engineering", "Business", "Arts", "Humanities", "Social Sciences", "Other"],
                default=st.session_state.user_preferences["subject_interest"]
            )
            learning_styles = st.multiselect(
                "Learning Styles",
                ["Visual", "Auditory", "Reading/Writing", "Kinesthetic", "Social", "Solitary", "Logical", "Verbal"],
                default=st.session_state.user_preferences["learning_styles"]
            )
            preferred_difficulty = st.selectbox(
                "Preferred Difficulty",
                ["Not Set", "Beginner", "Intermediate", "Advanced"],
                index=["Not Set", "Beginner", "Intermediate", "Advanced"].index(st.session_state.user_preferences["preferred_difficulty"])
            )
        
        # Learning Preferences
        col3, col4 = st.columns(2)
        with col3:
            time_available_per_week = st.selectbox(
                "Time Available Per Week",
                ["Not Set", "1-2 hours", "3-5 hours", "6-10 hours", "11+ hours"],
                index=["Not Set", "1-2 hours", "3-5 hours", "6-10 hours", "11+ hours"].index(st.session_state.user_preferences["time_available_per_week"])
            )
            preferred_schedule = st.selectbox(
                "Preferred Schedule",
                ["Not Set", "Flexible", "Structured", "Intensive"],
                index=["Not Set", "Flexible", "Structured", "Intensive"].index(st.session_state.user_preferences["preferred_schedule"])
            )
        
        with col4:
            preferred_study_methods = st.multiselect(
                "Preferred Study Methods",
                [
                    "Video Lectures",
                    "Reading Textbooks",
                    "Practice Exercises",
                    "Group Discussions",
                    "Flashcards",
                    "Mind Maps",
                    "Summaries",
                    "Online Courses",
                    "Interactive Tutorials",
                    "Lab Work",
                    "Case Studies",
                    "Project-based Learning"
                ],
                default=st.session_state.user_preferences["preferred_study_methods"]
            )
        
        # Additional Notes
        additional_notes = st.text_area(
            "Additional Notes",
            value=st.session_state.user_preferences["additional_notes"],
            placeholder="Any other information that might help personalize your learning experience..."
        )
        
        # Form submit buttons
        col7, col8, col9 = st.columns(3)
        with col7:
            submitted = st.form_submit_button("Save Preferences")
        with col8:
            skip = st.form_submit_button("Skip for Now")
        with col9:
            close = st.form_submit_button("Close")
        
        if submitted:
            new_preferences = {
                "name": name,
                "level": level,
                "grade_level": grade_level,
                "major": major,
                "subject_interest": subject_interest,
                "learning_styles": learning_styles,
                "preferred_study_methods": preferred_study_methods,
                "preferred_difficulty": preferred_difficulty,
                "time_available_per_week": time_available_per_week,
                "preferred_schedule": preferred_schedule,
                "additional_notes": additional_notes,
                "has_set_preferences": True,
                "has_skipped_preferences": False
            }
            st.session_state.user_preferences.update(new_preferences)
            auth_manager.update_user_preferences(st.session_state.user, new_preferences)
            st.success("Preferences saved successfully!")
            st.session_state.show_preferences_modal = False
            st.rerun()
        elif skip:
            st.session_state.user_preferences.update({
                "has_set_preferences": True,
                "has_skipped_preferences": True
            })
            auth_manager.update_user_preferences(st.session_state.user, st.session_state.user_preferences)
            st.info("You can set your preferences later using the sidebar button.")
            st.session_state.show_preferences_modal = False
            st.rerun()
        elif close:
            st.session_state.show_preferences_modal = False
            st.rerun()

def show_session_preferences_modal(editing_session_id=None):
    """Display the study session preferences modal for creating or editing a session."""
    try:
        # Initialize session state variables if they don't exist
        if "temp_resources" not in st.session_state:
            st.session_state.temp_resources = []
if "syllabus_data" not in st.session_state:
    st.session_state.syllabus_data = None

        # Get the editing session if we have an ID
        editing_session = None
        if editing_session_id:
            editing_session = session_manager.get_session(st.session_state.user, editing_session_id)
            if not editing_session:
                st.error("Session not found")
                st.session_state.show_session_modal = False
                st.rerun()
                return
        
        st.subheader("📚 Study Session Setup")
        
        # Syllabus Section
        st.markdown("### 📋 Course Syllabus")
        
        # Check if syllabus is already uploaded
        syllabus_uploaded = st.session_state.syllabus_data is not None or (editing_session and editing_session.preferences.get('syllabus'))
        
        if syllabus_uploaded:
            st.success("✅ Syllabus uploaded successfully!")
            syllabus_data = st.session_state.syllabus_data if st.session_state.syllabus_data else editing_session.preferences.get('syllabus')
            st.write(f"**Course Name:** {syllabus_data['course_name']}")
            with st.expander("View Syllabus Content"):
                st.write("**Session Content:**")
                for topic in syllabus_data["session_content"]:
                    st.write(f"- {topic}")
        
        # Syllabus upload field
        uploaded_syllabus = st.file_uploader("Upload Course Syllabus (PDF)", type=["pdf"])
        
        if uploaded_syllabus is not None:
            # Process the uploaded syllabus
            syllabus_data = process_uploaded_syllabus(uploaded_syllabus)
    if syllabus_data:
        st.session_state.syllabus_data = syllabus_data
                st.success("✅ Syllabus uploaded successfully!")
        st.write(f"**Course Name:** {syllabus_data['course_name']}")
                with st.expander("View Syllabus Content"):
                    st.write("**Session Content:**")
                    for topic in syllabus_data["session_content"]:
                        st.write(f"- {topic}")
            else:
                st.error("Failed to process the syllabus. Please try again with a different file.")
        
        # Create form for session preferences
        with st.form("session_preferences_form"):
            # Session name
            session_name = st.text_input(
                "Session Name",
                value=editing_session.name if editing_session else "",
                help="Give your study session a descriptive name"
            )
            
            # Field of study
            field_of_study = st.text_input(
                "Field of Study",
                value=editing_session.preferences.get("field_of_study", "") if editing_session else "",
                help="Enter the subject or field you're studying"
            )
            
            # Study goal
            study_goal = st.text_area(
                "Study Goal",
                value=editing_session.preferences.get("goal", "") if editing_session else "",
                help="What do you want to achieve in this study session?"
            )
            
            # Context
            context = st.text_area(
                "Additional Context",
                value=editing_session.preferences.get("context", "") if editing_session else "",
                help="Any additional context that might help (e.g., upcoming exam, project details)"
            )
            
            # Session duration
            col1, col2 = st.columns(2)
            with col1:
                default_days = 7
                if editing_session and editing_session.preferences.get("days"):
                    try:
                        default_days = int(editing_session.preferences.get("days"))
                    except (ValueError, TypeError):
                        pass
                
                session_days = st.number_input(
                    "Number of Days",
                    min_value=1,
                    value=default_days,
                    step=1,
                    help="How many days do you plan to study?"
                )
            with col2:
                time_options = ["15 minutes", "30 minutes", "1 hour", "2 hours", "3 hours", "4+ hours"]
                default_time = "1 hour"
                if editing_session and editing_session.preferences.get("time_per_day"):
                    default_time = editing_session.preferences.get("time_per_day")
                    if default_time not in time_options:
                        default_time = "1 hour"
                
                session_time_per_day = st.selectbox(
                    "Time Per Day",
                    time_options,
                    index=time_options.index(default_time),
                    help="How much time per day?"
                )
            
            # Difficulty level
            difficulty_options = ["Beginner", "Intermediate", "Advanced", "Expert"]
            default_difficulty = "Intermediate"
            if editing_session and editing_session.preferences.get("difficulty"):
                default_difficulty = editing_session.preferences.get("difficulty")
                if default_difficulty not in difficulty_options:
                    default_difficulty = "Intermediate"
            
            difficulty = st.select_slider(
                "Difficulty Level",
                options=difficulty_options,
                value=default_difficulty,
                help="Select the difficulty level of the material"
            )
            
            # Additional notes
            notes = st.text_area(
                "Additional Notes",
                value=editing_session.preferences.get("notes", "") if editing_session else "",
                help="Any additional notes or instructions for this study session"
            )
            
            # Submit button
            submit_button = st.form_submit_button(
                "Save Session" if editing_session else "Create Session"
            )
            
            if submit_button:
                if not session_name:
                    st.error("Please enter a session name")
                    return
                
                try:
                    # Create preferences dictionary
                    preferences = {
                        "field_of_study": field_of_study,
                        "goal": study_goal,
                        "context": context,
                        "days": session_days,
                        "time_per_day": session_time_per_day,
                        "difficulty": difficulty,
                        "notes": notes,
                        "syllabus": st.session_state.syllabus_data if syllabus_uploaded else None,
                        "resources": st.session_state.temp_resources
                    }
                    
                    if editing_session:
                        # Update existing session
                        success = session_manager.update_session(
                            st.session_state.user,
                            editing_session.session_id,
                            preferences
                        )
                        if success:
                            st.success("Session updated successfully!")
                            # Clear temporary resources and syllabus data
                            st.session_state.temp_resources = []
                            st.session_state.syllabus_data = None
                            # Clear editing state
                            st.session_state.editing_session = None
                            st.session_state.show_session_modal = False
                            st.rerun()
                        else:
                            st.error("Failed to update session")
                    else:
                        # Create new session
                        try:
                            session_id = session_manager.create_session(
                                st.session_state.user,
                                session_name,
                                preferences
                            )
                            if session_id:
                                st.success("Session created successfully!")
                                # Clear temporary resources and syllabus data
                                st.session_state.temp_resources = []
                                st.session_state.syllabus_data = None
                                # Clear modal state
                                st.session_state.show_session_modal = False
                                st.rerun()
                            else:
                                st.error("Failed to create session")
                        except Exception as e:
                            logger.error(f"Error creating session: {str(e)}")
                            st.error(f"Error creating session: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Error saving session: {str(e)}")
                    st.error(f"Error saving session: {str(e)}")
        
        # Add resources section outside the form
        st.markdown("---")
        st.subheader("📑 Learning Resources")
        
        # Add new resource section
        with st.expander("Add New Resource"):
            resource_type = st.selectbox(
                "Resource Type",
                ["Textbook", "Course Notes", "Lecture Slides", "Assignment", "Exam Study Guide", "Other"]
            )
            resource_name = st.text_input("Resource Name/Title")
            
            # Resource source selection
            resource_source = st.radio(
                "Resource Source",
                ["URL", "File Upload"],
                horizontal=True
            )
            
            if resource_source == "URL":
                resource_url = st.text_input("Resource URL")
                if st.button("Add URL Resource"):
                    if not resource_name:
                        st.warning("Please enter a resource name")
                    elif not resource_url:
                        st.warning("Please enter a URL")
                    else:
                        new_resource = {
                            "title": resource_name,
                            "type": resource_type,
                            "url": resource_url
                        }
                        st.session_state.temp_resources.append(new_resource)
                        st.success(f"Added URL resource: {resource_name}")
                        st.rerun()
            else:
                uploaded_file = st.file_uploader(
                    "Upload Resource File",
                    type=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "mp4", "mp3"]
                )
                if st.button("Add File Resource"):
                    if not resource_name:
                        st.warning("Please enter a resource name")
                    elif not uploaded_file:
                        st.warning("Please upload a file")
                    else:
                        try:
                            with st.spinner(f"Uploading {uploaded_file.name}..."):
                                # Save file and get metadata
                                file_metadata = session_manager._save_uploaded_file(
                                    uploaded_file,
                                    st.session_state.user,
                                    "temp"  # Temporary storage for resources
                                )
                                
                                # Add file metadata to resource
                                new_resource = {
                                    "title": resource_name,
                                    "type": resource_type,
                                    "filename": file_metadata["filename"],
                                    "path": file_metadata["path"],
                                    "file_type": file_metadata["type"],
                                    "size": file_metadata["size"],
                                    "uploaded_at": file_metadata["uploaded_at"]
                                }
                                
                                st.session_state.temp_resources.append(new_resource)
                                st.success(f"✅ Successfully uploaded {file_metadata['filename']}")
                                st.rerun()
                        except Exception as e:
                            logger.error(f"Error uploading resource file: {str(e)}")
                            st.error(f"❌ Error uploading file: {str(e)}")
        
        # Display existing resources
        if st.session_state.temp_resources:
            st.write("Current Resources:")
            for idx, resource in enumerate(st.session_state.temp_resources):
                with st.expander(f"{resource['title']}"):
                    st.write(f"**Type:** {resource['type']}")
                    
                    # Display URL or file information
                    if "url" in resource:
                        st.write(f"**URL:** {resource['url']}")
                    elif "path" in resource:
                        st.write(f"**File:** {resource['filename']}")
                        st.write(f"**Size:** {resource['size']} bytes")
                        st.write(f"**Uploaded:** {resource['uploaded_at']}")
                        
                        # Add download button for files
                        file_path = os.path.join(session_manager.uploads_dir, resource['path'])
                        if os.path.exists(file_path):
                            with open(file_path, 'rb') as f:
                                st.download_button(
                                    label="⬇️ Download",
                                    data=f,
                                    file_name=resource['filename'],
                                    mime=resource.get('file_type', 'application/octet-stream')
                                )
                    
                    if st.button("🗑️ Remove", key=f"remove_resource_{idx}"):
                        # If it's a file, delete it
                        if "path" in resource:
                            try:
                                file_path = os.path.join(session_manager.uploads_dir, resource['path'])
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception as e:
                                logger.error(f"Error deleting resource file: {str(e)}")
                        
                        st.session_state.temp_resources.pop(idx)
                        st.rerun()
    
    except Exception as e:
        logger.error(f"Error in session preferences modal: {str(e)}")
        st.error("An error occurred while showing the session preferences. Please try again.")

def delete_session_and_refresh(user, session_id):
    """Helper function to delete a session and clean up all related state."""
    logger.info(f"Deleting session {session_id} for user {user}")
    
    try:
        # Delete from both session managers to ensure complete cleanup
        success_new = session_manager.delete_session(user, session_id)
        success_old, _ = StudySessionManager().delete_session(user, session_id)
        
        if success_new or success_old:
            # Clear ALL session state except authentication
            preserved_auth = {
                "is_authenticated": st.session_state.get("is_authenticated", False),
                "user": st.session_state.get("user", None),
                "user_preferences": st.session_state.get("user_preferences", {})
            }
            
            # Clear everything from session state
            for key in list(st.session_state.keys()):
                try:
                    del st.session_state[key]
                except Exception:
                    pass
            
            # Restore authentication state
            for key, value in preserved_auth.items():
                st.session_state[key] = value
            
            st.success("Session deleted successfully")
            
            # Force complete refresh of the page
            st.experimental_rerun()
        else:
            st.error("Failed to delete session. Please try again.")
            
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        st.error("An error occurred while deleting the session. Please try again.")

def show_session_list():
    """Display the list of study sessions."""
    st.sidebar.subheader("Study Sessions")
    
    if st.sidebar.button("Create New Session", key="create_session_sidebar_button"):
        st.session_state.show_session_modal = True
    
    sessions = session_manager.get_user_sessions(st.session_state.user)
    
    if not sessions:
        st.sidebar.info("No study sessions yet. Create one to get started!")
        return
    
    for session in sessions:
        with st.sidebar.expander(f"📚 {session.name}"):
            if session.preferences.get('goal'):
                st.write(f"**Goal:** {session.preferences['goal']}")
            
            # Handle duration display for both old and new formats
            duration_text = ""
            if 'days' in session.preferences and 'time_per_day' in session.preferences:
                duration_text = f"{session.preferences['days']} days, {session.preferences['time_per_day']} per day"
            elif 'time_commitment' in session.preferences:
                duration_text = f"{session.preferences['time_commitment']} hours"
            else:
                duration_text = "Not specified"
            st.write(f"**Duration:** {duration_text}")
            
            # Handle progress display
            progress = session.progress if isinstance(session.progress, (int, float)) else 0
            st.write(f"**Progress:** {progress}%")
            
            if st.button("Open Session", key=f"open_{session.session_id}"):
                st.session_state.current_session = session.session_id
                st.rerun()
            
            if st.button("Delete Session", key=f"delete_sidebar_{session.session_id}"):
                delete_session_and_refresh(st.session_state.user, session.session_id)

def display_session(session_id):
    """Display a specific session"""
    # Check authentication first
    if not st.session_state.is_authenticated or not st.session_state.user:
        logger.error("Attempted to display session without authentication")
        st.error("Please log in to view sessions")
        return
    
    logger.info(f"Attempting to display session with ID: {session_id}")
    logger.info(f"Current user: {st.session_state.user}")
    
    try:
        session = session_manager.get_session(st.session_state.user, session_id)
        logger.info(f"Retrieved session: {session}")
        
        if not session:
            logger.error(f"Session not found for ID: {session_id}")
            st.error("Session not found")
            # Clear session state and force refresh
            if "current_sessions" in st.session_state:
                del st.session_state.current_sessions
            st.rerun()
            return
        
        # Create columns for main content and chat
        main_col, chat_col = st.columns([2, 1])
        
        with main_col:
            # Display session information
            st.header(f"📚 {session.name}")
            
            # Display session details
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Session Details")
                st.write(f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Last Updated:** {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            with col2:
                st.subheader("Session Preferences")
                for key, value in session.preferences.items():
                    if key != "syllabus":  # Skip syllabus as it's displayed separately
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            # Display syllabus if it exists
            if session.preferences.get('syllabus'):
                st.markdown("### 📋 Course Syllabus")
                syllabus_data = session.preferences['syllabus']
                st.write(f"**Course Name:** {syllabus_data['course_name']}")
                with st.expander("View Syllabus Content"):
                    st.write("**Session Content:**")
                    for topic in syllabus_data["session_content"]:
                        st.write(f"- {topic}")
            
            # Display session materials
            st.subheader("📑 Learning Materials")
            
            # Add file upload
            uploaded_files = st.file_uploader(
                "Upload learning materials",
                accept_multiple_files=True,
                type=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "mp4", "mp3"]
            )
            
            if uploaded_files:
                for file in uploaded_files:
                    try:
                        with st.spinner(f"Uploading {file.name}..."):
                            # Save file and get metadata
                            file_metadata = session_manager._save_uploaded_file(file, st.session_state.user, session_id)
                            
                            # Add material to session
                            material = {
                                "title": file_metadata["filename"],
                                "description": f"Uploaded on {file_metadata['uploaded_at']}",
                                "type": file_metadata["type"],
                                "size": file_metadata["size"],
                                "path": file_metadata["path"]
                            }
                            
                            if session_manager.add_material(st.session_state.user, session_id, material):
                                st.success(f"✅ Successfully uploaded {file_metadata['filename']}")
                            else:
                                st.error(f"❌ Failed to add {file_metadata['filename']} to session")
                    except Exception as e:
                        logger.error(f"Error uploading file: {str(e)}")
                        st.error(f"❌ Error uploading {file.name}: {str(e)}")
            
            # Display existing materials
            if session.materials:
                for material in session.materials:
                    with st.expander(f"{material.get('title', 'Untitled')}"):
                        st.write(f"**Description:** {material.get('description', 'No description')}")
                        st.write(f"**Type:** {material.get('type', 'Unknown')}")
                        st.write(f"**Size:** {material.get('size', 0)} bytes")
                        
                        # Add download button
                        if material.get('path'):
                            file_path = os.path.join(session_manager.uploads_dir, material['path'])
                            if os.path.exists(file_path):
                                with open(file_path, 'rb') as f:
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=f,
                                        file_name=material['title'],
                                        mime=material.get('type', 'application/octet-stream')
                                    )
                            else:
                                st.warning("⚠️ File not found on server")
                        
                        # Add delete button
                        if st.button("🗑️ Delete", key=f"delete_{material.get('path', '')}"):
                            if session_manager.remove_material(st.session_state.user, session_id, material['path']):
                                st.success("✅ Material deleted successfully")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete material")
            else:
                st.info("📝 No materials added yet. Upload some files to get started!")
            
            # Display session notes
            st.subheader("📝 Notes")
            if session.notes:
                for note in session.notes:
                    with st.expander(f"{note.get('title', 'Untitled')}"):
                        st.write(note.get('content', 'No content'))
            else:
                st.info("No notes added yet")
            
            # Display session progress
            st.subheader("📊 Progress")
            if session.progress:
                for key, value in session.progress.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
else:
                st.info("No progress tracked yet")
            
            # Add buttons for session actions
            col1, col2, col3 = st.columns(3)
            
            # Generate unique keys for each button using timestamp and random suffix
            timestamp = datetime.now().timestamp()
            button_suffix = uuid.uuid4().hex[:8]
            
            with col1:
                if st.button("Update Session", key=f"update_{session_id}_{timestamp}_{button_suffix}"):
                    st.session_state.editing_session = session_id
                    st.session_state.show_session_modal = True
                    st.rerun()
            
            with col2:
                if st.button("Delete Session", key=f"delete_tab_{session_id}_{timestamp}_{button_suffix}"):
                    delete_session_and_refresh(st.session_state.user, session_id)
                    return  # Exit after deletion
            
            with col3:
                if st.button("Clear Chat History", key=f"clear_chat_{session_id}_{timestamp}_{button_suffix}"):
                    session_manager.clear_chat_history(st.session_state.user, session_id)
                    st.success("Chat history cleared successfully")
                    st.rerun()
        
        with chat_col:
            st.markdown("### 💬 Session Chat")
            
            # Initialize session-specific chat history if not exists
            chat_key = f"chat_history_{session_id}"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = session.chat_history if session.chat_history else []
            
            # Display chat messages
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state[chat_key]:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
            
            # Chat input
            if prompt := st.chat_input(f"Chat with your study assistant about {session.name}..."):
                # Add user message to chat
                user_msg = {"role": "user", "content": prompt}
                st.session_state[chat_key].append(user_msg)
                
                # Get AI response
                try:
                    assistant = get_assistant_agent()
                    response = assistant.chat(
                        prompt,
                        context={
                            "session_name": session.name,
                            "session_goal": session.preferences.get("goal", ""),
                            "session_context": session.preferences.get("context", ""),
                            "session_difficulty": session.preferences.get("difficulty", ""),
                            "syllabus": session.preferences.get("syllabus", None)
                        }
                    )
                    
                    # Add assistant message to chat
                    assistant_msg = {"role": "assistant", "content": response}
                    st.session_state[chat_key].append(assistant_msg)
                    
                    # Save chat history to session
                    session_manager.add_chat_message(st.session_state.user, session_id, user_msg)
                    session_manager.add_chat_message(st.session_state.user, session_id, assistant_msg)
                    
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error in chat: {str(e)}")
                    st.error("Failed to get response from assistant. Please try again.")
                
    except Exception as e:
        logger.error(f"Error displaying session: {str(e)}")
        st.error("An error occurred while displaying the session. Please try again.")
        return

# Main App Logic
if not st.session_state.is_authenticated:
    show_login_form()
else:
    # Show logout button in sidebar
    show_logout_button()
    
    # Main App Title with User's Name
    st.title(f"Welcome to LearnMate, {st.session_state.user_preferences['name'] or st.session_state.user}!")
    
    # Add buttons to update preferences and create sessions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Set/Update General Preferences", key="update_preferences_button"):
            st.session_state.show_preferences_modal = True
            st.session_state.preferences_source = "button"
    with col2:
        if st.button("Create New Study Session", key="create_session_main_button"):
            st.session_state.show_session_modal = True
    
    # Show preferences modal if not set and not skipped
    if st.session_state.is_authenticated and not st.session_state.user_preferences["has_set_preferences"]:
        st.session_state.show_preferences_modal = True
        st.session_state.preferences_source = "initial"
    
    # Show the modals if needed
    if st.session_state.show_preferences_modal:
        show_general_preferences_modal()
    
    if st.session_state.show_session_modal:
        editing_session_id = getattr(st.session_state, 'editing_session', None)
        show_session_preferences_modal(editing_session_id)
        if editing_session_id:
            st.session_state.editing_session = None
        # Reset form timestamp after showing the form
        st.session_state.form_timestamp = None
    
    # First, update the session list in the sidebar
    show_session_list()
    
    # Get the latest list of sessions
    current_sessions = session_manager.get_user_sessions(st.session_state.user)
    
    # Display sessions in tabs only if we have valid sessions
    if current_sessions:
        st.header("Your Study Sessions")
        
        # Create tabs for each session
        session_names = [session.name for session in current_sessions]
        session_tabs = st.tabs(session_names)
        
        # Display each session in its tab
        for i, session in enumerate(current_sessions):
            with session_tabs[i]:
                try:
                    # Verify the session still exists before displaying
                    current_session = session_manager.get_session(st.session_state.user, session.session_id)
                    if current_session:
                        display_session(session.session_id)
                    else:
                        # If session doesn't exist, force a page refresh
                        st.warning("This session has been deleted.")
                        if "current_sessions" in st.session_state:
                            del st.session_state.current_sessions
                        st.rerun()
                except Exception as e:
                    logger.error(f"Error displaying session {session.session_id}: {str(e)}")
                    st.error("Error displaying this session. It may have been deleted.")
                    st.rerun()
    else:
        st.info("You don't have any study sessions yet. Create one to get started!")
    
    # Display session preferences modal if needed
    if st.session_state.show_session_preferences:
        show_session_preferences_modal()
