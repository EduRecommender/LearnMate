import os
import json
import requests
from typing import Dict, Any, List, Optional
import time
import logging

logger = logging.getLogger(__name__)

class DeepSeekAPI:
    """Utility class for interacting with the DeepSeek API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key is required")
        
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using DeepSeek's web search capability"""
        try:
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json={
                    "query": query,
                    "max_results": max_results
                }
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            logger.error(f"Error searching web with DeepSeek: {str(e)}")
            return []
    
    async def generate_content(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate content using DeepSeek's text generation capability"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating content with DeepSeek: {str(e)}")
            return ""
    
    async def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content using DeepSeek"""
        prompt = f"""
        Extract the following metadata from this content:
        - Title
        - Main topics
        - Difficulty level (beginner, intermediate, advanced)
        - Estimated duration in minutes
        - Key concepts
        
        Content: {content[:2000]}  # Limit content length
        
        Return the metadata as a JSON object.
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            
            # Try to parse the JSON response
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # If parsing fails, return a basic structure
                return {
                    "title": "Unknown",
                    "topics": [],
                    "difficulty": "intermediate",
                    "duration_minutes": 30,
                    "key_concepts": []
                }
        except Exception as e:
            logger.error(f"Error extracting metadata with DeepSeek: {str(e)}")
            return {
                "title": "Unknown",
                "topics": [],
                "difficulty": "intermediate",
                "duration_minutes": 30,
                "key_concepts": []
            }
    
    async def rate_limit_handler(self, func, *args, **kwargs):
        """Handle rate limiting for API calls"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit exceeded
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry.")
                        time.sleep(wait_time)
                        continue
                raise
            except Exception as e:
                raise 