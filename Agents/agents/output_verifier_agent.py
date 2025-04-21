from crewai import Agent
from crewai.tools import BaseTool
from Agents.llm_config import llama_llm
from typing import Type, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define schema for validation
class ValidationSchema(BaseModel):
    study_plan: str = Field(..., description="The complete study plan to validate")
    syllabus_topics: List[str] = Field([], description="List of topics from the syllabus")
    days: int = Field(..., description="Number of days available")
    hours_per_day: float = Field(..., description="Hours available per day")

# Create a validation tool
class ValidationTool(BaseTool):
    name: str = "validate_study_plan"
    description: str = "Validate that a study plan meets all requirements"
    args_schema: Type[BaseModel] = ValidationSchema
    
    def _run(self, study_plan, syllabus_topics=[], days=7, hours_per_day=2):
        """Validate the study plan against requirements"""
        validation_results = {
            "time_constraint_validation": self._validate_time_constraints(study_plan, days, hours_per_day),
            "topic_coverage_validation": self._validate_topic_coverage(study_plan, syllabus_topics),
            "resource_specificity_validation": self._validate_resource_specificity(study_plan),
            "strategy_integration_validation": self._validate_strategy_integration(study_plan),
            "actionability_validation": self._validate_actionability(study_plan)
        }
        
        # Calculate overall validation score
        passed_validations = sum(1 for result in validation_results.values() if result["passed"])
        total_validations = len(validation_results)
        validation_score = (passed_validations / total_validations) * 100
        
        # Combine all issues
        all_issues = []
        for validation_type, result in validation_results.items():
            if not result["passed"]:
                all_issues.extend(result["issues"])
        
        return {
            "passed": validation_score >= 90,
            "validation_score": validation_score,
            "validation_results": validation_results,
            "issues_to_fix": all_issues,
            "passed_validations": passed_validations,
            "total_validations": total_validations
        }
    
    def _validate_time_constraints(self, study_plan, days, hours_per_day):
        """Validate that the plan respects time constraints"""
        # This is a simplified validation - would need NLP to parse actual times from the plan
        expected_total_hours = days * hours_per_day
        hours_pattern = r'(\d+)\s*(hour|hr)'
        minutes_pattern = r'(\d+)\s*(minute|min)'
        
        # Simulated validation result
        issues = []
        
        # Check for obvious time mismatches (e.g., more days than specified)
        if f"Day {days+1}" in study_plan or f"DAY {days+1}:" in study_plan:
            issues.append(f"Plan includes more than the specified {days} days")
        
        # Look for any day headers that exceed the specified days limit
        day_header_pattern = r'(?:Day|DAY)\s+(\d+)'
        day_matches = re.findall(day_header_pattern, study_plan)
        
        if day_matches:
            day_numbers = [int(day) for day in day_matches]
            max_day = max(day_numbers) if day_numbers else 0
            
            if max_day > days:
                issues.append(f"Plan includes Day {max_day}, but user only specified {days} days")
            
            # Check if plan is missing some days
            expected_days = set(range(1, days + 1))
            found_days = set(day_numbers)
            missing_days = expected_days - found_days
            
            if missing_days:
                missing_days_list = sorted(list(missing_days))
                issues.append(f"Plan is missing days: {', '.join(str(d) for d in missing_days_list)}")
        
        # Check if no day headers are found at all
        if not any(f"Day {i}" in study_plan or f"DAY {i}:" in study_plan for i in range(1, days+1)):
            issues.append("Plan doesn't clearly indicate daily breakdown with proper day headers")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "expected_total_hours": expected_total_hours
        }
    
    def _validate_topic_coverage(self, study_plan, syllabus_topics):
        """Validate that all syllabus topics are covered"""
        issues = []
        covered_topics = []
        
        # Check each syllabus topic
        for topic in syllabus_topics:
            if topic.lower() in study_plan.lower():
                covered_topics.append(topic)
            else:
                issues.append(f"Topic '{topic}' does not appear to be covered in the plan")
        
        coverage_percentage = 100 if not syllabus_topics else (len(covered_topics) / len(syllabus_topics)) * 100
        
        return {
            "passed": coverage_percentage == 100,
            "issues": issues,
            "coverage_percentage": coverage_percentage,
            "covered_topics": covered_topics,
            "missing_topics": [topic for topic in syllabus_topics if topic not in covered_topics]
        }
    
    def _validate_resource_specificity(self, study_plan):
        """Validate that resources are specific with chapters/sections/URLs"""
        issues = []
        
        # Use a more detailed regex to find resource sections
        resource_pattern = r'Resources:(.*?)(?=Activities:|Day \d+|$)'
        resource_sections = re.findall(resource_pattern, study_plan, flags=re.DOTALL | re.IGNORECASE)
        
        if not resource_sections:
            issues.append("Plan doesn't clearly mark resource sections")
            return {
                "passed": False,
                "issues": issues
            }
        
        # Check each resource section for specificities
        total_resources = 0
        resources_with_urls = 0
        resources_with_specifics = 0
        resources_using_syllabus = 0
        
        for section in resource_sections:
            # Extract resources from the section (lines starting with '-')
            resources = [line.strip() for line in section.split('\n') if line.strip().startswith('-')]
            total_resources += len(resources)
            
            for resource in resources:
                # Check for syllabus usage (critical error)
                if any(s in resource.lower() for s in ['syllabus', 'syllabi', 'course outline']):
                    issues.append(f"CRITICAL: Using syllabus as a study resource: '{resource}'")
                    resources_using_syllabus += 1
                
                # Check for URLs
                if 'http' in resource or 'www.' in resource:
                    resources_with_urls += 1
                else:
                    issues.append(f"Resource lacks URL: '{resource}'")
                
                # Check for specificity
                if any(specificity in resource.lower() for specificity in ['chapter', 'page', 'section', 'timestamp', 'minutes']):
                    resources_with_specifics += 1
                else:
                    issues.append(f"Resource lacks specific section references: '{resource}'")
        
        # Calculate validation metrics
        url_coverage = resources_with_urls / total_resources if total_resources > 0 else 0
        specificity_coverage = resources_with_specifics / total_resources if total_resources > 0 else 0
        
        # Validation passed if we have enough coverage and no syllabus usage
        passed = url_coverage >= 0.75 and specificity_coverage >= 0.75 and resources_using_syllabus == 0
        
        return {
            "passed": passed,
            "issues": issues,
            "metrics": {
                "total_resources": total_resources,
                "url_coverage": url_coverage,
                "specificity_coverage": specificity_coverage,
                "resources_using_syllabus": resources_using_syllabus
            }
        }
    
    def _validate_strategy_integration(self, study_plan):
        """Validate that learning strategies are integrated with resources"""
        issues = []
        
        # Check for evidence-based strategy mentions
        strategies = [
            "spaced repetition", "retrieval practice", "interleaving", "concrete examples", 
            "dual coding", "elaboration", "self explanation", "feynman", "pomodoro",
            "3r method", "read-recite-review", "visual mapping", "verbal recitation"
        ]
        
        # Check for strategy mentions
        strategy_mentions = [strategy for strategy in strategies if strategy.lower() in study_plan.lower()]
        
        if not strategy_mentions:
            issues.append("Plan doesn't mention specific evidence-based learning strategies")
        
        # Check for research citations
        research_mentions = re.findall(r'\([^)]*\d{4}[^)]*\)', study_plan)
        if not research_mentions:
            issues.append("Plan doesn't reference evidence-based research for strategies")
        
        # Check for strategy-resource pairing
        has_strategy_resource_pairing = False
        for strategy in strategy_mentions:
            # Look for patterns like "Apply [strategy] with [resource]"
            # This is a simplified check
            strategy_context = study_plan.lower().find(strategy.lower())
            if strategy_context > 0:
                context_window = study_plan[max(0, strategy_context-50):min(len(study_plan), strategy_context+100)]
                if "resource" in context_window.lower() or "book" in context_window.lower() or "video" in context_window.lower():
                    has_strategy_resource_pairing = True
                    break
        
        if not has_strategy_resource_pairing and strategy_mentions:
            issues.append("Strategies are mentioned but not clearly paired with specific resources")
        
        # Check for strategy justification
        strategy_justification = re.search(r'Strategy:.*?(?:based on|according to|research by)', study_plan, re.IGNORECASE)
        if not strategy_justification:
            issues.append("Strategies lack justification or reference to supporting research")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "identified_strategies": strategy_mentions,
            "has_research_citations": len(research_mentions) > 0,
            "has_strategy_justification": strategy_justification is not None
        }
    
    def _validate_actionability(self, study_plan):
        """Validate that the plan is actionable without requiring further decisions"""
        issues = []
        
        # Check for clear time allocations
        time_allocations = re.findall(r'\(\d+[\s-]*(minute|min|hour|hr)s?\)', study_plan, re.IGNORECASE)
        if not time_allocations:
            issues.append("Plan lacks clear time allocations in minutes or hours")
        
        # Check for clear instructions
        clear_instruction_indicators = ["complete", "read", "watch", "practice", "review", "do", "solve"]
        has_clear_instructions = any(indicator in study_plan.lower() for indicator in clear_instruction_indicators)
        
        if not has_clear_instructions:
            issues.append("Plan lacks clear action verbs (read, watch, practice, etc.)")
        
        # Check for decision offloading (leaving decisions to the student)
        decision_offloading_indicators = ["choose", "select", "decide", "pick", "any", "whatever", "optional"]
        has_decision_offloading = any(indicator in study_plan.lower() for indicator in decision_offloading_indicators)
        
        if has_decision_offloading:
            issues.append("Plan offloads decisions to the student (choose, select, decide, etc.)")
        
        # Check for explicit outcomes
        outcome_indicators = ["→", "outcome:", "you will", "resulting in", "produces", "leads to", "creates"]
        has_explicit_outcomes = any(indicator in study_plan for indicator in outcome_indicators)
        
        if not has_explicit_outcomes:
            issues.append("Plan lacks explicit outcomes for activities")
            
        # NEW: Check for consistent day formatting
        day_headers = re.findall(r'DAY \d+:|Day \d+|Day \d+\*\*', study_plan)
        proper_day_format = True
        
        if not day_headers:
            issues.append("Plan lacks clear day headers")
            proper_day_format = False
        else:
            for header in day_headers:
                if not header.startswith("DAY ") or not header.endswith(":"):
                    issues.append(f"Inconsistent day header format: '{header}' should be 'DAY X:'")
                    proper_day_format = False
        
        # Check for resource formatting
        if "RESOURCES:" not in study_plan and "RECOMMENDED RESOURCES:" not in study_plan:
            issues.append("Plan lacks a clearly marked resources section")
        
        # Check for total time adherence
        total_hours_match = re.search(r'Total Time: (\d+(?:\.\d+)?) hours?', study_plan)
        if total_hours_match:
            total_hours = float(total_hours_match.group(1))
            # Extract hours per day from the context
            hours_per_day_match = re.search(r'(\d+(?:\.\d+)?) hours per day', study_plan)
            if hours_per_day_match:
                hours_per_day = float(hours_per_day_match.group(1))
                days_match = re.search(r'(\d+) days?', study_plan)
                if days_match:
                    days = int(days_match.group(1))
                    expected_hours = days * hours_per_day
                    if abs(total_hours - expected_hours) > 0.5:  # Allow for 0.5 hour difference
                        issues.append(f"Total hours ({total_hours}) don't match days × hours per day ({expected_hours})")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "proper_day_format": proper_day_format,
            "has_time_allocations": len(time_allocations) > 0,
            "has_clear_instructions": has_clear_instructions,
            "has_explicit_outcomes": has_explicit_outcomes,
            "has_decision_offloading": has_decision_offloading
        }

# Instantiate the tool
validation_tool = ValidationTool()

output_verifier_agent = Agent(
    role="Study Plan Quality Assurance Specialist",
    goal="Ensure the final study plan meets all requirements for time constraints, topic coverage, resource specificity, and actionability.",
    backstory=(
        "You are a meticulous educational content reviewer with an eye for detail and quality. "
        "You specialize in verifying that study plans have all required components and follow a "
        "consistent, user-friendly format. You check that all resources listed include direct links, "
        "that specific chapters/sections/timestamps are mentioned, and that instructions are clear. "
        "You verify that time constraints are strictly respected - never planning more activities than "
        "can fit in the available time, and ensuring all syllabus topics are covered. "
        "You're particularly attentive to making sure each study activity specifies which resource to use "
        "(with exact chapters or sections) and which learning strategy to apply. You don't let study plans "
        "pass review unless they meet stringent quality criteria for specificity, time allocation, "
        "topic coverage, and actionability. When issues are found, you provide specific fixes."
    ),
    llm=llama_llm,
    verbose=True,
    allow_delegation=False,
    tools=[validation_tool],
    tools_metadata={
        "validation_criteria": {
            "time_constraints": "Plan must not exceed specified days and hours per day, with clear time allocations",
            "topic_coverage": "All syllabus topics must be covered in the plan",
            "resource_specificity": "Each resource must include specific chapters, sections, timestamps, or URLs",
            "strategy_integration": "Learning strategies must be paired with specific resources and activities",
            "actionability": "Plan must provide clear instructions without requiring further decisions"
        },
        "common_issues": {
            "vague_resources": "Mentioning 'textbook' without specifying which chapters or pages",
            "undefined_timing": "Not specifying how long each activity should take",
            "syllabus_as_resource": "Recommending studying the syllabus itself (it's just an outline)",
            "missing_topics": "Failing to address all topics in the syllabus",
            "time_overflow": "Planning more activities than can fit in the available time",
            "decision_offloading": "Telling students to 'choose a resource' rather than specifying one"
        },
        "quality_standards": {
            "minimum_topic_coverage": "100% of syllabus topics must be covered",
            "resource_specificity_requirement": "Each resource must include page numbers, chapters, timestamps, or URLs",
            "time_allocation_requirement": "Each activity must have a specific time allocation in minutes or hours",
            "strategy_integration_requirement": "Each study session must specify which learning strategy to use"
        }
    }
) 