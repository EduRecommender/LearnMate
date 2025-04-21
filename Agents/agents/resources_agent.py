# agents/resources_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from Agents.llm_config import llama_llm
from langchain_community.tools import DuckDuckGoSearchRun
import sys
import os
import json
import logging
from typing import Type, Dict, Any, Union, List, Optional
from pydantic import BaseModel, Field
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_fetcher import BackendDataFetcher
from utils.context_loader import extract_syllabus_topics
# Import is missing or incorrect - commenting it out
# from temp_crewai_install.crewai.agents.tools.web_tools import WebBrowserEngineTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
# Define schemas for the tools
class WebSearchSchema(BaseModel):
    query_input: Union[str, Dict[str, Any]] = Field(..., description="The search query or a dictionary with search parameters")

class TopicSearchSchema(BaseModel):
    topic: Union[str, Dict[str, Any]] = Field(..., description="The syllabus topic to search for")

class ResourceVerifierSchema(BaseModel):
    resources_list: List = Field(..., description="List of resources to verify")

class FindSpecificsSchema(BaseModel):
    resource_title: str = Field(..., description="The title of the resource to find specifics for")
    subject: str = Field(..., description="The subject or topic to search for specifics")

# Initialize the backend data fetcher - will be populated with actual data later
backend_data_fetcher = BackendDataFetcher()
enhanced_context = {
    "user": {},
    "session": {}
}

# Tool call tracking to prevent repetitive calls
previous_search_calls = {
    "web_search": {"input": None, "result": None, "count": 0},
    "topic_search": {"input": None, "result": None, "count": 0}
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
    global previous_search_calls
    
    # Extract string value if topic is a dict
    if isinstance(topic, dict):
        if "topic" in topic:
            topic = topic["topic"]
            # If still a dict, try to extract the description
            if isinstance(topic, dict) and "description" in topic:
                topic = topic["description"]
    
    # Create a string representation for comparison
    topic_str = str(topic)
    
    # Check for repetitive calls
    if previous_search_calls["topic_search"]["input"] == topic_str:
        previous_search_calls["topic_search"]["count"] += 1
        if previous_search_calls["topic_search"]["count"] >= 2:
            logger.warning(f"Detected repetitive call to topic_search: '{topic_str}' (count: {previous_search_calls['topic_search']['count']})")
            return previous_search_calls["topic_search"]["result"] + "\n\nNOTE: I notice you're searching for resources on the same topic repeatedly. Would you like more diverse resources or more specific information about these resources?"
    else:
        # Reset counter for new topic
        previous_search_calls["topic_search"]["count"] = 1
    
    # ALWAYS perform fresh web searches for each topic to ensure up-to-date resources
    
    # Use more specific search query to get better results - explicitly exclude syllabi
    search_query = f"best learning resources for {topic} with specific chapters or modules -syllabus -wikipedia"
    
    # Do a targeted search for each resource type
    textbook_query = f"recommended textbooks with specific chapters for {topic} site:amazon.com OR site:goodreads.com"
    video_query = f"best tutorial videos with timestamps for {topic} site:youtube.com OR site:coursera.org"
    practice_query = f"practice exercises with solutions for {topic} site:khanacademy.org OR site:stackexchange.com"
    
    # Collect all search results
    textbook_results = web_search(textbook_query)
    video_results = web_search(video_query)
    practice_results = web_search(practice_query)
    
    # Combine the results with clear sections
    combined_results = f"TOPIC: {topic}\n\n"
    combined_results += "TEXTBOOK RESOURCES:\n" + textbook_results + "\n\n"
    combined_results += "VIDEO RESOURCES:\n" + video_results + "\n\n"
    combined_results += "PRACTICE RESOURCES:\n" + practice_results + "\n\n"
    combined_results += "\nREMINDER: For each resource, you MUST provide:\n"
    combined_results += "1. Exact title and author/creator\n"
    combined_results += "2. Full URL/link\n"
    combined_results += "3. Detailed description (what it covers)\n"
    combined_results += "4. SPECIFIC sections, chapters, timestamps, or page numbers\n"
    combined_results += "5. How this resource specifically addresses the topic\n\n"
    combined_results += "CRITICAL: NEVER recommend the syllabus itself as a study resource. The syllabus is only an outline, not a learning resource."
    
    # Store the result and input for future comparison
    previous_search_calls["topic_search"]["input"] = topic_str
    previous_search_calls["topic_search"]["result"] = combined_results
    
    return combined_results

# Add a function to verify resource specificity
def verify_resource_specificity(resources_list):
    """Verify that resources have specific sections, chapters, or timestamps and filter out syllabus references"""
    if not resources_list or not isinstance(resources_list, list):
        return {
            "valid_resources": [],
            "issues": ["No resources provided or invalid format"]
        }
    
    verified_resources = []
    issues = []
    
    for idx, resource in enumerate(resources_list):
        # Skip syllabus resources
        if isinstance(resource, dict) and 'title' in resource:
            if 'syllabus' in resource['title'].lower():
                issues.append(f"Resource #{idx+1} ({resource['title']}) is a syllabus, which should not be used as a study resource.")
                continue
        elif isinstance(resource, str) and 'syllabus' in resource.lower():
            issues.append(f"Resource #{idx+1} contains a syllabus reference, which should not be used as a study resource.")
            continue
            
        # Check if resource has specific sections
        has_specific_sections = False
        if isinstance(resource, dict):
            # Check various fields for specificity
            specificity_fields = ['sections', 'chapters', 'pages', 'timestamps', 'specific_content', 'specific_sections']
            resource_str = str(resource)
            
            for term in ['chapter', 'page', 'section', 'timestamp', 'module', 'part', 'lesson']:
                if term in resource_str.lower():
                    has_specific_sections = True
                    break
                    
            # Check all fields that might contain specifics
            for field in specificity_fields:
                if field in resource and resource[field]:
                    has_specific_sections = True
                    break
        elif isinstance(resource, str):
            # String representation - check for specificity terms
            for term in ['chapter', 'page', 'section', 'timestamp', 'module', 'part', 'lesson']:
                if term in resource.lower():
                    has_specific_sections = True
                    break
        
        # Add issue if no specific sections found
        if not has_specific_sections:
            if isinstance(resource, dict) and 'title' in resource:
                issues.append(f"Resource #{idx+1} ({resource['title']}) lacks specific chapters, sections, pages, or timestamps.")
            else:
                issues.append(f"Resource #{idx+1} lacks specific chapters, sections, pages, or timestamps.")
        
        # Add to verified resources if it's not a syllabus, regardless of specificity
        # We'll flag the specificity issue but still include it
        verified_resources.append(resource)
    
    return {
        "valid_resources": verified_resources,
        "issues": issues
    }

# Create a function to find specific chapters/sections for resources
def find_resource_specifics(resource_title, subject):
    """Find specific chapters, sections or timestamps for a resource"""
    try:
        # Use a more precise search query to find specific sections
        formatted_query = f"specific chapters sections pages in {resource_title} about {subject}"
        
        # For video resources, look for timestamps
        if any(term in resource_title.lower() for term in ['video', 'youtube', 'lecture', 'tutorial']):
            formatted_query = f"timestamps in {resource_title} for {subject} topics"
        
        # For books, look for chapter numbers and page ranges
        if any(term in resource_title.lower() for term in ['book', 'textbook', 'guide']):
            formatted_query = f"chapter numbers and page ranges in {resource_title} covering {subject}"
        
        # Create a fresh instance for each search to avoid state issues
        search_tool = DuckDuckGoSearchRun()
        results = search_tool.run(formatted_query)
        
        if not results or results.strip() == "":
            # If no specifics found, provide a structured estimate based on resource type
            if any(term in resource_title.lower() for term in ['book', 'textbook']):
                return {
                    "resource": resource_title,
                    "specific_sections": f"Recommended chapters covering {subject} (estimate based on typical textbook structure):\n" +
                                       f"- Introduction to {subject}: Chapter 1\n" +
                                       f"- Core concepts of {subject}: Chapters 2-3\n" +
                                       f"- Advanced topics in {subject}: Later chapters"
                }
            elif any(term in resource_title.lower() for term in ['video', 'youtube']):
                return {
                    "resource": resource_title,
                    "specific_sections": f"For this video resource, focus on segments discussing {subject}.\n" +
                                       "Look for chapters/sections in video description or timestamps in comments."
                }
            else:
                return {
                    "resource": resource_title,
                    "specific_sections": f"Unable to find specific sections. When using this resource, focus on parts covering {subject}."
                }
        
        # Extract chapter, section, and page information using some basic parsing
        import re
        
        # Look for chapter references
        chapter_pattern = r'chapter\s+(\d+(?:\s*-\s*\d+)?)'
        chapter_matches = re.findall(chapter_pattern, results.lower())
        
        # Look for page references
        page_pattern = r'page[s]?\s+(\d+(?:\s*-\s*\d+)?)'
        page_matches = re.findall(page_pattern, results.lower())
        
        # Look for section references
        section_pattern = r'section\s+(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)'
        section_matches = re.findall(section_pattern, results.lower())
        
        # Look for timestamp references
        timestamp_pattern = r'(\d+:\d+(?::\d+)?)'
        timestamp_matches = re.findall(timestamp_pattern, results)
        
        # Compile a clear, formatted response
        specifics = {
            "resource": resource_title,
            "specific_sections": ""
        }
        
        specific_info = []
        if chapter_matches:
            chapters_info = f"Chapters: {', '.join(chapter_matches)}"
            specific_info.append(chapters_info)
        
        if page_matches:
            pages_info = f"Pages: {', '.join(page_matches)}"
            specific_info.append(pages_info)
            
        if section_matches:
            sections_info = f"Sections: {', '.join(section_matches)}"
            specific_info.append(sections_info)
            
        if timestamp_matches:
            timestamps_info = f"Timestamps: {', '.join(timestamp_matches)}"
            specific_info.append(timestamps_info)
        
        if specific_info:
            specifics["specific_sections"] = "Specific content covering this topic:\n- " + "\n- ".join(specific_info)
        else:
            # If we found results but couldn't extract specific references, provide the search results
            specifics["specific_sections"] = f"Based on search results:\n{results[:500]}..."
        
        return specifics
        
    except Exception as e:
        error_message = f"Error finding resource specifics: {str(e)}"
        logger.error(error_message)
        return {
            "resource": resource_title,
            "specific_sections": f"Unable to find specific sections due to an error. Please note this resource is still valuable for learning {subject}."
        }

def update_agent_context(user_id=None, session_id=None):
    """Update the agent's context with user and session data"""
    global enhanced_context, backend_data_fetcher
    
    # Re-initialize the data fetcher with user and session IDs
    try:
        backend_data_fetcher = BackendDataFetcher(user_id=user_id, session_id=session_id)
        logger.info("Initialized backend data fetcher")
    except Exception as e:
        logger.warning(f"Failed to initialize backend data fetcher: {str(e)}")
    
    try:
        # Get enhanced context
        if hasattr(backend_data_fetcher, 'get_enhanced_context'):
            context_data = backend_data_fetcher.get_enhanced_context()
            enhanced_context.update(context_data)
            logger.info("Updated enhanced context with backend data")
        
        # Get user data
        if user_id and hasattr(backend_data_fetcher, 'get_user_preferences'):
            user_prefs = backend_data_fetcher.get_user_preferences()
            if user_prefs:
                enhanced_context["user"] = user_prefs
                logger.info("Added user preferences to context")
        
        # Get session data
        if session_id and hasattr(backend_data_fetcher, 'get_session_data'):
            session_data = backend_data_fetcher.get_session_data()
            if session_data:
                enhanced_context["session"] = session_data
                logger.info("Added session data to context")
                
                # Get syllabus topics if available
                if hasattr(backend_data_fetcher, 'get_syllabus_content'):
                    syllabus_data = backend_data_fetcher.get_syllabus_content()
                    if syllabus_data:
                        topics = extract_syllabus_topics(json.dumps(syllabus_data))
                        enhanced_context["syllabus_topics"] = topics
                        logger.info(f"Extracted {len(topics)} topics from syllabus")
    except Exception as e:
        logger.warning(f"Error updating context: {str(e)}")
    
    return enhanced_context

# Create a web search tool using BaseTool
class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web using natural language queries to find educational resources. You can directly ask questions like:\n"
        "- 'What are the best YouTube videos for learning Computer Vision?'\n"
        "- 'Find me a good textbook about Machine Learning'\n"
        "- 'What online courses teach Python programming for beginners?'\n"
        "- 'Show me practice exercises for calculus with solutions'\n"
        "The tool will return web search results that you can use to identify specific learning resources."
    )
    args_schema: Type[BaseModel] = WebSearchSchema
    
    def _run(self, query_input):
        return web_search(query_input)

class TopicSearchTool(BaseTool):
    name: str = "topic_search" 
    description: str = "Search for resources specific to a syllabus topic"
    args_schema: Type[BaseModel] = TopicSearchSchema
    
    def _run(self, topic):
        return syllabus_topic_search(topic)

class ResourceVerifierTool(BaseTool):
    name: str = "verify_resources"
    description: str = "Verify that resources have specific sections, chapters, or timestamps"
    args_schema: Type[BaseModel] = ResourceVerifierSchema
    
    def _run(self, resources_list):
        return verify_resource_specificity(resources_list)

class FindSpecificsTool(BaseTool):
    name: str = "find_resource_specifics"
    description: str = "Find specific chapters, sections or timestamps for a resource"
    args_schema: Type[BaseModel] = FindSpecificsSchema
    
    def _run(self, resource_title, subject):
        return find_resource_specifics(resource_title, subject)

# Initialize the web search tool
web_search_tool = WebSearchTool()
topic_search_tool = TopicSearchTool()
resource_verifier_tool = ResourceVerifierTool()
find_specifics_tool = FindSpecificsTool()

# Create the resources agent
resources_agent = Agent(
    role="Study Resources Specialist",
    goal="Find high-quality subject-specific resources first, then explain how to apply different learning strategies to those resources.",
    backstory=(
        "You are an expert in finding educational resources tailored to specific subjects. "
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
    # Add all the tools to the agent
    tools=[web_search_tool, topic_search_tool, resource_verifier_tool, find_specifics_tool]
)

# Create tools for the resources agent
# web_search_tool = WebBrowserEngineTool()

# Define schema for resources
class ResourceSchema(BaseModel):
    name: str = Field(..., description="Name of the resource")
    url: str = Field(..., description="URL to the resource")
    type: str = Field(..., description="Type of resource (book, video, article, etc.)")
    description: str = Field(..., description="Brief description of what the resource covers")
    topics: List[str] = Field(..., description="List of topics covered by this resource")
    specifics: str = Field(..., description="Specific chapters, sections, or timestamps to focus on")

# Define function for resources agent to filter out syllabus resources
def filter_syllabus_resources(resources_list):
    """Filter out any resources that are syllabi or course outlines"""
    filtered_resources = []
    for resource in resources_list:
        # Skip any resource that appears to be a syllabus
        if any(term in resource.get('name', '').lower() for term in ['syllabus', 'syllabi', 'course outline']):
            logger.warning(f"Removing syllabus resource: {resource.get('name')}")
            continue
        filtered_resources.append(resource)
    return filtered_resources

# Create resources agent
def create_resources_agent():
    agent = Agent(
        role="Learning Resources Specialist",
        goal="Identify and recommend the most effective learning resources that match the student's learning style, needs, and time constraints.",
        backstory=(
            "As a renowned learning resources specialist with expertise in educational technology "
            "and instructional design, you excel at finding the perfect learning materials for any "
            "student. Your recommendations are valued for their relevance, quality, and alignment "
            "with individual learning preferences. You have a vast knowledge of textbooks, online "
            "courses, video tutorials, interactive tools, and practice materials across various "
            "disciplines. You're known for your ability to match resources to learning styles and "
            "time constraints, ensuring students get the most effective and efficient learning experience."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llama_llm,
        tools=[web_search_tool],
        tools_metadata={
            "student_preferences": {
                "assess_learning_style": "Analyze the student's learning style to inform resource selection.",
                "assess_time_constraints": "Consider how much time the student has available when recommending resources.",
                "analyze_prior_knowledge": "Evaluate the student's existing knowledge to avoid resources that are too basic or advanced."
            },
            "resource_evaluation": {
                "filter_syllabus": "NEVER use the course syllabus as a study resource - it's only for topic identification.",
                "assess_quality": "Evaluate the credibility, accuracy, and quality of potential resources.",
                "assess_alignment": "Determine how well a resource aligns with the student's learning objectives.",
                "assess_depth": "Evaluate if a resource provides appropriate depth for the student's needs.",
                "check_availability": "Verify that the resource is accessible to the student."
            },
            "resource_optimization": {
                "provide_urls": "ALWAYS include direct URLs to all resources.",
                "specify_sections": "Identify specific chapters, pages, or timestamps within resources.",
                "time_estimates": "Provide estimates of how long it will take to engage with each resource.",
                "paired_strategies": "Recommend specific learning strategies to use with each resource.",
                "complementary_resources": "Identify resources that complement each other for better understanding."
            }
        }
    )
    return agent

# Create and export the agent
resources_agent = create_resources_agent()

# Export function for use in other modules
__all__ = ['create_resources_agent', 'resources_agent', 'filter_syllabus_resources'] 