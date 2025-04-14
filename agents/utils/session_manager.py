import json
import os
import uuid
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import traceback

from agents.schemas.sessions import StudySession, ChatMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('session_manager.log')
    ]
)
logger = logging.getLogger(__name__)

class SessionManager:
    """Manages study sessions using the StudySession schema"""
    
    def __init__(self, sessions_file: str = "data/study_sessions.json", uploads_dir: str = "data/uploads"):
        self.sessions_file = sessions_file
        self.uploads_dir = uploads_dir
        self.backup_dir = "data/backups"
        logger.info(f"Initializing SessionManager with sessions file: {sessions_file}")
        logger.info(f"Using uploads directory: {uploads_dir}")
        self._ensure_sessions_file()
        self._ensure_uploads_dir()
        self._ensure_backup_dir()
    
    def _ensure_uploads_dir(self):
        """Ensure the uploads directory exists"""
        try:
            logger.debug(f"Ensuring uploads directory exists: {self.uploads_dir}")
            if not os.path.exists(self.uploads_dir):
                os.makedirs(self.uploads_dir)
                logger.info(f"Created uploads directory: {self.uploads_dir}")
        except Exception as e:
            logger.error(f"Error creating uploads directory: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to create uploads directory: {str(e)}")
    
    def _ensure_backup_dir(self):
        """Ensure the backup directory exists"""
        try:
            logger.debug(f"Ensuring backup directory exists: {self.backup_dir}")
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
                logger.info(f"Created backup directory: {self.backup_dir}")
        except Exception as e:
            logger.error(f"Error creating backup directory: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _ensure_sessions_file(self):
        """Ensure the sessions file exists"""
        try:
            logger.debug(f"Ensuring sessions file exists: {self.sessions_file}")
            # Create parent directory if it doesn't exist
            parent_dir = os.path.dirname(self.sessions_file)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
                logger.info(f"Created parent directory: {parent_dir}")
                
            if not os.path.exists(self.sessions_file):
                logger.info(f"Creating empty sessions file: {self.sessions_file}")
                with open(self.sessions_file, "w") as f:
                    json.dump({}, f)
        except Exception as e:
            logger.error(f"Error creating sessions file: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to create sessions file: {str(e)}")
    
    def _create_backup(self):
        """Create a backup of the sessions file"""
        try:
            if os.path.exists(self.sessions_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(self.backup_dir, f"sessions_{timestamp}.json")
                logger.info(f"Creating backup of sessions file: {backup_file}")
                shutil.copy2(self.sessions_file, backup_file)
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _load_sessions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load sessions from file"""
        try:
            logger.debug(f"Loading sessions from file: {self.sessions_file}")
            with open(self.sessions_file, "r") as f:
                sessions = json.load(f)
                logger.debug(f"Loaded {sum(len(user_sessions) for user_sessions in sessions.values())} sessions for {len(sessions)} users")
                return sessions
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding sessions JSON: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create a backup of the corrupt file
            if os.path.exists(self.sessions_file):
                corrupt_file = f"{self.sessions_file}.corrupt"
                logger.warning(f"Creating backup of corrupt file: {corrupt_file}")
                shutil.copy2(self.sessions_file, corrupt_file)
            
            logger.info("Returning empty sessions dictionary")
            return {}
        except Exception as e:
            logger.error(f"Error loading sessions: {str(e)}")
            logger.error(traceback.format_exc())
            return {}
    
    def _save_sessions(self, sessions: Dict[str, List[Dict[str, Any]]]):
        """Save sessions to file"""
        try:
            # Create a backup before saving
            self._create_backup()
            
            logger.debug(f"Saving {sum(len(user_sessions) for user_sessions in sessions.values())} sessions to file")
            # Use a temporary file to avoid corruption if the program crashes
            temp_file = f"{self.sessions_file}.tmp"
            with open(temp_file, "w") as f:
                json.dump(sessions, f, indent=4, default=str)
            
            # Replace the original file with the temporary file
            os.replace(temp_file, self.sessions_file)
            logger.debug("Sessions saved successfully")
        except Exception as e:
            logger.error(f"Error saving sessions: {str(e)}")
            logger.error(traceback.format_exc())
            # If the temporary file exists but wasn't moved, clean it up
            if os.path.exists(f"{self.sessions_file}.tmp"):
                try:
                    os.remove(f"{self.sessions_file}.tmp")
                except:
                    pass
    
    def _convert_legacy_session(self, session_data: Dict[str, Any]) -> Optional[StudySession]:
        """Convert legacy session format to StudySession schema"""
        try:
            session_id = session_data.get("session_id", "unknown")
            logger.debug(f"Converting legacy session: {session_id}")
            
            # Ensure all required fields exist
            required_fields = ["session_id", "user_id", "name", "created_at", "updated_at", "preferences"]
            for field in required_fields:
                if field not in session_data:
                    logger.error(f"Missing required field in session data: {field}")
                    return None

            # Convert timestamp to datetime
            try:
                created_at = datetime.strptime(session_data["created_at"], "%Y-%m-%d %H:%M:%S")
                updated_at = datetime.strptime(session_data["updated_at"], "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                logger.error(f"Error parsing datetime: {e}")
                # Use current time as fallback
                logger.warning("Using current time as fallback for invalid timestamps")
                current_time = datetime.now()
                created_at = current_time
                updated_at = current_time
            
            # Handle chat history conversion if it exists
            chat_history = session_data.get("chat_history", [])
            # Validate chat history format
            validated_chat_history = []
            for msg in chat_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    # Ensure message_id exists
                    if "message_id" not in msg:
                        msg["message_id"] = str(uuid.uuid4())
                    
                    # Ensure timestamp exists
                    if "timestamp" not in msg:
                        msg["timestamp"] = datetime.now().isoformat()
                    
                    validated_chat_history.append(msg)
            
            # Create StudySession object with proper defaults
            return StudySession(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                name=session_data["name"],
                created_at=created_at,
                updated_at=updated_at,
                preferences=session_data.get("preferences", {}),
                materials=session_data.get("materials", []),
                notes=session_data.get("notes", []),
                progress=session_data.get("progress", {}),
                chat_history=validated_chat_history,
                metadata=session_data.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Error converting legacy session: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def create_session(self, user_id: str, name: str, preferences: Dict[str, Any]) -> str:
        """Create a new study session"""
        try:
            logger.info(f"Creating session for user: {user_id}, name: {name}")
            sessions = self._load_sessions()
            
            # Generate session ID using timestamp format
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.debug(f"Generated session ID: {session_id}")
            
            # Create session data
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "name": name,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "preferences": preferences if preferences else {},
                "materials": [],
                "notes": [],
                "progress": {},
                "chat_history": []
            }
            
            # Initialize user's sessions if it doesn't exist
            if user_id not in sessions:
                logger.debug(f"First session for user: {user_id}")
                sessions[user_id] = []
            
            # Add to user's sessions
            sessions[user_id].append(session_data)
            
            # Save updated sessions
            self._save_sessions(sessions)
            
            logger.info(f"Created session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def get_user_sessions(self, user_id: str) -> List[StudySession]:
        """Get all sessions for a user"""
        try:
            logger.info(f"Getting sessions for user: {user_id}")
            sessions = self._load_sessions()
            user_sessions = sessions.get(user_id, [])
            logger.debug(f"Found {len(user_sessions)} sessions for user: {user_id}")
            
            # Convert each session, filtering out None results
            converted_sessions = []
            for session in user_sessions:
                converted = self._convert_legacy_session(session)
                if converted:
                    converted_sessions.append(converted)
                else:
                    logger.warning(f"Failed to convert session: {session.get('session_id', 'unknown')}")
            
            logger.info(f"Returning {len(converted_sessions)} valid sessions for user: {user_id}")
            return converted_sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def get_session(self, user_id: str, session_id: str) -> Optional[StudySession]:
        """Get a specific session"""
        try:
            logger.info(f"Getting session {session_id} for user: {user_id}")
            sessions = self._load_sessions()
            user_sessions = sessions.get(user_id, [])
            
            for session in user_sessions:
                if session["session_id"] == session_id:
                    logger.debug(f"Found session: {session_id}")
                    converted = self._convert_legacy_session(session)
                    if converted:
                        return converted
                    else:
                        logger.warning(f"Failed to convert session: {session_id}")
                        return None
            
            logger.warning(f"Session not found: {session_id} for user: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def update_session(self, user_id: str, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update a session"""
        try:
            logger.info(f"Updating session {session_id} for user: {user_id}")
            logger.debug(f"Updates: {updates}")
            
            sessions = self._load_sessions()
            user_sessions = sessions.get(user_id, [])
            
            for i, session in enumerate(user_sessions):
                if session["session_id"] == session_id:
                    # Update session data
                    session["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Handle deeply nested updates
                    for key, value in updates.items():
                        if key == "preferences" and isinstance(value, dict) and isinstance(session.get("preferences"), dict):
                            # Merge preferences instead of overwriting
                            for pref_key, pref_value in value.items():
                                session["preferences"][pref_key] = pref_value
                        elif key == "progress" and isinstance(value, dict) and isinstance(session.get("progress"), dict):
                            # Merge progress instead of overwriting
                            for prog_key, prog_value in value.items():
                                session["progress"][prog_key] = prog_value
                        else:
                            # Direct assignment for other fields
                            session[key] = value
                    
                    # Save updated sessions
                    self._save_sessions(sessions)
                    logger.info(f"Successfully updated session: {session_id}")
                    return True
            
            logger.warning(f"Session not found for update: {session_id} for user: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a session"""
        try:
            logger.info(f"Deleting session {session_id} for user: {user_id}")
            sessions = self._load_sessions()
            user_sessions = sessions.get(user_id, [])
            
            # Find and remove session
            for i, session in enumerate(user_sessions):
                if session["session_id"] == session_id:
                    user_sessions.pop(i)
                    sessions[user_id] = user_sessions
                    
                    # Save updated sessions
                    self._save_sessions(sessions)
                    logger.info(f"Successfully deleted session: {session_id}")
                    return True
            
            logger.warning(f"Session not found for deletion: {session_id} for user: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def add_chat_message(self, user_id: str, session_id: str, message: Dict[str, str]) -> bool:
        """Add a chat message to a session"""
        try:
            logger.info(f"Adding chat message to session {session_id} for user: {user_id}")
            logger.debug(f"Message: {message}")
            
            sessions = self._load_sessions()
            user_sessions = sessions.get(user_id, [])
            
            for session in user_sessions:
                if session["session_id"] == session_id:
                    # Initialize chat_history if it doesn't exist
                    if "chat_history" not in session:
                        session["chat_history"] = []
                    
                    # Validate message format
                    if not isinstance(message, dict) or "role" not in message or "content" not in message:
                        logger.warning(f"Invalid message format: {message}")
                        return False
                    
                    # Ensure message_id exists
                    if "message_id" not in message:
                        message["message_id"] = str(uuid.uuid4())
                        logger.debug(f"Generated message ID: {message['message_id']}")
                    
                    # Ensure timestamp exists
                    if "timestamp" not in message:
                        message["timestamp"] = datetime.now().isoformat()
                    
                    # Add message to chat history
                    session["chat_history"].append(message)
                    session["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Save updated sessions
                    self._save_sessions(sessions)
                    logger.info(f"Successfully added message to session: {session_id}")
                    return True
            
            logger.warning(f"Session not found for adding message: {session_id} for user: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding chat message: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def clear_chat_history(self, user_id: str, session_id: str) -> bool:
        """Clear chat history for a session"""
        try:
            logger.info(f"Clearing chat history for session {session_id}, user: {user_id}")
            sessions = self._load_sessions()
            user_sessions = sessions.get(user_id, [])
            
            for session in user_sessions:
                if session["session_id"] == session_id:
                    # Create a backup of the chat history
                    if "chat_history" in session and session["chat_history"]:
                        try:
                            history_backup_dir = os.path.join(self.backup_dir, "chat_history")
                            os.makedirs(history_backup_dir, exist_ok=True)
                            
                            backup_file = os.path.join(
                                history_backup_dir, 
                                f"chat_history_{user_id}_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            )
                            
                            with open(backup_file, "w") as f:
                                json.dump(session["chat_history"], f, indent=4, default=str)
                            
                            logger.info(f"Created chat history backup: {backup_file}")
                        except Exception as e:
                            logger.warning(f"Failed to backup chat history: {str(e)}")
                    
                    # Clear chat history
                    session["chat_history"] = []
                    session["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Save updated sessions
                    self._save_sessions(sessions)
                    logger.info(f"Successfully cleared chat history for session: {session_id}")
                    return True
            
            logger.warning(f"Session not found for clearing chat history: {session_id} for user: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error clearing chat history: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _save_uploaded_file(self, file, user_id: str, session_id: str) -> Dict[str, str]:
        """Save an uploaded file and return its metadata"""
        try:
            # Create user and session directories if they don't exist
            user_dir = os.path.join(self.uploads_dir, user_id)
            session_dir = os.path.join(user_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_filename = getattr(file, 'filename', 'untitled')
            file_ext = os.path.splitext(original_filename)[1]
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
            file_path = os.path.join(session_dir, unique_filename)
            
            logger.info(f"Saving uploaded file: {original_filename} to {file_path}")
            
            # Save the file
            if hasattr(file, 'read'):
                # For file-like objects (e.g., from FastAPI)
                with open(file_path, 'wb') as f:
                    f.write(file.read())
            else:
                # For path strings (e.g., local files)
                shutil.copy2(file, file_path)
            
            # Return file metadata
            return {
                "original_name": original_filename,
                "path": file_path,
                "uploaded_at": datetime.now().isoformat(),
                "size": os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            logger.error(traceback.format_exc())
            raise 