# tasks/strategy_task.py

from crewai import Task
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class StrategyTaskOutput(BaseModel):
    recommended_strategies: List[Dict] = Field(
        ...,
        description="The list of 3-5 recommended learning strategies"
    )
    rationale: str = Field(
        ...,
        description="Explanation of why these strategies are appropriate for this student and subject"
    )

def create_strategy_task():
    description = """
    Analyze the student's learning preferences, subject material, and time constraints to recommend effective study strategies that will maximize their learning outcomes.
    
    Your task is to:
    1. Review the student profile including learning style, challenges, and exam timeline
    2. Analyze the subject matter and its complexity
    3. Consider the time constraints (days until exam and available study hours per day)
    4. Recommend 3-5 evidence-based learning strategies tailored to the student's specific situation
    5. Include the Read-Recite-Review (3R) technique from McDaniel et al. (2009) as one of your recommended strategies, explaining how to implement it for the student's specific subject:
       a. READ: First carefully read a section of text (1-2 pages)
       b. RECITE: Close the book/notes and recall/summarize the key points aloud or in writing
       c. REVIEW: Reopen the material and check accuracy of recall, correcting any errors
       d. Repeat for each section of material
       e. Explain how to adapt 3R for different subject types (math vs. history vs. languages)
    6. Provide concrete implementation steps for each strategy
    7. Explain how these strategies address the student's specific challenges
    8. Include time-specific recommendations based on the exam timeline:
       a. HIGH PRESSURE (1-3 days): Focus on most critical concepts, rapid review techniques
       b. MEDIUM PRESSURE (4-7 days): Balanced approach with strategic content coverage 
       c. LOW PRESSURE (8+ days): Comprehensive coverage with spaced repetition
    9. Adapt strategies to match the student's learning style preferences with specific modifications:
       a. VISUAL: How to convert text to diagrams, use color-coding, mind maps
       b. AUDITORY: Recording summaries, group discussions, verbal explanations
       c. READING/WRITING: Note-taking formats, written summaries, text annotations
       d. KINESTHETIC: Movement-based learning, manipulatives, teaching concepts to others
    
    Your recommendations should be backed by cognitive science and educational research findings in the knowledge base. Be specific about implementation and avoid generic advice. Each strategy should include clear steps the student can follow immediately.
    """
    
    expected_output = """
    You must provide the following sections in your response:
    
    1. STRATEGY SUMMARY: A brief overview of your recommended approach based on the student's profile and time constraints.
    
    2. RECOMMENDED STRATEGIES: List 3-5 specific evidence-based strategies, with the 3R technique as one of them. For each strategy include:
       - Name and brief description
       - Why this is appropriate for this student's situation
       - Step-by-step implementation instructions
       - Expected benefits
       - Time allocation recommendation
    
    3. TIME MANAGEMENT GUIDANCE: Based on days until exam, provide:
       - Daily study schedule structure
       - Priority topics to focus on
       - Break recommendations (e.g., Pomodoro technique: 25 min study + 5 min break)
       - Review frequency (e.g., review previous day's material for 15 min daily)
       - Emergency strategies if time pressure increases
    
    4. LEARNING STYLE ADAPTATIONS: Specific modifications to implement the strategies based on the student's learning style preferences:
       - For visual learners: How to visualize concepts
       - For auditory learners: How to utilize audio-based learning
       - For reading/writing learners: How to optimize text-based learning
       - For kinesthetic learners: How to incorporate movement and hands-on activities
    
    5. ADDRESSING CHALLENGES: How your recommended strategies specifically address the student's mentioned challenges, with at least one targeted technique per challenge.
    
    Your response should be practical, specific to the student's subject matter, and immediately actionable.
    """
    
    return Task(
        description=description,
        expected_output=expected_output,
        human_input=True
    )

# If you need to use the raw context, set it as a property on the agent or
# pass it when executing the task
