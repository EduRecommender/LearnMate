from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Any, List, Optional, Dict
from datetime import datetime
import os
import uuid
import logging
import json
import traceback
import tempfile
import asyncio
import re
import time
import psutil
import requests

from ....database import get_db, SessionLocal
from ....services.session import SessionService
from ....schemas.user import (
    User,
    StudySession as StudySessionSchema,
    StudySessionCreate,
    StudySessionUpdate,
    Resource as ResourceSchema,
    ResourceCreate,
    ChatMessage as ChatMessageSchema,
    ChatMessageCreate,
)
from ....models.user import User as UserModel, Resource, StudySession, ChatMessage
from ....services.user import UserService
from ....services.job_store import job_store
from ....services.study_plan_engine import StudyPlanEngineError, create_engine
from ....core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

start_time = time.time()

# Global variables for tracking Ollama status
ollama_available = False
ollama_last_error = None

# Initialize Ollama if available
try:
    logger.info("Attempting to initialize Ollama model")
    
    # Try importing langchain first
    try:
        # For langchain 0.1.0+ compatibility
        from langchain_community.llms import Ollama
        from langchain.callbacks.manager import CallbackManager
        logger.info("Using langchain_community.llms for Ollama")
    except ImportError:
        # Fallback to older langchain
        try:
            from langchain.llms import Ollama
            from langchain.callbacks.manager import CallbackManager
            logger.info("Using langchain.llms for Ollama")
        except ImportError:
            logger.error("Could not import Ollama from either langchain_community or langchain")
            raise
    
    # Create a regular Ollama model client with compatible parameters
    ollama_llm = Ollama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.7,
        timeout=3600  # 1 hour timeout for Ollama API calls
    )
    
    # Test the connection
    logger.info("Testing Ollama connection with a direct API call...")
    try:
        import requests
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": "Say hello", "stream": False},
            timeout=10
        )
        if response.status_code == 200:
            logger.info(f"✅ Direct API call to Ollama succeeded: {response.status_code}")
            # Print a sample of the response
            logger.info(f"Response sample: {response.json().get('response', '')[:50]}...")
        else:
            logger.error(f"❌ Direct API call to Ollama failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Ollama API returned status code {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error making direct API call to Ollama: {str(e)}")
        
    # Now test the LangChain integration
    logger.info("Testing LangChain Ollama integration...")
    try:
        test_prompt = "hello"
        logger.info(f"Sending test prompt to Ollama via LangChain: '{test_prompt}'")
        
        # Use a try-except to catch any internal errors
        try:
            test_response = ollama_llm.invoke(test_prompt, timeout=10)
            
            # Log the full test response
            logger.info("="*50)
            logger.info("OLLAMA TEST RESPONSE:")
            logger.info("-"*50)
            logger.info(test_response)
            logger.info("-"*50)
            
            # Also log some configuration details
            logger.info(f"Ollama configuration:")
            logger.info(f"- Model: {ollama_llm.model}")
            logger.info(f"- URL: {ollama_llm.base_url}")
            logger.info(f"- Temperature: {ollama_llm.temperature}")
            logger.info(f"- Timeout: {ollama_llm.timeout}")
            logger.info("="*50)
        except Exception as inner_e:
            logger.error(f"❌ Error inside LangChain invoke method: {str(inner_e)}")
            logger.error(traceback.format_exc())
            raise inner_e
            
        # If we get here, the connection was successful
        ollama_available = True
        llama_llm = ollama_llm  # Assign to the global variable
        logger.info("✅ Successfully connected to Ollama")
        
    except Exception as e:
        logger.error(f"❌ Error testing Ollama connection through LangChain: {str(e)}")
        logger.error(f"Make sure Ollama is running with model: {settings.OLLAMA_MODEL}")
        logger.error(traceback.format_exc())
        ollama_available = False
        llama_llm = None
        ollama_last_error = str(e)
        # Reraise to abort initialization
        raise
    
except Exception as e:
    logger.error(f"Error initializing Ollama: {str(e)}")
    logger.error(traceback.format_exc())
    ollama_available = False
    llama_llm = None
    ollama_last_error = str(e)

router = APIRouter()

# Replace the simplified get_current_user with the proper one
get_current_user_simplified = UserService.get_current_user

@router.get("/", response_model=List[StudySessionSchema])
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve study sessions.
    """
    print("\n\n==== STARTING LIST_SESSIONS ====")
    sessions = SessionService.get_user_sessions(db, user_id=current_user.id, skip=skip, limit=limit)
    
    print(f"Found {len(sessions)} sessions")
    for session_idx, session in enumerate(sessions):
        print(f"Session {session_idx} - ID: {session.id}, Name: {session.name}")
        if hasattr(session, 'resources'):
            print(f"  Contains {len(session.resources)} resources")
            for res_idx, resource in enumerate(session.resources):
                print(f"  Resource {res_idx} - ID: {resource.id}, Name: {resource.name}")
                if hasattr(resource, 'resource_metadata'):
                    metadata_type = type(resource.resource_metadata).__name__
                    print(f"    Metadata type: {metadata_type}")
                    print(f"    Is dict: {isinstance(resource.resource_metadata, dict)}")
                    if hasattr(resource.resource_metadata, '__dict__'):
                        print(f"    Has __dict__: {resource.resource_metadata.__dict__}")
                    if hasattr(resource.resource_metadata, '_sa_instance_state'):
                        print(f"    Has _sa_instance_state")
                    
                    # Force conversion to dict or default to empty dict
                    if resource.resource_metadata is None:
                        print(f"    Metadata is None, converting to empty dict")
                        resource.resource_metadata = {}
                    elif not isinstance(resource.resource_metadata, dict):
                        # Type check for SQLAlchemy MetaData
                        metadata_type = type(resource.resource_metadata).__name__
                        if hasattr(resource.resource_metadata, '_sa_instance_state') or metadata_type == 'MetaData':
                            print(f"    WARNING: Converting MetaData ({metadata_type}) to empty dict")
                            resource.resource_metadata = {}
                        else:
                            try:
                                print(f"    Converting non-dict metadata to dict")
                                resource.resource_metadata = dict(resource.resource_metadata)
                            except Exception as e:
                                print(f"    EXCEPTION: Failed to convert metadata to dict: {str(e)}")
                                print(f"    Exception type: {type(e).__name__}")
                                resource.resource_metadata = {}
    
    print("==== RETURNING SESSIONS ====\n\n")
    return sessions

@router.post("/", response_model=StudySessionSchema)
async def create_session(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_in: StudySessionCreate,
) -> Any:
    """
    Create new study session.
    """
    session = SessionService.create_session(db, user_id=current_user.id, session_in=session_in)
    return session

@router.get("/{session_id}", response_model=StudySessionSchema)
async def get_session(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
) -> Any:
    """
    Get study session by ID.
    """
    print(f"\n\n==== STARTING GET_SESSION for ID: {session_id} ====")
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )
        
    print(f"Session ID: {session.id}, Name: {session.name}")
    if hasattr(session, 'resources'):
        print(f"  Contains {len(session.resources)} resources")
        for res_idx, resource in enumerate(session.resources):
            print(f"  Resource {res_idx} - ID: {resource.id}, Name: {resource.name}")
            if hasattr(resource, 'resource_metadata'):
                metadata_type = type(resource.resource_metadata).__name__
                print(f"    Metadata type: {metadata_type}")
                print(f"    Is dict: {isinstance(resource.resource_metadata, dict)}")
                try:
                    print(f"    Dir: {dir(resource.resource_metadata)[:10]}")
                except Exception as e:
                    print(f"    Dir error: {str(e)}")
                    
                if hasattr(resource.resource_metadata, '__dict__'):
                    print(f"    Has __dict__: {resource.resource_metadata.__dict__}")
                if hasattr(resource.resource_metadata, '_sa_instance_state'):
                    print(f"    Has _sa_instance_state")
                
                # Force conversion to dict or default to empty dict
                if resource.resource_metadata is None:
                    print(f"    Metadata is None, converting to empty dict")
                    resource.resource_metadata = {}
                elif not isinstance(resource.resource_metadata, dict):
                    # Type check for SQLAlchemy MetaData
                    metadata_type = type(resource.resource_metadata).__name__
                    print(f"    MetaData direct class check: {metadata_type == 'MetaData'}")
                    print(f"    MetaData 'in' name check: {'MetaData' in metadata_type}")
                    
                    if hasattr(resource.resource_metadata, '_sa_instance_state') or metadata_type == 'MetaData' or 'MetaData' in metadata_type:
                        print(f"    WARNING: Converting MetaData ({metadata_type}) to empty dict in get_session")
                        resource.resource_metadata = {}
                    else:
                        try:
                            print(f"    Converting non-dict metadata to dict in get_session")
                            resource.resource_metadata = dict(resource.resource_metadata)
                        except Exception as e:
                            print(f"    EXCEPTION: Failed to convert metadata to dict in get_session: {str(e)}")
                            print(f"    Exception type: {type(e).__name__}")
                            resource.resource_metadata = {}
    
    print("==== RETURNING SESSION ====\n\n")
    return session

@router.put("/{session_id}", response_model=StudySessionSchema)
async def update_session(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
    session_in: StudySessionUpdate,
) -> Any:
    """
    Update study session.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this session",
        )
    session = SessionService.update_session(db, session_id, session_in)
    return session

@router.delete("/{session_id}")
async def delete_session(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
) -> Any:
    """
    Delete study session.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this session",
        )
    SessionService.delete_session(db, session_id)
    return {"status": "success"}

@router.post("/{session_id}/resources", response_model=ResourceSchema)
async def upload_resource(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
    file: UploadFile = File(...),
) -> Any:
    """
    Upload resource to study session.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this session")

    # Create resource
    resource_in = ResourceCreate(
        session_id=session_id,
        name=file.filename,
        type="file",
        content=None,
        resource_metadata={"content_type": file.content_type}
    )
    
    try:
        resource = await SessionService.upload_resource(db, resource_in, file)
        return resource
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload resource: {str(e)}")

@router.delete("/{session_id}/resources/{resource_id}")
async def delete_resource(
    *,
    db: Session = Depends(get_db),
    session_id: int,
    resource_id: int,
) -> Any:
    """
    Delete resource from study session.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    
    resource = SessionService.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    if resource.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource does not belong to this session",
        )
    
    SessionService.delete_resource(db, resource_id)
    return {"status": "success"}

@router.post("/{session_id}/syllabus", response_model=StudySessionSchema)
async def upload_syllabus(
    *,
    db: Session = Depends(get_db),
    session_id: int,
    file: UploadFile = File(...),
) -> Any:
    """
    Upload syllabus to study session.
    """
    import tempfile
    
    try:
        from app.services.syllabus_processor import process_uploaded_syllabus
        has_processor = True
        logger.info("Syllabus processor imported successfully")
    except ImportError as e:
        has_processor = False
        logger.warning(f"Syllabus processor not available: {str(e)}")
    
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    
    # Save the original PDF file as a resource
    original_resource_in = ResourceCreate(
        session_id=session_id,
        name=file.filename,
        type="file",
        content=None,
        resource_metadata={"content_type": file.content_type, "is_syllabus": True, "is_original": True}
    )
    
    # Need to save to a temporary file to process it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        # Read the content of the uploaded file
        content = await file.read()
        # Write it to the temporary file
        temp_file.write(content)
        temp_file.flush()
        temp_file_path = temp_file.name
    
    try:
        # Store the original PDF file
        # Reset the file position for upload
        await file.seek(0)
        original_resource = await SessionService.upload_resource(db, original_resource_in, file)
        
        # Process the syllabus if processor is available
        syllabus_info = {"resource_id": original_resource.id}
        
        if has_processor:
            try:
                # Process the uploaded syllabus using the temp file path
                syllabus_data = process_uploaded_syllabus(temp_file_path)
                
                # Create a text resource with the processed content
                if syllabus_data and (syllabus_data.get("course_name") or syllabus_data.get("session_content")):
                    # Create a formatted text version of the processed syllabus
                    processed_text = f"# {syllabus_data.get('course_name', 'Unknown Course')}\n\n"
                    processed_text += "## Session Content\n\n"
                    
                    for topic in syllabus_data.get("session_content", []):
                        processed_text += f"- {topic}\n"
                    
                    # Create a text resource with the processed content
                    text_resource_in = ResourceCreate(
                        session_id=session_id,
                        name=f"{os.path.splitext(file.filename)[0]}_processed.txt",
                        type="text",
                        content=processed_text,
                        resource_metadata={
                            "content_type": "text/plain", 
                            "is_syllabus": True,
                            "is_processed": True,
                            "format": "markdown"
                        }
                    )
                    
                    # Create the text resource directly without a file
                    text_resource = Resource(
                        session_id=text_resource_in.session_id,
                        name=text_resource_in.name,
                        type=text_resource_in.type,
                        content=text_resource_in.content,
                        resource_metadata=text_resource_in.resource_metadata
                    )
                    
                    db.add(text_resource)
                    db.commit()
                    db.refresh(text_resource)
                    
                    # Update the syllabus info with the processed data
                    syllabus_info = {
                        "original_resource_id": original_resource.id,
                        "processed_resource_id": text_resource.id,
                        "course_name": syllabus_data.get("course_name", "Unknown Course"),
                        "session_content": syllabus_data.get("session_content", []),
                        "processed": True
                    }
                    
                    logger.info(f"Syllabus processed successfully for session {session_id}")
                else:
                    # No useful data extracted
                    logger.warning(f"No useful data extracted from syllabus for session {session_id}")
                    syllabus_info["processed"] = False
                    syllabus_info["error"] = "No useful data extracted from syllabus"
                
            except Exception as e:
                # If processing fails, still save the syllabus but mark it as not processed
                logger.error(f"Failed to process syllabus: {str(e)}")
                logger.exception("Error details:")
                syllabus_info["processed"] = False
                syllabus_info["error"] = str(e)
        else:
            # If processor is not available, just save the resource ID
            syllabus_info["processed"] = False
            syllabus_info["error"] = "Syllabus processor not available"
        
        # Update the session with the syllabus info
        session.syllabus = syllabus_info
        db.add(session)
        db.commit()
        db.refresh(session)
        
    except Exception as e:
        logger.error(f"Error in syllabus upload: {str(e)}")
        logger.exception("Error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process syllabus: {str(e)}"
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    
    return session

@router.get("/{session_id}/resources/{resource_id}/download")
async def download_resource(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
    resource_id: int,
) -> Any:
    """
    Download a resource file.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )
    
    resource = SessionService.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    if resource.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource does not belong to this session",
        )
    
    if not resource.path or not os.path.exists(resource.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource file not found",
        )
    
    return FileResponse(
        resource.path,
        filename=resource.name,
        media_type=resource.resource_metadata.get('content_type', 'application/octet-stream')
    )

# Chat endpoints
@router.get("/{session_id}/chat", response_model=List[ChatMessageSchema])
async def get_chat_history(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
) -> Any:
    """
    Get chat history for a study session.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )
    
    # Get chat history from the SessionService
    # If no chat history exists, return an empty list
    chat_history = SessionService.get_chat_history(db, session_id) or []
    return chat_history

@router.get("/{session_id}/chat/status/{request_id}", response_model=Dict[str, Any])
async def check_chat_message_status(
    session_id: int,
    request_id: str,
    current_user: User = Depends(get_current_user_simplified),
    db: Session = Depends(get_db),
):
    """Check the status of an asynchronous chat message request"""
    try:
        request_data = job_store.get(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Request not found")
        if request_data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this request")
        if int(request_data["session_id"]) != int(session_id):
            raise HTTPException(status_code=400, detail="Request doesn't match session ID")

        response = {
            "status": request_data["status"],
            "stage": request_data.get("stage"),
            "started_at": request_data["started_at"],
            "updated_at": request_data.get("updated_at"),
        }
        if request_data.get("result"):
            response["result"] = request_data["result"]
        if request_data.get("error"):
            response["error"] = request_data["error"]
        return response
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error checking chat message status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/chat/{request_id}/events")
async def stream_chat_message_events(
    session_id: int,
    request_id: str,
    current_user: User = Depends(get_current_user_simplified),
):
    """Stream stage/status updates for a long-running chat request."""
    request_data = job_store.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Request not found")
    if request_data["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this request")
    if int(request_data["session_id"]) != int(session_id):
        raise HTTPException(status_code=400, detail="Request doesn't match session ID")

    async def event_generator():
        index = 0
        while True:
            events = job_store.events_since(request_id, index)
            for event in events:
                index += 1
                yield f"data: {json.dumps(event)}\n\n"

            latest = job_store.get(request_id)
            if latest and latest.get("status") in {"succeeded", "failed"} and index >= len(latest.get("events", [])):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/{session_id}/chat/start", response_model=Dict[str, Any])
async def start_chat_message_processing(
    session_id: int,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_simplified),
    db: Session = Depends(get_db),
):
    """Start processing a chat message asynchronously"""
    try:
        # Check if session exists and user is authorized
        session = db.query(StudySession).filter(StudySession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
            
        message = request.get("message", "")
        logger.info(f"Starting asynchronous processing for message in session {session_id}")
        request_id = str(uuid.uuid4())
        job_store.create(request_id, session_id=session_id, message=message, user_id=current_user.id)
        logger.info(f"Created request {request_id} for session {session_id}")
        asyncio.create_task(
            process_chat_message_background(
                request_id=request_id,
                session_id=session_id,
                message=message,
                current_user=current_user,
            )
        )
        return {"request_id": request_id, "status": "queued", "stage": "context"}
    except Exception as e:
        logger.error(f"Error starting chat message processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Update the legacy send_message endpoint to use the new system
@router.post("/{session_id}/chat", response_model=Dict[str, Any])
async def send_chat_message(
    session_id: int,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_simplified),
    db: Session = Depends(get_db),
):
    """Send a message to the chat and get a response.
    This endpoint now starts async processing and returns the request ID.
    """
    try:
        message = request.get("message", "")
        logger.info(f"Chat message received for session {session_id}")
        
        start_response = await start_chat_message_processing(
            session_id=session_id,
            request={"message": message},
            current_user=current_user,
            db=db
        )
        request_id = start_response["request_id"]
        await asyncio.sleep(0.5)  # Wait 500ms to see if it completes quickly
        try:
            status_response = await check_chat_message_status(
                session_id=session_id,
                request_id=request_id,
                current_user=current_user,
                db=db
            )
            
            if status_response["status"] == "succeeded" and "result" in status_response:
                return status_response["result"]
        except Exception as check_error:
            logger.error(f"Error checking immediate status: {str(check_error)}")
        return {
            "message_id": f"pending-{request_id}",
            "role": "assistant",
            "content": "Processing your request...",
            "timestamp": datetime.now().isoformat(),
            "is_processing": True,
            "request_id": request_id,
            "status": "queued",
            "stage": "context",
        }
        
    except ValueError as e:
        # Handle known errors with appropriate status codes
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "authorized" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in send_chat_message: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}/chat")
async def clear_chat_history(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
) -> Any:
    """
    Clear chat history for a study session.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to clear chat history for this session",
        )
    
    # Clear chat history
    SessionService.clear_chat_history(db, session_id)
    
    return {"status": "success"}

# Add these helper functions before the send_chat_message_internal function
def check_if_study_plan_request(message: str) -> bool:
    """Check if a message is requesting a study plan"""
    message_lower = message.lower()
    study_plan_keywords = [
        "study plan", "learning plan", "plan for", "create a plan",
        "help me study", "help me prepare", "study schedule",
        "study guide", "study strategy", "learning strategy",
        "make me a plan", "create a study", "plan based on",
        "personalized study", "detailed daily", "daily activities",
        "how should i study", "how to study", "structured plan",
        "schedule for studying", "prepare for exam", "exam preparation",
        "plan my study", "organize my learning", "syllabus plan",
        "prepare for my course", "learning roadmap", "study roadmap"
    ]

    return any(keyword in message_lower for keyword in study_plan_keywords)

def check_if_study_plan_revision(message: str, db: Session, session_id: int) -> tuple:
    """Check if the user is requesting a revision to an existing study plan
    Returns a tuple of (is_revision, difficult_topics, focus_sessions, specific_resources)
    """
    message_lower = message.lower()
    revision_keywords = [
        "revise the plan", "update the plan", "modify the plan", "change the plan",
        "adjust the study plan", "can you modify", "need more time for",
        "don't understand", "struggling with", "having trouble with",
        "need help with", "focus more on", "spend more time on",
        "allocate more time", "prefer different resources", "different approach",
        "too difficult", "too easy", "too much time", "not enough time",
        "better resources", "prefer to use", "would rather use",
    ]

    is_revision = any(keyword in message_lower for keyword in revision_keywords)
    if not is_revision:
        return (False, [], None, [])

    difficult_topics = []
    struggle_phrases = [
        "struggle with", "difficult for me", "having trouble with",
        "not understanding", "confused about", "need help with",
        "problem with", "challenging", "hard to grasp",
        "focus more on", "more time for", "don't understand",
    ]

    for phrase in struggle_phrases:
        if phrase in message_lower:
            topic_start = message_lower.find(phrase) + len(phrase)
            topic_end = message_lower.find(".", topic_start)
            if topic_end == -1:
                for delimiter in [",", "and", "but", "\n", " so "]:
                    pos = message_lower.find(delimiter, topic_start)
                    if pos != -1:
                        topic_end = min(topic_end, pos) if topic_end != -1 else pos

                if topic_end == -1:
                    topic_end = len(message_lower)

            topic = message_lower[topic_start:topic_end].strip()
            if topic and len(topic) < 100:
                difficult_topics.append(topic)

    focus_sessions = None
    session_patterns = [
        r"session\s*(\d+)", r"day\s*(\d+)", r"week\s*(\d+)",
        r"lecture\s*(\d+)", r"module\s*(\d+)",
    ]

    for pattern in session_patterns:
        matches = re.findall(pattern, message_lower)
        if matches:
            focus_sessions = [int(match) for match in matches]
            break

    specific_resources = []
    resources = db.query(Resource).filter(Resource.session_id == session_id).all()

    for resource in resources:
        if resource.name.lower() in message_lower:
            specific_resources.append({
                "id": resource.id,
                "name": resource.name,
                "type": resource.type if hasattr(resource, 'type') else "UNKNOWN",
            })

    resource_types = ["book", "video", "article", "paper", "tutorial", "course", "website"]
    for res_type in resource_types:
        if res_type in message_lower:
            pos = message_lower.find(res_type)
            start = max(0, pos - 30)
            end = min(len(message_lower), pos + 30)
            context = message_lower[start:end]

            already_captured = any(res.get("name", "").lower() in context for res in specific_resources)
            if not already_captured:
                specific_resources.append({
                    "id": None,
                    "name": context.strip(),
                    "type": res_type,
                })

    return (is_revision, difficult_topics, focus_sessions, specific_resources)

def get_ollama_response(session: StudySession, message: str, db: Session) -> str:
    """Get a response from the Ollama API for regular chat messages"""
    try:
        # Add global declaration to access the Ollama model
        global llama_llm
        
        if not llama_llm:
            logger.error("Ollama model is not initialized")
            return "I'm sorry, but the planning service is not available right now. Please try again later."
        
        # Get chat history for context (last 7 messages)
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.timestamp.desc()).limit(7).all()
        
        # Check if this message is asking to revise a study plan
        is_study_plan_revision, difficult_topics, focus_sessions, specific_resources = check_if_study_plan_revision(
            message, db, session.id
        )
        
        # Format chat history for the prompt
        chat_history_text = ""
        if chat_messages:
            # Process in reversed order to get chronological order
            for chat_msg in reversed(chat_messages):
                if chat_msg.role == "user":
                    chat_history_text += f"User: {chat_msg.content}\n"
                else:
                    chat_history_text += f"Assistant: {chat_msg.content}\n"
        
        # Create the appropriate prompt based on conversation context
        if is_study_plan_revision:
            # Find the most recent study plan in the chat history
            study_plan_message = None
            for msg in chat_messages:
                if msg.role == "assistant" and "STUDY PLAN OVERVIEW:" in msg.content:
                    study_plan_message = msg
                    break
            
            # If we found a study plan to revise
            if study_plan_message:
                prompt = f"""SYSTEM: You are an educational assistant helping a student with {session.field_of_study}. 
The student previously received a study plan from you and is now requesting revisions or clarifications.

STUDENT GOAL: {session.study_goal}

PREVIOUS STUDY PLAN:
{study_plan_message.content[:500]}... (truncated for brevity)

REVISION REQUEST:
{message}

KEY ADJUSTMENTS NEEDED:
- Difficult topics identified: {', '.join(difficult_topics) if difficult_topics else 'None specified'}
- Sessions/days to focus on: {focus_sessions if focus_sessions else 'None specified'}
- Specific resources mentioned: {', '.join([res['name'] for res in specific_resources]) if specific_resources else 'None specified'}

Please explain how you would adapt the study plan based on this feedback. Be conversational and helpful.
Do NOT create a full new study plan in this response - just discuss the potential changes and ask if they want you to generate a revised plan.

YOUR RESPONSE:"""
            else:
                # Looks like a revision request but we can't find the original plan
                prompt = f"""SYSTEM: You are an educational assistant helping a student with {session.field_of_study}. 
The student seems to be asking for revisions to a study plan, but I couldn't find the original plan in the chat history.

STUDENT GOAL: {session.study_goal}

CHAT HISTORY:
{chat_history_text}

CURRENT MESSAGE: 
{message}

Respond conversationally, acknowledging their request for revisions. Explain that you need more details about what kind of study plan they want.
Ask if they would like you to create a new study plan based on their current needs. Be helpful and friendly.

YOUR RESPONSE:"""
        else:
            # Regular conversational prompt
            prompt = f"""SYSTEM: You are an educational assistant helping a student with {session.field_of_study}. 
Be helpful, clear, and conversational. Provide specific information relevant to their questions.

STUDENT GOAL: {session.study_goal}

CHAT HISTORY:
{chat_history_text}

CURRENT QUESTION: 
{message}

YOUR RESPONSE:"""
        
        # Log request details
        logger.info(f"Sending chat prompt to Ollama, length: {len(prompt)}")
        
        # Get response from Ollama
        response_text = llama_llm.invoke(prompt)
        logger.info(f"Received response from Ollama, length: {len(response_text)}")
        logger.info(f"Response preview: {response_text[:100]}")
        
        return response_text
    except Exception as e:
        logger.error(f"Error in get_ollama_response: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        return f"I'm sorry, but I couldn't generate a response at this time. Error: {str(e)}"

def get_user_task_context(db: Session, current_user: User, session: StudySession) -> dict:
    """Extract user context from preferences and session data for tasks"""
    try:
        # Get comprehensive user preferences
        user_preferences = {}
        if hasattr(current_user, 'preferences') and current_user.preferences:
            if isinstance(current_user.preferences, str):
                try:
                    user_preferences = json.loads(current_user.preferences)
                except:
                    user_preferences = {"preferences": current_user.preferences}
            else:
                user_preferences = current_user.preferences
        
        logger.info(f"Retrieved user preferences: {user_preferences}")
        
        # Get session-specific preferences
        session_preferences = {}
        if hasattr(session, 'preferences') and session.preferences:
            if isinstance(session.preferences, str):
                try:
                    session_preferences = json.loads(session.preferences)
                except:
                    session_preferences = {"preferences": session.preferences}
            else:
                session_preferences = session.preferences
        
        logger.info(f"Retrieved session preferences: {session_preferences}")
        
        # Get available resources for this session
        resources = []
        db_resources = db.query(Resource).filter(Resource.session_id == session.id).all()
        
        # Track specific resource types
        books = []
        videos = []
        websites = []
        other_resources = []
        
        # Check for syllabus content
        syllabus_content = None
        syllabus_sessions = []
        syllabus_resource = None
        
        # First, try to directly check session.syllabus if available
        if hasattr(session, 'syllabus') and session.syllabus:
            logger.info(f"Session has syllabus attribute: {session.syllabus}")
            try:
                if isinstance(session.syllabus, dict):
                    # Try to get the processed resource ID
                    processed_id = session.syllabus.get('processed_resource_id')
                    original_id = session.syllabus.get('original_resource_id')
                    
                    if processed_id:
                        logger.info(f"Looking for processed syllabus resource with ID: {processed_id}")
                        syllabus_resource = db.query(Resource).filter(Resource.id == processed_id).first()
                    elif original_id:
                        logger.info(f"Looking for original syllabus resource with ID: {original_id}")
                        syllabus_resource = db.query(Resource).filter(Resource.id == original_id).first()
                elif isinstance(session.syllabus, str):
                    try:
                        syllabus_data = json.loads(session.syllabus)
                        if isinstance(syllabus_data, dict):
                            processed_id = syllabus_data.get('processed_resource_id')
                            original_id = syllabus_data.get('original_resource_id')
                            
                            if processed_id:
                                logger.info(f"Looking for processed syllabus resource with ID: {processed_id}")
                                syllabus_resource = db.query(Resource).filter(Resource.id == processed_id).first()
                            elif original_id:
                                logger.info(f"Looking for original syllabus resource with ID: {original_id}")
                                syllabus_resource = db.query(Resource).filter(Resource.id == original_id).first()
                    except:
                        logger.error("Failed to parse syllabus json")
            except Exception as e:
                logger.error(f"Error extracting syllabus from session: {str(e)}")
        
        # Process all resources (even if we already found a syllabus)
        for resource in db_resources:
            resource_data = {
                "id": resource.id,
                "name": resource.name,
                "url": resource.url if hasattr(resource, 'url') else None,
                "type": resource.type if hasattr(resource, 'type') else "UNKNOWN",
                "path": resource.path if hasattr(resource, 'path') else None,
                "content": resource.content if hasattr(resource, 'content') and resource.type == "text" else None,
            }
            
            # Add metadata if available
            if hasattr(resource, 'resource_metadata') and resource.resource_metadata:
                try:
                    if isinstance(resource.resource_metadata, str):
                        try:
                            metadata = json.loads(resource.resource_metadata)
                            resource_data["metadata"] = metadata
                        except:
                            resource_data["metadata"] = {"raw": resource.resource_metadata}
                    else:
                        resource_data["metadata"] = resource.resource_metadata
                except Exception as e:
                    logger.error(f"Error processing resource metadata: {str(e)}")
                    resource_data["metadata"] = {}
                    
                # Check if this is a syllabus resource
                try:
                    is_syllabus = False
                    if isinstance(resource_data["metadata"], dict):
                        is_syllabus = resource_data["metadata"].get('is_syllabus', False)
                    
                    if is_syllabus:
                        logger.info(f"Resource {resource.id} has is_syllabus flag")
                        
                        # If we haven't found a syllabus yet, or this one is processed, prioritize it
                        is_processed = False
                        if isinstance(resource_data["metadata"], dict):
                            is_processed = resource_data["metadata"].get('is_processed', False)
                        
                        if not syllabus_resource or is_processed:
                            logger.info(f"Using resource {resource.id} as syllabus source (processed: {is_processed})")
                            syllabus_resource = resource
                except Exception as e:
                    logger.error(f"Error checking if resource is syllabus: {str(e)}")
            
            # Extract resource type from name or metadata
            resource_name_lower = resource_data["name"].lower()
            
            # Categorize the resource
            if '.pdf' in resource_name_lower or 'book' in resource_name_lower or 'textbook' in resource_name_lower:
                books.append(resource_data)
            elif 'video' in resource_name_lower or 'youtube' in resource_name_lower or '.mp4' in resource_name_lower:
                videos.append(resource_data)
            elif 'website' in resource_name_lower or 'link' in resource_name_lower or '.html' in resource_name_lower:
                websites.append(resource_data)
            else:
                other_resources.append(resource_data)
            
            resources.append(resource_data)
        
        logger.info(f"Found {len(resources)} resources for this session")
        logger.info(f"Resource breakdown: {len(books)} books, {len(videos)} videos, {len(websites)} websites")
        
        # Process syllabus if found
        if syllabus_resource:
            logger.info(f"Processing syllabus resource: {syllabus_resource.id}, {syllabus_resource.name}")
            try:
                # Get the syllabus content
                if hasattr(syllabus_resource, 'content') and syllabus_resource.content:
                    syllabus_content = syllabus_resource.content
                    logger.info(f"Using syllabus content from resource {syllabus_resource.id}")
                elif hasattr(syllabus_resource, 'path') and syllabus_resource.path and os.path.exists(syllabus_resource.path):
                    try:
                        with open(syllabus_resource.path, 'r') as f:
                            syllabus_content = f.read()
                            logger.info(f"Read syllabus content from file {syllabus_resource.path}")
                    except Exception as file_error:
                        logger.error(f"Error reading syllabus file: {str(file_error)}")
                
                # Extract sessions from syllabus content
                if syllabus_content:
                    logger.info(f"Processing syllabus content: {len(syllabus_content)} chars")
                    
                    # Try to extract session information using common patterns
                    session_patterns = [
                        r"(?:Session|Week|Lecture|Module|Topic)\s*(\d+)[\s:]+([^\n]+)",  # Session X: Topic
                        r"(?:Day|Session|Week|Lecture|Module)\s*(\d+)(?:\n|\r\n|\r)([^\n]+)",  # Session X\nTopic
                        r"(\d+)[\.\s]+([^\n]+)"  # 1. Topic
                    ]
                    
                    for pattern in session_patterns:
                        matches = re.findall(pattern, syllabus_content)
                        if matches:
                            for session_num, topic in matches:
                                syllabus_sessions.append({
                                    "session_number": session_num.strip(),
                                    "topic": topic.strip()
                                })
                            
                            logger.info(f"Extracted {len(syllabus_sessions)} sessions from syllabus")
                            break  # Use the first pattern that works
            except Exception as e:
                logger.error(f"Error processing syllabus resource: {str(e)}")
        
        # Get conversation context and user struggles/preferences
        chat_messages = []
        try:
            recent_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
            
            # Extract messages and convert to text
            for msg in reversed(recent_messages):  # Reverse to get chronological order
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp)
                })
            
            logger.info(f"Retrieved {len(chat_messages)} recent chat messages for context")
        except Exception as e:
            logger.error(f"Error retrieving chat messages: {str(e)}")
        
        # Extract user struggles or topic preferences from chat messages
        difficult_topics = []
        for msg in chat_messages:
            if msg["role"] == "user":
                content = msg["content"].lower()
                struggle_phrases = ["struggle with", "difficult for me", "having trouble with", 
                                   "not understanding", "confused about", "need help with",
                                   "problem with", "challenging", "hard to grasp"]
                
                for phrase in struggle_phrases:
                    if phrase in content:
                        # Find the topic after the struggle phrase
                        topic_start = content.find(phrase) + len(phrase)
                        topic_end = content.find(".", topic_start)
                        if topic_end == -1:
                            topic_end = len(content)
                            
                        topic = content[topic_start:topic_end].strip()
                        if topic and len(topic) < 100:  # Reasonable topic length
                            difficult_topics.append(topic)
        
        logger.info(f"Identified difficult topics: {difficult_topics}")
        
        # Build comprehensive user context with all available data
        user_context = {
            # Basic session information
            "subject": session.field_of_study,
            "subject_details": session.name,
            "study_goal": session.study_goal,
            "context": session.context if hasattr(session, 'context') and session.context else "",
            
            # Study time preferences
            "study_days": session_preferences.get("study_days", "5"),
            "hours_per_day": session_preferences.get("hours_per_day", "2"),
            "days_until_exam": session_preferences.get("days_until_exam", "30"),
            
            # Learning preferences
            "learning_style": user_preferences.get("learning_styles", ["visual"])[0] if user_preferences.get("learning_styles") else "visual",
            "preferred_study_methods": user_preferences.get("preferred_study_methods", []),
            "difficulty_level": session_preferences.get("difficulty_level", "intermediate"),
            
            # Resources information
            "resources": resources,
            "books": books,
            "videos": videos,
            "websites": websites,
            "other_resources": other_resources,
            
            # Syllabus information
            "has_syllabus": syllabus_content is not None,
            "syllabus_content": syllabus_content,
            "syllabus_sessions": syllabus_sessions,
            
            # User difficulties
            "difficult_topics": difficult_topics,
            
            # Recent chat context
            "chat_messages": chat_messages,
            
            # User demographics if available
            "education_level": user_preferences.get("education_level", "undergraduate"),
            "prior_knowledge": session_preferences.get("prior_knowledge", "basic"),
        }
        
        # Log the context to help with debugging
        logger.info(f"Created user context for task with {len(user_context)} fields")
        logger.info(f"Context includes syllabus: {user_context['has_syllabus']}")
        logger.info(f"Context includes {len(user_context['resources'])} resources")
        logger.info(f"Context includes {len(user_context['syllabus_sessions'])} syllabus sessions")
        
        return user_context
    except Exception as e:
        logger.error(f"Error creating user context: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a minimal context to avoid breaking the flow
        return {
            "subject": session.field_of_study,
            "study_goal": session.study_goal,
            "error": f"Error extracting context: {str(e)}"
        }

async def run_multiagent_tasks(user_query: str, task_context: dict, progress_callback=None) -> Dict[str, Any]:
    """Run multiagent tasks to generate a complete study plan"""
    logger.info("Starting explicit multi-agent study plan generation")
    task_context = dict(task_context)
    task_context["user_query"] = user_query
    engine = create_engine()
    result = engine.generate(task_context, progress=progress_callback)
    return result.model_dump()

# Add these missing functions after the updated send_chat_message endpoint
async def process_chat_message_background(
    request_id: str,
    session_id: int,
    message: str,
    current_user: User,
):
    """Process a chat message in the background and store the result"""
    start_time = time.time()
    task_type = "chat"
    error = None
    db = None
    
    try:
        db = SessionLocal()
        # Check if this is a study plan request
        is_study_plan_request = check_if_study_plan_request(message)
        is_revision, _, _, _ = check_if_study_plan_revision(message, db, session_id)
        
        if is_study_plan_request:
            task_type = "study_plan"
        elif is_revision:
            task_type = "study_plan_revision"
        
        def progress(stage: str, progress_message: str) -> None:
            job_store.event(request_id, stage=stage, message=progress_message, status="running")

        logger.info(f"Background processing started for request {request_id} (type: {task_type})")
        result = await send_chat_message_internal(
            session_id=session_id,
            message=message,
            current_user=current_user,
            db=db,
            progress_callback=progress,
        )

        job_store.succeed(request_id, result)
        logger.info(f"Background processing completed for request {request_id}")
        await capture_processing_metrics(
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            start_time=start_time,
            result_data=result
        )
    except Exception as e:
        error = e
        logger.error(f"Error in background processing: {str(e)}")
        logger.error(traceback.format_exc())
        if isinstance(e, StudyPlanEngineError):
            job_store.fail(request_id, stage=e.stage, message=e.message, retryable=e.retryable)
        else:
            job_store.fail(request_id, stage=task_type, message=str(e), retryable=True)
        await capture_processing_metrics(
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            start_time=start_time,
            error=e
        )
    finally:
        if db is not None:
            db.close()

async def send_chat_message_internal(
    session_id: int,
    message: str,
    current_user: User,
    db: Session,
    progress_callback=None,
):
    """Internal function to process a chat message and return the result"""
    try:
        # Recreate the logic from send_chat_message but without HTTP response
        logger.info(f"Processing chat message for session {session_id}")
        
        # Check if session exists
        session = db.query(StudySession).filter(StudySession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
            
        if session.user_id != current_user.id:
            raise ValueError("Not authorized to access this session")
        
        # Create user message in the database
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=message,
            timestamp=datetime.now(),
            message_id=str(uuid.uuid4())  # Add a UUID as message_id
        )
        db.add(user_message)
        db.commit()
        
        # Check if this is a request to revise an existing study plan
        is_revision, difficult_topics, focus_sessions, specific_resources = check_if_study_plan_revision(
            message, db, session_id
        )
        
        # Check for initial study plan request
        is_study_plan_request = check_if_study_plan_request(message)
        logger.info(f"Is study plan request: {is_study_plan_request}")
        logger.info(f"Is revision request: {is_revision}")
        engine_name = "chat"
        
        # If it's a revision request, generate a new plan through the explicit engine
        if is_revision:
            engine_name = "multi_agent"
            logger.info(f"Generating revised study plan. Difficult topics: {difficult_topics}")
            
            # Get comprehensive user context
            task_context = get_user_task_context(db, current_user, session)
            
            # Add the newly identified difficult topics to the context
            if difficult_topics:
                if not task_context.get('difficult_topics'):
                    task_context['difficult_topics'] = []
                task_context['difficult_topics'].extend(difficult_topics)
                # Remove duplicates
                task_context['difficult_topics'] = list(set(task_context['difficult_topics']))
            
            # Add focus sessions information if available
            if focus_sessions:
                task_context['focus_sessions'] = focus_sessions
                
            # Add specific resources if mentioned
            if specific_resources:
                task_context['preferred_resources'] = specific_resources
            
            # Add the revision request to the context
            task_context['revision_request'] = message
            
            try:
                # Run the multiagent process to generate revised study plan
                revised_plan = await run_multiagent_tasks(
                    user_query=f"Please revise the study plan based on my feedback: {message}",
                    task_context=task_context,
                    progress_callback=progress_callback,
                )
                
                # Create a conversational response that presents the revised plan
                response_text = f"I've created a revised study plan based on your feedback. I've allocated more time for the topics you're finding challenging and adjusted the resource recommendations.\n\n{revised_plan['content']}"
                
            except Exception as e:
                logger.error(f"Error generating revised study plan: {str(e)}")
                logger.error(traceback.format_exc())
                raise
                
        # If it's an initial study plan request, process it with the multiagent system
        elif is_study_plan_request:
            engine_name = "multi_agent"
            logger.info("Detected study plan request. Using explicit multi-agent engine")
            try:
                task_context = get_user_task_context(db, current_user, session)
                engine_result = await run_multiagent_tasks(
                    user_query=message,
                    task_context=task_context,
                    progress_callback=progress_callback,
                )
                response_text = engine_result["content"]
                logger.info(f"Successfully generated study plan with {len(response_text)} characters")
            except Exception as e:
                logger.error(f"Error generating study plan: {str(e)}")
                logger.error(traceback.format_exc())
                raise
        else:
            # Regular chat message (not a study plan request)
            if llama_llm is not None:
                try:
                    # Use regular chat mode
                    response_text = get_ollama_response(session, message, db)
                except Exception as e:
                    logger.error(f"Error connecting to Ollama: {str(e)}")
                    
                    # Check if specific error types to give better errors
                    error_str = str(e).lower()
                    if "connection" in error_str or "timeout" in error_str or "refused" in error_str:
                        response_text = (
                            "I apologize, but I cannot connect to Ollama. Please make sure it is running "
                            f"with model '{settings.OLLAMA_MODEL}'. Technical details: Connection error"
                        )
                    else:
                        response_text = (
                            f"I apologize, but there seems to be an issue with the planning service. "
                            f"Technical details: {str(e)}"
                        )
            else:
                logger.warning("Ollama unavailable; returning setup guidance")
                
                # Try to initialize Ollama right here if it's not already available
                try:
                    if 'llama_llm' not in globals() or globals()['llama_llm'] is None:
                        logger.info("Attempting to initialize Ollama directly")
                        from langchain.llms import Ollama
                        globals()['llama_llm'] = Ollama(
                            model=settings.OLLAMA_MODEL,
                            base_url=settings.OLLAMA_BASE_URL,
                            temperature=0.7
                        )
                        test_response = globals()['llama_llm'].invoke("hello", timeout=5)
                        logger.info(f"Successfully initialized Ollama directly: {test_response[:50]}...")
                        return await send_chat_message_internal(session_id, message, current_user, db)
                except Exception as e:
                    logger.error(f"Failed to initialize Ollama directly: {str(e)}")
                
                response_text = (
                    "I apologize, but the planning service is unavailable at the moment. "
                    f"Please ensure Ollama is running with model '{settings.OLLAMA_MODEL}'. "
                    f"The server should be available at {settings.OLLAMA_BASE_URL}."
                )
        
        # Check if response_text is None or empty, and use a fallback if needed
        if not response_text or response_text.strip() == "":
            logger.warning("Ollama response is empty. Returning setup guidance.")
            response_text = "Sorry, I couldn't generate a response. Please try again shortly."
        
        # Create assistant message in the database
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            timestamp=datetime.now(),
            message_id=str(uuid.uuid4())  # Add a UUID as message_id
        )
        db.add(assistant_message)
        db.commit()
        
        # Return the formatted result for the caller
        return {
            "message_id": assistant_message.id,
            "role": "assistant",
            "content": response_text,
            "timestamp": assistant_message.timestamp.isoformat(),
            "engine": engine_name,
        }
        
    except Exception as e:
        logger.error(f"Error in send_chat_message_internal: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise

async def capture_processing_metrics(
    request_id: str,
    session_id: int,
    task_type: str,
    start_time: float,
    result_data: Dict[str, Any] = None,
    error: Exception = None
):
    """
    Capture processing metrics for analytics and monitoring
    
    Args:
        request_id: The unique ID of the request
        session_id: The session ID
        task_type: Type of task (e.g., "study_plan", "chat", "revision")
        start_time: When processing started (time.time() value)
        result_data: Optional result data
        error: Optional exception if processing failed
    """
    try:
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log the details
        if error:
            logger.info(f"Task {task_type} for request {request_id} failed after {processing_time:.2f}s: {str(error)}")
        else:
            logger.info(f"Task {task_type} for request {request_id} completed in {processing_time:.2f}s")
            
            # Additional logging for study plans
            if task_type == "study_plan" and result_data and "content" in result_data:
                content_length = len(result_data["content"])
                overview_present = "STUDY PLAN OVERVIEW:" in result_data["content"]
                days_present = all(f"DAY {i}:" in result_data["content"] for i in range(1, 6))
                
                logger.info(f"Study plan metrics - Length: {content_length}, " 
                          f"Has overview: {overview_present}, Has all days: {days_present}")
        
        # Store metrics in a central location
        metrics_data = {
            "request_id": request_id,
            "session_id": session_id,
            "task_type": task_type,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "success": error is None,
            "error_message": str(error) if error else None
        }
        
        os.makedirs(os.path.dirname(settings.METRICS_PATH), exist_ok=True)
        
        with open(settings.METRICS_PATH, "a") as f:
            f.write(json.dumps(metrics_data) + "\n")
            
    except Exception as e:
        # Don't let metrics collection failures impact the main flow
        logger.error(f"Error capturing metrics: {str(e)}")

def get_processing_metrics_summary(session_id: Optional[int] = None, limit: int = 20) -> Dict[str, Any]:
    """
    Get a summary of processing metrics for diagnostics
    
    Args:
        session_id: Optional session ID to filter by
        limit: Maximum number of recent records to include
        
    Returns:
        Dictionary with metrics summary
    """
    try:
        metrics_path = settings.METRICS_PATH
        if not os.path.exists(metrics_path):
            return {
                "status": "no_data",
                "message": "No metrics data available yet"
            }
            
        # Load metrics from file
        metrics = []
        with open(metrics_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if session_id is None or data.get("session_id") == session_id:
                        metrics.append(data)
                except:
                    continue
                    
        # Get only the most recent records
        metrics = sorted(metrics, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        
        # Calculate summary statistics
        if not metrics:
            return {
                "status": "no_matching_data",
                "message": f"No metrics found for session_id={session_id}"
            }
            
        # Get stats by task type
        task_types = {}
        for m in metrics:
            task_type = m.get("task_type", "unknown")
            if task_type not in task_types:
                task_types[task_type] = {
                    "count": 0,
                    "success_count": 0,
                    "total_time": 0,
                    "max_time": 0,
                    "min_time": float("inf")
                }
                
            stats = task_types[task_type]
            stats["count"] += 1
            if m.get("success", False):
                stats["success_count"] += 1
                
            proc_time = m.get("processing_time", 0)
            stats["total_time"] += proc_time
            stats["max_time"] = max(stats["max_time"], proc_time)
            stats["min_time"] = min(stats["min_time"], proc_time)
            
        # Calculate averages and format the results
        for task_type, stats in task_types.items():
            stats["avg_time"] = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            stats["success_rate"] = (stats["success_count"] / stats["count"] * 100) if stats["count"] > 0 else 0
            # Format times to 2 decimal places
            for key in ["avg_time", "max_time", "min_time"]:
                stats[key] = round(stats[key], 2)
            stats["success_rate"] = round(stats["success_rate"], 1)
            
        return {
            "status": "success",
            "session_id": session_id,
            "metrics_count": len(metrics),
            "task_type_stats": task_types,
            "recent_metrics": metrics[:5]  # Include 5 most recent metrics
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {str(e)}")
        return {
            "status": "error",
            "message": f"Error getting metrics: {str(e)}"
        }

@router.get("/{session_id}/metrics", response_model=Dict[str, Any])
async def get_session_metrics(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
) -> Any:
    """
    Get metrics and diagnostics for a study session.
    """
    # Check authorization
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )
    
    # Get the metrics summary
    metrics = get_processing_metrics_summary(session_id=session_id)
    
    service_status = {
        "ollama_available": ollama_available,
        "ollama_error": ollama_last_error,
        "study_plan_engine": "bounded_orchestrator_ollama",
    }
    
    # System health check
    system_health = {
        "memory_usage_mb": round(psutil.Process().memory_info().rss / (1024 * 1024), 2),
        "api_uptime_minutes": round((time.time() - globals().get("start_time", time.time())) / 60, 2) if "start_time" in globals() else None,
        "queue_size": 0
    }
    
    return {
        "session_id": session_id,
        "metrics": metrics,
        "service_status": service_status,
        "system_health": system_health
    }

# Create a class to capture token usage
class TokenUsageTracker:
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0
        
    def record_usage(self, prompt_tokens, completion_tokens):
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_requests += 1
        
    def get_stats(self):
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_requests": self.total_requests,
            "avg_prompt_tokens": self.total_prompt_tokens / self.total_requests if self.total_requests > 0 else 0,
            "avg_completion_tokens": self.total_completion_tokens / self.total_requests if self.total_requests > 0 else 0
        }
        
    def log_stats(self):
        stats = self.get_stats()
        logger.info("=" * 50)
        logger.info("TOKEN USAGE STATISTICS:")
        logger.info(f"Total requests: {stats['total_requests']}")
        logger.info(f"Total tokens: {stats['total_tokens']}")
        logger.info(f"  - Prompt tokens: {stats['total_prompt_tokens']}")
        logger.info(f"  - Completion tokens: {stats['total_completion_tokens']}")
        logger.info(f"Average tokens per request:")
        logger.info(f"  - Prompt: {stats['avg_prompt_tokens']:.1f}")
        logger.info(f"  - Completion: {stats['avg_completion_tokens']:.1f}")
        logger.info("=" * 50)

# Initialize the token tracker
token_tracker = TokenUsageTracker()

# Monkeypatch the Ollama invoke method to track tokens
original_ollama_invoke = None

def token_tracking_invoke_wrapper(self, prompt, *args, **kwargs):
    """Wrapper to track token usage for Ollama"""
    global original_ollama_invoke, token_tracker
    
    if original_ollama_invoke is None:
        logger.error("Original Ollama invoke method not saved")
        return "Error: Could not track token usage"
    
    # Call the original method
    start_time = time.time()
    result = original_ollama_invoke(self, prompt, *args, **kwargs)
    completion_time = time.time() - start_time
    
    # Estimate token counts (very rough estimation)
    prompt_tokens = len(prompt.split())
    completion_tokens = len(result.split()) if result else 0
    
    # Record the usage
    token_tracker.record_usage(prompt_tokens, completion_tokens)
    
    # Log the usage for this request
    logger.debug(f"Request tokens - Prompt: {prompt_tokens}, Completion: {completion_tokens}")
    logger.debug(f"Completion time: {completion_time:.2f}s, Tokens/sec: {completion_tokens/completion_time if completion_time > 0 else 0:.1f}")
    
    # Every 5 requests, log the overall stats
    if token_tracker.total_requests % 5 == 0:
        token_tracker.log_stats()
    
    return result

# Store the original invoke method and apply our wrapper
# This will happen when Ollama is initialized
