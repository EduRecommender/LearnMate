# LearnMate

An intelligent learning companion application that helps users organize their study sessions, track progress, and access personalized learning resources.

## Project Overview

LearnMate consists of three main components:
- **Frontend**: Next.js web application with a modern UI
- **Backend**: FastAPI server providing API endpoints and AI functionality
- **LLM Integration**: Ollama for running local LLM models

## Getting Started with Docker

The easiest way to run the full LearnMate application stack is using Docker.

### Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose installed
- Git repository cloned locally

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# OpenAI API (optional, only if you're using OpenAI models)
OPENAI_API_KEY=your_openai_key_here

# Other optional API keys
HUGGINGFACE_TOKEN=your_huggingface_token_here
YOUTUBE_API_KEY=your_youtube_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### Running with Docker Compose

Start all services with one command:

```bash
docker-compose up -d
```

This will:
1. Start Ollama with Llama 3 8B model
2. Launch the FastAPI backend
3. Start the Next.js frontend
4. Set up all necessary connections between services

### Accessing the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8002
- **Ollama API**: http://localhost:11434

### Running Tests

To run the test suite:

```bash
docker-compose up pytest
```

### Stopping the Stack

```bash
docker-compose down
```

To also remove the persistent volume with Ollama models:

```bash
docker-compose down -v
```

## Manual Setup (Non-Docker)

For development or if you prefer not to use Docker, you can set up each component individually.

### Prerequisites
- Node.js and npm
- Python 3.x
- Ollama (https://ollama.com/)

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run the backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### LLM Setup (Ollama)
```bash
# Start Ollama service
ollama serve

# In another terminal, run the LLM model
ollama run llama3:8b
```

## Project Structure

- `frontend/`: Next.js web application
- `backend/`: FastAPI server and Python backend code
- `agents/`: AI agent implementations
- `data/`: Data storage and resources
- `backend/tests/`: Test suite for backend functionality



