import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UserPreferencesManager:
    """Manages user preferences and learning profiles"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.preferences_file = os.path.join(data_dir, "user_preferences.json")
        self._ensure_data_dir()
        self._ensure_preferences_file()
    
    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _ensure_preferences_file(self):
        """Ensure the preferences file exists"""
        if not os.path.exists(self.preferences_file):
            with open(self.preferences_file, 'w') as f:
                json.dump({}, f)
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get preferences for a specific user"""
        try:
            preferences = self._load_preferences()
            return preferences.get(user_id, self._get_default_preferences())
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return self._get_default_preferences()
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update preferences for a specific user"""
        try:
            # Load existing preferences
            all_preferences = self._load_preferences()
            
            # Update user preferences
            all_preferences[user_id] = preferences
            
            # Save updated preferences
            self._save_preferences(all_preferences)
            
            return True
        except Exception as e:
            logger.error(f"Error updating user preferences: {str(e)}")
            return False
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
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
    
    def _load_preferences(self) -> Dict[str, Dict[str, Any]]:
        """Load preferences from file"""
        try:
            with open(self.preferences_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading preferences: {str(e)}")
            return {}
    
    def _save_preferences(self, preferences: Dict[str, Dict[str, Any]]):
        """Save preferences to file"""
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(preferences, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving preferences: {str(e)}")
            raise 