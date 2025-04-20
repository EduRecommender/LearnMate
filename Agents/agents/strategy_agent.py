# agents/strategy_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from llm_config import llama_llm
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.syllabus_parser import parse_syllabus
import logging
from pydantic import BaseModel, Field
from typing import Type

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tool call tracking to prevent repetitive calls
previous_syllabus_analysis = {"input": None, "result": None, "count": 0}

# Define a function to analyze syllabi
def analyze_syllabus(syllabus_text):
    """Analyze a syllabus to identify key topics and requirements"""
    global previous_syllabus_analysis
    
    try:
        # Extract string value if syllabus_text is a dict
        if isinstance(syllabus_text, dict):
            if "syllabus_text" in syllabus_text:
                syllabus_text = syllabus_text["syllabus_text"]
                # If still a dict, try to extract the description
                if isinstance(syllabus_text, dict) and "description" in syllabus_text:
                    syllabus_text = syllabus_text["description"]
        
        # Convert to string to ensure comparison works
        syllabus_str = str(syllabus_text)
        
        # Check for repetitive calls
        if previous_syllabus_analysis["input"] == syllabus_str:
            previous_syllabus_analysis["count"] += 1
            if previous_syllabus_analysis["count"] >= 2:
                logger.warning(f"Detected repetitive call to analyze_syllabus (count: {previous_syllabus_analysis['count']})")
                return previous_syllabus_analysis["result"] + "\n\nNOTE: I've already analyzed this syllabus. If you need different information from it, please specify what additional details you're looking for."
        else:
            # Reset counter for new input
            previous_syllabus_analysis["count"] = 1
        
        parsed_data = parse_syllabus(syllabus_text)
        if parsed_data:
            result = f"Syllabus Analysis:\n{parsed_data}"
        else:
            result = "No clear syllabus structure found. Please provide specific topics to focus on."
        
        # Store the result and input for future comparison
        previous_syllabus_analysis["input"] = syllabus_str
        previous_syllabus_analysis["result"] = result
        
        return result
    except Exception as e:
        logger.error(f"Error analyzing syllabus: {e}")
        return "Error analyzing syllabus. Please provide specific topics to focus on."

# Define the schema for the syllabus analyzer tool
class SyllabusAnalyzerSchema(BaseModel):
    syllabus_text: str = Field(..., description="The syllabus text to analyze")

# Create proper CrewAI BaseTool classes
class SyllabusAnalyzerTool(BaseTool):
    name: str = "analyze_syllabus"
    description: str = "Analyze a syllabus to identify key topics and requirements"
    args_schema: Type[BaseModel] = SyllabusAnalyzerSchema
    
    def _run(self, syllabus_text):
        return analyze_syllabus(syllabus_text)

# Instantiate the tool class
syllabus_analyzer_tool = SyllabusAnalyzerTool()

# Create the strategy agent with the BaseTool instance
strategy_agent = Agent(
    role="Learning Strategy Specialist",
    goal="Identify the most effective learning strategies for a specific subject and student profile.",
    backstory=(
        "You are an expert in learning strategies with a deep understanding of educational psychology "
        "and cognitive science. You know exactly which learning techniques work best for different "
        "subjects and student profiles. You understand that different subjects require unique approaches "
        "and that students have unique learning preferences. You're skilled at analyzing syllabi and "
        "breaking down complex topics into structured learning plans. Your recommendations are based on "
        "evidence-based learning techniques that maximize retention and comprehension."
    ),
    llm=llama_llm,
    verbose=True,
    allow_delegation=False,
    tools=[syllabus_analyzer_tool],
    # Optionally, you can add metadata that might be useful for the agent
    tools_metadata={
        "evidence_based_strategies": [
            "spaced_repetition", 
            "retrieval_practice", 
            "interleaving", 
            "concrete_examples",
            "dual_coding", 
            "elaboration", 
            "self_explanation", 
            "feynman_technique"
        ]
    }
)
