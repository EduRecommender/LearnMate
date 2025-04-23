# LearnMate Docker Setup

This guide explains how to run the complete LearnMate application stack using Docker and Docker Compose.

## Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose installed on your system
- Git repository cloned locally

## Environment Variables

Create a `.env` file in the root directory with any required API keys:

```
# OpenAI API (optional, only if you're using OpenAI models)
OPENAI_API_KEY=your_openai_key_here

# Other optional API keys
HUGGINGFACE_TOKEN=your_huggingface_token_here
YOUTUBE_API_KEY=your_youtube_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## Running the Complete Stack

Start all services with Docker Compose:

```bash
docker-compose up -d
```

This will:
1. Start the Ollama service with the Llama 3 8B model
2. Start the FastAPI backend once Ollama is healthy
3. Start the Next.js frontend once the backend is healthy
4. Set up all necessary connections between services

## Running Individual Services

You can also run individual components:

```bash
# Run just the backend
docker-compose up backend

# Run just the frontend
docker-compose up frontend

# Run just Ollama
docker-compose up ollama
```

## Running Tests

To run the pytest test suite:

```bash
docker-compose up pytest
```

## Accessing the Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8002
  - API Documentation: http://localhost:8002/docs
  - Health Check: http://localhost:8002/health
- **Ollama API**: http://localhost:11434

## Development Workflow

The Docker Compose setup includes volume mounts for both the backend and frontend, so changes to your local code will be reflected in the containers:

- Frontend (Next.js) changes will trigger automatic hot reloading
- Backend (FastAPI) changes will also be reflected with hot reloading enabled

## Container Management

### Viewing Logs

```bash
# View logs for all services
docker-compose logs

# View logs for a specific service
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f
```

### Stopping the Stack

```bash
# Stop all services but keep volumes
docker-compose down

# Stop and remove all volumes (including Ollama models)
docker-compose down -v
```

### Rebuilding Services

If you make changes to Dockerfiles or dependencies:

```bash
# Rebuild a specific service
docker-compose build backend

# Rebuild and restart a service
docker-compose up -d --build frontend
```

## Troubleshooting

### Common Issues

1. **Ollama not downloading models**: Check Ollama logs with `docker-compose logs ollama`
2. **Services not connecting**: Ensure that the backend can reach Ollama via its service name
3. **Port conflicts**: Make sure ports 3000, 8002, and 11434 are not in use by other applications

### Container Health Checks

All services include health checks to ensure they're running correctly:

```bash
# Check service health status
docker-compose ps
```

## Production Deployment Notes

For production deployment:

1. Modify environment variables appropriately
2. Consider setting up proper persistent volumes for data
3. Configure appropriate resource limits in the docker-compose.yml file 