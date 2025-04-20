# agents/planner_agent.py

from crewai import Agent
from crewai.tools import BaseTool
from llm_config import llama_llm
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Type
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_schedule(days, hours_per_day, start_date=None):
    """Calculate a study schedule based on the number of days and hours per day"""
    if not start_date:
        start_date = datetime.now()
    
    schedule = []
    for i in range(int(days)):
        day = start_date + timedelta(days=i)
        schedule.append({
            'day': day.strftime('%A, %B %d'),
            'date': day.strftime('%Y-%m-%d'),
            'hours': hours_per_day
        })
    
    return schedule

# Define schema for the scheduler tool
class SchedulerSchema(BaseModel):
    days: int = Field(..., description="Number of days to schedule")
    hours_per_day: float = Field(2.0, description="Hours per day to study")
    start_date: str = Field(None, description="Start date for the schedule (optional)")

# Create proper CrewAI BaseTool classes
class SchedulerTool(BaseTool):
    name: str = "calculate_schedule"
    description: str = "Calculate a study schedule based on the number of days and hours per day"
    args_schema: Type[BaseModel] = SchedulerSchema
    
    def _run(self, days, hours_per_day=2, start_date=None):
        return calculate_schedule(days, hours_per_day, start_date)

# Instantiate the tool class
scheduler_tool = SchedulerTool()

# Create the planner agent with BaseTool instance
planner_agent = Agent(
    role="Study Plan Architect",
    goal="Create a detailed, day-by-day study plan that integrates learning strategies and resources.",
    backstory=(
        "You are a master planner with expertise in creating effective study schedules. "
        "You understand how to distribute learning activities optimally over time, "
        "combining strategies like spaced repetition, interleaving, and deliberate practice. "
        "You know how to break down complex subjects into manageable daily tasks. "
        "You excel at creating practical, actionable plans that balance intensive "
        "focus with proper breaks and review sessions. Your specialty is incorporating "
        "evidence-based learning methods into realistic schedules that account for "
        "a student's available time and preferences."
    ),
    llm=llama_llm,
    verbose=True,
    allow_delegation=False,
    tools=[scheduler_tool],
    # Add tools metadata with context
    tools_metadata={
        "scheduler_options": {
            "minimum_daily_sessions": 1,
            "maximum_daily_hours": 6,
            "recommended_session_length": 45,
            "recommended_break_time": 15
        }
    }
)
