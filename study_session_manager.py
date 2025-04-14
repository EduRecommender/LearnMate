import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

class StudySessionManager:
    def __init__(self):
        self.sessions_file = "data/study_sessions.json"
        self._ensure_sessions_file_exists()
    
    def _ensure_sessions_file_exists(self):
        """Ensure the sessions file exists and create it if it doesn't."""
        os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w') as f:
                json.dump({}, f)
    
    def create_session(self, username, session_name, session_preferences):
        """Create a new study session for a user."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions:
            sessions[username] = {}
        
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        sessions[username][session_id] = {
            "name": session_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "preferences": session_preferences,
            "materials": [],
            "notes": [],
            "progress": 0
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
        
        return session_id
    
    def get_user_sessions(self, username):
        """Get all study sessions for a user."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions:
            return {}
        
        return sessions[username]
    
    def get_session(self, username, session_id):
        """Get a specific study session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions or session_id not in sessions[username]:
            return None
        
        return sessions[username][session_id]
    
    def update_session(self, username, session_id, updates):
        """Update a study session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions or session_id not in sessions[username]:
            return False, "Session not found"
        
        for key, value in updates.items():
            if key == "preferences":
                sessions[username][session_id]["preferences"].update(value)
            else:
                sessions[username][session_id][key] = value
        
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
        
        return True, "Session updated successfully"
    
    def add_material(self, username, session_id, material):
        """Add a learning material to a session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions or session_id not in sessions[username]:
            return False, "Session not found"
        
        sessions[username][session_id]["materials"].append({
            "title": material.get("title", ""),
            "type": material.get("type", ""),
            "url": material.get("url", ""),
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
        
        return True, "Material added successfully"
    
    def add_note(self, username, session_id, note):
        """Add a note to a session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions or session_id not in sessions[username]:
            return False, "Session not found"
        
        sessions[username][session_id]["notes"].append({
            "content": note,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
        
        return True, "Note added successfully"
    
    def update_progress(self, username, session_id, progress):
        """Update the progress of a session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions or session_id not in sessions[username]:
            return False, "Session not found"
        
        sessions[username][session_id]["progress"] = progress
        
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
        
        return True, "Progress updated successfully"
    
    def delete_session(self, username, session_id):
        """Delete a study session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
        
        if username not in sessions or session_id not in sessions[username]:
            return False, "Session not found"
        
        del sessions[username][session_id]
        
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=4)
        
        return True, "Session deleted successfully" 