from crewai import Task
from Agents.agents.chat_agent import chat_agent
from Agents.tasks.output_verification_task import verification_task

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
    agent=chat_agent,
    # This task will get inputs directly from the chat loop
    async_execution=False,
    human_input=False,  # We'll handle user input in the main loop instead
) 