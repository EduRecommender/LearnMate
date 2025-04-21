# llm_config.py

from langchain_ollama import OllamaLLM

llama_llm = OllamaLLM(
    model="ollama/llama3:8b",
    base_url="http://localhost:11434",
    temperature=0.7
)

# Redundant import to help with imports
# No need to change this file - it's already correctly defined
