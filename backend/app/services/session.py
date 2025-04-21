from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import UploadFile
import os
import aiofiles
from datetime import datetime
import uuid
import json

from ..models.user import StudySession, DifficultyLevel, Resource, ResourceType
from ..schemas.user import StudySessionCreate, StudySessionUpdate, ResourceCreate, ChatMessageCreate, ChatMessage
from ..core.config import settings

class SessionService:
    @staticmethod
    def get_session(db: Session, session_id: int) -> Optional[StudySession]:
        """Get a study session by ID."""
        session = db.query(StudySession).filter(StudySession.id == session_id).first()
        return SessionService._ensure_session_safe(session)

    @staticmethod
    def get_user_sessions(
        db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[StudySession]:
        """Get all study sessions for a user."""
        sessions = (
            db.query(StudySession)
            .filter(StudySession.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Sanitize each session before returning
        for session in sessions:
            SessionService._ensure_session_safe(session)
            
        return sessions

    @staticmethod
    def create_session(
        db: Session, user_id: int, session_in: StudySessionCreate
    ) -> StudySession:
        """Create a new study session."""
        db_session = StudySession(
            user_id=user_id,
            name=session_in.name,
            field_of_study=session_in.field_of_study,
            study_goal=session_in.study_goal,
            context=session_in.context,
            time_commitment=session_in.time_commitment,
            difficulty_level=session_in.difficulty_level,
            preferences=session_in.preferences,
            progress=session_in.progress,
            syllabus=session_in.syllabus,
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # Sanitize before returning
        return SessionService._ensure_session_safe(db_session)

    @staticmethod
    def update_session(
        db: Session, session_id: int, session_in: StudySessionUpdate
    ) -> Optional[StudySession]:
        """Update a study session."""
        db_session = SessionService.get_session(db, session_id)
        if not db_session:
            return None

        update_data = session_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_session, field, value)

        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # Already sanitized by get_session, but sanitize again to be safe
        return SessionService._ensure_session_safe(db_session)

    @staticmethod
    def delete_session(db: Session, session_id: int) -> bool:
        """Delete a study session."""
        db_session = SessionService.get_session(db, session_id)
        if not db_session:
            return False
        
        # Delete associated resources first
        for resource in db_session.resources:
            SessionService.delete_resource(db, resource.id)
        
        db.delete(db_session)
        db.commit()
        return True

    @staticmethod
    def _sanitize_metadata(metadata):
        """Sanitize metadata to ensure it's always a dictionary, never a MetaData object."""
        try:
            print(f"Sanitizing metadata of type: {type(metadata).__name__}")
            print(f"Metadata repr: {repr(metadata)}")
            
            if metadata is None:
                print("  Metadata is None, returning empty dict")
                return {}
            
            if not isinstance(metadata, dict):
                print("  Metadata is not a dict, attempting conversion")
                try:
                    # Check for SQLAlchemy MetaData objects
                    metadata_type = type(metadata).__name__
                    print(f"  Metadata type name: {metadata_type}")
                    
                    if hasattr(metadata, '_sa_instance_state'):
                        print("  Found _sa_instance_state attribute")
                        return {}
                        
                    if metadata_type == 'MetaData' or 'MetaData' in metadata_type:
                        print("  Found MetaData in type name")
                        return {}
                        
                    # Try standard dict conversion
                    try:
                        print("  Attempting dict() conversion")
                        result = dict(metadata)
                        print(f"  Conversion successful: {result}")
                        return result
                    except (TypeError, ValueError) as e:
                        print(f"  Dict conversion failed: {str(e)}")
                        
                    # Try to extract __dict__ if available
                    if hasattr(metadata, '__dict__'):
                        print("  Found __dict__, using that")
                        return metadata.__dict__
                    
                    print("  All conversion attempts failed, returning empty dict")
                    return {}
                    
                except Exception as e:
                    print(f"  Exception in metadata conversion: {str(e)}")
                    return {}
            
            print("  Metadata is already a dict, returning as is")
            return metadata
            
        except Exception as e:
            print(f"CRITICAL: Exception in _sanitize_metadata: {str(e)}")
            return {}
        
    @staticmethod
    def _ensure_resource_safe(resource):
        """Ensure a resource is safe for serialization by Pydantic."""
        if resource is None:
            return None
            
        try:
            print(f"Ensuring resource is safe for serialization - ID: {resource.id}, Name: {resource.name}")
            
            # Handle resource_metadata - critical field that causes serialization errors
            if hasattr(resource, 'resource_metadata'):
                print(f"  Resource has resource_metadata")
                metadata_type = type(resource.resource_metadata).__name__
                print(f"  Original metadata type: {metadata_type}")
                
                # Handle explicit MetaData case
                if metadata_type == 'MetaData' or 'MetaData' in metadata_type:
                    print(f"  CRITICAL: Found direct MetaData object!")
                    resource.resource_metadata = {}
                    return resource
                
                # Use our sanitization method for normal cases
                resource.resource_metadata = SessionService._sanitize_metadata(resource.resource_metadata)
                print(f"  After sanitization, metadata type: {type(resource.resource_metadata).__name__}")
                
            return resource
            
        except Exception as e:
            print(f"CRITICAL ERROR in _ensure_resource_safe: {str(e)}")
            if hasattr(resource, 'resource_metadata'):
                resource.resource_metadata = {}
            return resource
        
    @staticmethod
    def _ensure_session_safe(session):
        """Ensure a session and all its resources are safe for serialization."""
        if session is None:
            return None
            
        # Handle all resources in the session
        if hasattr(session, 'resources') and session.resources:
            for resource in session.resources:
                SessionService._ensure_resource_safe(resource)
                
        return session

    @staticmethod
    def get_resource(db: Session, resource_id: int) -> Optional[Resource]:
        """Get a resource by ID."""
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if resource:
            return SessionService._ensure_resource_safe(resource)
        return None

    @staticmethod
    async def upload_resource(db: Session, resource_in: ResourceCreate, file: UploadFile) -> Resource:
        """Upload a resource file and create a resource record."""
        # Generate a unique filename to prevent collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        upload_dir = os.path.join("uploads", "resources")
        
        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, unique_filename)
        try:
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
        except Exception as e:
            # Clean up the file if it was created
            if os.path.exists(file_path):
                os.remove(file_path)
            raise Exception(f"Failed to save file: {str(e)}")

        # Create resource record
        try:
            # Ensure resource_metadata is a dictionary
            metadata = resource_in.resource_metadata
            if metadata is None:
                metadata = {"content_type": file.content_type}
            elif not isinstance(metadata, dict):
                try:
                    metadata = dict(metadata)
                except (TypeError, ValueError):
                    metadata = {}
                metadata["content_type"] = file.content_type
            else:
                metadata["content_type"] = file.content_type
                
            resource = Resource(
                session_id=resource_in.session_id,
                name=resource_in.name,
                path=file_path,
                type=resource_in.type,
                content=resource_in.content,
                resource_metadata=metadata
            )
            db.add(resource)
            db.commit()
            db.refresh(resource)
            # Ensure the resource_metadata is a dictionary before returning
            return SessionService._ensure_resource_safe(resource)
        except Exception as e:
            # Clean up the file if the database operation fails
            if os.path.exists(file_path):
                os.remove(file_path)
            db.rollback()
            raise Exception(f"Failed to create resource record: {str(e)}")

    @staticmethod
    def delete_resource(db: Session, resource_id: int) -> bool:
        """Delete a resource and its associated file."""
        resource = SessionService.get_resource(db, resource_id)
        if not resource:
            return False

        # Delete file if it exists
        if resource.path and os.path.exists(resource.path):
            try:
                os.remove(resource.path)
            except OSError:
                pass  # Ignore file deletion errors

        db.delete(resource)
        db.commit()
        return True

    # Chat methods
    @staticmethod
    def get_chat_history(db: Session, session_id: int) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        session = SessionService.get_session(db, session_id)
        if not session:
            return []
        
        # If chat_history doesn't exist in session_metadata, initialize it
        if not session.session_metadata:
            session.session_metadata = {}
        
        chat_history = session.session_metadata.get("chat_history", [])
        return chat_history
    
    @staticmethod
    def add_chat_message(db: Session, session_id: int, message: ChatMessageCreate) -> Dict[str, Any]:
        """Add a message to the session's chat history."""
        session = SessionService.get_session(db, session_id)
        if not session:
            raise ValueError("Session not found")
        
        # Initialize session_metadata and chat_history if they don't exist
        if not session.session_metadata:
            session.session_metadata = {}
        
        if "chat_history" not in session.session_metadata:
            session.session_metadata["chat_history"] = []
        
        # Convert message to dictionary
        message_dict = {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "metadata": message.metadata or {}
        }
        
        # Add message to chat history
        session.session_metadata["chat_history"].append(message_dict)
        
        # Save changes
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return message_dict
    
    @staticmethod
    def clear_chat_history(db: Session, session_id: int) -> bool:
        """Clear chat history for a session."""
        session = SessionService.get_session(db, session_id)
        if not session:
            return False
        
        # Initialize session_metadata if it doesn't exist
        if not session.session_metadata:
            session.session_metadata = {}
        
        # Clear chat history
        session.session_metadata["chat_history"] = []
        
        # Save changes
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return True

    @staticmethod
    def ensure_session_resources_metadata(session):
        """Ensure all resources in a session have properly formatted metadata."""
        if session and hasattr(session, 'resources'):
            for resource in session.resources:
                SessionService._ensure_resource_safe(resource)
        return session 