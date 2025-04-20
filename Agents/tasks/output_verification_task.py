from crewai import Task
from Agents.agents.output_verifier_agent import output_verifier_agent
from Agents.tasks.planner_task import planner_task

verification_task = Task(
    description=(
        "Review and enhance the study plan created by the Planner Agent to ensure it meets "
        "all quality standards and includes all necessary information to be immediately actionable. "
        "\n\n"
        "VERIFICATION CHECKLIST:"
        "\n1. Ensure each resource has a direct URL/link that is fully functional"
        "\n2. Include specific chapters, sections, or timestamps ONLY if they were actually provided in the previous tasks - do not invent these details"
        "\n3. Check that time allocations are appropriate and realistic"
        "\n4. Ensure instructions for applying each learning strategy are clear and detailed"
        "\n5. Verify that all terms and concepts are clearly explained"
        "\n6. Add any missing information needed to make the plan immediately actionable"
        "\n7. Format the plan consistently with clear headings and organized sections"
        "\n8. Ensure all links and references are working and point to accessible resources"
        "\n\n"
        "If any information is missing or incomplete, enhance it with additional details "
        "to make the study plan more effective and easier to follow. However, do NOT invent "
        "specific section references (chapters, timestamps) if they weren't actually found "
        "during resource discovery."
    ),
    expected_output=(
        "A fully verified and enhanced study plan that: \n"
        "1. Maintains the original structure and content where appropriate\n"
        "2. Includes direct, working links to all resources\n"
        "3. Contains specific section references (chapters, timestamps, etc.) only where they were actually found\n"
        "4. Has detailed, clear instructions for each activity\n"
        "5. Is consistently formatted with proper headings and organization\n"
        "6. Is immediately actionable without requiring additional research\n"
        "\n"
        "The enhanced plan should maintain the same basic daily structure as the original "
        "but with improved clarity, completeness, and precision."
    ),
    agent=output_verifier_agent,
    # This task depends on the planner task
    async_execution=False,
    human_input=False,
    depends_on=[planner_task]
) 