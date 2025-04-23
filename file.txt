FROM ollama/ollama:latest

# Install necessary utilities
RUN apt-get update && apt-get install -y curl netcat

# Copy the pull script into the container
COPY pull.sh /pull.sh
RUN chmod +x /pull.sh

# Set the entrypoint to the pull script
ENTRYPOINT ["/pull.sh"]