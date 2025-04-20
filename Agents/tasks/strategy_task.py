# tasks/strategy_task.py

from crewai import Task
from Agents.agents.strategy_agent import strategy_agent

# Create the strategy task
strategy_task = Task(
    description=(
        "Identify and explain the most effective learning strategies for the specific subject, "
        "considering the student's learning profile and preferences. "
        "\n\n"
        "You should:"
        "\n1. Analyze the subject matter and identify its unique learning challenges"
        "\n2. Consider the student's learning style, available study time, and preferences"
        "\n3. Recommend 5-7 specific, evidence-based learning strategies that are particularly effective for this subject"
        "\n4. For each strategy, explain exactly how to implement it for this specific subject"
        "\n5. Prioritize strategies proven by cognitive science research"
        "\n6. Include a mix of strategies for initial learning, deep processing, and retention/recall"
    ),
    expected_output=(
        "A comprehensive analysis of effective learning strategies for the subject, formatted as follows:\n\n"
        
        "SUBJECT ANALYSIS:\n"
        "- Subject complexity: [assessment of complexity level]\n"
        "- Key learning challenges: [list specific challenges]\n"
        "- Core skill requirements: [conceptual understanding, memorization, problem-solving, etc.]\n\n"
        
        "RECOMMENDED LEARNING STRATEGIES:\n\n"
        
        "1. [STRATEGY NAME]\n"
        "- Why it works for this subject: [explanation]\n"
        "- Implementation steps:\n"
        "  a. [Specific implementation instructions for this subject]\n"
        "  b. [Continue with specific steps]\n"
        "- Expected benefits: [concrete outcomes]\n"
        "- Scientific basis: [brief research backing]\n\n"
        
        "[Repeat for each recommended strategy]\n\n"
        
        "STRATEGY COMBINATIONS AND SEQUENCING:\n"
        "- Initial learning phase: [which strategies to use first]\n"
        "- Deep processing phase: [which strategies to use for deeper understanding]\n"
        "- Retention and recall phase: [which strategies to use for long-term retention]"
    ),
    agent=strategy_agent,
    async_execution=False,
    human_input=False
)

# If you need to use the raw context, set it as a property on the agent or
# pass it when executing the task
