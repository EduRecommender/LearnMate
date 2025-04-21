from crewai import Task
from Agents.agents.output_verifier_agent import output_verifier_agent
from Agents.tasks.planner_task import planner_task
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import json
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VerificationOutput(BaseModel):
    """Output of the verification task"""
    verified: bool = Field(..., description="Whether the study plan meets all requirements")
    improved_plan: Optional[str] = Field(None, description="Improved study plan if verification failed")
    verification_notes: Dict[str, Any] = Field(
        ..., description="Notes on verification process and issues found"
    )

def validate_study_plan(task_output) -> Tuple[bool, Any]:
    """
    Validate the study plan meets requirements.
    
    Args:
        task_output: The output of the task
        
    Returns:
        Tuple[bool, Any]: (success, result/error_message)
    """
    plan = task_output.raw
    issues = []
    
    # Check 1: Validate time allocation
    expected_hours = None
    expected_days = None
    
    # Extract hours and days from context
    if hasattr(task_output, 'context') and task_output.context and isinstance(task_output.context, dict):
        context = task_output.context
        if "user" in context:
            user_context = context["user"]
            expected_hours = user_context.get("hours_per_day")
            expected_days = user_context.get("days_until_exam")
            
            if expected_hours and expected_days:
                expected_hours = float(expected_hours)
                expected_days = int(expected_days)
                total_expected_hours = expected_hours * expected_days
                
                # Count hours specified in the plan
                hour_pattern = r'(\d+)\s*(?:hour|hr)'
                minute_pattern = r'(\d+)\s*(?:minute|min)'
                
                hours_found = re.findall(hour_pattern, plan, re.IGNORECASE)
                minutes_found = re.findall(minute_pattern, plan, re.IGNORECASE)
                
                total_hours = sum(int(hr) for hr in hours_found) + sum(int(min) / 60 for min in minutes_found)
                
                # Check if the plan specifies enough hours
                if total_hours < total_expected_hours * 0.8:  # Allow 20% margin
                    issues.append(f"Plan only accounts for approximately {total_hours:.1f} hours, but user requested {total_expected_hours} hours ({expected_hours} hours/day for {expected_days} days)")
    
    # Check 2: Plan structure validation
    if expected_days:
        # Check if plan has the right number of days
        day_pattern = r'(?:DAY|Day)\s+(\d+)'
        days_found = re.findall(day_pattern, plan)
        
        if days_found:
            days_present = sorted([int(day) for day in days_found])
            
            # Check if all days are present and the maximum day matches expected days
            if max(days_present, default=0) > expected_days:
                issues.append(f"Plan includes {max(days_present)} days but user requested only {expected_days} days")
            
            if len(days_present) != expected_days:
                issues.append(f"Plan should include exactly {expected_days} days, but found {len(days_present)} days")
    
    # Check 3: Validate resource specificity
    if "relevant chapters" in plan.lower() and not re.search(r'chapter\s+\d+', plan, re.IGNORECASE):
        issues.append("Plan mentions 'relevant chapters' but doesn't specify chapter numbers")
    
    if "relevant sections" in plan.lower() and not re.search(r'section\s+\d+|pages?\s+\d+', plan, re.IGNORECASE):
        issues.append("Plan mentions 'relevant sections' but doesn't specify section numbers or page numbers")
    
    # Check 4: Validate specific learning strategies
    strategy_pattern = r'using\s+((?:3R|spaced repetition|retrieval practice|interleaving|elaboration|feynman|pomodoro)\s+(?:technique|method|strategy))'
    strategies_found = re.findall(strategy_pattern, plan, re.IGNORECASE)
    
    if not strategies_found:
        issues.append("Plan doesn't explicitly mention evidence-based learning strategies")
    
    # Check 5: Validate break inclusion
    break_pattern = r'(\d+)[\- ]minute break'
    breaks_found = re.findall(break_pattern, plan, re.IGNORECASE)
    
    if not breaks_found:
        issues.append("Plan doesn't include scheduled breaks with specific durations")
    
    # Check 6: Validate there are specific time allocations
    if not re.search(r'(\d+)\s*(?:hour|hr|minute|min)', plan, re.IGNORECASE):
        issues.append("Plan doesn't include specific time allocations for activities")
    
    # Make decision based on issues found
    success = len(issues) == 0
    
    if success:
        logger.info("Study plan validation passed")
        return (True, task_output.raw)
    else:
        logger.warning(f"Study plan validation failed with {len(issues)} issues")
        error_message = "The plan has the following issues that need to be fixed:\n- " + "\n- ".join(issues)
        return (False, error_message)
    
def create_verification_task(output_verifier_agent=None):
    """Create and return a task for verifying and improving the study plan."""
    
    task_description = """
    # TASK: STUDY PLAN VERIFICATION AND IMPROVEMENT
    
    ## GOAL
    Review the proposed study plan against strict requirements and improve it to ensure all criteria are met fully.
    
    ## VERIFICATION REQUIREMENTS
    The study plan MUST meet ALL of the following requirements:
    
    1. **STRICT TIME CONSTRAINTS**: 
       - The total study time MUST EXACTLY match days × hours per day (within 30 minutes)
       - Each day should use approximately the allocated hours per day
       - Break times must be included in the total time calculation
    
    2. **COMPLETE TOPIC COVERAGE**: 
       - EVERY topic from the syllabus must be covered
       - No topic should be missing or insufficiently addressed
       
    3. **SPECIFIC RESOURCE REFERENCES**:
       - Each resource must specify exact chapters, page numbers, or timestamps
       - The syllabus itself should NEVER be recommended as a study resource
       - Each resource must be clearly linked to specific learning activities
       
    4. **EVIDENCE-BASED STRATEGY IMPLEMENTATION**:
       - Each study session must specify which evidence-based strategy to use
       - Strategies must be appropriate for the topic and resource
       - The 3R strategy and other evidence-based methods must be properly implemented
       
    5. **ACTIONABLE INSTRUCTIONS**:
       - Each study session must have clear, specific instructions
       - Instructions must be detailed enough to follow without additional decisions
       
    6. **PRECISE TIME ALLOCATION**:
       - Each activity must have a specific time allocation in minutes
       - Time allocations must be realistic and appropriate for the activity
       
    7. **BREAK INCLUSION**:
       - Appropriate breaks must be scheduled between study sessions
       - Break durations must be specified in minutes
       
    8. **REVIEW SESSIONS**:
       - Regular review sessions must be included
       - Review sessions should use spaced repetition principles
    
    ## EXPECTED OUTPUT
    If the study plan meets ALL requirements, approve it. If ANY requirement is not met:
    1. Identify specific issues with detailed explanations
    2. Fix ALL issues to create an improved final plan
    3. Format the improved plan with clear day-by-day structure
    4. Return verification notes and the improved plan
    
    The final study plan MUST be comprehensive, clearly formatted, and ready for the student to follow without any further adjustments.
    """
    
    # Modified version of the guardrail function that returns text directly
    def text_based_guardrail(task_output) -> Tuple[bool, Any]:
        result, message = validate_study_plan(task_output)
        return (result, message)
    
    verification_task = Task(
        description=task_description,
        expected_output="""
        A verification report that includes:
        1. Whether the study plan meets all requirements
        2. Specific improvements if any requirements are not met
        3. A complete, improved study plan if verification failed
        4. Verification notes for each requirement
        """,
        agent=output_verifier_agent,
        guardrail=text_based_guardrail
    )
    
    return verification_task

# No need to create an instance here since it will be created with the agent in main.py 