# tasks/planner_task.py

from crewai import Task
from datetime import timedelta
from Agents.agents.planner_agent import planner_agent
from Agents.tasks.strategy_task import create_strategy_task
from Agents.tasks.resources_task import resources_task

# Create strategy task (agent will be set later)
strategy_task = create_strategy_task()

# Create the planner task
planner_task = Task(
    name="planner_task",
    description=(
        "Create a detailed day-by-day study plan that integrates learning strategies and resources. "
        "\n\n"
        "PLAN REQUIREMENTS:"
        "\n1. Create a structured schedule for each day with specific time allocations"
        "\n2. Ensure the total study time exactly matches the user's constraints (days × hours per day)"
        "\n3. For each study block, specify:"
        "\n   a. Exact duration in minutes (e.g., '45 minutes')"
        "\n   b. Which specific learning strategy to use"
        "\n   c. Which specific resource to use (with chapter/section/timestamp)"
        "\n   d. Clear instructions on what to do"
        "\n4. Include appropriate breaks using evidence-based techniques"
        "\n5. Add regular review sessions of previously covered material"
        "\n6. Ensure every topic from the syllabus is covered"
        "\n\n"
        "CRITICAL TIME CONSTRAINTS:"
        "\n1. The plan MUST NOT exceed the specified number of days"
        "\n2. Each day MUST NOT exceed the specified hours per day"
        "\n3. Time allocations should be realistic and include breaks"
        "\n4. The total time usage should be exactly as specified, not under or over"
        "\n\n"
        "FORMAT REQUIREMENTS:"
        "\n1. Organize by day with clear headings (e.g., 'Day 1 - Monday, June 1')"
        "\n2. For each activity, include all required details in a structured format"
        "\n3. Make instructions clear and actionable"
        "\n4. Include a brief introduction explaining the overall approach"
        "\n5. End with a summary of what was covered and next steps"
    ),
    expected_output=(
        "A comprehensive day-by-day study plan that:"
        "\n1. Respects time constraints exactly (never exceeding days or hours per day)"
        "\n2. Covers all syllabus topics"
        "\n3. Specifies exact resources (with chapters/sections) for each activity"
        "\n4. Integrates learning strategies appropriately"
        "\n5. Includes properly timed breaks and review sessions"
        "\n6. Is immediately actionable without requiring further decisions"
    ),
    agent=None  # Will be set when the crew is created
)

def create_planner_task(planner_agent=None):
    """Create a task to generate a detailed study plan"""
    # Create a copy of the planner_task with the provided agent
    task = planner_task
    if planner_agent:
        task.agent = planner_agent
    return task
