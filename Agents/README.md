# Study Plan Generator with CrewAI

A multi-agent system that creates personalized study plans based on learning science research and user data from the LearnMate application.

## Features

- **Strategy Agent**: Analyzes scientific research on learning methods to recommend effective study strategies
- **Resources Agent**: Searches the web for specific study resources including exact chapters, pages and timestamps
- **Planner Agent**: Creates detailed, day-by-day study plans based on recommended strategies and resources
- **Interactive Input**: Collects user information about subject, exam type, and study preferences
- **Research-Based**: Uses scientific context to justify recommended learning strategies
- **Web Search Integration**: Uses DuckDuckGo search to find up-to-date, specific resource recommendations
- **Backend Data Integration**: Connects to LearnMate backend to use:
  - User preferences and learning styles
  - Session data and preferences
  - Course syllabus content for topic-specific resources
  - Existing session resources

## Agent Workflow

1. **Strategy Agent** analyzes research to recommend learning strategies based on user's needs and syllabus
2. **Resources Agent** performs web searches to find specific resources for each strategy and syllabus topic
3. **Planner Agent** creates a comprehensive study plan incorporating strategies, resources, and syllabus

## Setup

### Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running with Interactive Mode

For standalone usage without backend data:

```bash
python main.py
```

### Running with Backend Data

To use user preferences and session data from the backend:

```bash
python main.py --user_id <user_id> --session_id <session_id>
```

To combine backend data with interactive input:

```bash
python main.py --user_id <user_id> --session_id <session_id> --interactive
```

## Integration with LearnMate

The agent system integrates with LearnMate:

1. **User Preferences**: Pulls learning style, difficulty preferences, time availability
2. **Session Data**: Uses session-specific information (subject, exam type, study hours)
3. **Syllabus Integration**: Extracts topics from uploaded syllabi to target resources
4. **Existing Resources**: Considers resources already added to the study session

## Data Usage

When connected to backend data, the system:

1. Extracts syllabus topics and searches for resources specific to each topic
2. Tailors recommendations based on user's learning style preferences
3. Creates study plans that align with the syllabus structure
4. Considers time constraints and study preferences from the session
5. Produces more personalized and relevant study plans

## Troubleshooting

- If experiencing import errors, ensure all dependencies are installed
- For syllabus processing issues, check that the syllabus file was properly uploaded
- When running with backend data, verify the user_id and session_id are correct
- If the LLM connection fails, ensure Ollama is running with the llama3 model available

## Files Structure

- `main.py` - Main application entry point with user input collection and backend data integration
- `agents/`
  - `strategy_agent.py` - Agent for analyzing learning science research with syllabus awareness
  - `resources_agent.py` - Agent for searching the web for study resource recommendations by topic
  - `planner_agent.py` - Agent for creating detailed study plans aligned with syllabus
- `tasks/`
  - `strategy_task.py` - Task definition for strategy recommendations
  - `resources_task.py` - Task with web search instructions for resource recommendations by topic
  - `planner_task.py` - Task definition for syllabus-aligned study plan creation
- `utils/`
  - `context_loader.py` - Loads scientific research from PDFs and text files
  - `data_fetcher.py` - Fetches user and session data from the LearnMate backend
- `knowledge_base/` - Scientific papers and research on learning methods

## Usage

Run the application with:

```bash
python main.py
```

Follow the prompts to input your study needs and preferences, and receive a personalized study plan along with recommended resources. 