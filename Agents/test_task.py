#!/usr/bin/env python
"""
Debug test script for crewAI Task and TaskOutput.
"""

from crewai import Agent, Task, Crew, Process, TaskOutput
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_crewai_task():
    """Test crewAI Task and TaskOutput initialization."""
    try:
        from langchain.llms import Ollama

        llm = Ollama(
            model="llama3",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Create agent
        agent = Agent(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",
            llm=llm
        )
        
        # Test TaskOutput with string
        logger.info("Testing TaskOutput with string agent")
        try:
            task_output = TaskOutput(
                agent="Test Agent",  # STRING
                output_files=["test.txt"],
                description="Test description"
            )
            logger.info("SUCCESS: TaskOutput accepts string agent")
        except Exception as e:
            logger.error(f"ERROR: TaskOutput with string agent failed: {str(e)}")
        
        # Test TaskOutput with Agent object
        logger.info("Testing TaskOutput with Agent object")
        try:
            task_output = TaskOutput(
                agent=agent,  # AGENT OBJECT
                output_files=["test.txt"],
                description="Test description"
            )
            logger.info("SUCCESS: TaskOutput accepts Agent object")
        except Exception as e:
            logger.error(f"ERROR: TaskOutput with Agent object failed: {str(e)}")
        
        # Test Task with string agent
        logger.info("Testing Task with string agent")
        try:
            task = Task(
                description="Test description",
                expected_output="Test output",
                agent="Test Agent"  # STRING
            )
            logger.info("SUCCESS: Task accepts string agent")
        except Exception as e:
            logger.error(f"ERROR: Task with string agent failed: {str(e)}")
        
        # Test Task with Agent object
        logger.info("Testing Task with Agent object")
        try:
            task = Task(
                description="Test description",
                expected_output="Test output",
                agent=agent  # AGENT OBJECT
            )
            logger.info("SUCCESS: Task accepts Agent object")
        except Exception as e:
            logger.error(f"ERROR: Task with Agent object failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Overall test error: {str(e)}")

if __name__ == "__main__":
    test_crewai_task() 