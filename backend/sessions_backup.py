from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Any, List, Optional, Dict
from datetime import datetime
import os
import uuid
import sys
import logging
import json
import traceback
import tempfile
from io import BytesIO
import base64
import asyncio
from concurrent.futures import ProcessPoolExecutor
import re
import time
from pydantic import ValidationError
import psutil

from ....database import get_db
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track API startup time
start_time = time.time()

# FORCE multiagent to be available - manual override
has_multiagent = True
logger.info("FORCED multiagent system to be ENABLED at top level")

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

# Set up direct assistant agent using Ollama
class OllamaAssistantAgent:
    """Assistant agent that uses Ollama directly"""
    
    def __init__(self, model_name="llama3:8b"):
        self.model_name = model_name
        logger.info(f"OllamaAssistantAgent initialized with model: {model_name}")
    
    async def generate_response(self, messages, max_tokens=1000):
        """Generate a response using Ollama LLM"""
        try:
            # Format messages into a prompt
            prompt = ""
            for m in messages:
                role = m.get('role', 'user')
                content = m.get('content', '')
                prompt += f"{role}: {content}\n"
            
            # Add assistant prefix for the response
            prompt += "assistant: "
            
            # Use global llama_llm if available
            if 'llama_llm' in globals() and globals()['llama_llm'] is not None:
                return globals()['llama_llm'].invoke(prompt)
            else:
                return "I'm sorry, Ollama LLM is not available."
        except Exception as e:
            logger.error(f"Error in OllamaAssistantAgent.generate_response: {str(e)}")
            return f"Error generating response: {str(e)}"

# Simple message class for chat context
class AgentChatMessage:
    """Chat message class for assistant interactions"""
    
    def __init__(self, content="", role="user"):
        self.content = content
        self.role = role
    
    def to_dict(self):
        return {"content": self.content, "role": self.role}

# Set up the assistant agent using Ollama
assistant_agent = OllamaAssistantAgent()
has_assistant = True

# Create a simple orchestrator class for study plan generation 
class SimpleAgentOrchestrator:
    """A simplified orchestrator to manage agent workflows"""
    
    def __init__(self):
        logger.info("SimpleAgentOrchestrator initialized")
        self.llm = None
    
    def set_llm(self, llm_instance):
        """Set the LLM instance to use for agent tasks"""
        self.llm = llm_instance
        return self
    
    def run_study_plan_generation(self, context):
        """Run study plan generation with the provided context"""
        try:
            # Import the create_study_plan function from Agents.main
            from Agents.main import create_study_plan
            
            if self.llm is None:
                logger.warning("No LLM set for SimpleAgentOrchestrator, using default")
                # Try to use the global llama_llm if available
                if 'llama_llm' in globals():
                    self.llm = llama_llm
            
            # Generate the study plan using our new implementation
            logger.info(f"Generating study plan with context: {context.get('subject', 'unknown subject')}")
            
            # Ensure the LLM is set in llm_config.py
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent.parent))
            
            import agents.llm_config
            if self.llm:
                # Set the llm in the llm_config module
                agents.llm_config.llama_llm = self.llm
            
            # Generate the study plan
            plan = create_study_plan(context)
            
            # Check if plan is an error message (string starts with "Error" or "Failed")
            if isinstance(plan, str) and (plan.startswith("Error") or plan.startswith("Failed")):
                # Use fallback if main generation failed
                logger.warning(f"Using fallback plan generation due to error: {plan}")
                from Agents.study_assistant.main import create_fallback_plan
                return create_fallback_plan(context, plan)
            else:
                return plan
            
        except Exception as e:
            logger.error(f"Error in SimpleAgentOrchestrator.run_study_plan_generation: {str(e)}")
            logger.exception("Error details:")

            # Try to use fallback if available
            try:
                from Agents.study_assistant.main import create_fallback_plan
                return create_fallback_plan(context, str(e))
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback plan: {str(fallback_error)}")
                return f"Failed to generate study plan: {str(e)}"

# Initialize the orchestrator
orchestrator = SimpleAgentOrchestrator()
has_orchestrator = True

# Add these new imports
import traceback
import importlib.util
from pathlib import Path

# Add the parent directory to the Python path to import from agents directory
base_path = Path(__file__).parent.parent.parent.parent.parent.parent
agents_path = base_path / "agents"
sys.path.append(str(base_path))

# Specify the multiagent directory name - using agents/agents instead of Testing_multiagent_copy
multiagent_dir = "agents"

# Global variables for tracking Ollama status
ollama_available = False
ollama_last_error = None

# Initialize Ollama if available
try:
    logger.info("Attempting to initialize Ollama LLM")
    
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
    
    # Create a regular Ollama LLM with only compatible parameters
    ollama_llm = Ollama(
        model="llama3:8b",  # Use the model that's actually available
        base_url="http://localhost:11434",
        temperature=0.7,
        timeout=3600  # 1 hour timeout for Ollama API calls
    )
    
    # Test the connection
    logger.info("Testing Ollama connection...")
    try:
        # Try with a very simple prompt and reduced timeout for the test
        test_response = ollama_llm.invoke("hello", timeout=5)
        logger.info(f"Ollama test response: {test_response[:50]}...")
        logger.info(f"Ollama model: {ollama_llm.model}, base_url: {ollama_llm.base_url}")
        
        # If we get here, the connection was successful
        ollama_available = True
        llama_llm = ollama_llm  # Assign to the global variable
        logger.info("✅ Successfully connected to Ollama")
        
        # Set the LLM in the orchestrator
        if orchestrator:
            orchestrator.set_llm(llama_llm)
            logger.info("Set Ollama LLM in the orchestrator")
    except Exception as e:
        logger.error(f"❌ Error testing Ollama connection: {str(e)}")
        logger.error(f"Make sure Ollama is running with: ollama run llama3:8b")
        logger.error(traceback.format_exc())
        ollama_available = False
        llama_llm = None
        ollama_last_error = str(e)
        # Reraise to abort initialization
        raise
    
    # Now try to set up the CrewAI integration
    try:
        logger.info("Initializing CrewAI")
        from crewai import Agent, Task, Crew, Process, TaskOutput
        from langchain.agents import Tool
        from langchain_community.chat_models import ChatOpenAI
        from langchain_core.language_models.chat_models import BaseChatModel
        
        # Create a fake ChatOpenAI class that uses our Ollama LLM
        class OllamaFakeOpenAI(ChatOpenAI):
            def __init__(self, *args, **kwargs):
                # Call the parent constructor with fake values
                super().__init__(
                    model="gpt-3.5-turbo",  # Doesn't matter, we'll override
                    api_key="sk-fake-key",
                    base_url="https://example.com",
                    temperature=0.7,
                    request_timeout=3600,  # 1 hour timeout for OpenAI API calls
                    *args, **kwargs
                )
                
                # Store the Ollama LLM in a way that doesn't trigger Pydantic validation
                # Using object.__setattr__ to bypass Pydantic's field validation
                object.__setattr__(self, "_ollama_llm", llama_llm)
                
            def invoke(self, prompt, *args, **kwargs):
                # Just delegate to our working Ollama instance
                try:
                    # Access using the private attribute instead
                    ollama_instance = object.__getattribute__(self, "_ollama_llm")
                    
                    if isinstance(prompt, str):
                        # Direct string prompt
                        return ollama_instance.invoke(prompt)
                    else:
                        # Handle message-style inputs by converting to a string
                        messages_text = ""
                        for message in prompt.messages:
                            role = message.type if hasattr(message, 'type') else "unknown"
                            content = message.content if hasattr(message, 'content') else str(message)
                            messages_text += f"{role}: {content}\n"
                        return ollama_instance.invoke(messages_text)
                except Exception as e:
                    logger.error(f"Error invoking Ollama: {str(e)}")
                    return f"Error: {str(e)}"
            
            def __call__(self, prompt, *args, **kwargs):
                # Also override direct calls
                return self.invoke(prompt, *args, **kwargs)
        
        # Create a fake OpenAI interface that uses our Ollama instance
        fake_openai = OllamaFakeOpenAI()
        
        # Initialize agents
        logger.info("Initializing strategy agent")
        strategy_agent = Agent(
            role="Learning Strategy Expert",
            goal="Recommend the most effective learning strategies for the student",
            backstory="""You are an expert in educational psychology and learning strategies.
            You understand the science of effective learning and can recommend
            personalized study strategies based on learning styles and preferences.""",
            llm=fake_openai,
            verbose=True
        )
        strategist_agent = strategy_agent  # Create an alias for consistency
        
        logger.info("Initializing resources agent")
        resources_agent = Agent(
            role="Educational Resource Finder",
            goal="Find the best learning resources for the recommended strategies",
            backstory="""You are an expert in finding high-quality educational resources.
            You know where to find the best books, websites, videos, and tools for any subject.""",
            llm=fake_openai,
            verbose=True
        )
        
        logger.info("Initializing planner agent")
        planner_agent = Agent(
            role="Study Plan Creator",
            goal="Create a detailed, actionable study plan integrating the strategies and resources",
            backstory="""You are an expert in creating effective study plans and schedules.
            You know how to break down complex subjects into manageable chunks and create 
            realistic timelines that keep students motivated and on track.""",
            llm=fake_openai,
            verbose=True
        )
        
        logger.info("Initializing data fetcher agent")
        data_fetcher_agent = Agent(
            role="Data and Research Analyst",
            goal="Research specific topics and find detailed information",
            backstory="""You are an expert researcher who can find detailed information on any topic.
            You know how to validate sources and compile comprehensive information.""",
            llm=fake_openai,
            verbose=True
        )
        
        # Initialize tasks
        logger.info("Initializing strategy task")
        strategy_task = Task(
            description="Analyze learning preferences and recommend 3-5 evidence-based learning strategies",
            expected_output="A detailed analysis of 3-5 learning strategies with explanations of why they are appropriate",
            agent=strategy_agent
        )
        strategist_task = strategy_task  # Create an alias for consistency
        
        logger.info("Initializing resources task")
        resources_task = Task(
            description="Find high-quality learning resources that match the recommended strategies",
            expected_output="A list of 5-10 specific resources with explanations of how they align with the strategies",
            agent=resources_agent
        )
        
        logger.info("Initializing planner task")
        planner_task = Task(
            description="Create a detailed daily/weekly study plan integrating the strategies and resources",
            expected_output="A comprehensive study plan with specific activities, resources, and time allocations",
            agent=planner_agent
        )
        
        logger.info("Successfully initialized all agents and tasks")
        
        # If we made it here, set has_multiagent to True
        has_multiagent = True
        logger.info("Multi-agent system successfully initialized")
        
    except Exception as e:
        logger.error(f"Error initializing CrewAI: {str(e)}")
        logger.error(traceback.format_exc())
        has_multiagent = False  # Make sure this is set to False on error
    
except Exception as e:
    logger.error(f"Error initializing Ollama: {str(e)}")
    logger.error(traceback.format_exc())
    ollama_available = False
    llama_llm = None
    has_multiagent = False
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

# Dictionary to store ongoing requests
processing_requests = {}

# Provide a way to persist requests between server restarts
# This is a simple file-based persistence that will work for development
def save_request_data(request_id, data):
    import json
    import os
    
    # Create directory if it doesn't exist
    os.makedirs("./data/chat_requests", exist_ok=True)
    
    # Save request data to a file
    try:
        with open(f"./data/chat_requests/{request_id}.json", "w") as f:
            json.dump(data, f)
        logger.info(f"Saved request data for {request_id}")
    except Exception as e:
        logger.error(f"Failed to save request data: {str(e)}")

def load_request_data(request_id):
    import json
    import os
    
    # Load request data from file
    try:
        file_path = f"./data/chat_requests/{request_id}.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
            logger.info(f"Loaded request data for {request_id}")
            # Also update the in-memory cache
            processing_requests[request_id] = data
            return data
        else:
            logger.warning(f"No saved data found for request {request_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to load request data: {str(e)}")
        return None

@router.get("/{session_id}/chat/status/{request_id}", response_model=Dict[str, Any])
async def check_chat_message_status(
    session_id: int,
    request_id: str,
    current_user: User = Depends(get_current_user_simplified),
    db: Session = Depends(get_db),
):
    """Check the status of an asynchronous chat message request"""
    try:
        logger.info(f"Checking status for request {request_id} in session {session_id}")
        
        # Special handling for fallback IDs created by the frontend
        if request_id.startswith("fallback-"):
            logger.info(f"Handling fallback request ID: {request_id}")
            # These are special IDs generated by the frontend when it can't reach the start endpoint
            # We'll treat them as completed and let the frontend handle the message display
            return {
                "status": "complete",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "result": {
                    "message_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": "I'm sorry, but there was an issue with the message processing. The system is working in fallback mode.",
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        # Check if the request exists in memory
        if request_id not in processing_requests:
            logger.info(f"Request {request_id} not found in memory, trying to load from disk")
            
            # Try to load from disk
            request_data = load_request_data(request_id)
            if not request_data:
                logger.error(f"Request {request_id} not found in memory or disk")
                raise HTTPException(status_code=404, detail="Request not found")
        else:
            # Get the request data from memory
            request_data = processing_requests[request_id]
            logger.info(f"Found request {request_id} in memory, status: {request_data['status']}")
        
        # Check authorization
        if request_data["user_id"] != current_user.id:
            logger.warning(f"User {current_user.id} not authorized to access request {request_id}")
            raise HTTPException(status_code=403, detail="Not authorized to access this request")
        
        # Check if the request is for the specified session
        if int(request_data["session_id"]) != int(session_id):
            logger.warning(f"Request {request_id} doesn't match session ID {session_id}")
            raise HTTPException(status_code=400, detail="Request doesn't match session ID")
        
        # Return status and result if available
        response = {
            "status": request_data["status"],
            "started_at": request_data["started_at"]
        }
        
        if request_data["status"] == "complete" and request_data["result"]:
            response["result"] = request_data["result"]
            
            # Don't immediately clean up - keep for a while
            if "completed_at" in request_data:
                completed_time = datetime.fromisoformat(request_data["completed_at"])
                now = datetime.now()
                if (now - completed_time).total_seconds() > 86400:  # 24 hours
                    # Remove the request data after 24 hours
                    logger.info(f"Cleaning up completed request {request_id}")
                    processing_requests.pop(request_id, None)
                    # Also remove file
                    import os
                    try:
                        os.remove(f"./data/chat_requests/{request_id}.json")
                    except Exception as e:
                        logger.error(f"Failed to remove request file: {str(e)}")
        
        return response
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error checking chat message status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Check if this is a fallback request ID
        fallback_id = request.get("fallback_id", None)
        if fallback_id and fallback_id.startswith("fallback-"):
            logger.info(f"Using provided fallback ID: {fallback_id}")
            request_id = fallback_id
        else:
            # Generate a unique ID for this request
            request_id = str(uuid.uuid4())
        
        # Store the request info
        request_data = {
            "session_id": session_id,
            "message": message,
            "user_id": current_user.id,
            "status": "processing",
            "started_at": datetime.now().isoformat(),
            "result": None
        }
        
        # Store in memory
        processing_requests[request_id] = request_data
        
        # Persist to disk
        save_request_data(request_id, request_data)
        
        logger.info(f"Created request {request_id} for session {session_id}")
        
        # Start processing in background
        asyncio.create_task(
            process_chat_message_background(
                request_id=request_id,
                session_id=session_id,
                message=message,
                current_user=current_user,
                db=db
            )
        )
        
        return {"request_id": request_id, "status": "processing"}
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
        
        # Generate a fallback ID that can be used by the frontend
        fallback_id = f"fallback-{int(time.time() * 1000)}"
        
        # Start processing in the background and get the request ID
        start_response = await start_chat_message_processing(
            session_id=session_id,
            request={"message": message, "fallback_id": fallback_id},
            current_user=current_user,
            db=db
        )
        
        request_id = start_response["request_id"]
        
        # Process the message immediately, but still return quickly
        asyncio.create_task(
            process_chat_message_background(
                request_id=request_id,
                session_id=session_id,
                message=message,
                current_user=current_user,
                db=db
            )
        )
        
        # For backwards compatibility, wait briefly and check if the result is ready
        # This helps with simple requests that can be processed quickly
        await asyncio.sleep(0.5)  # Wait 500ms to see if it completes quickly
        
        try:
            status_response = await check_chat_message_status(
                session_id=session_id,
                request_id=request_id,
                current_user=current_user,
                db=db
            )
            
            if status_response["status"] == "complete" and "result" in status_response:
                # The message was processed quickly, return the result directly
                return status_response["result"]
        except Exception as check_error:
            logger.error(f"Error checking immediate status: {str(check_error)}")
        
        # The message is still processing, return an in-progress response
        return {
            "message_id": f"pending-{request_id}",
            "role": "assistant",
            "content": "Processing your request...",
            "timestamp": datetime.now().isoformat(),
            "is_processing": True,
            "request_id": request_id
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
    try:
        # Try to use the dedicated module
        from Agents.study_assistant.user_input import is_study_plan_request
        return is_study_plan_request(message)
    except ImportError:
        # Fallback to built-in implementation
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
    try:
        # Try to use the dedicated module for checking revision requests
        from Agents.study_assistant.user_input import is_study_plan_revision, extract_difficult_topics, extract_syllabus_references, extract_all_preferences
        
        # Check if it's a revision request
        is_revision = is_study_plan_revision(message)
        
        # If it's not a revision, return quickly
        if not is_revision:
            return (False, [], None, [])
        
        # Extract preferences
        preferences = extract_all_preferences(message)
        
        # Get difficult topics
        difficult_topics = preferences.get('difficult_topics', [])
        
        # Get focus sessions
        focus_sessions = preferences.get('focus_sessions')
        
        # Extract specific resources from database
        specific_resources = []
        resources = db.query(Resource).filter(Resource.session_id == session_id).all()
        
        for resource in resources:
            if resource.name.lower() in message.lower():
                specific_resources.append({
                    "id": resource.id,
                    "name": resource.name,
                    "type": resource.type if hasattr(resource, 'type') else "UNKNOWN"
                })
        
        # Add preferred resource types if available
        if "preferred_resource_types" in preferences:
            for res_type in preferences["preferred_resource_types"]:
                specific_resources.append({
                    "id": None,
                    "name": f"Any {res_type}",
                    "type": res_type
                })
        
        return (is_revision, difficult_topics, focus_sessions, specific_resources)
        
    except ImportError:
        # Fallback to built-in implementation
        message_lower = message.lower()
        
        # Keywords for revisions
        revision_keywords = [
            "revise the plan", "update the plan", "modify the plan", "change the plan",
            "adjust the study plan", "can you modify", "need more time for",
            "don't understand", "struggling with", "having trouble with", 
            "need help with", "focus more on", "spend more time on",
            "allocate more time", "prefer different resources", "different approach",
            "too difficult", "too easy", "too much time", "not enough time",
            "better resources", "prefer to use", "would rather use"
        ]
        
        is_revision = any(keyword in message_lower for keyword in revision_keywords)
        
        # If it's not a revision, return quickly
        if not is_revision:
            return (False, [], None, [])
        
        # Extract difficult topics or areas that need more focus
        difficult_topics = []
        struggle_phrases = ["struggle with", "difficult for me", "having trouble with", 
                           "not understanding", "confused about", "need help with",
                           "problem with", "challenging", "hard to grasp", 
                           "focus more on", "more time for", "don't understand"]
        
        for phrase in struggle_phrases:
            if phrase in message_lower:
                # Find the topic after the struggle phrase
                topic_start = message_lower.find(phrase) + len(phrase)
                topic_end = message_lower.find(".", topic_start)
                if topic_end == -1:  # If no period, look for other delimiters
                    for delimiter in [",", "and", "but", "\n", " so "]:
                        pos = message_lower.find(delimiter, topic_start)
                        if pos != -1:
                            topic_end = min(topic_end, pos) if topic_end != -1 else pos
                            
                    if topic_end == -1:  # Still not found, use the rest of the message
                        topic_end = len(message_lower)
                        
                topic = message_lower[topic_start:topic_end].strip()
                if topic and len(topic) < 100:  # Reasonable topic length
                    difficult_topics.append(topic)
        
        # Extract specific sessions or days to focus on
        focus_sessions = None
        session_patterns = [
            r"session\s*(\d+)", r"day\s*(\d+)", r"week\s*(\d+)", 
            r"lecture\s*(\d+)", r"module\s*(\d+)"
        ]
        
        for pattern in session_patterns:
            matches = re.findall(pattern, message_lower)
            if matches:
                focus_sessions = [int(match) for match in matches]
                break
        
        # Extract specific resources mentioned
        specific_resources = []
        
        # First get all resources for this session to match against
        resources = db.query(Resource).filter(Resource.session_id == session_id).all()
        
        for resource in resources:
            if resource.name.lower() in message_lower:
                specific_resources.append({
                    "id": resource.id,
                    "name": resource.name,
                    "type": resource.type if hasattr(resource, 'type') else "UNKNOWN"
                })
        
        # Also check for generic resource types
        resource_types = ["book", "video", "article", "paper", "tutorial", "course", "website"]
        for res_type in resource_types:
            if res_type in message_lower:
                # Find the full resource mention
                pos = message_lower.find(res_type)
                start = max(0, pos - 30)  # Look 30 chars before
                end = min(len(message_lower), pos + 30)  # and 30 chars after
                context = message_lower[start:end]
                
                # If not already captured and seems to be a specific mention
                already_captured = any(res.get("name", "").lower() in context for res in specific_resources)
                if not already_captured:
                    specific_resources.append({
                        "id": None,
                        "name": context.strip(),
                        "type": res_type
                    })
        
        return (is_revision, difficult_topics, focus_sessions, specific_resources)

def get_ollama_response(session: StudySession, message: str, db: Session) -> str:
    """Get a response from the Ollama API for regular chat messages"""
    try:
        # Add global declaration to access the Ollama LLM
        global llama_llm
        
        if not llama_llm:
            logger.error("Ollama LLM is not initialized")
            return "I'm sorry, but the language model is not available right now. Please try again later."
        
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

def validate_task_params(agent, context=None):
    """Validate task parameters to prevent type errors
    
    Args:
        agent: Should be an Agent object, not a string
        context: If provided, should be a list of TaskOutput objects
        
    Raises:
        TypeError: If parameters have incorrect types
    """
    if not isinstance(agent, Agent):
        raise TypeError(f"Task agent must be an Agent object, not {type(agent).__name__}")
    
    if context is not None:
        if not isinstance(context, list):
            raise TypeError(f"Task context must be a list, not {type(context).__name__}")
        
        for item in context:
            if not isinstance(item, TaskOutput):
                raise TypeError(f"Task context items must be TaskOutput objects, not {type(item).__name__}")

async def run_multiagent_tasks(user_query: str, task_context: dict) -> str:
    """Run multiagent tasks to generate a complete study plan"""
    try:
        logger.info(f"Starting multiagent study plan generation")
        logger.info(f"User query: {user_query}")
        logger.info(f"Context keys available: {list(task_context.keys())}")
        
        # Extract key context fields for better logging
        subject = task_context.get('subject', 'the subject')
        study_goal = task_context.get('study_goal', 'learning effectively')
        has_resources = len(task_context.get('resources', [])) > 0
        has_syllabus = task_context.get('has_syllabus', False)
        
        logger.info(f"Generating plan for {subject} with goal: {study_goal}")
        logger.info(f"Has resources: {has_resources}, Has syllabus: {has_syllabus}")
        
        # Add the original user query to the context
        task_context['user_query'] = user_query
        
        # Try to use our proper multi-agent system
        try:
            # Check if we have a working LLM first
            if 'llama_llm' not in globals() or globals()['llama_llm'] is None:
                logger.warning("LLM not available for running multiagent tasks")
                raise Exception("LLM not available")

            # Try direct generation using the LLM instead of the complex agent system
            # This is more reliable especially when CrewAI causes issues
            return generate_direct_study_plan(globals()['llama_llm'], task_context)
            
        except Exception as e:
            logger.error(f"Error in direct plan generation: {str(e)}")
            logger.error(traceback.format_exc())
            logger.info("Falling back to backup plan generation")
            
            # Create a comprehensive fallback study plan based on the context
            return create_fallback_study_plan(task_context)
    except Exception as e:
        logger.error(f"Critical error in run_multiagent_tasks: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Last resort fallback - very basic plan that should always work
        return create_basic_fallback_plan(task_context)

def create_basic_fallback_plan(task_context: dict) -> str:
    """Create a very basic fallback study plan when everything else fails"""
    # Extract the bare minimum needed for a study plan
    subject = task_context.get('subject', 'your subject')
    goal = task_context.get('study_goal', 'mastering the material')
    days = task_context.get('study_days', '5')
    
    # Create a super simple plan structure
    return f"""STUDY PLAN OVERVIEW:
I've created a study plan to help you with {subject} focused on {goal}.

DAY 1:
- Morning:
  * Introduction to {subject} fundamentals (45 minutes)
  * Take notes on key concepts and terminology (30 minutes)
- Afternoon:
  * Review your class materials and notes (60 minutes)
  * Practice with basic examples (45 minutes)

DAY 2:
- Morning:
  * Review previous day's material (20 minutes)
  * Study core theories and principles (60 minutes)
- Afternoon:
  * Work through example problems (45 minutes)
  * Create summary notes of what you've learned (30 minutes)

DAY 3:
- Morning:
  * Review previous material (30 minutes)
  * Focus on more advanced concepts (60 minutes)
- Afternoon:
  * Practice applying concepts to real-world scenarios (60 minutes)
  * Self-assessment: test your understanding (30 minutes)

DAY 4:
- Morning:
  * Review areas of difficulty identified in self-assessment (45 minutes)
  * Deep dive into complex topics (60 minutes)
- Afternoon:
  * Work on practice problems focusing on difficult areas (60 minutes)
  * Create a concept map connecting all key ideas (30 minutes)

DAY 5:
- Morning:
  * Comprehensive review of all material (60 minutes)
  * Practice with exam-style questions (45 minutes)
- Afternoon:
  * Final review of difficult concepts (45 minutes)
  * Prepare questions for your instructor about any unclear points (30 minutes)

IMPLEMENTATION TIPS:
* Start each study session with a 5-minute review of previous material
* Take short breaks every 25-30 minutes to maintain focus
* Alternate between learning theory and practical application
* Use multiple resources to reinforce your understanding

This plan can be adjusted based on your progress and specific needs.
"""

def create_fallback_study_plan(task_context: dict) -> str:
    """Create a more detailed fallback study plan using available context"""
    try:
        # Extract useful information from the context
        subject = task_context.get('subject', 'the subject')
        study_goal = task_context.get('study_goal', 'mastering the material')
        hours_per_day = task_context.get('hours_per_day', '2')
        study_days = task_context.get('study_days', '5')
        learning_style = task_context.get('learning_style', 'visual')
        difficult_topics = task_context.get('difficult_topics', [])
        
        # Extract resource information
        resources = []
        if task_context.get('resources'):
            for resource in task_context['resources'][:3]:  # Use up to 3 resources
                resources.append(f"- {resource.get('name', 'Resource')}")
        
        # Create resource recommendations based on available information
        resource_text = "\n".join(resources) if resources else "- Use your course textbook and lecture notes\n- Look for online tutorials and videos on the subject"
        
        # Create a study approach based on learning style
        study_approach = ""
        if learning_style.lower() == 'visual':
            study_approach = "This plan emphasizes visual learning methods like diagrams, charts, and video resources."
        elif learning_style.lower() == 'auditory':
            study_approach = "This plan emphasizes auditory learning methods like lectures, discussions, and explaining concepts out loud."
        elif learning_style.lower() == 'kinesthetic':
            study_approach = "This plan emphasizes hands-on learning methods like practice exercises and real-world applications."
        else:
            study_approach = "This plan balances different learning methods to help you master the material effectively."
            
        # Adjust for difficult topics
        difficulty_focus = ""
        if difficult_topics:
            topics = ", ".join(difficult_topics[:3])
            difficulty_focus = f"I've allocated extra time for topics you find challenging: {topics}."
            
        # Create the plan
        return f"""STUDY PLAN OVERVIEW:
I've created a personalized {study_days}-day study plan for {subject} focused on {study_goal}. {study_approach} {difficulty_focus}

DAY 1:
- Morning:
  * Introduction to key concepts in {subject} (45 minutes)
  * Create a glossary of important terms and definitions (30 minutes)
- Afternoon:
  * Review foundational principles using your resources (60 minutes)
  * Practice applying basic concepts through exercises (45 minutes)

DAY 2:
- Morning:
  * Review previous day's material with flashcards (20 minutes)
  * Study intermediate concepts and principles (60 minutes)
- Afternoon:
  * Work through example problems (45 minutes)
  * Create visual summaries or diagrams of key relationships (30 minutes)

DAY 3:
- Morning:
  * Quiz yourself on previously covered material (30 minutes)
  * Focus on more advanced topics in {subject} (60 minutes)
- Afternoon:
  * Apply concepts to practical scenarios or problems (60 minutes)
  * Identify areas where you need more practice (30 minutes)

DAY 4:
- Morning:
  * Deep review of difficult concepts and topics (45 minutes)
  * Study advanced applications and techniques (60 minutes)
- Afternoon:
  * Practice with complex problems and scenarios (60 minutes)
  * Summarize what you've learned in your own words (30 minutes)

DAY 5:
- Morning:
  * Comprehensive review of all material (60 minutes)
  * Take a practice test or work through sample problems (45 minutes)
- Afternoon:
  * Address gaps in knowledge identified from practice test (45 minutes)
  * Create a final summary document of key concepts and techniques (30 minutes)

RECOMMENDED RESOURCES:
{resource_text}

IMPLEMENTATION TIPS:
* Use the Pomodoro technique: 25 minutes of focused study followed by 5-minute breaks
* Connect new information to concepts you already understand
* Explain concepts out loud as if teaching someone else
* Review material before sleep to improve retention

You can adjust this plan based on your progress and specific needs.
"""
    except Exception as e:
        logger.error(f"Error creating fallback plan: {str(e)}")
        return create_basic_fallback_plan(task_context)

def generate_direct_study_plan(llm, task_context: dict) -> str:
    """Generate a study plan directly using the LLM without agent complexity"""
    try:
        # Extract key information for the prompt
        subject = task_context.get('subject', 'the subject')
        study_goal = task_context.get('study_goal', 'learning effectively')
        hours_per_day = task_context.get('hours_per_day', '2')
        study_days = task_context.get('study_days', '5')
        learning_style = task_context.get('learning_style', 'visual')
        difficult_topics = task_context.get('difficult_topics', [])
        
        # Format resource information
        resources_text = ""
        if task_context.get('resources'):
            resources_text = "AVAILABLE RESOURCES:\n"
            for idx, resource in enumerate(task_context['resources'][:5]):
                resources_text += f"{idx+1}. {resource.get('name', 'Resource')}\n"
        
        # Format difficult topics
        difficult_topics_text = ""
        if difficult_topics:
            difficult_topics_text = "CHALLENGING TOPICS:\n"
            for topic in difficult_topics[:3]:
                difficult_topics_text += f"- {topic}\n"
        
        # Create a detailed prompt for the LLM
        prompt = f"""You are an expert educational planner helping a student create a detailed study plan.

STUDENT INFORMATION:
- Subject: {subject}
- Goal: {study_goal}
- Available time: {hours_per_day} hours per day
- Plan duration: {study_days} days
- Learning style: {learning_style}
{difficult_topics_text}
{resources_text}

Your task is to create a comprehensive, day-by-day study plan that will help this student achieve their goal.

The plan should:
1. Include specific activities for each day with time allocations
2. Incorporate the student's learning style preferences
3. Reference specific resources when available
4. Allocate more time to difficult topics if specified
5. Include regular reviews of previous material
6. Include appropriate breaks

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

STUDY PLAN OVERVIEW:
[Write 1-2 paragraphs describing the overall approach]

DAY 1:
- Morning:
  * [Specific activity with time allocation]
  * [Another specific activity with time allocation]
- Afternoon:
  * [Specific activity with time allocation]
  * [Another specific activity with time allocation]

DAY 2:
[Same format as Day 1]

[Continue for all days]

RECOMMENDED RESOURCES:
- [Resource recommendation with specific sections if applicable]
- [Another resource recommendation]

IMPLEMENTATION TIPS:
- [Practical tip for staying on track]
- [Another practical tip]

Do not deviate from this format. The day headings must be formatted exactly as shown.
"""
        
        # Generate the plan
        logger.info("Generating study plan directly with LLM")
        start_time = time.time()
        
        # Get response from LLM
        response = llm.invoke(prompt)
        
        execution_time = time.time() - start_time
        logger.info(f"Generated plan in {execution_time:.2f} seconds")
        
        # Validate the response
        if not response or len(response.strip()) < 200:
            logger.warning(f"Direct LLM plan generation produced short output: {len(response) if response else 0} chars")
            return create_fallback_study_plan(task_context)
            
        # Make sure it has the right format
        if "STUDY PLAN OVERVIEW:" not in response and "DAY 1:" not in response:
            logger.warning("Direct LLM plan doesn't have the required format")
            
            # Try to fix the format
            if "Day 1" in response or "day 1" in response:
                # It has days but wrong format, try to correct it
                fixed_response = "STUDY PLAN OVERVIEW:\n"
                fixed_response += "Here is your personalized study plan for " + subject + ".\n\n"
                
                # Add the days with correct formatting
                for i in range(1, int(study_days) + 1):
                    day_pattern = f"[Dd]ay {i}|DAY {i}"
                    if re.search(day_pattern, response):
                        # Extract the day's content
                        day_match = re.search(f"{day_pattern}.*?(?=[Dd]ay {i+1}|DAY {i+1}|$)", response, re.DOTALL)
                        if day_match:
                            day_content = day_match.group(0)
                            # Format it correctly
                            fixed_response += f"DAY {i}:\n"
                            fixed_response += day_content.replace(f"Day {i}", "").replace(f"day {i}", "").replace(f"DAY {i}", "")
                            fixed_response += "\n"
                
                # Add the rest of the sections if they exist
                if "RESOURCES" in response or "Resources" in response:
                    resources_match = re.search("(?:RESOURCES|Resources).*?(?=IMPLEMENTATION|Implementation|$)", response, re.DOTALL)
                    if resources_match:
                        fixed_response += "\nRECOMMENDED RESOURCES:\n"
                        fixed_response += resources_match.group(0).replace("RESOURCES", "").replace("Resources", "")
                
                if "IMPLEMENTATION" in response or "Implementation" in response:
                    implementation_match = re.search("(?:IMPLEMENTATION|Implementation).*", response, re.DOTALL)
                    if implementation_match:
                        fixed_response += "\nIMPLEMENTATION TIPS:\n"
                        fixed_response += implementation_match.group(0).replace("IMPLEMENTATION", "").replace("Implementation", "")
                
                response = fixed_response
            else:
                # It doesn't even have days, use fallback
                return create_fallback_study_plan(task_context)
        
        return response
    except Exception as e:
        logger.error(f"Error in direct study plan generation: {str(e)}")
        logger.error(traceback.format_exc())
        return create_fallback_study_plan(task_context)

# Add these missing functions after the updated send_chat_message endpoint
async def process_chat_message_background(
    request_id: str,
    session_id: int,
    message: str,
    current_user: User,
    db: Session,
):
    """Process a chat message in the background and store the result"""
    start_time = time.time()
    task_type = "chat"
    error = None
    
    try:
        # Check if this is a study plan request
        is_study_plan_request = check_if_study_plan_request(message)
        is_revision, _, _, _ = check_if_study_plan_revision(message, db, session_id)
        
        if is_study_plan_request:
            task_type = "study_plan"
        elif is_revision:
            task_type = "study_plan_revision"
        
        # This runs the actual processing logic
        logger.info(f"Background processing started for request {request_id} (type: {task_type})")
        
        # Reuse the logic from send_chat_message
        result = await send_chat_message_internal(
            session_id=session_id,
            message=message,
            current_user=current_user,
            db=db
        )
        
        # Store the result in memory
        if request_id in processing_requests:
            processing_requests[request_id]["status"] = "complete"
            processing_requests[request_id]["result"] = result
            processing_requests[request_id]["completed_at"] = datetime.now().isoformat()
            processing_requests[request_id]["processing_time"] = time.time() - start_time
            
            # Also update the persisted data
            save_request_data(request_id, processing_requests[request_id])
        
            logger.info(f"Background processing completed for request {request_id}")
            
            # Capture metrics after successful processing
            await capture_processing_metrics(
                request_id=request_id,
                session_id=session_id,
                task_type=task_type,
                start_time=start_time,
                result_data=result
            )
        else:
            logger.error(f"Request {request_id} not found in memory when storing result")
    except Exception as e:
        error = e
        logger.error(f"Error in background processing: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Store the error
        if request_id in processing_requests:
            processing_requests[request_id]["status"] = "error"
            processing_requests[request_id]["error"] = str(e)
            processing_requests[request_id]["completed_at"] = datetime.now().isoformat()
            processing_requests[request_id]["processing_time"] = time.time() - start_time
            
            # Update persisted data
            save_request_data(request_id, processing_requests[request_id])
        else:
            logger.error(f"Request {request_id} not found in memory when trying to update error status")
        
        # Capture metrics for the error case
        await capture_processing_metrics(
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            start_time=start_time,
            error=e
        )

async def send_chat_message_internal(
    session_id: int,
    message: str,
    current_user: User,
    db: Session,
):
    """Internal function to process a chat message and return the result"""
    try:
        # Recreate the logic from send_chat_message but without HTTP response
        logger.info(f"Processing chat message for session {session_id}")
        
        # Add global declarations for all the variables we might need
        global has_multiagent, llama_llm, strategy_agent, resources_agent, planner_agent
        global strategist_task, resources_task, planner_task, data_fetcher_agent
        
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
        
        # If it's a revision request and we have multiagent, generate a new plan
        if is_revision and has_multiagent and llama_llm is not None:
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
                    task_context=task_context
                )
                
                # Create a conversational response that presents the revised plan
                response_text = f"I've created a revised study plan based on your feedback. I've allocated more time for the topics you're finding challenging and adjusted the resource recommendations.\n\n{revised_plan}"
                
            except Exception as e:
                logger.error(f"Error generating revised study plan: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Fall back to regular chat mode
                response_text = get_ollama_response(session, message, db)
                response_text = "I understand you want to modify your study plan. " + response_text
                
        # If it's an initial study plan request, process it with the multiagent system
        elif is_study_plan_request:
            logger.info("Detected study plan request. Attempting to use CrewAI")
            
            # First check if we have working Ollama regardless of agents
            if llama_llm is not None:
                try:
                    # Always use the new multiagent task runner for study plans
                    logger.info("Using multiagent system for study plan")
                    # Get comprehensive user context with syllabus and resources
                task_context = get_user_task_context(db, current_user, session)
                
                    # Run the multiagent process to generate study plan
                    response_text = await run_multiagent_tasks(
                    user_query=message,
                    task_context=task_context
                )
                
                    # Verify the response has the expected format
                    if response_text and len(response_text) > 100:
                        logger.info(f"Successfully generated study plan with {len(response_text)} characters")
        else:
                        logger.warning(f"Study plan seems too short ({len(response_text) if response_text else 0} chars)")
                except Exception as e:
                    logger.error(f"Error generating study plan: {str(e)}")
                    logger.error(traceback.format_exc())
                    response_text = f"I'm sorry, but I encountered an error while creating your study plan: {str(e)}. Please try again later."
            else:
                # No Ollama available
                response_text = "I apologize, but I don't have access to language models at the moment. Please ensure Ollama is running on your system with the command 'ollama run llama3:8b'."
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
                            "I apologize, but I cannot connect to the language model. Please make sure Ollama is running "
                            "with the command 'ollama run llama3:8b'. Technical details: Connection error"
                        )
                    else:
                        response_text = (
                            f"I apologize, but there seems to be an issue with the language model. "
                            f"Technical details: {str(e)}"
                        )
            else:
                # No LLM available
                logger.warning("No LLM available, using placeholder response")
                
                # Try to initialize Ollama right here if it's not already available
                try:
                    if 'llama_llm' not in globals() or globals()['llama_llm'] is None:
                        logger.info("Attempting to initialize Ollama LLM directly")
                        from langchain.llms import Ollama
                        globals()['llama_llm'] = Ollama(
                            model="llama3:8b", 
                            base_url="http://localhost:11434",
                            temperature=0.7
                        )
                        test_response = globals()['llama_llm'].invoke("hello", timeout=5)
                        logger.info(f"Successfully initialized Ollama directly: {test_response[:50]}...")
                        return await send_chat_message_internal(session_id, message, current_user, db)  # Retry now that we have LLM
                except Exception as e:
                    logger.error(f"Failed to initialize Ollama directly: {str(e)}")
                
                server_url = "http://localhost:11434"
                response_text = (
                    "I apologize, but I don't have access to language models at the moment. "
                    f"Please ensure Ollama is running on your system with the command 'ollama run llama3:8b'. "
                    f"The server should be available at {server_url}."
                )
        
        # Check if response_text is None or empty, and use a fallback if needed
        if not response_text or response_text.strip() == "":
            logger.warning("LLM response is empty. Using fallback message.")
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
            "timestamp": assistant_message.timestamp.isoformat()
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
        
        # Create directory if it doesn't exist
        os.makedirs("./data/metrics", exist_ok=True)
        
        # Append to metrics file
        with open("./data/metrics/processing_metrics.jsonl", "a") as f:
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
        metrics_path = "./data/metrics/processing_metrics.jsonl"
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
    
    # Add LLM status information
    llm_status = {
        "ollama_available": ollama_available,
        "ollama_error": ollama_last_error,
        "has_multiagent": has_multiagent,
        "has_orchestrator": "orchestrator" in globals() and globals()["orchestrator"] is not None,
    }
    
    # System health check
    system_health = {
        "memory_usage_mb": round(psutil.Process().memory_info().rss / (1024 * 1024), 2) if 'psutil' in sys.modules else None,
        "api_uptime_minutes": round((time.time() - globals().get("start_time", time.time())) / 60, 2) if "start_time" in globals() else None,
        "queue_size": len(processing_requests)
    }
    
    return {
        "session_id": session_id,
        "metrics": metrics,
        "llm_status": llm_status,
        "system_health": system_health
    }