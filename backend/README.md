# LearnMate Backend

The FastAPI-based backend for the LearnMate application, providing API endpoints, AI functionality, and data management.

## Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.x
- **Database**: SQLite (study_sessions.db)
- **AI Integration**: Ollama, OpenAI (optional)

## Local Development Setup

### Prerequisites

- Python 3.9+
- Ollama installed and running

### Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (optional):
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OPENAI_API_KEY=your_openai_key_here
   HUGGINGFACE_TOKEN=your_huggingface_token
   YOUTUBE_API_KEY=your_youtube_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   ```

### Running the Backend

Start the FastAPI server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

The API will be available at http://127.0.0.1:8002

### API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://127.0.0.1:8002/docs
- ReDoc: http://127.0.0.1:8002/redoc

## Docker Setup

The backend can also be run via Docker:

```bash
# From the project root directory
docker-compose up backend
```

This will start just the backend service configured to connect with Ollama.

## Project Structure

- `app/`: Main application code
  - `main.py`: FastAPI application entry point
  - `routes/`: API endpoint definitions
  - `models/`: Data models
- `tests/`: Test suite
- `agents/`: AI agent implementations
- `data/`: Data files and resources
- `requirements.txt`: Python dependencies

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific_module.py

# Run with coverage
pytest --cov=app
```

## Health Check

The backend provides a health check endpoint at `/health` which can be used to verify the service is running properly. 