# tasks/planner_task.py

from crewai import Task
from datetime import timedelta
from Agents.agents.planner_agent import planner_agent
from Agents.tasks.strategy_task import strategy_task
from Agents.tasks.resources_task import resources_task

# Create the planner task
planner_task = Task(
    description=(
        "Create a detailed daily study plan that incorporates the strategies and resources "
        "identified by other team members. Break down how to apply each learning strategy "
        "with specific resources on specific days. The plan should be practical, realistic, "
        "and personalized to the student's needs."
        "\n\n"
        "You have access to:"
        "\n1. A list of effective learning strategies for the student's subject"
        "\n2. A detailed list of specific resources for each strategy"
        "\n3. Student's preferences on learning style, available time, and schedule needs"
        "\n4. Any syllabus or curriculum details"
        "\n\n"
        "Your plan MUST include:"
        "\n1. A day-by-day schedule for the entire study period"
        "\n2. How many hours to dedicate each day"
        "\n3. Specific strategy+resource combinations for each day"
        "\n4. EXACTLY what sections of each resource to use (pages, chapters, timestamps)"
        "\n5. Expected outcomes and milestones to track progress"
        "\n6. Breaks and review sessions built into the schedule"
        "\n7. Weekend vs. weekday adjustments based on available time"
        "\n8. Recommendations for note-taking and retention during each study session"
    ),
    expected_output=(
        "A comprehensive, day-by-day study plan that integrates strategies and resources into "
        "a personalized schedule. Format as follows:\n\n"
        
        "STUDY PLAN OVERVIEW:\n"
        "- Subject: [Subject Name]\n"
        "- Total Study Period: [X days/weeks]\n"
        "- Daily Time Commitment: [X-Y hours]\n"
        "- Major Milestones: [List key milestones]\n\n"
        
        "DAY 1: [Day of week, Date if applicable]\n"
        "- Time Block 1 ([duration]): [Strategy] using [Specific Resource]\n"
        "  * Exactly what to study: [Specific chapters/sections/pages/timestamps]\n"
        "  * How to implement the strategy: [Concrete steps]\n"
        "  * Expected outcome: [What student should achieve]\n"
        "- Time Block 2 ([duration]): [Details as above]\n"
        "- Review session ([duration]): [Specific review technique]\n\n"
        
        "[Repeat for each day of the study period]\n\n"
        
        "PROGRESS TRACKING:\n"
        "- Key checkpoints: [List how to self-assess understanding]\n"
        "- Adjustments: [When and how to modify the plan if falling behind]\n\n"
        
        "ADDITIONAL RECOMMENDATIONS:\n"
        "- Note-taking approach: [Subject-specific note techniques]\n"
        "- Environment: [Study environment suggestions]\n"
        "- Support: [When to seek additional help]"
    ),
    agent=planner_agent,
    async_execution=False,
    human_input=False,
    # This task depends on both strategy and resources tasks
    depends_on=[strategy_task, resources_task]
)
