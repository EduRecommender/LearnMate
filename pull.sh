#!/bin/bash
set -e

# Start Ollama server in the background
ollama serve &
SERVER_PID=$!

# Wait for the Ollama server to be ready
echo "Waiting for Ollama server to start..."
until curl -s http://localhost:11434/api/version > /dev/null; do
  sleep 1
done
echo "Ollama server is up."

# Pull the desired model
ollama pull llama3:8b
echo "--------------------------------"
echo "Model pulled.--------------------------------"

# Wait for the server process to keep the container running
wait $SERVER_PID