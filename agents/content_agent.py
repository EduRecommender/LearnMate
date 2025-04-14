import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from agents.base import ContentAgent, AgentResponse
from agents.schemas.messages import ContentType, ContentMetadata, StudyContent, ContentQuery
from agents.utils.validation import validate_content_query, validate_study_content
from agents.utils.deepseek_api import DeepSeekAPI

logger = logging.getLogger(__name__)

class DeepSeekContentAgent(ContentAgent):
    """Content Agent that uses DeepSeek API for content retrieval"""
    
    def __init__(self, agent_id: str = "deepseek-content-agent", api_key: Optional[str] = None):
        super().__init__(agent_id)
        self.api = DeepSeekAPI(api_key)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process the input data and return a response"""
        try:
            if not await self.validate_input(input_data):
                return self._create_error_response("Invalid input data")
            
            query = ContentQuery(**input_data)
            return await self.search_content(query)
        except Exception as e:
            logger.error(f"Error processing content query: {str(e)}")
            return await self.handle_error(e)
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate the input data"""
        try:
            validate_content_query(input_data)
            return True
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False
    
    async def search_content(self, query: ContentQuery) -> AgentResponse:
        """Search for relevant content using DeepSeek API"""
        try:
            # Construct search query based on topic and difficulty
            search_query = f"{query.topic} {query.difficulty} educational resources"
            
            # Add content type filters if specified
            if query.content_types:
                content_types = [ct.value for ct in query.content_types]
                search_query += f" {' OR '.join(content_types)}"
            
            # Add source filters if specified
            if query.preferred_sources:
                search_query += f" site:({' OR site:'.join(query.preferred_sources)})"
            
            # Perform web search
            results = await self.api.search_web(search_query, max_results=10)
            
            if not results:
                return self._create_error_response("No content found matching your criteria")
            
            # Process and filter results
            content_items = []
            for result in results:
                # Skip excluded sources
                if query.excluded_sources and any(source in result.get('url', '') for source in query.excluded_sources):
                    continue
                
                # Extract metadata using DeepSeek
                metadata = await self.api.extract_metadata(result.get('snippet', ''))
                
                # Create content item
                content_item = StudyContent(
                    content_id=str(uuid.uuid4()),
                    metadata=ContentMetadata(
                        title=metadata.get('title', result.get('title', 'Unknown')),
                        content_type=self._determine_content_type(result, query.content_types),
                        difficulty=metadata.get('difficulty', query.difficulty),
                        duration_minutes=metadata.get('duration_minutes', 30),
                        source=result.get('source', 'Web'),
                        url=result.get('url'),
                        tags=metadata.get('topics', []),
                        description=metadata.get('description', result.get('snippet', ''))
                    ),
                    content=result.get('snippet', ''),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # Validate content
                if await self.validate_content(content_item.__dict__):
                    content_items.append(content_item)
            
            if not content_items:
                return self._create_error_response("No valid content found after filtering")
            
            # Sort by relevance (simple implementation)
            content_items.sort(key=lambda x: len(x.metadata.tags or []), reverse=True)
            
            return self._create_success_response(
                data=content_items,
                metadata={"query": query.__dict__, "count": len(content_items)}
            )
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            return await self.handle_error(e)
    
    async def validate_content(self, content: Dict[str, Any]) -> bool:
        """Validate retrieved content"""
        try:
            validate_study_content(content)
            return True
        except Exception as e:
            logger.error(f"Content validation error: {str(e)}")
            return False
    
    def _determine_content_type(self, result: Dict[str, Any], preferred_types: List[ContentType]) -> ContentType:
        """Determine the content type from the search result"""
        url = result.get('url', '').lower()
        
        # Check URL patterns
        if any(ext in url for ext in ['.pdf', '.doc', '.docx']):
            return ContentType.TEXTBOOK
        elif any(ext in url for ext in ['.mp4', '.avi', '.mov', 'youtube.com', 'vimeo.com']):
            return ContentType.VIDEO
        elif any(ext in url for ext in ['.quiz', 'quizlet.com', 'kahoot.com']):
            return ContentType.QUIZ
        elif any(ext in url for ext in ['.flashcard', 'anki', 'memrise.com']):
            return ContentType.FLASHCARD
        elif any(ext in url for ext in ['.exercise', 'problem', 'practice']):
            return ContentType.EXERCISE
        
        # If no match found, use the first preferred type or default to ARTICLE
        if preferred_types:
            return preferred_types[0]
        return ContentType.ARTICLE 