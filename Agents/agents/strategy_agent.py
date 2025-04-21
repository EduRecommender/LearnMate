# agents/strategy_agent.py

from crewai import Agent
from crewai.tools import BaseTool
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.syllabus_parser import parse_syllabus
import logging
from pydantic import BaseModel, Field
from typing import Type, Dict, Any, List, Optional, Union
from Agents.llm_config import llama_llm
import json

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
    syllabus_text: Union[str, Dict[str, Any], Any] = Field(..., description="The syllabus text to analyze")

# Create proper CrewAI BaseTool classes
class SyllabusAnalyzerTool(BaseTool):
    name: str = "analyze_syllabus"
    description: str = "Analyze a syllabus to identify key topics and requirements"
    args_schema: Type[BaseModel] = SyllabusAnalyzerSchema
    
    def _run(self, syllabus_text):
        return analyze_syllabus(syllabus_text)

# Define a list of evidence-based learning strategies based on academic research
EVIDENCE_BASED_STRATEGIES = {
    "spaced_repetition": {
        "name": "Spaced Repetition",
        "description": "Reviewing content at increasing intervals over time to improve long-term retention",
        "research": "Based on research by Ebbinghaus (1885) and reinforced by studies from Dunlosky et al. (2013)",
        "best_for": ["fact-heavy subjects", "vocabulary", "formulas", "definitions"],
        "implementation": "Use flashcards with increasing intervals between reviews (1 day, 3 days, 7 days, etc.)",
        "time_efficiency": "high",
        "high_pressure_compatible": True
    },
    "retrieval_practice": {
        "name": "Retrieval Practice",
        "description": "Actively recalling information rather than passive re-reading",
        "research": "Studies by Roediger & Karpicke (2006) show this outperforms re-reading by 50%",
        "best_for": ["exams", "factual recall", "concept mastery"],
        "implementation": "Close book/notes and write everything you remember about a topic, then check accuracy",
        "time_efficiency": "high",
        "high_pressure_compatible": True
    },
    "interleaving": {
        "name": "Interleaving",
        "description": "Mixing different topics or problem types within a study session",
        "research": "Research by Rohrer & Taylor (2007) shows superior long-term retention vs. blocked practice",
        "best_for": ["problem-solving subjects", "mathematics", "physics"],
        "implementation": "Mix problems from different chapters rather than completing one topic at a time",
        "time_efficiency": "medium",
        "high_pressure_compatible": False
    },
    "concrete_examples": {
        "name": "Concrete Examples",
        "description": "Connecting abstract concepts to specific, concrete examples",
        "research": "Studies on elaborative encoding (Craik & Lockhart, 1972)",
        "best_for": ["abstract concepts", "theoretical subjects"],
        "implementation": "For each theory or concept, find or create 2-3 real-world examples",
        "time_efficiency": "medium",
        "high_pressure_compatible": True
    },
    "dual_coding": {
        "name": "Dual Coding",
        "description": "Combining verbal and visual information to enhance memory",
        "research": "Based on Paivio's Dual Coding Theory (1971), showing 65% better recall",
        "best_for": ["visual learners", "complex systems", "processes"],
        "implementation": "Create diagrams, mind maps, or drawings to visualize text-based information",
        "time_efficiency": "low",
        "high_pressure_compatible": False
    },
    "elaboration": {
        "name": "Elaborative Interrogation",
        "description": "Asking 'why' and 'how' questions about the material",
        "research": "Research by Pressley et al. (1987) demonstrates improved conceptual understanding",
        "best_for": ["conceptual understanding", "theory-heavy subjects"],
        "implementation": "Ask yourself 'Why is this true?' or 'How does this relate to what I already know?'",
        "time_efficiency": "medium",
        "high_pressure_compatible": True
    },
    "self_explanation": {
        "name": "Self-Explanation",
        "description": "Explaining concepts in your own words to identify knowledge gaps",
        "research": "Chi et al. (1989) showed deeper understanding through self-explanation",
        "best_for": ["complex topics", "identifying misconceptions"],
        "implementation": "After reading a passage, explain the concept as if teaching someone else",
        "time_efficiency": "medium",
        "high_pressure_compatible": True
    },
    "pomodoro": {
        "name": "Pomodoro Technique",
        "description": "Structured time management with focused work periods and short breaks",
        "research": "Based on attention span research by Doran (1999)",
        "best_for": ["focus issues", "procrastination", "lengthy study sessions"],
        "implementation": "25 minutes of focused study followed by a 5-minute break, repeat 4 times then take a longer break",
        "time_efficiency": "high",
        "high_pressure_compatible": False
    },
    "feynman_technique": {
        "name": "Feynman Technique",
        "description": "Teaching a concept in simple language to ensure deep understanding",
        "research": "Based on Nobel physicist Richard Feynman's learning methods",
        "best_for": ["complex subjects", "deep understanding"],
        "implementation": "1. Study a concept, 2. Explain it simply as if to a child, 3. Identify gaps, 4. Review and simplify explanation",
        "time_efficiency": "medium",
        "high_pressure_compatible": True
    }
}

# Instantiate the tool class
syllabus_analyzer_tool = SyllabusAnalyzerTool()

def load_knowledge_base():
    """Load content from knowledge base files and create a structured knowledge base"""
    knowledge_base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
    knowledge_base = {}
    
    if not os.path.exists(knowledge_base_dir):
        logger.warning(f"Knowledge base directory not found: {knowledge_base_dir}")
        return knowledge_base
    
    # Load textual content from non-PDF files
    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(knowledge_base_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    # Extract the topic name from the filename
                    topic = filename.replace('-', ' ').replace('_', ' ').replace('.txt', '')
                    knowledge_base[topic] = {
                        'source': filename,
                        'content': content,
                        'type': 'text'
                    }
                    logger.info(f"Loaded knowledge base file: {filename}")
            except Exception as e:
                logger.error(f"Error loading knowledge base file {filename}: {e}")
    
    # Just register PDF files without trying to parse them
    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith('.pdf'):
            file_path = os.path.join(knowledge_base_dir, filename)
            topic = filename.replace('-', ' ').replace('_', ' ').replace('.pdf', '')
            knowledge_base[topic] = {
                'source': filename,
                'content': f"PDF Reference: {filename}",
                'type': 'pdf'
            }
            logger.info(f"Registered PDF knowledge base file: {filename}")
    
    return knowledge_base

def extract_evidence_based_strategies():
    """Extract and summarize key evidence-based strategies from knowledge base files"""
    kb = load_knowledge_base()
    strategies_summary = {}
    
    # Add the 3R strategy as a baseline (always included since it's specifically mentioned in research)
    strategies_summary["3r_technique"] = {
        "name": "Read-Recite-Review (3R) Strategy",
        "description": "A three-step study strategy that involves reading a text, reciting from memory what was read, and reviewing the text again to correct any errors in recall",
        "research": "Based on research by McDaniel et al. (2009) showing superior retention compared to rereading",
        "best_for": ["text-based learning", "comprehension", "recall improvement"],
        "implementation": "1. Read a section of text, 2. Set aside the material and recite everything you can remember, 3. Review the text again to identify what you missed",
        "time_efficiency": "high",
        "high_pressure_compatible": True,
        "source": "mcdaniel-et-al-2009-the-read-recite-review-study-strategy-effective-and-portable.pdf"
    }
    
    # Extract strategies from study methods text file if available
    if "styding methods" in kb:
        study_methods_content = kb["styding methods"]["content"]
        
        # Extract spaced repetition strategies
        if "spaced repetition" in study_methods_content.lower():
            strategies_summary["spaced_practice"] = {
                "name": "Spaced Practice",
                "description": "Distributing learning over time rather than massing (cramming) in one session",
                "research": "Based on research showing superior long-term retention compared to massed practice",
                "best_for": ["long-term retention", "fact learning", "skill development"],
                "implementation": "Schedule shorter study sessions spread out over days or weeks rather than cramming",
                "time_efficiency": "high",
                "high_pressure_compatible": False,
                "source": "styding-methods.txt"
            }
        
        # Extract active recall strategies
        if "active recall" in study_methods_content.lower() or "retrieval practice" in study_methods_content.lower():
            strategies_summary["active_recall"] = {
                "name": "Active Recall",
                "description": "Actively stimulating memory during the learning process by testing yourself",
                "research": "Studies show testing yourself is more effective than rereading or passive review",
                "best_for": ["memorization", "fact retention", "concept mastery"],
                "implementation": "Use flashcards, practice tests, or close your book and recall key points",
                "time_efficiency": "high",
                "high_pressure_compatible": True,
                "source": "styding-methods.txt"
            }
    
    # Look for Pomodoro technique
    for topic, data in kb.items():
        content = data.get('content', '').lower()
        if "pomodoro" in content:
            strategies_summary["pomodoro"] = {
                "name": "Pomodoro Technique",
                "description": "A time management method using a timer to break work into intervals, traditionally 25 minutes in length, separated by short breaks",
                "research": "Based on psychology research showing improved focus and reduced mental fatigue",
                "best_for": ["focus issues", "procrastination", "large projects"],
                "implementation": "1. Set timer for 25 min, 2. Work with full focus, 3. Take 5 min break, 4. After 4 cycles, take longer break",
                "time_efficiency": "high",
                "high_pressure_compatible": True,
                "source": topic
            }
    
    # Always include these fundamental strategies based on research in EVIDENCE_BASED_STRATEGIES
    strategies_summary.update({k: v for k, v in EVIDENCE_BASED_STRATEGIES.items() if k not in strategies_summary})
    
    return strategies_summary

# Enhanced strategy creation with knowledge base
def create_strategy_agent():
    """Create and return a strategy agent with knowledge base integration"""
    # Load knowledge base content
    kb = load_knowledge_base()
    evidence_based_strategies = extract_evidence_based_strategies()
    
    # Create a summary of available knowledge base resources
    kb_summary = []
    for topic, data in kb.items():
        if data['type'] == 'text':
            # For text files, include a snippet of the content
            content_preview = data['content'][:200] + "..." if len(data['content']) > 200 else data['content']
            kb_summary.append(f"Topic: {topic}\nSource: {data['source']}\nPreview: {content_preview}\n")
        else:
            # For PDFs, just note their existence
            kb_summary.append(f"Topic: {topic}\nSource: {data['source']} (PDF reference)\n")
    
    kb_summary_text = "\n".join(kb_summary)
    
    # Create a summary of evidence-based strategies from knowledge base
    strategies_summary = []
    for strategy_id, strategy_info in evidence_based_strategies.items():
        strategies_summary.append(
            f"Strategy: {strategy_info['name']}\n"
            f"Research base: {strategy_info['research']}\n"
            f"Best for: {', '.join(strategy_info['best_for'])}\n"
            f"Implementation: {strategy_info['implementation']}\n"
            f"Source: {strategy_info.get('source', 'Research literature')}\n"
        )
    
    strategies_summary_text = "\n".join(strategies_summary)
    
    # Enhanced backstory with knowledge base information
    enhanced_backstory = (
        "You are an expert in learning strategies with a deep understanding of educational psychology "
        "and cognitive science. You know exactly which learning techniques work best for different "
        "subjects and student profiles. You understand that different subjects require unique approaches "
        "and that students have unique learning preferences. You're skilled at analyzing syllabi and "
        "breaking down complex topics into structured learning plans. Your recommendations are based on "
        "evidence-based learning techniques that maximize retention and comprehension. "
        "You carefully consider time constraints and adapt your strategy recommendations accordingly, "
        "never suggesting time-intensive methods when a student is under time pressure. "
        "You base all your recommendations on scientific research and cognitive science principles. "
        "\n\nYou have access to the following knowledge base resources: \n" + kb_summary_text +
        "\n\nYou MUST specifically utilize and recommend these evidence-based learning strategies from research studies: \n" + strategies_summary_text +
        "\n\nALWAYS recommend the Read-Recite-Review (3R) Strategy from McDaniel et al. (2009) as one of your core strategies, as research shows it's highly effective across different subjects."
    )
    
    # Create the strategy agent with the BaseTool instance and knowledge base
    strategy_agent = Agent(
        role="Learning Strategy Specialist",
        goal="Identify the most effective, evidence-based learning strategies for a specific subject and student profile based on time constraints and learning preferences. Always use research-backed strategies from the knowledge base.",
        backstory=enhanced_backstory,
        llm=llama_llm,
        verbose=True,
        allow_delegation=False,
        tools=[syllabus_analyzer_tool],
        # Add the research-based strategies directly in tools_metadata
        tools_metadata={
            "evidence_based_strategies": EVIDENCE_BASED_STRATEGIES,
            "time_constraint_guidelines": {
                "high_pressure": {
                    "description": "For very short timeframes (1-3 days before exam)",
                    "recommended_strategies": ["retrieval_practice", "3r_technique", "self_explanation", "active_recall"],
                    "avoid_strategies": ["dual_coding", "interleaving", "pomodoro"],
                    "session_structure": "Focused 1.5-2 hour blocks with 5-minute breaks every 30 minutes",
                    "daily_plan": "Focus on most high-yield topics and practice questions only",
                    "prioritization": "Identify and focus on topics worth the most points on the exam"
                },
                "medium_pressure": {
                    "description": "For moderate timeframes (4-7 days before exam)",
                    "recommended_strategies": ["retrieval_practice", "3r_technique", "concrete_examples", "elaboration", "spaced_repetition"],
                    "avoid_strategies": ["dual_coding"],
                    "session_structure": "1-hour focused blocks with 10-minute breaks",
                    "daily_plan": "Start with difficult topics in the morning, review easier topics later in the day",
                    "prioritization": "Cover all major topics with emphasis on areas of weakness"
                },
                "low_pressure": {
                    "description": "For longer timeframes (8+ days before exam)",
                    "recommended_strategies": ["interleaving", "dual_coding", "3r_technique", "feynman_technique", "pomodoro", "spaced_repetition"],
                    "session_structure": "Pomodoro technique with proper breaks",
                    "daily_plan": "Systematic coverage of all topics with dedicated review days",
                    "prioritization": "Comprehensive coverage with deeper exploration of complex topics"
                }
            },
            "learning_style_adaptations": {
                "visual": {
                    "recommended_strategies": ["dual_coding", "concrete_examples", "mind_mapping"],
                    "study_materials": "Diagrams, charts, color-coded notes, flashcards with images",
                    "implementation_tips": "Convert text information into visual representations, use color-coding for different categories or concepts"
                },
                "auditory": {
                    "recommended_strategies": ["self_explanation", "elaboration", "3r_technique"],
                    "study_materials": "Recorded lectures, discussion groups, verbal summarization",
                    "implementation_tips": "Read material aloud, discuss concepts with study partners, record and replay explanations"
                },
                "reading/writing": {
                    "recommended_strategies": ["retrieval_practice", "feynman_technique", "3r_technique", "note_taking"],
                    "study_materials": "Written summaries, practice essays, detailed notes, rewriting concepts in own words",
                    "implementation_tips": "Create written outlines of key concepts, practice writing answers to potential exam questions"
                },
                "kinesthetic": {
                    "recommended_strategies": ["concrete_examples", "interleaving", "teaching_others"],
                    "study_materials": "Hands-on activities, role-playing, physical movement while studying",
                    "implementation_tips": "Create physical models, use movement when memorizing, teach concepts through demonstration"
                },
                "multimodal": {
                    "recommended_strategies": ["3r_technique", "spaced_repetition", "retrieval_practice", "dual_coding"],
                    "study_materials": "Combination of materials from other learning styles",
                    "implementation_tips": "Alternate between different study methods to engage multiple learning modalities"
                }
            },
            "subject_specific_adaptations": {
                "mathematics": {
                    "recommended_strategies": ["worked_examples", "retrieval_practice", "spaced_repetition"],
                    "implementation_tips": "Focus on problem-solving techniques, practice varied problem types, explain solutions step-by-step"
                },
                "sciences": {
                    "recommended_strategies": ["3r_technique", "concrete_examples", "dual_coding", "elaboration"],
                    "implementation_tips": "Connect concepts to real-world applications, visualize processes, explain mechanisms in own words"
                },
                "humanities": {
                    "recommended_strategies": ["3r_technique", "elaboration", "self_explanation", "note_taking"],
                    "implementation_tips": "Create thesis statements for key arguments, connect ideas across different texts or periods"
                },
                "languages": {
                    "recommended_strategies": ["spaced_repetition", "retrieval_practice", "immersion"],
                    "implementation_tips": "Practice active vocabulary recall, engage with authentic materials, create conversational contexts"
                }
            },
            "knowledge_base": kb
        }
    )
    
    return strategy_agent

# Create the strategy agent using the enhanced function
strategy_agent = create_strategy_agent()
  