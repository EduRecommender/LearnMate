from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Set specific loggers to DEBUG level
logging.getLogger("app.api.v1.endpoints.sessions").setLevel(logging.DEBUG)
logging.getLogger("app.services.llm_service").setLevel(logging.DEBUG)
logging.getLogger("app.services.ollama_service").setLevel(logging.DEBUG)
logging.getLogger("app.services.study_plan_service").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.INFO)  # Reduce noise from HTTP requests
logger = logging.getLogger(__name__)

# Import Base first
from app.models import Base

# Import all models from user.py
from app.models.user import User, StudySession, Resource, DifficultyLevel, ResourceType

# Import database engine 
from app.database import engine

# Create tables AFTER all models are imported
Base.metadata.create_all(bind=engine)

# Import API endpoints after models and DB are set up
from app.api.v1.endpoints import auth, sessions

app = FastAPI(
    title="LearnMate API",
    description="Backend API for LearnMate - Your AI Study Partner",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001"
    ],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Add error handling middleware
@app.middleware("http")
async def add_error_handling(request: Request, call_next):
    start_time = time.time()
    try:
        logger.debug(f"Request started: {request.method} {request.url}")
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.debug(f"Request completed: {request.method} {request.url} in {process_time:.2f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {request.method} {request.url} after {process_time:.2f}s")
        logger.exception("Error details:")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

# Include routers - use simple prefixes for compatibility with frontend
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])

@app.get("/")
async def root():
    return {"message": "Welcome to LearnMate API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def check_environment():
    """Check environment variables and AI setup during startup."""
    try:
        import os
        print("\n=== ENVIRONMENT DIAGNOSTICS ===")
        
        # Check OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            print(f"- OpenAI API key found: {openai_api_key[:5]}...")
            if not openai_api_key.startswith("sk-"):
                print("  WARNING: OpenAI API key doesn't look valid (should start with 'sk-')")
        else:
            print("- OpenAI API key NOT found")
            
        # Check for other relevant environment variables
        relevant_vars = [
            "PYTHONPATH",
            "MODEL_PATH",
            "HUGGINGFACE_TOKEN"
        ]
        
        for var in relevant_vars:
            value = os.getenv(var)
            if value:
                print(f"- {var} found: {value[:10]}..." if len(value) > 10 else f"- {var} found: {value}")
            else:
                print(f"- {var} NOT found")
                
        print("\n=== AI BACKEND DIAGNOSTICS ===")
        
        # Check for OpenAI package
        try:
            import openai
            print(f"- OpenAI package found (version: {openai.__version__})")
        except ImportError:
            print("- OpenAI package NOT found")
        
        # Check for transformers package (needed for DeepSeek)
        try:
            import transformers
            print(f"- Transformers package found (version: {transformers.__version__})")
        except ImportError:
            print("- Transformers package NOT found (needed for DeepSeek)")
            
        # Check if agents directory exists
        agents_path = os.path.join(os.path.abspath('../../..'), 'agents')
        if os.path.exists(agents_path):
            print(f"- Agents directory found at: {agents_path}")
            agent_files = [f for f in os.listdir(agents_path) if f.endswith('.py')]
            print(f"  Agent files: {', '.join(agent_files) if agent_files else 'No .py files found'}")
        else:
            print(f"- Agents directory NOT found at expected path: {agents_path}")
        
        print("=== DIAGNOSTICS COMPLETE ===\n")
    except Exception as e:
        print(f"Error during environment check: {str(e)}")

# Add configuration for direct startup with long timeouts
if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get configuration from environment or use defaults
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8002))
    
    # Start uvicorn with extended timeouts
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        timeout_keep_alive=7200,  # 2 hour keep-alive timeout
        timeout_graceful_shutdown=7200,  # 2 hour graceful shutdown
        log_level="info",
    )