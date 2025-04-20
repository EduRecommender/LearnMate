# agents/resources_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from langchain.utilities import DuckDuckGoSearchAPIWrapper
from langchain.tools import DuckDuckGoSearchRun
from llm_config import llama_llm
import sys
import os
import json
import logging
from typing import Type, Dict, Any, Union, List, Optional
from pydantic import BaseModel, Field
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_fetcher import BackendDataFetcher
from utils.context_loader import extract_syllabus_topics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from utils.backend_data_fetcher import BackendDataFetcher
except ImportError:
    logger.warning("BackendDataFetcher import failed, using empty context")
    
# Define schemas for the tools
class WebSearchSchema(BaseModel):
    query_input: Union[str, Dict[str, Any]] = Field(..., description="The search query or a dictionary with search parameters")

class TopicSearchSchema(BaseModel):
    topic: str = Field(..., description="The syllabus topic to search for")

# Initialize the backend data fetcher - will be populated with actual data later
backend_data_fetcher = BackendDataFetcher()
enhanced_context = {
    "user": {},
    "session": {}
}

# Create a custom search function that uses DuckDuckGoSearchRun internally
def web_search(query_input, **kwargs) -> str:
    """Perform a web search with a formatted query and return the results."""
    try:
        # Handle various input formats from the agent
        if isinstance(query_input, dict):
            # Extract query from different possible dictionary structures
            if "query" in query_input:
                query = query_input.get("query")
                resource_type = query_input.get("type", "")
            else:
                # Fall back to our previous format
                query = query_input.get("search_query", "")
                resource_type = query_input.get("resource_type", "")
                learning_strategy = query_input.get("learning_strategy", "")
                
                # If needed, check for learning strategy
                if not learning_strategy and "strategy" in query_input:
                    learning_strategy = query_input.get("strategy", "")
        else:
            # If it's not a dict, use it directly as a string query
            query = query_input
            resource_type = ""
            learning_strategy = ""
                
        # If the query is already a well-formed natural language string, use it directly
        if isinstance(query, str) and len(query) > 15 and (" " in query):
            # If we have a resource type, still try to incorporate it
            if resource_type and isinstance(resource_type, str) and resource_type.strip():
                # Only add resource type if it's not already in the query
                if resource_type.lower() not in query.lower():
                    formatted_query = f"{query} {resource_type}"
                else:
                    formatted_query = query
            else:
                formatted_query = query
        
        # Handle structured dictionary input for creating a composed query
        elif query:
            # Create a natural language query based primarily on the subject matter
            # Focus on finding good resources for the subject first
            if resource_type:
                if isinstance(resource_type, list) and len(resource_type) > 0:
                    resource_type = resource_type[0]  # Use the first type if it's a list
                
                # Different query formats based on resource type
                if 'video' in resource_type.lower():
                    formatted_query = f"recommended videos for learning about {query}"
                elif 'book' in resource_type.lower() or 'textbook' in resource_type.lower():
                    formatted_query = f"best books or textbooks on {query}"
                elif 'course' in resource_type.lower():
                    formatted_query = f"top online courses for {query}"
                elif 'exercise' in resource_type.lower() or 'practice' in resource_type.lower():
                    formatted_query = f"practice problems or exercises for {query}"
                else:
                    formatted_query = f"{resource_type} for learning {query}"
            else:
                formatted_query = f"best resources to learn {query}"
            
            # Only mention learning strategy if absolutely necessary
            if learning_strategy and not 'general' in learning_strategy.lower():
                formatted_query += f" for {learning_strategy}"
        else:
            # Fallback for empty query
            formatted_query = "educational resources"
        
        print(f"Searching for: {formatted_query}")
        
        # Create a fresh instance for each search to avoid state issues
        search_tool = DuckDuckGoSearchRun()
        results = search_tool.run(formatted_query)
        
        if not results or results.strip() == "":
            return "No search results found. Try a different search query."
        
        # Format the results nicely
        formatted_results = f"Search query: '{formatted_query}'\n\nResults:\n{results}\n\n"
        formatted_results += "Based on these search results, identify specific resources for learning the subject. For each resource, include:\n"
        formatted_results += "1. The title of the resource\n"
        formatted_results += "2. Direct URL/link to the resource\n"
        formatted_results += "3. Brief description of the resource\n"
        formatted_results += "4. Any specific chapters, sections, timestamps, or page numbers IF MENTIONED in the search results. Do not hallucinate these details if they are not provided.\n\n"
        formatted_results += "You'll later explain how to apply specific learning strategies to these subject-specific resources."
        
        return formatted_results
    except Exception as e:
        error_message = f"Error performing web search: {str(e)}. Try a different search query."
        print(f"Search error: {error_message}")
        return error_message

# Create a function that searches for resources based on syllabus topics
def syllabus_topic_search(topic):
    """Search for resources specific to a syllabus topic"""
    return web_search(f"best learning resources for {topic}")

# Create proper CrewAI BaseTool classes
class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for educational resources related to the subject"
    args_schema: Type[BaseModel] = WebSearchSchema
    
    def _run(self, query_input):
        return web_search(query_input)

class TopicSearchTool(BaseTool):
    name: str = "topic_search" 
    description: str = "Search for resources specific to a syllabus topic"
    args_schema: Type[BaseModel] = TopicSearchSchema
    
    def _run(self, topic):
        return syllabus_topic_search(topic)

# Instantiate the tool classes
web_search_tool = WebSearchTool()
topic_search_tool = TopicSearchTool()

# Update agent context with backend data
def update_agent_context(user_id=None, session_id=None):
    """Update the agent's context with backend data"""
    global backend_data_fetcher, enhanced_context
    if user_id or session_id:
        backend_data_fetcher = BackendDataFetcher(user_id=user_id, session_id=session_id)
        enhanced_context = backend_data_fetcher.get_enhanced_context()
        # Update the agent tools_metadata with the new context
        if hasattr(resources_agent, 'tools_metadata'):
            resources_agent.tools_metadata.update({
                "user_preferences": enhanced_context.get("user", {}).get("preferences", {}),
                "session_data": enhanced_context.get("session", {}).get("data", {}),
                "syllabus": enhanced_context.get("session", {}).get("syllabus", {})
            })
        else:
            resources_agent.tools_metadata = {
                "user_preferences": enhanced_context.get("user", {}).get("preferences", {}),
                "session_data": enhanced_context.get("session", {}).get("data", {}),
                "syllabus": enhanced_context.get("session", {}).get("syllabus", {})
            }
        print("Resources agent context updated with backend data")
    return enhanced_context

# Create the resources agent with BaseTool instances
resources_agent = Agent(
    role="Study Resources Specialist",
    goal="Find high-quality subject-specific resources tailored to syllabus topics and learning preferences.",
    backstory=(
        "You are an expert in finding educational resources tailored to specific subjects and syllabus topics. "
        "When a syllabus is available, you analyze its topics and find targeted resources for each key topic. "
        "You consider the student's learning style and preferences when recommending resources. "
        "You first find the best content for learning a particular subject (videos, books, courses, etc.). "
        "If they are mentioned in search results, you note specific chapters, timestamps, or sections, "
        "but you do NOT invent these details if they're not actually available in the search results. "
        "Then, you explain how to apply different learning strategies to those subject-specific "
        "resources. You understand that the key is to find excellent subject content first, then apply "
        "appropriate learning techniques to that content. You're skilled at using natural language queries "
        "to search the web effectively and find exactly what students need."
    ),
    llm=llama_llm,
    verbose=True,
    allow_delegation=False,
    tools=[web_search_tool, topic_search_tool],
    # Add tools metadata with the enhanced context
    tools_metadata={
        "user_preferences": enhanced_context.get("user", {}).get("preferences", {}),
        "session_data": enhanced_context.get("session", {}).get("data", {}),
        "syllabus": enhanced_context.get("session", {}).get("syllabus", {})
    }
) 