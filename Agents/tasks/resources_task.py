from crewai import Task
from Agents.agents.resources_agent import resources_agent
from Agents.tasks.strategy_task import create_strategy_task

# Create strategy task (agent will be set later)
strategy_task = create_strategy_task()

# Create the resources task with web search instructions
resources_task = Task(
    name="resources_task",
    description=(
        "Find high-quality resources for learning the subject that align with the recommended strategies. "
        "\n\n"
        "TASK PROCESS:"
        "\n1. Identify specific books, online courses, videos, websites, and practice materials for the subject"
        "\n2. Ensure resources match the student's learning style (visual, auditory, reading/writing, kinesthetic)"
        "\n3. For EACH resource, provide:"
        "\n   a. Exact title and author/creator"
        "\n   b. Complete URL or reference information"
        "\n   c. Detailed description of what it covers"
        "\n   d. SPECIFIC chapters, pages, video timestamps, or modules most relevant"
        "\n4. Explain how to use each resource with the learning strategies from the previous task"
        "\n\n"
        "CRITICAL REQUIREMENTS:"
        "\n1. Use web search for ALL resources - do NOT rely on memory"
        "\n2. Provide resources for EVERY topic in the syllabus or subject area"
        "\n3. Include a mix of resource types (textual, visual, interactive, practice)"
        "\n4. NEVER suggest studying the syllabus itself - it's just an outline"
        "\n5. Every resource MUST include specific sections (chapters, pages, timestamps)"
        "\n6. Evaluate each resource for quality before recommending it"
        "\n7. Organize resources by topic for easier reference"
        "\n\n"
        "OUTPUT FORMAT:"
        "\nProvide a well-structured list of resources organized by topic or resource type."
        "\nFor each resource, include all required details in a consistent format."
        "\nExplain how each resource supports specific learning strategies."
    ),
    expected_output=(
        "A comprehensive list of high-quality, specific resources for the subject, "
        "including exact chapters, sections, or timestamps for each resource, "
        "organized by topic, with clear explanations of how to use each resource "
        "with the recommended learning strategies."
    ),
    agent=None  # Will be set when the crew is created
)

def create_resources_task(resources_agent=None):
    """Create a task to find high-quality resources for learning the subject"""
    # Create a copy of the resources_task with the provided agent
    task = resources_task
    if resources_agent:
        task.agent = resources_agent
    return task 