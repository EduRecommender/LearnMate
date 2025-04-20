from crewai import Task
from Agents.agents.resources_agent import resources_agent
from Agents.tasks.strategy_task import strategy_task

# Create the resources task with web search instructions
resources_task = Task(
    description=(
        "Search the web to find highly specific study resources for the given subject and learning strategies. "
        "For each learning strategy from the previous task, perform separate web searches to find resources "
        "specifically designed to implement that strategy. "
        "\n\n"
        "SEARCH PROCESS FOR EACH STRATEGY:"
        "\n1. For each learning strategy, perform multiple web searches using different queries"
        "\n2. Use search queries that combine the subject, the strategy name, and terms like 'specific chapters', "
        "'recommended sections', 'timestamps', etc."
        "\n3. Look for resource recommendations from educational websites, forums, course platforms, etc."
        "\n4. For books, search for specific chapter recommendations or reviews mentioning useful sections"
        "\n5. For videos, search for ones that include timestamps in their descriptions"
        "\n6. For online courses, look for syllabi or module breakdowns"
        "\n\n"
        "REQUIRED FOR EACH RESOURCE FOUND:"
        "\n1. The full title/name of the resource"
        "\n2. Author/creator names when available"
        "\n3. Direct URL or exact location where to find it"
        "\n4. SPECIFIC sections most relevant to the subject (page numbers, chapters, video timestamps)"
        "\n5. Which learning strategy this resource supports and how to use it for that strategy"
        "\n6. Any cost information (free, subscription, one-time purchase)"
        "\n\n"
        "IMPORTANT: Your recommendations must be based on actual web search results. "
        "Use the web_search tool for each strategy and subject combination. "
        "Include a mix of different types of resources (books, videos, interactive tools, etc.)."
    ),
    expected_output=(
        "A comprehensive list of specific study resources found through web search, organized by learning strategy:\n\n"
        
        "FOR EACH LEARNING STRATEGY FROM THE PREVIOUS TASK:\n"
        "STRATEGY: [Name of learning strategy]\n\n"
        
        "SEARCH QUERIES USED:\n"
        "- [List the actual search queries you used to find resources]\n\n"
        
        "RESOURCES FOUND FOR THIS STRATEGY:\n"
        "1. [RESOURCE TYPE: Book/Video/Course/etc.]\n"
        "   - Title: [Exact title]\n"
        "   - Creator: [Author/Instructor name]\n"
        "   - Where to find: [Direct URL or specific store/platform]\n"
        "   - Specific sections: [Exact chapters, page numbers, video timestamps if found]\n"
        "   - How it implements this strategy: [Brief explanation]\n"
        "   - Cost: [Price information if available]\n"
        "   - Source of recommendation: [Where you found this recommendation]\n\n"
        
        "2. [Next resource...]\n\n"
        
        "[Repeat for each learning strategy from previous task]"
    ),
    agent=resources_agent,
    # This task depends on the strategy task
    async_execution=False,
    human_input=False,
    depends_on=[strategy_task]
) 