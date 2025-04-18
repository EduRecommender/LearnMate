from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Any, List, Optional, Dict
from datetime import datetime
import os
import uuid
import sys
import logging
import json
import tempfile

from ....database import get_db
from ....services.session import SessionService
from ....schemas.user import (
    User,
    StudySession as StudySessionSchema,
    StudySessionCreate,
    StudySessionUpdate,
    Resource as ResourceSchema,
    ResourceCreate,
    ChatMessage,
    ChatMessageCreate,
)
from ....models.user import User as UserModel, Resource
from ....services.user import UserService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import OpenAI if available
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    has_openai = True
    logger.info("OpenAI integration enabled")
except (ImportError, Exception) as e:
    has_openai = False
    openai_client = None
    logger.warning(f"OpenAI integration not available: {str(e)}")

# Try to import the DeepSeekAssistantAgent
try:
    # Add the root directory to the path to find the agents module
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
    if root_dir not in sys.path:
        sys.path.append(root_dir)
    
    from agents.assistant_agent import DeepSeekAssistantAgent
    from agents.schemas.messages import ChatMessage as AgentChatMessage
    
    # Initialize with a small model for reliability
    assistant_agent = DeepSeekAssistantAgent(model_name="facebook/opt-125m")
    has_assistant = True
    logger.info("DeepSeek Assistant Agent integration enabled")
except (ImportError, Exception) as e:
    has_assistant = False
    assistant_agent = None
    logger.warning(f"DeepSeek Assistant Agent integration not available: {str(e)}")
    logger.exception("Error details:")

# Try to import the agent orchestrator
try:
    from agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator()
    has_orchestrator = True
    logger.info("Agent Orchestrator integration enabled")
except (ImportError, Exception) as e:
    has_orchestrator = False
    orchestrator = None
    logger.warning(f"Agent Orchestrator integration not available: {str(e)}")
    logger.exception("Error details:")

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
    
    # Try to import the syllabus processor
    try:
        # Add the root directory to the path to access the syllabus_processor
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
        if root_dir not in sys.path:
            sys.path.append(root_dir)
        
        from syllabus_processor import process_uploaded_syllabus
        has_processor = True
        logger.info("Syllabus processor imported successfully")
    except (ImportError, Exception) as e:
        has_processor = False
        logger.warning(f"Syllabus processor not available: {str(e)}")
        logger.exception("Error details:")
    
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
@router.get("/{session_id}/chat", response_model=List[ChatMessage])
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

@router.post("/{session_id}/chat", response_model=ChatMessage)
async def send_chat_message(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_simplified),
    session_id: int,
    message: Dict[str, Any] = Body(...),
) -> Any:
    """
    Send a message to the chat and get a response.
    """
    logger.info(f"\n\n==== STARTING CHAT REQUEST for session_id: {session_id} ====")
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to chat in this session",
        )
    
    logger.info(f"User: {current_user.username}, Session: {session.name}")
    logger.info(f"Message: {message.get('message', '')[:50]}...")
    logger.info(f"Field of study: {session.field_of_study}")
    logger.info(f"Study goal: {session.study_goal}")
    
    # Create user message
    user_message = ChatMessageCreate(
        message_id=str(uuid.uuid4()),
        role="user",
        content=message.get("message", ""),
        timestamp=datetime.now()
    )
    
    # Add message to chat history
    chat_message = SessionService.add_chat_message(db, session_id, user_message)
    logger.info(f"Added user message to chat history: {chat_message['message_id']}")
    
    # Get chat history for context
    chat_history = SessionService.get_chat_history(db, session_id)
    
    # SIMPLIFIED: Generate a hard-coded response based on message content
    user_content = message.get("message", "").lower()
    
    # Generate appropriate response based on message content
    if "study plan" in user_content or "plan" in user_content:
        assistant_content = f"""Here's a study plan for {session.field_of_study}:

Week 1-2: Fundamentals
- Study basic concepts and terminology
- Read introductory chapters in your textbook
- Complete 3 practice exercises daily

Week 3-4: Intermediate Concepts
- Dive deeper into key theoretical frameworks
- Watch video lectures on core topics
- Begin working on small projects

Week 5-6: Advanced Applications
- Focus on practical applications
- Study real-world examples and case studies
- Work on a challenging project that integrates multiple concepts

Weekly schedule:
- 1-2 hours daily of focused study
- Weekend review sessions
- Quizzes after completing each section

Remember to take breaks and use active recall techniques!"""

    elif "recommend" in user_content or "resource" in user_content or "material" in user_content:
        assistant_content = f"""Here are some excellent resources for {session.field_of_study}:

1. Textbooks:
   - "{session.field_of_study}: A Comprehensive Guide" by Smith & Johnson
   - "Fundamentals of {session.field_of_study}" by Rebecca Williams

2. Online Courses:
   - MIT OpenCourseWare: Introduction to {session.field_of_study}
   - Coursera: {session.field_of_study} Specialization by Stanford

3. Video Tutorials:
   - YouTube channel: {session.field_of_study} Academy
   - LinkedIn Learning: {session.field_of_study} Essential Training

4. Practice Platforms:
   - {session.field_of_study}Hub - Interactive exercises
   - Practice{session.field_of_study}.io - Real-world challenges

Which of these would you like me to elaborate on?"""

    elif "difficult" in user_content or "struggling" in user_content or "hard" in user_content or "help" in user_content:
        assistant_content = f"""Many students find {session.field_of_study} challenging at first. Here are some strategies to overcome common difficulties:

1. Break down complex concepts into smaller, manageable parts
2. Use visual aids and diagrams to understand relationships
3. Join study groups or find a study partner
4. Practice regularly with simple exercises before tackling complex problems
5. Apply concepts to real-world scenarios that interest you
6. Take short, frequent study sessions instead of cramming
7. Explain concepts in your own words (teach someone else)
8. Review fundamentals if you're struggling with advanced topics

What specific topic are you finding most challenging? I can provide more targeted suggestions."""

    elif "quiz" in user_content or "test" in user_content or "exam" in user_content:
        assistant_content = f"""To prepare for your {session.field_of_study} test:

1. Create a study schedule working backward from your test date
2. Review your notes and highlight key concepts
3. Make flashcards for definitions and formulas
4. Take practice tests under timed conditions
5. Focus on understanding concepts, not just memorizing
6. Study in short, focused sessions with breaks in between
7. Get sufficient sleep, especially the night before the exam
8. Review common mistake patterns from previous assessments

Would you like me to help create a specific test preparation schedule for you?"""

    else:
        # Default response for any other type of message
        assistant_content = f"""I'm here to help with your {session.field_of_study} studies! I can:

1. Create a personalized study plan
2. Recommend high-quality resources
3. Explain difficult concepts
4. Help with test preparation
5. Suggest effective study techniques
6. Answer questions about {session.field_of_study} topics
7. Track your progress

What specific aspect of {session.field_of_study} would you like assistance with today?"""
    
    # Create assistant message with required fields
    message_id = str(uuid.uuid4())
    timestamp = datetime.now()
    
    # Create assistant message as a proper dictionary with all required fields
    assistant_message_dict = {
        "message_id": message_id,
        "role": "assistant",
        "content": assistant_content,
        "timestamp": timestamp
    }
    
    # Create the ChatMessageCreate object for SessionService
    assistant_message = ChatMessageCreate(
        message_id=message_id,
        role="assistant",
        content=assistant_content,
        timestamp=timestamp
    )
    
    # Add assistant message to chat history
    assistant_reply = SessionService.add_chat_message(db, session_id, assistant_message)
    logger.info(f"Added assistant response to chat history: {assistant_reply['message_id']}")
    
    # EXTRA LOGGING: Log key information about the response being sent back
    logger.info(f"RESPONSE DETAILS:")
    logger.info(f"Response ID: {assistant_reply['message_id']}")
    logger.info(f"Response role: {assistant_reply['role']}")
    logger.info(f"Response timestamp: {assistant_reply['timestamp']}")
    logger.info(f"Response content length: {len(assistant_reply['content'])}")
    logger.info(f"Response content first 100 chars: {assistant_reply['content'][:100]}")
    logger.info(f"Response content last 100 chars: {assistant_reply['content'][-100:]}")
    logger.info(f"Full response object: {json.dumps(assistant_reply)}")
    
    # Ensure we're returning a proper dictionary with all required fields
    response_dict = {
        "message_id": assistant_reply["message_id"],
        "role": assistant_reply["role"],
        "content": assistant_reply["content"],
        "timestamp": assistant_reply["timestamp"]
    }
    
    logger.info(f"==== CHAT REQUEST COMPLETED ====\n\n")
    
    # Return a properly formatted response object
    return response_dict

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