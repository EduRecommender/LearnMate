import json

import pytest

from backend.app.services.methodology_search import MethodologySearchTool
from backend.app.services.resource_search import ResourceSearchTool
from backend.app.services.study_plan_engine import StudyPlanEngine, StudyPlanEngineError


class FakeOllama:
    def __init__(self, responses=None, available=True):
        self.responses = list(responses or [])
        self.available = available
        self.calls = []

    def assert_available(self):
        if not self.available:
            raise StudyPlanEngineError("context", "Ollama unavailable", retryable=True)

    def generate(self, prompt):
        self.calls.append(prompt)
        if not self.responses:
            raise AssertionError("FakeOllama ran out of responses")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def j(data):
    return json.dumps(data)


def specialist(content, evidence=None, warnings=None, status="succeeded", needs_retry=False):
    return j({
        "status": status,
        "content": content,
        "evidence": evidence or [],
        "warnings": warnings or [],
        "needs_retry": needs_retry,
    })


def valid_plan(days=2):
    day_sections = "\n".join(
        f"DAY {day}:\n- Study core topic {day} for 50 minutes.\n- Take a 10-minute break.\n"
        for day in range(1, days + 1)
    )
    return f"""STUDY PLAN OVERVIEW:
This plan uses retrieval practice and spaced repetition.

{day_sections}
RECOMMENDED RESOURCES:
Use Computer Vision textbook.pdf chapters about kernels and pooling.

IMPLEMENTATION TIPS:
Review notes after each session.
"""


def base_context(days=2):
    return {
        "subject": "Computer Vision",
        "study_goal": "Final exam preparation",
        "days_until_exam": days,
        "hours_per_day": 2,
        "resources": [{
            "id": 2,
            "name": "Computer Vision textbook.pdf",
            "type": "file",
            "content": "Convolutional neural networks use kernels, pooling, and feature maps for image classification.",
        }],
    }


def success_responses(plan=None):
    plan = plan or valid_plan(days=2)
    return [
        j({"action": "delegate", "agent": "strategy", "task": "Create evidence-based study strategy."}),
        j({"tool_calls": [{"tool": "search_methodology", "query": "retrieval practice spaced repetition exam prep"}]}),
        specialist("Use retrieval practice, spaced repetition, and error review."),
        j({"action": "approve", "agent": "strategy"}),
        j({"action": "delegate", "agent": "resources", "task": "Find grounded resources for weak topics."}),
        j({"tool_calls": [{"tool": "search_resources", "query": "convolutional neural networks kernels pooling"}]}),
        specialist("Use Computer Vision textbook.pdf sections about kernels and pooling."),
        j({"action": "approve", "agent": "resources"}),
        j({"action": "delegate", "agent": "planner", "task": "Create a day-by-day plan using the approved strategy and resources."}),
        j({"tool_calls": [{"tool": "search_methodology", "query": "study plan design focus blocks breaks"}]}),
        specialist(plan),
        j({"action": "approve", "agent": "planner"}),
        j({"action": "delegate", "agent": "verifier", "task": "Verify the plan against constraints and grounding."}),
        specialist("Verified: schedule, sections, and resource grounding pass."),
        j({"action": "approve", "agent": "verifier"}),
        j({"action": "delegate", "agent": "formatter", "task": "Format the verified plan for the chat response."}),
        specialist(plan),
        j({"action": "approve", "agent": "formatter"}),
        j({"action": "final", "content": plan}),
    ]


def test_orchestrator_delegates_agents_uses_tools_and_returns_success():
    events = []
    engine = StudyPlanEngine(llm=FakeOllama(success_responses()))

    result = engine.generate(base_context(), progress=lambda stage, message: events.append((stage, message)))

    assert result.status == "succeeded"
    assert "DAY 1:" in result.content
    assert "DAY 2:" in result.content
    assert result.resources_used[0]["name"] == "Computer Vision textbook.pdf"
    assert any(stage == "orchestrator" and "approved formatter" in message for stage, message in events)
    assert any(stage == "strategy" and "searched methodology" in message for stage, message in events)
    assert any(stage == "resources" and "searched uploaded resources" in message for stage, message in events)
    assert any(stage == "planning" and "searched methodology" in message for stage, message in events)


def test_orchestrator_retries_failed_specialist_then_succeeds():
    responses = [
        j({"action": "delegate", "agent": "strategy", "task": "Create strategy."}),
        specialist("Too vague.", status="failed", needs_retry=True),
        j({"action": "retry", "agent": "strategy", "feedback": "Use methodology evidence."}),
        j({"tool_calls": [{"tool": "search_methodology", "query": "retrieval practice"}]}),
        specialist("Use retrieval practice and spaced repetition with daily error review."),
        j({"action": "approve", "agent": "strategy"}),
    ] + success_responses()[4:]
    engine = StudyPlanEngine(llm=FakeOllama(responses))

    result = engine.generate(base_context())

    assert result.status == "succeeded"
    assert "DAY 2:" in result.content


def test_orchestrator_fails_when_max_steps_exceeded():
    engine = StudyPlanEngine(llm=FakeOllama([
        j({"action": "tool_call", "tool": "search_methodology", "query": "retrieval practice"})
        for _ in range(12)
    ]))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate(base_context())

    assert exc_info.value.stage == "orchestrator"
    assert "max step limit" in exc_info.value.message


def test_malformed_json_from_orchestrator_fails_explicitly():
    engine = StudyPlanEngine(llm=FakeOllama(["I am not JSON"]))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate(base_context())

    assert exc_info.value.stage == "orchestrator"
    assert "malformed JSON" in exc_info.value.message


def test_unknown_tool_action_fails_explicitly():
    engine = StudyPlanEngine(llm=FakeOllama([
        j({"action": "tool_call", "tool": "web_search", "query": "cnn"})
    ]))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate(base_context())

    assert exc_info.value.stage == "orchestrator"
    assert "Unknown orchestrator tool" in exc_info.value.message


def test_specialist_malformed_json_fails_explicitly():
    engine = StudyPlanEngine(llm=FakeOllama([
        j({"action": "delegate", "agent": "resources", "task": "Find resources."}),
        "not json",
    ]))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate(base_context())

    assert exc_info.value.stage == "resources"
    assert "malformed JSON" in exc_info.value.message


def test_verifier_rejects_missing_day_sections():
    bad_plan = valid_plan(days=1)
    engine = StudyPlanEngine(llm=FakeOllama(success_responses(plan=bad_plan)))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate(base_context(days=2))

    assert exc_info.value.stage == "verification"
    assert "missing required day sections" in exc_info.value.message


def test_resources_approval_rejects_syllabus_as_resource():
    responses = [
        j({"action": "delegate", "agent": "resources", "task": "Find resources."}),
        specialist("RECOMMENDED RESOURCES:\nUse the course syllabus as the main resource.", evidence=[{"source": "course syllabus"}]),
        j({"action": "approve", "agent": "resources"}),
    ]
    engine = StudyPlanEngine(llm=FakeOllama(responses))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate(base_context())

    assert exc_info.value.stage == "resources"
    assert "syllabus" in exc_info.value.message


def test_engine_fails_when_ollama_unavailable_instead_of_fallback_plan():
    engine = StudyPlanEngine(llm=FakeOllama(available=False))

    with pytest.raises(StudyPlanEngineError) as exc_info:
        engine.generate({"subject": "Computer Vision"})

    assert exc_info.value.stage == "context"
    assert "Ollama unavailable" in exc_info.value.message


def test_resource_search_finds_relevant_uploaded_snippet_and_skips_syllabus():
    search = ResourceSearchTool()

    hits = search.search(
        [
            {
                "id": 1,
                "name": "course syllabus.pdf",
                "type": "file",
                "content": "Week 1 convolutional neural networks",
                "metadata": {"is_syllabus": True},
            },
            {
                "id": 2,
                "name": "vision notes.txt",
                "type": "text",
                "content": "Convolutional neural networks rely on convolution kernels and pooling layers.",
            },
        ],
        "I need help with convolutional neural networks and pooling",
    )

    assert len(hits) == 1
    assert hits[0]["id"] == 2
    assert "pooling layers" in hits[0]["snippet"]


def test_methodology_search_finds_study_methods():
    search = MethodologySearchTool()

    hits = search.search("retrieval practice spaced repetition")

    assert hits
    assert any("retrieval" in hit["snippet"].lower() or "spaced" in hit["snippet"].lower() for hit in hits)
