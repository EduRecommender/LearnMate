from crewai import Crew
from Agents.tasks.strategy_task import strategy_task
from Agents.agents.strategy_agent import strategy_agent
from Agents.tasks.planner_task import planner_task
from Agents.agents.planner_agent import planner_agent
from Agents.tasks.resources_task import resources_task
from Agents.agents.resources_agent import resources_agent
from Agents.tasks.output_verification_task import verification_task
from Agents.agents.output_verifier_agent import output_verifier_agent
import sys
import os
import logging
import traceback
from dotenv import load_dotenv
from Agents.llm_config import llama_llm  # Import LLM directly

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
    
    subject = input("\nWhat subject are you studying for? ")
    exam_type = input("What type of exam or test are you preparing for? ")
    days_until_exam = input("How many days do you have until the exam? ")
    
    # Add validation for hours per day
    hours_per_day = ""
    while not hours_per_day:
        hours_per_day = input("How many hours can you study per day? ")
        if not hours_per_day:
            print("Please enter a valid number of hours.")
    
    learning_style = input("\nHow do you prefer to learn? (e.g., visual, reading, hands-on) ")
    specific_challenges = input("Any specific challenges you face when studying? ")
    if not specific_challenges:
        specific_challenges = "no specific challenges"
    
    print("\nThank you! Generating your personalized study plan...\n")
    
    # Return user context as a dictionary
    return {
        "subject": subject,
        "exam_type": exam_type,
        "days_until_exam": days_until_exam or "7",  # Default to 7 days if empty
        "hours_per_day": hours_per_day, 
        "learning_style": learning_style or "visual",  # Default to visual if empty
        "specific_challenges": specific_challenges
    }

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
    """Generate a study plan using the CrewAI framework"""
    try:
        logger.info(f"Starting study plan generation for {context.get('subject', 'unknown subject')}")
        
        # Update the strategy task description with user context
        strategy_task.description = (
            f"Analyze learning preferences and available time for studying {context['subject']} "
            f"for a {context['exam_type']} in {context['days_until_exam']} days. "
            f"The student has {context['hours_per_day']} hours per day available, "
            f"prefers {context['learning_style']} learning methods, "
            f"and faces challenges with {context['specific_challenges']}. "
            f"Recommend 3-5 specific, evidence-based learning strategies that will be most effective "
            f"for this particular student and subject. "
            f"For each strategy, provide a detailed explanation of how it works, why it's effective "
            f"for this specific subject and learning style, and how to implement it correctly. "
            f"IMPORTANT: Name each strategy clearly and describe it in detail, as these names and details "
            f"will be used by later tasks to find resources and create a study plan."
        )
        
        # Update the resources task description with user context and web search approach
        resources_task.description = (
            f"Find high-quality resources for learning {context['subject']} that align with the recommended strategies. "
            f"\n\n"
            f"TASK CONTEXT: "
            f"The student is preparing for a {context['exam_type']} in {context['days_until_exam']} days, "
            f"has {context['hours_per_day']} hours per day to study, "
            f"prefers {context['learning_style']} learning methods, "
            f"and faces challenges with {context['specific_challenges']}. "
            f"\n\n"
            f"TASK PROCESS:"
            f"\n1. Identify specific books, online courses, videos, and websites for learning {context['subject']}"
            f"\n2. Based on the student's learning style ({context['learning_style']}), include a mix of resource types (videos, books, interactive exercises, etc.)"
            f"\n3. For each resource found, note any specific sections, chapters, page numbers, or timestamps that would be most helpful."
            f"\n4. For each learning strategy from the previous task, explain how to apply that strategy to these subject-specific resources"
            f"\n\n"
            f"IMPORTANT: Focus on finding the best resources for learning {context['subject']} that align with the student's learning style and the strategies recommended in task 1."
        )
        
        # Update the planner task description with user context
        planner_task.description = (
            f"Create a detailed {context['days_until_exam']}-day study plan for {context['subject']} "
            f"that directly integrates the specific learning strategies from task 1 with the resources "
            f"from task 2. "
            f"The student has {context['hours_per_day']} hours available per day, "
            f"prefers {context['learning_style']} learning methods, "
            f"and faces challenges with {context['specific_challenges']}. "
            f"\n\n"
            f"For each day of the plan:"
            f"\n1. Create activities with allocated time durations (e.g., '45 minutes', '1 hour')"
            f"\n2. For each activity, specify which strategy to use"
            f"\n3. For each strategy, specify the exact resource from task 2 to use"
            f"\n4. Include specific chapters, pages, video timestamps, or problem sets where appropriate"
            f"\n5. Include clear instructions on how to use that resource with that strategy"
            f"\n6. Add appropriate breaks using evidence-based techniques"
            f"\n7. Include regular review sessions of previous material"
            f"\n\n"
            f"IMPORTANT: Your plan must be specific, providing allocated time durations, strategies, and resources "
            f"for each study session. The goal is that the student can follow this plan without "
            f"needing to make any decisions about what to study or how to study it."
        )
        
        # Build a Crew with the plan generation agents
        plan_crew = Crew(
            agents=[strategy_agent, resources_agent, planner_agent, output_verifier_agent],
            tasks=[strategy_task, resources_task, planner_task, verification_task],
            verbose=True,
            # Use sequential process as required by this version of CrewAI
            process="sequential"
        )
        
        # Run the crew workflow
        logger.info("Executing crew workflow for study plan generation")
        result = plan_crew.kickoff()
        
        # Check if result is a string directly
        if isinstance(result, str):
            logger.info(f"Result is a string of length {len(result)}")
            return result
            
        # Handle the case where result might be an object with various attributes
        try:
            # Try different attribute patterns to get the actual content
            logger.info(f"Raw result type: {type(result)}")
            
            # Pattern 1: Direct string representation
            result_str = str(result)
            logger.info(f"Result string representation: {result_str[:100]}...")
            
            # Pattern 2: Check for 'output' attribute
            if hasattr(result, 'output'):
                output = str(result.output)
                logger.info(f"Found output attribute of length {len(output)}")
                if output and len(output) > 100:
                    return output
            
            # Pattern 3: Check if it has 'result' attribute
            if hasattr(result, 'result'):
                inner_result = str(result.result)
                logger.info(f"Found result attribute of length {len(inner_result)}")
                if inner_result and len(inner_result) > 100:
                    return inner_result
            
            # Pattern 4: Check for last_task_output
            if hasattr(result, 'last_task_output'):
                last_output = str(result.last_task_output)
                logger.info(f"Found last_task_output of length {len(last_output)}")
                if last_output and len(last_output) > 100:
                    return last_output
            
            # Pattern 5: Look for 'raw_output'
            if hasattr(result, 'raw_output'):
                raw = str(result.raw_output)
                logger.info(f"Found raw_output of length {len(raw)}")
                if raw and len(raw) > 100:
                    return raw
            
            # If we're here, fall back to string representation if it's long enough to be meaningful
            if len(result_str) > 100 and result_str != "I now can give a great answer.":
                logger.info(f"Using string representation of length {len(result_str)}")
                return result_str
                
            # Generate fallback response
            logger.warning("Could not extract valid output from any attribute")
            return """
STUDY PLAN GENERATION

Unfortunately, I wasn't able to generate a complete study plan due to a technical issue.
This is likely because the CrewAI framework version you're using doesn't return results in the expected format.

Here's what you can do:

1. Try a simpler approach: Use a single agent instead of a full crew
2. Update your CrewAI package: pip install -U crewai
3. Use the direct chat option for study advice

I apologize for the inconvenience. Would you like to try the chat approach instead?
"""
        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Failed to generate study plan: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error in generate_study_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Failed to generate study plan: {str(e)}"

def main():
    global study_plan, user_context
    try:
        # Get user input
        user_context = get_user_input()
        
        # Run the plan generation
        print("Starting to generate your study plan...")
        print("First, identifying the best learning strategies based on research...")
        print("Then, searching for specific resources with exact sections to use...")
        print("Next, creating your detailed day-by-day plan...")
        print("Finally, verifying and enhancing the plan with complete links and details...")
        print("This may take a few minutes. Please be patient.")
        
        study_plan = generate_study_plan(user_context)

        print("\n🧠 Your Personalized Study Plan:\n")
        print(study_plan)
        
        # After generating the study plan, start the chat loop
        print("\nChat Options:")
        print("1. Fast Chat (Recommended - much quicker responses)")
        print("2. Advanced Chat (Slower, with tool access)")
        print("3. Exit (No chat)")
        
        choice = input("\nSelect an option (1/2/3): ")
        
        if choice == "1":
            run_chat_loop(study_plan, user_context)
        elif choice == "2":
            run_crewai_chat(study_plan, user_context)
        else:
            print("\nThank you for using the Study Plan Generator. Good luck with your studies!")
        
    except AttributeError as e:
        print(f"\n❌ Error: {e}")
        print("\nThis might be due to a version mismatch in crewai. Check your installation.")
        print(f"Current error: {e}")
        
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

# Function to generate a study plan with a context dictionary (for API use)
def generate_plan_with_context(context):
    """Generate a study plan with the provided context dictionary"""
    try:
        return generate_study_plan(context)
    except Exception as e:
        logger.error(f"Error generating plan with context: {str(e)}")
        return f"Error generating study plan: {str(e)}"

# Entry point function for backend integration
def create_study_plan(context_dict):
    """
    Main entry point for the backend to generate a study plan
    
    Args:
        context_dict (dict): Dictionary containing user context information like subject, hours_per_day, etc.
        
    Returns:
        str: The generated study plan as a string
    """
    # Make sure imports are available
    if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Validate the context has required fields
    required_fields = ['subject', 'hours_per_day']
    for field in required_fields:
        if field not in context_dict:
            logger.error(f"Missing required field: {field}")
            return f"Error: Missing required field: {field}"
    
    # Set defaults for optional fields
    if 'exam_type' not in context_dict:
        context_dict['exam_type'] = 'exam'
    if 'days_until_exam' not in context_dict:
        context_dict['days_until_exam'] = '7'
    if 'learning_style' not in context_dict:
        context_dict['learning_style'] = 'visual'
    if 'specific_challenges' not in context_dict:
        context_dict['specific_challenges'] = 'no specific challenges'
    
    # Generate and return the study plan
    logger.info(f"Backend requested study plan for {context_dict.get('subject')}")
    plan = generate_study_plan(context_dict)
    return plan

if __name__ == "__main__":
    # Add the parent directory to the path to allow imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
