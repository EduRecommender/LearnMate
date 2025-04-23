# LearnMate Docker Setup

This repository includes Docker configuration to run the full LearnMate application stack:
- Ollama with Llama 3 8B model
- FastAPI backend
- Next.js frontend
- Automated tests with pytest

## Prerequisites

- Docker and Docker Compose installed on your system
- Git repository cloned locally

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# OpenAI API (optional, only if you're using OpenAI models)
OPENAI_API_KEY=your_openai_key_here
```

## Running the Stack

Start all services with Docker Compose:

```bash
docker-compose up -d
```

This will:
1. Start the Ollama service 
2. Pull the Llama 3 8B model automatically using the ollama-pull service
3. Start the FastAPI backend once Ollama is healthy
4. Start the Next.js frontend once the backend is healthy

## Running Tests

To run the pytest test suite:

```bash
docker-compose up pytest
```

This will run all the backend tests and show the results in the console.

## Accessing the Services

- Ollama API: http://localhost:11434
- Backend API: http://localhost:8002
- Frontend: http://localhost:3000

## Development Workflow

The Docker Compose setup includes volume mounts for both the backend and frontend, so changes to your local code will be reflected in the containers.

## Stopping the Stack

```bash
docker-compose down
```

To also remove the persistent volume with Ollama models:

```bash
docker-compose down -v
``` 