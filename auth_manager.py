import streamlit as st
import pandas as pd
import os
import hashlib
import json
from datetime import datetime

class AuthManager:
    def __init__(self):
        self.users_file = "data/users.json"
        self.sessions_file = "data/sessions.json"
        self._ensure_data_directory()
        self._load_users()
        self._load_sessions()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        os.makedirs("data", exist_ok=True)
        
        # Create users file if it doesn't exist
        if not os.path.exists(self.users_file):
            with open(self.users_file, "w") as f:
                json.dump({}, f)
        
        # Create sessions file if it doesn't exist
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, "w") as f:
                json.dump({}, f)
    
    def _load_users(self):
        """Load users from the JSON file."""
        with open(self.users_file, "r") as f:
            self.users = json.load(f)
    
    def _load_sessions(self):
        """Load active sessions from the JSON file."""
        with open(self.sessions_file, "r") as f:
            self.sessions = json.load(f)
    
    def _save_users(self):
        """Save users to the JSON file."""
        with open(self.users_file, "w") as f:
            json.dump(self.users, f, indent=4)
    
    def _save_sessions(self):
        """Save active sessions to the JSON file."""
        with open(self.sessions_file, "w") as f:
            json.dump(self.sessions, f, indent=4)
    
    def _hash_password(self, password):
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password, email=None):
        """Register a new user."""
        if username in self.users:
            return False, "Username already exists"
        
        # Initialize user preferences with default values
        default_preferences = {
            "name": "",
            "level": "Not Set",
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
        
        self.users[username] = {
            "password": self._hash_password(password),
            "email": email,
            "preferences": default_preferences,
            "created_at": datetime.now().isoformat()
        }
        self._save_users()
        return True, "User registered successfully"
    
    def login_user(self, username, password):
        """Login a user and create a session."""
        if username not in self.users:
            return False, "User not found"
        
        if self.users[username]["password"] != self._hash_password(password):
            return False, "Invalid password"
        
        # Create a new session
        session_id = hashlib.sha256(f"{username}{datetime.now().isoformat()}".encode()).hexdigest()
        self.sessions[session_id] = {
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        self._save_sessions()
        
        return True, session_id
    
    def logout_user(self):
        """Logout the current user."""
        if "session_id" in st.session_state:
            session_id = st.session_state.session_id
            if session_id in self.sessions:
                del self.sessions[session_id]
                self._save_sessions()
            del st.session_state.session_id
        st.session_state.is_authenticated = False
        st.session_state.user = None
    
    def check_session(self, session_id):
        """Check if a session is valid."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Update last active timestamp
            session["last_active"] = datetime.now().isoformat()
            self._save_sessions()
            return True, session["username"]
        return False, None
    
    def update_user_preferences(self, username, preferences):
        """Update user preferences."""
        if username in self.users:
            self.users[username]["preferences"] = preferences
            self._save_users()
            return True
        return False
    
    def get_user_preferences(self, username):
        """Get user preferences."""
        if username in self.users:
            # Get existing preferences or empty dict if none exist
            existing_preferences = self.users[username].get("preferences", {})
            
            # Define default preferences
            default_preferences = {
                "name": "",
                "level": "Not Set",
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
            
            # Merge existing preferences with defaults
            complete_preferences = default_preferences.copy()
            complete_preferences.update(existing_preferences)
            
            return complete_preferences
        return {} 