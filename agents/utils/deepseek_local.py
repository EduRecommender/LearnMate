import os
import json
import logging
import traceback
from typing import Dict, Any, List, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deepseek_model.log')
    ]
)
logger = logging.getLogger(__name__)

class DeepSeekLocal:
    """Utility class for using the open-source DeepSeek model locally"""
    
    def __init__(self, model_name: str = "deepseek-ai/deepseek-coder-6.7b-base"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing DeepSeekLocal with model: {model_name}")
        logger.info(f"Using device: {self.device}")
        
        # Get Hugging Face API token from environment variables
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not self.hf_token:
            logger.warning("No Hugging Face API token found. Some models may not be accessible.")
        else:
            logger.info(f"Hugging Face token found: {self.hf_token[:5]}...")
        
        try:
            logger.info("Loading tokenizer...")
            # Use token for authentication if available
            auth_kwargs = {"token": self.hf_token} if self.hf_token else {}
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, **auth_kwargs)
            logger.info(f"Tokenizer loaded successfully: {self.tokenizer.__class__.__name__}")
            
            # Check if we're using a small model that doesn't need device mapping
            is_small_model = "125m" in model_name or "350m" in model_name or "1.3b" in model_name
            logger.info(f"Is small model: {is_small_model}")
            
            # For small models, don't use device_map
            model_kwargs = {
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                **auth_kwargs
            }
            logger.info(f"Model dtype: {model_kwargs['torch_dtype']}")
            
            # Only use device_map for larger models
            if not is_small_model:
                try:
                    # Try to import accelerate to check if it's available
                    import accelerate
                    model_kwargs["device_map"] = "auto"
                    logger.info("Using accelerate for device mapping")
                except ImportError:
                    logger.warning("accelerate not available, falling back to standard loading")
                    logger.warning(traceback.format_exc())
            
            logger.info(f"Loading model with kwargs: {model_kwargs}")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                **model_kwargs
            )
            
            # Move model to device if not using device_map
            if not model_kwargs.get("device_map"):
                logger.info(f"Moving model to device: {self.device}")
                self.model = self.model.to(self.device)
                
            logger.info("Creating text generation pipeline")
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )
            logger.info(f"Successfully loaded model: {model_name}")
            
            # Log model size
            try:
                param_count = sum(p.numel() for p in self.model.parameters())
                logger.info(f"Model size: {param_count/1e6:.2f}M parameters")
            except Exception as e:
                logger.warning(f"Could not determine model size: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to load model {model_name}: {str(e)}")
    
    async def generate_text(self, prompt: str, max_length: int = 1000) -> str:
        """Generate text using the local DeepSeek model"""
        try:
            logger.info(f"Generating text with prompt: '{prompt[:50]}...'")
            logger.info(f"Max length: {max_length}")
            
            start_time = torch.cuda.Event(enable_timing=True) if self.device == "cuda" else None
            end_time = torch.cuda.Event(enable_timing=True) if self.device == "cuda" else None
            
            # Only measure time if using CUDA
            if start_time and end_time:
                start_time.record()
            
            outputs = self.generator(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                top_p=0.95,
                do_sample=True
            )
            
            if start_time and end_time:
                end_time.record()
                torch.cuda.synchronize()
                elapsed_time = start_time.elapsed_time(end_time) / 1000  # convert to seconds
                logger.info(f"Text generation took {elapsed_time:.2f} seconds")
            
            generated_text = outputs[0]["generated_text"]
            logger.info(f"Generated text length: {len(generated_text)} characters")
            logger.info(f"Generated text: '{generated_text[:100]}...'")
            
            return generated_text
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error generating text: {str(e)}"
    
    async def generate_strategy(self, content: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a study strategy based on content and user preferences"""
        try:
            logger.info("Generating study strategy")
            logger.debug(f"Content: {content}")
            logger.debug(f"User preferences: {user_preferences}")
            
            prompt = f"""
            Based on the following content and user preferences, recommend a study strategy:
            
            Content:
            Title: {content.get('title', 'Unknown')}
            Topics: {', '.join(content.get('topics', []))}
            Difficulty: {content.get('difficulty', 'intermediate')}
            
            User Preferences:
            Learning Styles: {', '.join(user_preferences.get('learning_styles', []))}
            Preferred Methods: {', '.join(user_preferences.get('preferred_study_methods', []))}
            Time Available: {user_preferences.get('time_available', '1-2 hours')}
            
            Recommend a study strategy that includes:
            1. The most effective study method for this content and user
            2. Step-by-step instructions
            3. Estimated duration
            4. Prerequisites (if any)
            5. Expected outcomes
            
            Return the strategy as a JSON object.
            """
            
            logger.debug(f"Strategy prompt: {prompt}")
            response = await self.generate_text(prompt, max_length=1000)
            logger.info("Strategy generation completed")
            
            # Try to extract JSON from the response
            try:
                logger.debug("Attempting to extract JSON from response")
                # Find JSON in the response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    logger.debug(f"Extracted JSON: {json_str}")
                    strategy_data = json.loads(json_str)
                    logger.info("Successfully parsed JSON response")
                    return strategy_data
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse JSON: {str(e)}")
                logger.warning(f"JSON extraction attempt: {response[start_idx:end_idx] if 'start_idx' in locals() else 'N/A'}")
            
            logger.info("Using fallback strategy response")
            # If JSON extraction fails, return a structured response
            return {
                "method": "active_recall",
                "instructions": "Review the content and test yourself on key concepts",
                "estimated_duration": 30,
                "prerequisites": [],
                "expected_outcomes": ["Understanding of key concepts", "Ability to recall information"]
            }
        except Exception as e:
            logger.error(f"Error generating strategy: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "method": "active_recall",
                "instructions": "Review the content and test yourself on key concepts",
                "estimated_duration": 30,
                "prerequisites": [],
                "expected_outcomes": ["Understanding of key concepts", "Ability to recall information"],
                "error": str(e)
            }
    
    async def generate_study_plan(self, topics: List[str], preferences: Dict[str, Any], 
                                 time_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a study plan based on topics and constraints"""
        try:
            logger.info("Generating study plan")
            logger.debug(f"Topics: {topics}")
            logger.debug(f"Preferences: {preferences}")
            logger.debug(f"Time constraints: {time_constraints}")
            
            prompt = f"""
            Create a study plan for the following topics and constraints:
            
            Topics: {', '.join(topics)}
            
            User Preferences:
            Learning Styles: {', '.join(preferences.get('learning_styles', []))}
            Preferred Methods: {', '.join(preferences.get('preferred_study_methods', []))}
            Difficulty: {preferences.get('difficulty', 'intermediate')}
            
            Time Constraints:
            Total Duration: {time_constraints.get('total_duration', 120)} minutes
            Days Available: {time_constraints.get('days', 7)}
            Time Per Day: {time_constraints.get('time_per_day', '1 hour')}
            
            Create a detailed study plan that includes:
            1. A breakdown of topics into subtopics
            2. Recommended resources for each subtopic
            3. Study methods for each subtopic
            4. Time allocation for each subtopic
            5. A day-by-day schedule
            
            Return the plan as a JSON object.
            """
            
            logger.debug(f"Study plan prompt: {prompt}")
            response = await self.generate_text(prompt, max_length=2000)
            logger.info("Study plan generation completed")
            
            # Try to extract JSON from the response
            try:
                logger.debug("Attempting to extract JSON from response")
                # Find JSON in the response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    logger.debug(f"Extracted JSON: {json_str}")
                    plan_data = json.loads(json_str)
                    logger.info("Successfully parsed JSON study plan")
                    return plan_data
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse JSON: {str(e)}")
                logger.warning(f"JSON extraction attempt: {response[start_idx:end_idx] if 'start_idx' in locals() else 'N/A'}")
            
            logger.info("Using fallback study plan")
            # If JSON extraction fails, return a basic structure
            return {
                "topics": topics,
                "subtopics": {},
                "resources": {},
                "methods": {},
                "time_allocation": {},
                "schedule": []
            }
        except Exception as e:
            logger.error(f"Error generating study plan: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "topics": topics,
                "subtopics": {},
                "resources": {},
                "methods": {},
                "time_allocation": {},
                "schedule": [],
                "error": str(e)
            }
    
    async def process_user_message(self, message: str, context: Dict[str, Any]) -> str:
        """Process a user message and generate a response"""
        try:
            logger.info("Processing user message")
            logger.debug(f"Message: '{message[:100]}...'")
            logger.debug(f"Context keys: {list(context.keys())}")
            
            # Extract useful context information for logs
            session_name = context.get('session_info', {}).get('name', 'Unknown')
            topics = context.get('session_info', {}).get('topics', [])
            
            logger.info(f"Processing message for session: {session_name}, topics: {topics}")
            
            prompt = f"""
            You are an AI study assistant. Respond to the following user message based on the context:
            
            User Message: {message}
            
            Context:
            Current Session: {context.get('session_info', {}).get('name', 'Unknown')}
            Topics: {', '.join(context.get('session_info', {}).get('topics', []))}
            Progress: {context.get('session_info', {}).get('progress', 'Not started')}
            Goal: {context.get('session_info', {}).get('goal', 'Not specified')}
            
            Provide a helpful, concise response that addresses the user's question or request.
            """
            
            logger.debug(f"Prompt: {prompt}")
            response = await self.generate_text(prompt, max_length=500)
            logger.info(f"Generated response of length {len(response)}")
            
            # Create a completely new, clean response by removing all prompt elements
            try:
                # Hard-coded removal approach - completely discard the prompt parts we know about
                clean_response = None
                
                # Remove any prefix that matches our prompt template
                response_lower = response.lower()
                for remove_text in [
                    "you are an ai study assistant",
                    "respond to the following user message",
                    "user message:",
                    "context:",
                    "current session:",
                    "topics:",
                    "progress:",
                    "goal:",
                    "provide a helpful"
                ]:
                    if remove_text in response_lower:
                        idx = response_lower.rfind(remove_text)
                        if idx > 0:
                            # Skip past all this prompt text
                            response = response[idx:]
                            response_lower = response.lower()
                
                # Remove the user's message if it's still in there
                if message.lower() in response_lower:
                    idx = response_lower.find(message.lower())
                    if idx >= 0:
                        end_idx = idx + len(message)
                        response = response[end_idx:]
                
                # Find the first complete sentence after all the prompts
                sentences = response.split('.')
                for i, sentence in enumerate(sentences):
                    # Skip empty sentences or those that still look like prompt parts
                    if (len(sentence.strip()) > 10 and 
                        "context" not in sentence.lower() and
                        "user message" not in sentence.lower() and
                        "session" not in sentence.lower() and
                        "topics" not in sentence.lower() and
                        "progress" not in sentence.lower() and
                        "goal" not in sentence.lower()):
                        
                        # Found a valid sentence, use the rest of the response from here
                        clean_response = '.'.join(sentences[i:])
                        break
                
                # If we have a valid clean response, return it
                if clean_response and len(clean_response.strip()) > 10:
                    logger.info(f"Successfully cleaned response: '{clean_response[:50]}...'")
                    return clean_response.strip()
                
                # Last resort - use a simpler approach
                # Just look for common AI response starters
                starters = [
                    "\n\nI can", "I can help", "I'd be happy", "Yes,", "No,", 
                    "Based on", "Here's", "Absolutely", "Sure", "Let me"
                ]
                
                for starter in starters:
                    if starter in response:
                        idx = response.find(starter)
                        if idx >= 0:
                            clean_response = response[idx:]
                            if len(clean_response.strip()) > 10:
                                logger.info(f"Found response starting with '{starter}': '{clean_response[:50]}...'")
                                return clean_response.strip()
                
                # If all else fails, just remove the most recognizable parts of the prompt
                # and return the rest
                clean_response = response.replace("You are an AI study assistant.", "")
                clean_response = clean_response.replace("Respond to the following user message based on the context:", "")
                clean_response = clean_response.replace("User Message:", "")
                clean_response = clean_response.replace("Context:", "")
                clean_response = clean_response.replace("Provide a helpful, concise response that addresses the user's question or request.", "")
                
                # Final fallback - if clean response is too short or empty, just return a generic response
                if len(clean_response.strip()) < 10:
                    logger.warning("Failed to extract a meaningful response, using generic fallback")
                    return f"I'll help you with your studies on {', '.join(topics)}. What specific questions do you have?"
                
                logger.info(f"Using fallback cleaning method: '{clean_response[:50]}...'")
                return clean_response.strip()
                
            except Exception as e:
                logger.error(f"Error cleaning response: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Last resort fallback to ensure we don't show the prompt
                logger.warning("Using emergency fallback response")
                return f"I can help you with your studies on {', '.join(topics)}. What would you like to know?"
            
            return response
        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}")
            logger.error(traceback.format_exc())
            return f"I'm sorry, I couldn't process your message. Please try again." 