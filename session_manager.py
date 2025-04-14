import json
import os
from datetime import datetime

class SessionManager:
    def __init__(self, json_path="user_sessions.json"):
        self.json_path = json_path
        self._initialize_json()

    def _initialize_json(self):
        if not os.path.exists(self.json_path):
            with open(self.json_path, 'w') as f:
                json.dump({"sessions": {}}, f)

    def create_session(self, session_id):
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        if session_id not in data["sessions"]:
            data["sessions"][session_id] = {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "chat_history": [],
                "uploaded_files": [],
                "recommendations": [],
                "preferences": {},
                "syllabus_data": None
            }
            self._save_json(data)

    def update_session(self, session_id, updates):
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        if session_id in data["sessions"]:
            data["sessions"][session_id].update(updates)
            data["sessions"][session_id]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_json(data)

    def get_session(self, session_id):
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        return data["sessions"].get(session_id)

    def add_chat_message(self, session_id, role, content):
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        if session_id in data["sessions"]:
            if "chat_history" not in data["sessions"][session_id]:
                data["sessions"][session_id]["chat_history"] = []
            
            data["sessions"][session_id]["chat_history"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            data["sessions"][session_id]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_json(data)

    def add_uploaded_file(self, session_id, file_info):
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        if session_id in data["sessions"]:
            if "uploaded_files" not in data["sessions"][session_id]:
                data["sessions"][session_id]["uploaded_files"] = []
            
            data["sessions"][session_id]["uploaded_files"].append({
                "filename": file_info.get("filename"),
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_type": file_info.get("type"),
                "size": file_info.get("size")
            })
            data["sessions"][session_id]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_json(data)

    def add_recommendation(self, session_id, recommendation_data):
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        if session_id in data["sessions"]:
            if "recommendations" not in data["sessions"][session_id]:
                data["sessions"][session_id]["recommendations"] = []
            
            data["sessions"][session_id]["recommendations"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": recommendation_data
            })
            data["sessions"][session_id]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_json(data)

    def _save_json(self, data):
        with open(self.json_path, 'w') as f:
            json.dump(data, f, indent=4)

    def get_all_sessions(self):
        with open(self.json_path, 'r') as f:
            return json.load(f)["sessions"] 