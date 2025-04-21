"""
Data fetcher utility to retrieve user information, preferences, and session data
from the backend to enhance agent context
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional

# Add paths to import from backend
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend'))
if backend_path not in sys.path:
    sys.path.append(backend_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackendDataFetcher:
    """Utility to fetch data from the backend to enhance agent context"""
    
    def __init__(self, user_id: Optional[str] = None, session_id: Optional[int] = None):
        self.user_id = user_id
        self.session_id = session_id
        self._init_managers()
    
    def _init_managers(self):
        """Initialize manager classes to access data"""
        try:
            # Import managers from the main app
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            
            # Try direct imports first
            try:
                from user_preferences_manager import UserPreferencesManager
                from study_session_manager import StudySessionManager
                self.preferences_manager = UserPreferencesManager()
                self.session_manager = StudySessionManager()
                logger.info("Successfully imported managers from main app")
            except ImportError:
                # If direct imports fail, try importing from backend
                try:
                    from app.services.user import UserService
                    from app.services.session import SessionService
                    self.user_service = UserService()
                    self.session_service = SessionService()
                    logger.info("Successfully imported services from backend")
                except ImportError as e:
                    logger.error(f"Failed to import services: {e}")
                    self.user_service = None
                    self.session_service = None
        except Exception as e:
            logger.error(f"Error initializing data fetcher: {e}")
            raise
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Fetch user preferences"""
        if not self.user_id:
            logger.warning("No user ID provided, returning default preferences")
            return self._get_default_preferences()
        
        try:
            # Try the main app preferences manager first
            if hasattr(self, 'preferences_manager'):
                return self.preferences_manager.get_user_preferences(self.user_id)
            
            # Try the backend user service as fallback
            if hasattr(self, 'user_service'):
                from sqlalchemy.orm import Session
                from app.database import get_db
                db = next(get_db())
                user = self.user_service.get_user_by_id(db, self.user_id)
                if user and hasattr(user, 'preferences'):
                    return user.preferences
            
            # If both approaches fail, check for the preferences file directly
            preferences_file = "user_preferences.json"
            if os.path.exists(preferences_file):
                with open(preferences_file, 'r') as f:
                    preferences = json.load(f)
                    return preferences.get(self.user_id, self._get_default_preferences())
            
            logger.warning("Could not retrieve user preferences, using defaults")
            return self._get_default_preferences()
        except Exception as e:
            logger.error(f"Error fetching user preferences: {e}")
            return self._get_default_preferences()
    
    def get_session_data(self) -> Dict[str, Any]:
        """Fetch study session data"""
        if not self.session_id:
            logger.warning("No session ID provided, returning empty session data")
            return {}
        
        try:
            # Try the main app session manager first
            if hasattr(self, 'session_manager') and self.user_id:
                return self.session_manager.get_session(self.user_id, self.session_id) or {}
            
            # Try the backend session service as fallback
            if hasattr(self, 'session_service'):
                from sqlalchemy.orm import Session
                from app.database import get_db
                db = next(get_db())
                session = self.session_service.get_session(db, self.session_id)
                if session:
                    # Convert SQLAlchemy model to dict
                    return {
                        "id": session.id,
                        "name": session.name,
                        "preferences": session.preferences,
                        "resources": [
                            {
                                "id": r.id,
                                "name": r.name,
                                "type": r.type,
                                "resource_metadata": r.resource_metadata
                            } for r in session.resources
                        ] if hasattr(session, 'resources') else [],
                        "syllabus": session.syllabus
                    }
            
            # If both approaches fail, check for the sessions file directly
            sessions_file = "data/study_sessions.json"
            if os.path.exists(sessions_file) and self.user_id:
                with open(sessions_file, 'r') as f:
                    sessions = json.load(f)
                    return sessions.get(self.user_id, {}).get(str(self.session_id), {})
            
            logger.warning("Could not retrieve session data, returning empty dict")
            return {}
        except Exception as e:
            logger.error(f"Error fetching session data: {e}")
            return {}
    
    def get_syllabus_content(self) -> Dict[str, Any]:
        """Fetch syllabus content from session data"""
        session_data = self.get_session_data()
        
        # Try to get syllabus from session data
        if session_data and 'syllabus' in session_data:
            return session_data['syllabus']
        
        # If session has preferences with syllabus data
        if session_data and 'preferences' in session_data and 'syllabus' in session_data['preferences']:
            return session_data['preferences']['syllabus']
        
        logger.warning("No syllabus found in session data")
        return {"course_name": None, "session_content": []}
    
    def get_session_resources(self) -> List[Dict[str, Any]]:
        """Fetch resources linked to the session"""
        session_data = self.get_session_data()
        
        if session_data and 'resources' in session_data:
            return session_data['resources']
        
        if session_data and 'materials' in session_data:
            return session_data['materials']
        
        logger.warning("No resources found in session data")
        return []
    
    def get_enhanced_context(self) -> Dict[str, Any]:
        """Get all relevant context data for agents"""
        user_preferences = self.get_user_preferences()
        session_data = self.get_session_data()
        syllabus = self.get_syllabus_content()
        resources = self.get_session_resources()
        
        # Combine all data into a comprehensive context
        context = {
            "user": {
                "id": self.user_id,
                "preferences": user_preferences
            },
            "session": {
                "id": self.session_id,
                "data": session_data,
                "syllabus": syllabus,
                "resources": resources
            }
        }
        
        return context
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
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
            "has_set_preferences": False
        } 