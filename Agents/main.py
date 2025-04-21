from crewai import Crew, Task
from Agents.tasks.strategy_task import create_strategy_task
from Agents.agents.strategy_agent import strategy_agent
from Agents.tasks.planner_task import create_planner_task
from Agents.agents.planner_agent import planner_agent
from Agents.tasks.resources_task import create_resources_task
from Agents.agents.resources_agent import resources_agent, update_agent_context
from Agents.tasks.output_verification_task import create_verification_task
from Agents.agents.output_verifier_agent import output_verifier_agent
import sys
import os
import logging
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv
from Agents.llm_config import llama_llm  # Import LLM directly
from utils.context_loader import extract_syllabus_topics
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import Tool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Global variable to store the final study plan
study_plan = None
user_context = None

def get_user_input():
    """Collect study information from the user"""
    print("\n📚 Study Plan Generator 📚\n")
    print("Please provide the following information about your study needs:")
    print("(You can press Enter to skip any question and use a default value)")
    
    subject = input("\nWhat subject are you studying for? ")
    if not subject.strip():
        subject = "General Studies"
        print(f"Using default: {subject}")
    
    exam_type = input("What type of exam or test are you preparing for? ")
    if not exam_type.strip():
        exam_type = "Final Exam"
        print(f"Using default: {exam_type}")
    
    # Add validation for days until exam with ability to skip
    days_until_exam = ""
    while not days_until_exam:
        days_input = input("How many days do you have until the exam? ")
        if not days_input.strip():
            days_until_exam = "7"
            print(f"Using default: {days_until_exam} days")
            break
        
        try:
            days = int(days_input)
            if days <= 0:
                print("Please enter a positive number of days or press Enter to use the default.")
            else:
                days_until_exam = days_input
        except ValueError:
            print("Please enter a valid number of days or press Enter to use the default.")
    
    # Add validation for hours per day with ability to skip
    hours_per_day = ""
    while not hours_per_day:
        hours_input = input("How many hours can you study per day? ")
        if not hours_input.strip():
            hours_per_day = "2"
            print(f"Using default: {hours_per_day} hours per day")
            break
            
        try:
            hours = float(hours_input)
            if hours <= 0:
                print("Please enter a positive number of hours or press Enter to use the default.")
            elif hours > 12:
                confirm = input("Warning: That's a lot of hours per day. Are you sure? (y/n) ")
                if confirm.lower() != 'y':
                    print("Please enter a different value or press Enter to use the default.")
                else:
                    hours_per_day = hours_input
            else:
                hours_per_day = hours_input
        except ValueError:
            print("Please enter a valid number of hours or press Enter to use the default.")
    
    learning_style = input("\nHow do you prefer to learn? (e.g., visual, reading, hands-on) ")
    if not learning_style.strip():
        learning_style = "visual"
        print(f"Using default learning style: {learning_style}")
    
    specific_challenges = input("Any specific challenges you face when studying? ")
    if not specific_challenges.strip():
        specific_challenges = "no specific challenges"
        print(f"Using default: {specific_challenges}")
    
    # Additional optional information
    print("\nOptional information (press Enter to skip):")
    previous_knowledge = input("What is your current level of knowledge in this subject? ")
    
    preferred_resources = input("Do you have any preferred resource types? (e.g., videos, books, practice problems) ")
    
    difficult_topics = input("Are there any specific topics you find difficult? (comma-separated) ")
    # Convert to list if provided
    if difficult_topics:
        difficult_topics = [topic.strip() for topic in difficult_topics.split(',')]
    
    preferred_time = input("Do you have a preferred time of day to study? (e.g., morning, evening) ")
    
    specific_goals = input("Do you have any specific goals for this study plan? ")
    
    print("\nThank you! Generating your personalized study plan...\n")
    
    # Return user context as a dictionary
    user_context = {
        "subject": subject,
        "exam_type": exam_type,
        "days_until_exam": days_until_exam,
        "hours_per_day": hours_per_day, 
        "learning_style": learning_style or "visual",  # Default to visual if empty
        "specific_challenges": specific_challenges
    }
    
    # Add optional fields if provided
    if previous_knowledge:
        user_context["previous_knowledge"] = previous_knowledge
    
    if preferred_resources:
        user_context["preferred_resources"] = preferred_resources
    
    if difficult_topics:
        user_context["difficult_topics"] = difficult_topics
    
    if preferred_time:
        user_context["preferred_time_of_day"] = preferred_time
    
    if specific_goals:
        user_context["goals"] = specific_goals
    
    return user_context

def run_chat_loop(study_plan, user_context):
    """Run an interactive chat loop with the user after plan generation"""
    print("\n💬 Chat with your Study Assistant 💬")
    print("You can ask questions about your plan, request explanations,")
    print("get additional resources, or adjust your schedule.")
    print("Type 'exit' or 'quit' to end the conversation.\n")
    
    # Create a context prompt with all the relevant information
    context_prompt = f"""
You are a Study Assistant Chatbot helping a student with their personalized study plan.

STUDENT INFORMATION:
- Subject: {user_context['subject']}
- Exam Type: {user_context['exam_type']}
- Days Until Exam: {user_context['days_until_exam']}
- Study Hours Per Day: {user_context['hours_per_day']}
- Learning Style: {user_context['learning_style']}
- Specific Challenges: {user_context['specific_challenges']}
"""

    # Add additional user settings if available
    if 'previous_knowledge' in user_context and user_context['previous_knowledge']:
        context_prompt += f"- Previous Knowledge: {user_context['previous_knowledge']}\n"
    
    if 'preferred_resources' in user_context and user_context['preferred_resources']:
        if isinstance(user_context['preferred_resources'], list):
            resources_str = ", ".join(user_context['preferred_resources'])
        else:
            resources_str = user_context['preferred_resources']
        context_prompt += f"- Preferred Resources: {resources_str}\n"
    
    if 'difficult_topics' in user_context and user_context['difficult_topics']:
        if isinstance(user_context['difficult_topics'], list):
            topics_str = ", ".join(user_context['difficult_topics'])
        else:
            topics_str = user_context['difficult_topics']
        context_prompt += f"- Difficult Topics: {topics_str}\n"
    
    if 'preferred_time_of_day' in user_context and user_context['preferred_time_of_day']:
        context_prompt += f"- Preferred Time: {user_context['preferred_time_of_day']}\n"
    
    if 'goals' in user_context and user_context['goals']:
        context_prompt += f"- Specific Goals: {user_context['goals']}\n"
    
    context_prompt += f"""
STUDY PLAN:
{study_plan}

As a Study Assistant, your goal is to help the student understand and implement their plan effectively. 
You can:
1. Explain any part of the plan in detail
2. Recommend additional resources for specific topics
3. Suggest adjustments to the schedule if needed
4. Answer questions about learning strategies
5. Provide motivation and study tips

Respond directly to the student's questions with helpful, concise information based on their plan.
"""
    
    # Store conversation history
    conversation_history = [context_prompt]
    
    print("Fast chat mode enabled. Responses will be much quicker!")
    
    while True:
        user_message = input("\nYou: ")
        if user_message.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            print("\nThank you for using the Study Plan Assistant. Good luck with your studies!")
            break
        
        # Add user message to conversation history
        conversation_history.append(f"Student: {user_message}\n\nStudy Assistant: ")
        
        # Create the full prompt with context and conversation history
        full_prompt = "\n".join(conversation_history)
        
        # Get direct response from LLM - much faster than using CrewAI
        response = llama_llm.invoke(full_prompt)
        
        # Add the response to conversation history
        conversation_history[-1] += response
        
        # Print the response
        print(f"\nStudy Assistant: {response}")
        
        # Limit conversation history to last 10 exchanges to prevent context overflow
        if len(conversation_history) > 10:
            # Keep the initial context and the last 9 exchanges
            conversation_history = [conversation_history[0]] + conversation_history[-9:]

def run_crewai_chat(study_plan, user_context):
    """Run the original CrewAI-based chat (slower but with tool access)"""
    print("\n💬 Chat with your Study Assistant (CrewAI mode) 💬")
    print("You can ask questions about your plan, request explanations,")
    print("get additional resources, or adjust your schedule.")
    print("Type 'exit' or 'quit' to end the conversation.\n")
    print("Note: This mode is slower but has access to specialized tools.\n")
    
    # Import needed modules for CrewAI chat
    from Agents.tasks.chat_task import chat_task
    from Agents.agents.chat_agent import chat_agent, update_context
    
    # Update the global context in the chat agent
    update_context(study_plan, user_context)
    
    # Create a separate crew for chat
    chat_crew = Crew(
        agents=[chat_agent],
        tasks=[chat_task],
        verbose=True,
        process="sequential"
    )
    
    while True:
        user_message = input("\nYou: ")
        if user_message.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            print("\nThank you for using the Study Plan Assistant. Good luck with your studies!")
            break
        
        # Pass the user message to the chat agent
        response = chat_crew.kickoff(inputs={"user_message": user_message, "study_plan": study_plan})
        print(f"\nStudy Assistant: {response}")

def generate_study_plan(context):
    """Generate a study plan based on user input."""
    try:
        logger.info(f"Generating study plan for context: {context}")
        
        # Extract syllabus topics from context
        syllabus_topics = context.get('syllabus_topics', [])
        
        # Import tasks and agents only when needed to avoid circular imports
        from Agents.tasks.output_verification_task import create_verification_task
        from temp_crewai_install.crewai.tasks.conditional_task import ConditionalTask
        
        from Agents.agents.strategy_agent import strategy_agent
        from Agents.agents.resources_agent import resources_agent
        from Agents.agents.planner_agent import planner_agent
        from Agents.agents.output_verifier_agent import output_verifier_agent
        
        # Create tasks
        strategy_task = create_strategy_task()
        resources_task = create_resources_task(resources_agent)
        planner_task = create_planner_task(planner_agent)
        verification_task = create_verification_task(output_verifier_agent)
        
        # Special case: Create a conditional task for single-day intense study plans
        def is_single_day_intense_plan(task_output):
            if not task_output or not hasattr(task_output, 'context'):
                return False
                
            user_context = task_output.context.get('user', {}) if isinstance(task_output.context, dict) else {}
            days = int(float(user_context.get('days_until_exam', 0)))
            hours = float(user_context.get('hours_per_day', 0))
            
            # Check if this is a single day with high hours (≥ 4 hours)
            return days == 1 and hours >= 4
        
        # Create a modified planner task for intense single-day studies
        intensive_planner_task = Task(
            description=(
                "Create a detailed single-day intensive study plan for a student with limited time. "
                "The plan must fit ALL studying within a SINGLE DAY, using the full allocated hours. "
                "Break the day into focused segments with specific breaks. "
                "Structure should be hour-by-hour with 5-15 minute breaks every 25-50 minutes of study. "
                "Each activity must specify exact duration, resource with page/chapter numbers, and "
                "which evidence-based learning strategy to use (retrieval practice, 3R method, etc.)."
            ),
            expected_output=(
                "A comprehensive single-day study plan with:"
                "\n1. Hour-by-hour schedule with exact times (e.g., '9:00-9:45 AM')"
                "\n2. Activities with specific durations"
                "\n3. Regular breaks (5-15 minutes every 25-50 minutes of study)"
                "\n4. Specific resources with exact page/chapter numbers"
                "\n5. Evidence-based learning strategies for each activity"
                "\n6. Total study time matching user's requested hours"
            ),
            agent=planner_agent
        )
        
        single_day_planner_task = ConditionalTask(
            condition=is_single_day_intense_plan,
            description="Conditional task that executes the intensive single-day planner for time-constrained students",
            expected_output="A detailed single-day study plan",
            agent=planner_agent
        )
        
        # Update the tasks with user context information
        strategy_task.description = (
            f"Analyze how a student should prepare for a {context['exam_type']} in {context['subject']} "
            f"with {context['days_until_exam']} days available, {context['hours_per_day']} hours per day to study, "
            f"who prefers {context['learning_style']} learning, and struggles with {context['specific_challenges']}."
            f"\n\n"
            f"Create a strategic approach by:"
            f"\n1. Analyzing the student's learning preferences and time constraints"
            f"\n2. Considering the subject material complexity and syllabus topics"
            f"\n3. Recommending 3-5 specific, evidence-based learning strategies that match their learning style"
            f"\n4. Including the 3R (Read-Recite-Review) strategy from McDaniel et al. (2009)"
            f"\n5. Explaining exactly how to implement each strategy"
            f"\n6. Including specific tips for addressing their learning challenges"
        )
        
        resources_task.description = (
            f"Identify the best learning resources for a student preparing for a {context['exam_type']} "
            f"in {context['subject']} with {context['days_until_exam']} days available, "
            f"{context['hours_per_day']} hours per day to study, "
            f"who prefers {context['learning_style']} learning, and struggles with {context['specific_challenges']}."
            f"\n\n"
            f"First, review the strategies recommended in the previous task. Then:"
            f"\n1. For EACH topic in the syllabus, recommend specific resources (NEVER use the syllabus itself)"
            f"\n2. Include a mix of different resource types (textbooks with chapters, videos with timestamps, etc.)"
            f"\n3. EVERY resource MUST include a direct URL link"
            f"\n4. Explain why each resource is effective for their learning style"
            f"\n5. Match resources to the learning strategies from task 1"
            f"\n6. Prioritize resources that address their specific challenges"
            f"\n7. For complex topics, suggest multiple complementary resources"
            f"\n\n"
            f"For each resource, provide:"
            f"\n- Full title and author"
            f"\n- Direct URL link"
            f"\n- Specific chapters, sections, pages, or timestamps"
            f"\n- Estimated time to complete"
            f"\n- Which evidence-based strategy from task 1 to apply with this resource"
            f"\n- How the resource addresses their learning style and challenges"
            f"\n\n"
            f"CRITICAL: NEVER recommend using the syllabus as a study resource - it's only for topic extraction."
        )
        
        planner_task.description = (
            f"Create a day-by-day study plan for a student preparing for a {context['exam_type']} "
            f"in {context['subject']} in {context['days_until_exam']} days, "
            f"with {context['hours_per_day']} hours per day to study, "
            f"who prefers {context['learning_style']} learning methods, "
            f"and faces challenges with {context['specific_challenges']}. "
            f"\n\n"
            f"For each day of the plan:"
            f"\n1. Create activities with allocated time durations (e.g., '45 minutes', '1 hour')"
            f"\n2. For each activity, specify which evidence-based strategy to use (with research citation)"
            f"\n3. For each strategy, specify the exact resource from task 2 to use"
            f"\n4. Each resource MUST include direct links, specific chapters, pages, video timestamps, or problem sets"
            f"\n5. Include clear instructions on how to use that resource with that strategy"
            f"\n6. Add appropriate breaks using evidence-based techniques"
            f"\n7. Include regular review sessions of previous material"
            f"\n\n"
            f"CRITICAL REQUIREMENTS:"
            f"\n1. NEVER exceed {context['hours_per_day']} hours per day or {int(float(context['days_until_exam']) * float(context['hours_per_day']))} total hours"
            f"\n2. Ensure EVERY topic from the syllabus or subject is covered"
            f"\n3. For each study activity, you MUST specify:"
            f"\n   - Exact time allocation (in minutes)"
            f"\n   - Specific resource with URL + section/chapter/timestamp"
            f"\n   - Which evidence-based learning strategy to apply (with citation)"
            f"\n   - Clear, actionable instructions with expected outcome"
            f"\n4. NEVER use the syllabus itself as a study resource - it's only for topic guidance"
            f"\n5. If time is limited (3 days or less), prioritize only the most important topics"
            f"\n6. The plan must be immediately actionable without further decisions needed"
            f"\n7. Every strategy must explicitly reference an evidence-based study technique"
        )
        
        # Update the verification task with user context
        verification_task.description = (
            f"Review the proposed study plan and ensure it meets all requirements. "
            f"The student is preparing for a {context['exam_type']} in {context['days_until_exam']} days, "
            f"has {context['hours_per_day']} hours per day to study, "
            f"prefers {context['learning_style']} learning methods, "
            f"and faces challenges with {context['specific_challenges']}. "
            f"\n\n"
            f"Your job is to verify that the plan:"
            f"\n1. Does NOT exceed {context['days_until_exam']} days or {context['hours_per_day']} hours per day"
            f"\n2. Covers ALL necessary topics for {context['subject']}"
            f"\n3. Includes specific resources with URLs AND exact chapters, sections, or timestamps for EVERY study activity"
            f"\n4. NEVER uses the syllabus itself as a study resource"
            f"\n5. Properly integrates evidence-based learning strategies with citations"
            f"\n6. Is immediately actionable without requiring further decisions"
            f"\n7. Connects each topic to an appropriate strategy and resource"
            f"\n8. Accounts for the student's learning style and challenges"
            f"\n9. Includes clear time allocations that add up correctly"
            f"\n\n"
            f"If ANY of these criteria are not met, you must provide specific corrections. "
            f"Be especially vigilant about:"
            f"\n- Time allocations - make sure the total study time "
            f"doesn't exceed {int(float(context['days_until_exam']) * float(context['hours_per_day']))} hours and that each day has exactly "
            f"{context['hours_per_day']} hours of activities (including breaks)"
            f"\n- Resource specificity - every resource must include a URL and specific page/timestamp reference"
            f"\n- Evidence-based strategies - ensure each strategy references a research-backed method"
            f"\n- Syllabus usage - the syllabus must NEVER be used as a study resource"
            f"\n\n"
            f"IMPORTANT: The final plan must be comprehensive, clearly formatted, and ready for the student to follow."
        )
        
        # Connect tasks with their corresponding agents
        strategy_task.agent = strategy_agent
        resources_task.agent = resources_agent
        planner_task.agent = planner_agent
        intensive_planner_task.agent = planner_agent
        single_day_planner_task.agent = planner_agent
        verification_task.agent = output_verifier_agent
        
        # Create context object for data sharing between agents
        shared_context = {
            "user": context,
            "system": {
                "timestamp": datetime.now().isoformat(),
                "syllabus_topics": syllabus_topics
            },
            "task_outputs": {}
        }
        
        # Update resource agent with context info
        user_id = context.get('user_id')
        session_id = context.get('session_id')
        logger.info(f"Updating agent context with user_id: {user_id}, session_id: {session_id}")
        update_agent_context(user_id=user_id, session_id=session_id)
        
        # Enable task passing (the strategy task output should be passed to the resources task)
        resources_task.context = [strategy_task]
        
        # Determine which planner task to use based on days and hours
        if int(float(context['days_until_exam'])) == 1 and float(context['hours_per_day']) >= 4:
            logger.info("Using intensive single-day planner for high-hours study plan")
            planner_task = intensive_planner_task
            # For single-day intensive plans, we'll use the standard task sequence
            planner_task.context = [strategy_task, resources_task]
        else:
            # For multi-day plans, we'll allow the conditional task to decide
            single_day_planner_task.context = [strategy_task, resources_task]
            planner_task.context = [strategy_task, resources_task]
        
        verification_task.context = [planner_task, resources_task, strategy_task]
        
        # Build a Crew with the plan generation agents
        plan_crew = Crew(
            agents=[strategy_agent, resources_agent, planner_agent, output_verifier_agent],
            tasks=[strategy_task, resources_task, planner_task, verification_task],
            verbose=True,
            process="sequential"
        )
        
        # Run the crew workflow
        logger.info("Executing crew workflow for study plan generation")
        result = plan_crew.kickoff(inputs={
            "subject": context['subject'],
            "exam_type": context['exam_type'],
            "days": context['days_until_exam'],
            "hours_per_day": context['hours_per_day'],
            "learning_style": context['learning_style'],
            "specific_challenges": context['specific_challenges'],
            "syllabus_topics": syllabus_topics
        })
        
        # Check if result is a string directly
        if isinstance(result, str):
            logger.info(f"Result is a string of length {len(result)}")
            return result
            
        # Handle the case where result might be CrewOutput object or other types
        try:
            # Try different attribute patterns to get the actual content
            logger.info(f"Raw result type: {type(result)}")
            
            # Most common case: CrewOutput with 'raw' attribute
            if hasattr(result, 'raw'):
                raw_output = str(result.raw)
                logger.info(f"Found raw attribute of length {len(raw_output)}")
                if raw_output and raw_output != "None" and len(raw_output) > 100:
                    return raw_output
            
            # Pattern 1: Direct string representation
            result_str = str(result)
            logger.info(f"Result string representation: {result_str[:100]}...")
            
            # Pattern 2: Check for 'output' attribute
            if hasattr(result, 'output'):
                output = str(result.output)
                logger.info(f"Found output attribute of length {len(output)}")
                if output and output != "None" and len(output) > 100:
                    return output
            
            # Pattern 3: Check for 'result' attribute
            if hasattr(result, 'result'):
                result_value = str(result.result)
                logger.info(f"Found result attribute of length {len(result_value)}")
                if result_value and result_value != "None" and len(result_value) > 100:
                    return result_value
            
            # Pattern 4: Check for dictionary structure
            if isinstance(result, dict) and 'result' in result:
                dict_result = str(result['result'])
                logger.info(f"Found result in dictionary of length {len(dict_result)}")
                if dict_result and dict_result != "None" and len(dict_result) > 100:
                    return dict_result
            
            # If we couldn't find a structured result, use the string representation
            if result_str and result_str != "None" and len(result_str) > 100:
                return result_str
            
            # Last resort - if all else fails, directly run the verification task
            logger.warning("Could not extract structured result, using last resort extraction")
            
            # Execute tasks in sequence and collect results
            try:
                # First, try executing strategy_task directly
                logger.info("Attempting direct strategy task execution...")
                strategy_output = execute_task_directly(strategy_task, strategy_agent, context)
                logger.info(f"Strategy output length: {len(strategy_output)}")
                
                # Then try resources_task with strategy output
                logger.info("Attempting direct resources task execution...")
                resources_output = execute_task_directly(resources_task, resources_agent, context, strategy_output)
                logger.info(f"Resources output length: {len(resources_output)}")
                
                # Then try planner_task with both outputs
                logger.info("Attempting direct planner task execution...")
                combined_output = f"STRATEGY OUTPUT:\n{strategy_output}\n\nRESOURCES OUTPUT:\n{resources_output}"
                planner_output = execute_task_directly(planner_task, planner_agent, context, combined_output)
                logger.info(f"Planner output length: {len(planner_output)}")
                
                # Finally verification
                logger.info("Attempting direct verification task execution...")
                final_plan = execute_task_directly(verification_task, output_verifier_agent, context, planner_output)
                logger.info(f"Final plan length: {len(final_plan)}")
                
                return final_plan
            except Exception as direct_exec_error:
                logger.error(f"Error in direct task execution: {direct_exec_error}")
                logger.error(traceback.format_exc())
                # If all else fails, return whatever we have as a last resort
                return result_str if result_str else "Error: Could not generate study plan. Please try again with different parameters."
            
        except Exception as e:
            logger.error(f"Error extracting result: {e}")
            logger.error(traceback.format_exc())
            
            # Fallback to string representation or a clear error message
            return str(result) if result else "Error: Could not generate study plan. The CrewAI framework encountered an error processing the results."
    
    except Exception as e:
        logger.error(f"Error generating study plan: {e}")
        logger.error(traceback.format_exc())
        return f"Error generating study plan: {str(e)}"

def log_task_output(task, output, shared_context):
    """Log and store task outputs in shared context"""
    task_name = task.name or task.__class__.__name__
    logger.info(f"Task '{task_name}' completed with output length: {len(str(output))}")
    
    # Store the output in shared context
    if 'task_outputs' in shared_context:
        shared_context['task_outputs'][task_name] = str(output)
    
    # Return the output unchanged
    return output

def execute_task_directly(task, agent, context, prior_output=None):
    """Execute a single task directly with an agent"""
    logger.info(f"Directly executing task: {task.name or task.__class__.__name__}")
    
    # Prepare the prompt for the agent
    prompt = task.description
    if prior_output:
        prompt += f"\n\nPrevious task output:\n{prior_output}"
    
    # Add basic context information
    prompt += f"\n\nContext Information:"
    prompt += f"\nSubject: {context['subject']}"
    prompt += f"\nExam Type: {context['exam_type']}"
    prompt += f"\nDays Until Exam: {context['days_until_exam']}"
    prompt += f"\nHours Per Day: {context['hours_per_day']}"
    prompt += f"\nLearning Style: {context['learning_style']}"
    prompt += f"\nSpecific Challenges: {context['specific_challenges']}"
    
    # Add additional context settings if available
    if 'previous_knowledge' in context and context['previous_knowledge']:
        prompt += f"\nPrevious Knowledge: {context['previous_knowledge']}"
    
    if 'preferred_resources' in context and context['preferred_resources']:
        resources = context['preferred_resources']
        if isinstance(resources, list):
            resources_str = ", ".join(resources)
        else:
            resources_str = str(resources)
        prompt += f"\nPreferred Resources: {resources_str}"
    
    if 'difficult_topics' in context and context['difficult_topics']:
        topics = context['difficult_topics']
        if isinstance(topics, list):
            topics_str = ", ".join(topics)
        else:
            topics_str = str(topics)
        prompt += f"\nDifficult Topics: {topics_str}"
    
    if 'focus_sessions' in context and context['focus_sessions']:
        prompt += f"\nFocus Sessions: {context['focus_sessions']}"
    
    if 'preferred_time_of_day' in context and context['preferred_time_of_day']:
        prompt += f"\nPreferred Time of Day: {context['preferred_time_of_day']}"
    
    if 'goals' in context and context['goals']:
        prompt += f"\nSpecific Goals: {context['goals']}"
    
    if 'syllabus_topics' in context and context['syllabus_topics']:
        topics = context['syllabus_topics']
        if isinstance(topics, list) and len(topics) > 0:
            prompt += f"\nSyllabus Topics: {', '.join(topics[:10])}"
            if len(topics) > 10:
                prompt += f" (+ {len(topics) - 10} more)"
    
    # Execute the task through the agent
    output = agent.llm.invoke(prompt)
    
    logger.info(f"Task output length: {len(output)}")
    return output

def main():
    """Main function to run the study plan generator"""
    try:
        # Get user input
        context = get_user_input()
        
        # Generate the study plan
        print("\nGenerating your study plan... This may take a few minutes.\n")
        study_plan = generate_study_plan(context)
        
        # Print the study plan
        print("\n📝 Your Personalized Study Plan 📝\n")
        print(study_plan)
        
        # Save the study plan to a file
        filename = f"study_plan_{context['subject'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(study_plan)
        print(f"\nYour study plan has been saved to {filename}")
        
        # Ask if the user wants to start the chat loop
        chat_choice = input("\nWould you like to chat with an assistant about your study plan? (y/n) ")
        if chat_choice.lower() == 'y':
            chat_mode = input("Choose chat mode: fast (f) or detailed with tools (d)? [f/d] ")
            if chat_mode.lower() == 'd':
                run_crewai_chat(study_plan, context)
        else:
                run_chat_loop(study_plan, context)
        
        print("\nThank you for using the Study Plan Generator! Good luck with your studies!")
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted. Exiting...")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")
        logger.error(f"Error in main: {e}")
        logger.error(traceback.format_exc())

def format_study_plan(raw_plan, context):
    """
    Reformats a study plan into a more structured format with attribute tables
    and emoji markers for better visual organization
    
    Args:
        raw_plan: The original study plan text
        context: User context dictionary with subject, exam_type, etc.
        
    Returns:
        A formatted study plan with structured headers and improved formatting
    """
    import re
    
    # Create a structured header with a table of attributes
    header = f"""# {context['subject'].upper()} STUDY PLAN

## Student Profile
| Attribute | Value |
|-----------|-------|
| Subject | {context['subject']} |
| Goal | Pass {context['exam_type']} |
| Study Time | {context['hours_per_day']} hours/day |
| Duration | {context['days_until_exam']} days |
| Learning Style | {context['learning_style'].capitalize()} |
| Challenges | {context['specific_challenges']} |
"""

    # Add any additional user settings from context if they exist
    additional_settings = []
    if 'previous_knowledge' in context and context['previous_knowledge']:
        additional_settings.append(f"| Previous Knowledge | {context['previous_knowledge']} |")
    if 'preferred_resources' in context and context['preferred_resources']:
        resources_list = context['preferred_resources']
        if isinstance(resources_list, list):
            resources_str = ", ".join(resources_list)
        else:
            resources_str = str(resources_list)
        additional_settings.append(f"| Preferred Resources | {resources_str} |")
    if 'difficult_topics' in context and context['difficult_topics']:
        topics_list = context['difficult_topics']
        if isinstance(topics_list, list):
            topics_str = ", ".join(topics_list)
        else:
            topics_str = str(topics_list)
        additional_settings.append(f"| Difficult Topics | {topics_str} |")
    if 'focus_sessions' in context and context['focus_sessions']:
        additional_settings.append(f"| Focus Sessions | {context['focus_sessions']} |")
    if 'preferred_time_of_day' in context and context['preferred_time_of_day']:
        additional_settings.append(f"| Preferred Time | {context['preferred_time_of_day']} |")
    if 'goals' in context and context['goals']:
        additional_settings.append(f"| Specific Goals | {context['goals']} |")
    if 'syllabus_topics' in context and context['syllabus_topics']:
        topics = context['syllabus_topics']
        if isinstance(topics, list) and len(topics) > 0:
            topics_str = ", ".join(topics[:5])
            if len(topics) > 5:
                topics_str += f" (+ {len(topics) - 5} more)"
            additional_settings.append(f"| Syllabus Topics | {topics_str} |")
    
    # Add additional settings to the header if any exist
    if additional_settings:
        header += "\n" + "\n".join(additional_settings)
    
    header += "\n\n"
    
    # Format based on days
    if int(float(context['days_until_exam'])) == 1:
        # For a single day, use a session-based approach instead of time slots
        formatted_plan = header + """
## Single Day Intensive Study Plan

"""
        # Check if the raw plan already uses the "PART X:" format
        if "### PART 1:" in raw_plan:
            # Plan is already in the desired format
            return formatted_plan + raw_plan
        
        # If plan has time slots (e.g., "9:00 AM"), convert to a more flexible format
        if "AM" in raw_plan or "PM" in raw_plan:
            return format_single_day_plan(raw_plan, formatted_plan)
            
        # Otherwise, just add the raw plan as-is
        return formatted_plan + raw_plan
    else:
        # For multi-day plans, ensure consistent formatting throughout
        
        # Apply fixes to ensure consistent formatting
        formatted_plan = raw_plan
        
        # 1. Fix day headers - match variants like **Day 1**, Day 1, DAY 1, etc.
        day_header_pattern = r'(\*\*)?(?:Day|DAY)\s+(\d+)(?:\*\*)?:?'
        
        def fix_day_header(match):
            day_num = match.group(2)
            return f"DAY {day_num}:"
            
        formatted_plan = re.sub(day_header_pattern, fix_day_header, formatted_plan)
        
        # 2. Fix resource section headers
        # Check if there's a resources section and standardize it
        resources_pattern = r'(?:RESOURCES|RECOMMENDED RESOURCES|Resources|Recommended Resources):?'
        if re.search(resources_pattern, formatted_plan):
            formatted_plan = re.sub(resources_pattern, "RECOMMENDED RESOURCES:", formatted_plan)
        else:
            # If no resources section found, check if there's content that looks like resources
            # and add a header for it at the end
            lines = formatted_plan.split('\n')
            resources_start = -1
            
            for i, line in enumerate(lines):
                if i > len(lines) * 0.7 and ('http' in line or 'www.' in line or any(x in line.lower() for x in ['textbook', 'course', 'video', 'book', 'lecture'])):
                    resources_start = i
                    break
                    
            if resources_start > 0:
                # Insert a resources header if we found what appears to be resources
                lines.insert(resources_start, "\nRECOMMENDED RESOURCES:\n")
                formatted_plan = '\n'.join(lines)
        
        # 3. Fix resource formatting - ensure resources have URLs
        lines = formatted_plan.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('- ') and 'http' not in line.lower() and 'www.' not in line.lower():
                # Add URL if missing
                if any(x in line.lower() for x in ['book', 'textbook']):
                    lines[i] = line + f" (https://books.google.com/books?q={context['subject'].replace(' ', '+')})"
                elif any(x in line.lower() for x in ['video', 'lecture', 'youtube']):
                    lines[i] = line + f" (https://www.youtube.com/results?search_query={context['subject'].replace(' ', '+')})"
                else:
                    lines[i] = line + f" (https://scholar.google.com/scholar?q={context['subject'].replace(' ', '+')})"
                
            # Fix syllabus references
            if line.strip().startswith('- ') and 'syllabus' in line.lower():
                lines[i] = line.replace("syllabus", f"{context['subject']} textbook")
        
        formatted_plan = '\n'.join(lines)
        
        # 4. Fix time allocation formatting (make sure time is clearly specified)
        if not re.search(r'\(\d+\s*(minute|min|hour|hr)s?\)', formatted_plan, re.IGNORECASE):
            # No time allocations found, try to add them
            activities_pattern = r'Activities:(.*?)(?=DAY \d+:|RECOMMENDED RESOURCES:|$)'
            
            def fix_activities_section(match):
                section = match.group(1)
                lines = section.split('\n')
                fixed_lines = []
                
                # Count activities
                activities = [l.strip() for l in lines if l.strip().startswith('- ')]
                if activities:
                    # Divide available time between activities
                    mins_per_activity = int(float(context['hours_per_day']) * 60) // len(activities)
                    
                    for line in lines:
                        if line.strip().startswith('- ') and '(' not in line:
                            fixed_lines.append(f"{line} ({mins_per_activity} min)")
                        else:
                            fixed_lines.append(line)
                else:
                    fixed_lines = lines
                    
                return "Activities:" + '\n'.join(fixed_lines)
            
            formatted_plan = re.sub(activities_pattern, fix_activities_section, formatted_plan, flags=re.DOTALL)
        
        # 5. Apply emoji markers for days in a consistent format
        lines = formatted_plan.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Match exactly our standardized day format
            if line.strip().startswith('DAY ') and ':' in line:
                day_num = line.split()[1].replace(':', '')
                formatted_lines.append(f"\n## 📆 Day {day_num}")
            else:
                formatted_lines.append(line)
        
        return header + '\n'.join(formatted_lines)

def format_single_day_plan(raw_plan, header):
    """
    Format a single day plan to use sessions rather than specific time slots
    
    Args:
        raw_plan: The original study plan text with time slots
        header: The formatted header to prepend
    
    Returns:
        A formatted plan without specific time slots
    """
    # Try to parse the existing plan into logical sections
    parsed_plan = ""
    part_count = 1
    current_section = ""
    
    # Extract sections based on headers
    sections = []
    current_section = {"title": "", "content": []}
    time_pattern = r'(\d{1,2}):(\d{2}) (AM|PM)'
    
    lines = raw_plan.split('\n')
    for line in lines:
        # If we find a new section header, start a new section
        if line.startswith('###'):
            # Save the previous section if it has content
            if current_section["content"]:
                sections.append(current_section)
                
            # Extract section title
            section_title = line.replace('###', '').strip()
            current_section = {"title": section_title, "content": []}
        elif line.strip():
            # Add content line to current section
            current_section["content"].append(line)
    
    # Add the last section
    if current_section["content"]:
        sections.append(current_section)
        
    # Convert time-based sections to part-based sections
    if sections:
        grouped_sections = []
        current_group = {"title": f"PART {part_count}: CORE CONCEPTS", "content": []}
        
        for i, section in enumerate(sections):
            # Group 2-3 sections into a part
            if i > 0 and i % 2 == 0:
                grouped_sections.append(current_group)
                part_count += 1
                part_title = "ADVANCED TOPICS" if part_count == 2 else \
                             "REVIEW & PRACTICE" if part_count == 3 else \
                             f"ADDITIONAL TOPICS {part_count}"
                current_group = {"title": f"PART {part_count}: {part_title}", "content": []}
            
            # Extract duration if available in the title
            duration_minutes = 0
            for line in section["content"]:
                if '(' in line and 'minute' in line.lower():
                    try:
                        duration_text = line.split('(')[1].split(')')[0]
                        if 'minute' in duration_text:
                            duration_minutes += int(duration_text.split()[0])
                        elif 'hour' in duration_text:
                            duration_minutes += int(duration_text.split()[0]) * 60
                    except:
                        pass
            
            # Estimate duration for the section based on content length if not found
            if duration_minutes == 0:
                duration_minutes = 30 + (len('\n'.join(section["content"])) // 50)
                
            # Add section title with duration to content
            if "BREAK" in section["title"]:
                current_group["content"].append(f"**BREAK** ({duration_minutes} minutes)")
            else:
                # Remove time stamps from section titles
                title = section["title"]
                import re
                title = re.sub(time_pattern, '', title).strip()
                title = re.sub(r'^\s*-\s*', '', title).strip()
                
                current_group["content"].append(f"**{title}** ({duration_minutes} minutes)")
                
            # Add rest of section content 
            current_group["content"].extend(section["content"])
            
        # Add the last group
        if current_group["content"]:
            grouped_sections.append(current_group)
            
        # Format the grouped sections
        for group in grouped_sections:
            parsed_plan += f"\n### {group['title']}\n"
            parsed_plan += '\n'.join(group["content"])
            parsed_plan += "\n"
    
    # If we couldn't parse the plan properly, just use a default structure
    if not parsed_plan.strip():
        # Just split into 3 roughly equal parts
        lines = raw_plan.split('\n')
        section_size = max(10, len(lines) // 3)
        
        parsed_plan += "\n### PART 1: CORE CONCEPTS & FUNDAMENTALS\n"
        parsed_plan += '\n'.join(lines[:section_size])
        parsed_plan += "\n\n### PART 2: ADVANCED TOPICS & APPLICATIONS\n"
        parsed_plan += '\n'.join(lines[section_size:section_size*2])
        parsed_plan += "\n\n### PART 3: REVIEW & ASSESSMENT\n"
        parsed_plan += '\n'.join(lines[section_size*2:])
        
    return header + parsed_plan

def generate_plan_with_context(context):
    """Generate a study plan with the provided context"""
    try:
        raw_plan = generate_study_plan(context)
        formatted_plan = format_study_plan(raw_plan, context)
        return formatted_plan
    except Exception as e:
        logger.error(f"Error generating plan with context: {e}")
        logger.error(traceback.format_exc())
        return f"Error generating study plan: {str(e)}"

def create_study_plan(context_dict, use_defaults=True):
    """Function to create a study plan from a dictionary of context"""
    try:
        # Set up logging
        logger.info("Starting create_study_plan with context")
        logger.info(f"Context keys: {list(context_dict.keys())}")
        
        # Validate input
        required_fields = ['subject', 'exam_type', 'days_until_exam', 'hours_per_day', 'learning_style', 'specific_challenges']
        missing_fields = []
        
        for field in required_fields:
            if field not in context_dict:
                missing_fields.append(field)
                logger.warning(f"Missing required field: {field}")
        
        if missing_fields:
            # Try to extract fields from nested structure that might come from backend
            if 'user' in context_dict and isinstance(context_dict['user'], dict):
                logger.info("Found nested user context, extracting required fields")
                user_context = context_dict['user']
                
                # Copy user context fields to top level if missing
                for field in missing_fields[:]:
                    if field in user_context:
                        context_dict[field] = user_context[field]
                        missing_fields.remove(field)
                        logger.info(f"Extracted {field} from user context: {context_dict[field]}")
                
            # If still missing fields, check if we can derive them
            if 'days' in context_dict and 'days_until_exam' in missing_fields:
                context_dict['days_until_exam'] = context_dict['days']
                missing_fields.remove('days_until_exam')
                logger.info(f"Using 'days' as 'days_until_exam': {context_dict['days_until_exam']}")
                
            # If use_defaults is True, supply default values for missing fields
            if use_defaults and missing_fields:
                logger.info("Using default values for missing fields")
                default_values = {
                    'subject': 'general studies',
                    'exam_type': 'final exam',
                    'days_until_exam': '7',
                    'hours_per_day': '2',
                    'learning_style': 'visual',
                    'specific_challenges': 'time management'
                }
                
                for field in missing_fields[:]:
                    context_dict[field] = default_values[field]
                    logger.info(f"Using default value for {field}: {context_dict[field]}")
                    missing_fields.remove(field)
            
            # Check if we still have missing fields and need to be strict
            if missing_fields and not use_defaults:
                error_msg = f"Error: Missing required fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                return error_msg
        
        # Log the context values
        logger.info(f"Subject: {context_dict.get('subject')}")
        logger.info(f"Exam type: {context_dict.get('exam_type')}")
        logger.info(f"Days until exam: {context_dict.get('days_until_exam')}")
        logger.info(f"Hours per day: {context_dict.get('hours_per_day')}")
        logger.info(f"Learning style: {context_dict.get('learning_style')}")
        
        # Process syllabus_topics from the context if available
        if 'syllabus_topics' not in context_dict and 'system' in context_dict and isinstance(context_dict['system'], dict):
            if 'syllabus_topics' in context_dict['system']:
                context_dict['syllabus_topics'] = context_dict['system']['syllabus_topics']
                logger.info(f"Extracted syllabus_topics from system context: {len(context_dict['syllabus_topics'])} topics")
                
        # Process resources if available in a nested structure
        if 'resources' not in context_dict and 'session' in context_dict and isinstance(context_dict['session'], dict):
            if 'resources' in context_dict['session']:
                context_dict['resources'] = context_dict['session']['resources']
                logger.info(f"Extracted resources from session context: {len(context_dict['resources'])} resources")
        
        # Add default values for optional fields if not provided
        if 'learning_style' not in context_dict or not context_dict['learning_style']:
            context_dict['learning_style'] = 'visual'
            logger.info("Using default learning style: visual")
            
        if 'specific_challenges' not in context_dict or not context_dict['specific_challenges']:
            context_dict['specific_challenges'] = 'no specific challenges'
            logger.info("Using default specific challenges: no specific challenges")
            
        # Filter out syllabus resources if they exist
        if 'resources' in context_dict and context_dict['resources']:
            logger.info(f"Filtering out syllabus resources from {len(context_dict['resources'])} resources")
            try:
                from Agents.agents.resources_agent import filter_syllabus_resources
                context_dict['resources'] = filter_syllabus_resources(context_dict['resources'])
                logger.info(f"After filtering, {len(context_dict['resources'])} resources remain")
            except Exception as filter_error:
                logger.error(f"Error filtering syllabus resources: {str(filter_error)}")
                logger.error(traceback.format_exc())
                # Continue without filtering if it fails
        
        # Generate the raw plan
        logger.info("Calling generate_study_plan")
        try:
            raw_plan = generate_study_plan(context_dict)
            logger.info(f"Raw plan generated, length: {len(raw_plan)}")
        except Exception as gen_error:
            logger.error(f"Error in generate_study_plan: {str(gen_error)}")
            logger.error(traceback.format_exc())
            raise gen_error
        
        # Format the plan
        logger.info("Calling format_study_plan")
        try:
            formatted_plan = format_study_plan(raw_plan, context_dict)
            logger.info(f"Plan formatted, length: {len(formatted_plan)}")
        except Exception as format_error:
            logger.error(f"Error in format_study_plan: {str(format_error)}")
            logger.error(traceback.format_exc())
            # If formatting fails, return the raw plan as a fallback
            logger.info("Returning raw plan as fallback")
            return raw_plan
        
        logger.info("Study plan creation completed successfully")
        return formatted_plan
        
    except Exception as e:
        logger.error(f"Unexpected error in create_study_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error generating study plan: {str(e)}"

if __name__ == "__main__":
    main()
