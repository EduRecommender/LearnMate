from crewai import Task
from Agents.agents.chat_agent import chat_agent
from Agents.tasks.output_verification_task import create_verification_task

# Create verification task instance if needed
verification_task = create_verification_task(None)

chat_task = Task(
    description=(
        "Engage in an interactive conversation with the user about their study plan. "
        "Use the completed study plan, resources, and strategies to provide helpful "
        "answers and assistance. Be ready to explain concepts, recommend additional "
        "resources, and help adjust the schedule if needed."
        "\n\n"
        "When responding to the user, consider:"
        "\n1. The specific details of their study plan (provided in the inputs)"
        "\n2. Their learning style and preferences"
        "\n3. The specific resources and strategies mentioned in their plan"
        "\n4. Any constraints or challenges they face"
        "\n\n"
        "The user's message is: {{user_message}}"
        "\n\n"
        "Their study plan is: {{study_plan}}"
    ),
    expected_output=(
        "Provide a helpful, accurate, and concise response to the user's question about their study plan. "
        "Your response should be personalized to their specific plan and needs."
    ),
    context={
        "format_instructions": """
When responding to the user, follow these format instructions:
1. First, understand what the user is asking about
2. Use your tools to get relevant information or perform actions
3. Provide a direct, helpful response based on the results

When using tools, follow this EXACT format to avoid validation errors:

Thought: [your reasoning]
Action: [tool name]
Action Input: {"key": "value"}

Examples of CORRECT tool calls:
- Action: explain_plan
  Action Input: {"query": "study schedule"}

- Action: recommend_resources  
  Action Input: {"topic": "machine learning"}

- Action: adjust_schedule
  Action Input: {"request": "add more breaks"}

Examples of INCORRECT tool calls to AVOID:
- DO NOT use: {"query": {"description": "study schedule"}}
- DO NOT use: {"topic": {"type": "str", "description": "machine learning"}}
- DO NOT use: "None (since we're not using the tool)"

IMPORTANT: Each tool expects a simple string value, not a complex object.
"""
    },
    agent=chat_agent,
    # This task will get inputs directly from the chat loop
    async_execution=False,
    human_input=False,  # We'll handle user input in the main loop instead
) 