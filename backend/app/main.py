from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

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
from app.core.config import settings

# Create tables AFTER all models are imported
Base.metadata.create_all(bind=engine)

# Import API endpoints after models and DB are set up
from app.api.v1.endpoints import auth, sessions

app = FastAPI(
    title="LearnMate API",
    description="Backend API for LearnMate study planning",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
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
