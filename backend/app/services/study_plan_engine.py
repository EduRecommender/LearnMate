import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import requests

from .methodology_search import MethodologySearchTool
from .resource_search import ResourceSearchTool
from ..core.config import settings


ProgressCallback = Callable[[str, str], None]


class StudyPlanEngineError(Exception):
    def __init__(self, stage: str, message: str, retryable: bool = True):
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.retryable = retryable


@dataclass
class StudyPlanEngineResult:
    status: str
    content: str
    stages: List[Dict[str, Any]] = field(default_factory=list)
    resources_used: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None

    def model_dump(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "stages": self.stages,
            "resources_used": self.resources_used,
            "warnings": self.warnings,
            "error": self.error,
        }


class OllamaClient:
    def __init__(self, model: str = settings.OLLAMA_MODEL, base_url: str = settings.OLLAMA_BASE_URL, timeout: int = 600):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def assert_available(self) -> None:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": "Reply with OK.", "stream": False},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise StudyPlanEngineError(
                "context",
                f"Ollama is not reachable at {self.base_url}. Start it with `ollama run {self.model}`.",
                retryable=True,
            ) from exc
        if response.status_code != 200:
            raise StudyPlanEngineError(
                "context",
                f"Ollama returned HTTP {response.status_code}. Ensure model `{self.model}` is installed and running.",
                retryable=True,
            )

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama returned HTTP {response.status_code}: {response.text[:300]}")
        text = response.json().get("response", "")
        if not text or not text.strip():
            raise RuntimeError("Ollama returned an empty response")
        return text.strip()


class AgentRunner:
    def __init__(self, llm: OllamaClient):
        self.llm = llm

    def run_json(self, stage: str, prompt: str) -> Dict[str, Any]:
        try:
            output = self.llm.generate(prompt)
        except Exception as exc:
            raise StudyPlanEngineError(stage, f"{stage.title()} agent failed: {exc}", retryable=True) from exc
        return self.parse_json(stage, output)

    def parse_json(self, stage: str, output: str) -> Dict[str, Any]:
        if not output or not output.strip():
            raise StudyPlanEngineError(stage, f"{stage.title()} agent returned an empty response.", retryable=True)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", output, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        raise StudyPlanEngineError(stage, f"{stage.title()} agent returned malformed JSON.", retryable=True)


class SpecialistAgent:
    STAGES = {
        "strategy": "strategy",
        "resources": "resources",
        "planner": "planning",
        "verifier": "verification",
        "formatter": "formatting",
    }

    TOOLS = {
        "strategy": {"search_methodology"},
        "resources": {"search_resources"},
        "planner": {"search_methodology"},
        "verifier": set(),
        "formatter": set(),
    }

    def __init__(
        self,
        name: str,
        runner: AgentRunner,
        resource_search: ResourceSearchTool,
        methodology_search: MethodologySearchTool,
        emit: ProgressCallback,
        max_tool_calls: int = 3,
    ):
        self.name = name
        self.stage = self.STAGES[name]
        self.runner = runner
        self.resource_search = resource_search
        self.methodology_search = methodology_search
        self.emit = emit
        self.max_tool_calls = max_tool_calls

    def run(self, context: Dict[str, Any], task: str, artifacts: Dict[str, Dict[str, Any]], feedback: str = "") -> Dict[str, Any]:
        observations: List[Dict[str, Any]] = []
        resource_hits: List[Dict[str, Any]] = []

        for step in range(1, self.max_tool_calls + 2):
            force_final = step > self.max_tool_calls
            prompt = self._prompt(context, task, artifacts, observations, feedback, step, force_final)
            decision = self.runner.run_json(self.stage, prompt)

            if "tool_calls" in decision and not force_final:
                tool_calls = decision.get("tool_calls")
                if not isinstance(tool_calls, list) or not tool_calls:
                    raise StudyPlanEngineError(self.stage, f"{self.name} requested invalid tool_calls.", retryable=True)
                for tool_call in tool_calls[: self.max_tool_calls]:
                    observation = self._execute_tool(context, tool_call)
                    observations.append(observation)
                    if observation["tool"] == "search_resources":
                        resource_hits.extend(observation.get("results", []))
                continue

            result = self._validate_specialist_result(decision)
            if not result["evidence"]:
                result["evidence"] = self._evidence_from_observations(observations)
            result["tool_observations"] = observations
            result["resource_hits"] = resource_hits
            return result

        raise StudyPlanEngineError(self.stage, f"{self.name} exceeded tool-call limit.", retryable=True)

    def _execute_tool(self, context: Dict[str, Any], tool_call: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(tool_call, dict):
            raise StudyPlanEngineError(self.stage, f"{self.name} emitted a non-object tool call.", retryable=True)
        tool = tool_call.get("tool")
        query = str(tool_call.get("query") or "").strip()
        if tool not in self.TOOLS[self.name]:
            raise StudyPlanEngineError(self.stage, f"{self.name} requested unknown tool: {tool}", retryable=False)
        if not query:
            raise StudyPlanEngineError(self.stage, f"{self.name} requested {tool} without a query.", retryable=True)

        if tool == "search_resources":
            results = self.resource_search.search(context.get("resources", []), query, limit=5)
            self.emit(self.stage, f"Resources agent searched uploaded resources for: {query}")
        elif tool == "search_methodology":
            results = self.methodology_search.search(query, limit=5)
            self.emit(self.stage, f"{self.name.title()} agent searched methodology for: {query}")
        else:
            raise StudyPlanEngineError(self.stage, f"Unknown tool requested: {tool}", retryable=False)
        return {"tool": tool, "query": query, "results": results}

    def _validate_specialist_result(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        required = {"status", "content", "evidence", "warnings", "needs_retry"}
        missing = sorted(required - set(decision.keys()))
        if missing:
            raise StudyPlanEngineError(self.stage, f"{self.name} result missing fields: {', '.join(missing)}.", retryable=True)
        if decision["status"] not in {"succeeded", "failed"}:
            raise StudyPlanEngineError(self.stage, f"{self.name} returned invalid status: {decision['status']}.", retryable=True)
        if not isinstance(decision["content"], str):
            raise StudyPlanEngineError(self.stage, f"{self.name} content must be a string.", retryable=True)
        if not isinstance(decision["evidence"], list):
            raise StudyPlanEngineError(self.stage, f"{self.name} evidence must be a list.", retryable=True)
        if not isinstance(decision["warnings"], list):
            raise StudyPlanEngineError(self.stage, f"{self.name} warnings must be a list.", retryable=True)
        if not isinstance(decision["needs_retry"], bool):
            raise StudyPlanEngineError(self.stage, f"{self.name} needs_retry must be boolean.", retryable=True)
        return {
            "agent": self.name,
            "stage": self.stage,
            "status": decision["status"],
            "content": decision["content"].strip(),
            "evidence": decision["evidence"],
            "warnings": decision["warnings"],
            "needs_retry": decision["needs_retry"],
        }

    def _evidence_from_observations(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        evidence = []
        for observation in observations:
            for result in observation.get("results", []):
                evidence.append({
                    "type": observation["tool"],
                    "query": observation["query"],
                    "source": result.get("name") or result.get("title") or result.get("source"),
                    "snippet": result.get("snippet", ""),
                })
        return evidence

    def _prompt(
        self,
        context: Dict[str, Any],
        task: str,
        artifacts: Dict[str, Dict[str, Any]],
        observations: List[Dict[str, Any]],
        feedback: str,
        step: int,
        force_final: bool,
    ) -> str:
        tools = ", ".join(sorted(self.TOOLS[self.name])) or "none"
        final_instruction = "You must now return the final specialist JSON. Do not call tools." if force_final else "Use tools if needed, otherwise return final specialist JSON."
        return f"""
You are the {self.name.title()} Agent in LearnMate.
Return JSON only.

Task:
{task}

Student/session context:
{json.dumps(self._context_summary(context), ensure_ascii=True)}

Approved/current artifacts:
{json.dumps(self._artifact_summary(artifacts), ensure_ascii=True)}

Feedback to address:
{feedback or "none"}

Tools available to you: {tools}
Tool-call shape:
{{"tool_calls": [{{"tool": "search_methodology", "query": "specific query"}}]}}
or
{{"tool_calls": [{{"tool": "search_resources", "query": "specific query"}}]}}

Final specialist shape:
{{"status": "succeeded", "content": "your output", "evidence": [], "warnings": [], "needs_retry": false}}

Observations so far:
{json.dumps(observations, ensure_ascii=True)}

Step {step}. {final_instruction}
"""

    def _context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "subject": context.get("subject"),
            "study_goal": context.get("study_goal"),
            "days_until_exam": context.get("days_until_exam"),
            "hours_per_day": context.get("hours_per_day"),
            "learning_style": context.get("learning_style"),
            "difficulty_level": context.get("difficulty_level"),
            "difficult_topics": context.get("difficult_topics", []),
            "syllabus_sessions": context.get("syllabus_sessions", [])[:20],
            "resource_catalog": [
                {"id": r.get("id"), "name": r.get("name"), "type": str(r.get("type"))}
                for r in context.get("resources", [])
                if isinstance(r, dict)
            ][:20],
        }

    def _artifact_summary(self, artifacts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        return {
            name: {
                "status": value.get("status"),
                "content": value.get("content", "")[:2500],
                "warnings": value.get("warnings", []),
            }
            for name, value in artifacts.items()
        }


class OrchestratorAgent:
    REQUIRED_APPROVALS = {"strategy", "resources", "planner", "verifier", "formatter"}

    def __init__(
        self,
        runner: AgentRunner,
        resource_search: ResourceSearchTool,
        methodology_search: MethodologySearchTool,
        verify_plan: Callable[[str, Dict[str, Any], List[Dict[str, Any]], List[str]], str],
        emit: ProgressCallback,
        max_steps: int = 12,
        max_retries: int = 2,
    ):
        self.runner = runner
        self.resource_search = resource_search
        self.methodology_search = methodology_search
        self.verify_plan = verify_plan
        self.emit = emit
        self.max_steps = max_steps
        self.max_retries = max_retries

    def run(self, context: Dict[str, Any], warnings: List[str]) -> StudyPlanEngineResult:
        artifacts: Dict[str, Dict[str, Any]] = {}
        tasks: Dict[str, str] = {}
        approved = set()
        retries = {name: 0 for name in self.REQUIRED_APPROVALS}
        transcript: List[Dict[str, Any]] = []
        resources_used: List[Dict[str, Any]] = []

        for step in range(1, self.max_steps + 1):
            self.emit("orchestrator", "Orchestrator agent is deciding the next action.")
            action = self.runner.run_json("orchestrator", self._prompt(context, artifacts, approved, transcript, step))
            kind = action.get("action")

            if kind == "delegate":
                agent_name = self._agent_name(action)
                task = str(action.get("task") or "").strip()
                if not task:
                    raise StudyPlanEngineError("orchestrator", "Delegate action missing task.", retryable=True)
                self.emit(self._stage_for(agent_name), f"Orchestrator delegated work to {agent_name}.")
                result = self._run_specialist(agent_name, context, task, artifacts)
                artifacts[agent_name] = result
                tasks[agent_name] = task
                resources_used.extend(result.get("resource_hits", []))
                transcript.append({"action": "delegate", "agent": agent_name, "status": result["status"], "needs_retry": result["needs_retry"]})

            elif kind == "approve":
                agent_name = self._agent_name(action)
                self._approve(agent_name, artifacts, context, resources_used, warnings)
                approved.add(agent_name)
                self.emit("orchestrator", f"Orchestrator approved {agent_name}.")
                transcript.append({"action": "approve", "agent": agent_name})

            elif kind == "retry":
                agent_name = self._agent_name(action)
                if agent_name not in artifacts or agent_name not in tasks:
                    raise StudyPlanEngineError("orchestrator", f"Cannot retry {agent_name} before delegation.", retryable=True)
                if retries[agent_name] >= self.max_retries:
                    raise StudyPlanEngineError(self._stage_for(agent_name), f"{agent_name} exceeded retry limit.", retryable=True)
                retries[agent_name] += 1
                feedback = str(action.get("feedback") or "Address orchestrator feedback and previous validation issues.")
                self.emit(self._stage_for(agent_name), f"Orchestrator requested retry from {agent_name}.")
                result = self._run_specialist(agent_name, context, tasks[agent_name], artifacts, feedback)
                artifacts[agent_name] = result
                resources_used.extend(result.get("resource_hits", []))
                approved.discard(agent_name)
                transcript.append({"action": "retry", "agent": agent_name, "status": result["status"]})

            elif kind == "tool_call":
                observation = self._execute_tool(context, action)
                transcript.append({"action": "tool_call", **observation})
                if observation["tool"] == "search_resources":
                    resources_used.extend(observation.get("results", []))

            elif kind == "final":
                if not self.REQUIRED_APPROVALS.issubset(approved):
                    missing = sorted(self.REQUIRED_APPROVALS - approved)
                    raise StudyPlanEngineError("orchestrator", f"Final requested before approvals: {', '.join(missing)}.", retryable=True)
                content = str(action.get("content") or artifacts["formatter"]["content"]).strip()
                content = self.verify_plan(content, context, resources_used, warnings)
                return StudyPlanEngineResult(
                    status="succeeded",
                    content=content,
                    stages=[],
                    resources_used=self._dedupe_hits(resources_used),
                    warnings=self._collect_warnings(warnings, artifacts),
                )

            else:
                raise StudyPlanEngineError("orchestrator", f"Unknown orchestrator action: {kind}", retryable=False)

        raise StudyPlanEngineError("orchestrator", "Orchestrator exceeded max step limit.", retryable=True)

    def _run_specialist(
        self,
        agent_name: str,
        context: Dict[str, Any],
        task: str,
        artifacts: Dict[str, Dict[str, Any]],
        feedback: str = "",
    ) -> Dict[str, Any]:
        agent = SpecialistAgent(
            agent_name,
            self.runner,
            self.resource_search,
            self.methodology_search,
            self.emit,
        )
        return agent.run(context, task, artifacts, feedback)

    def _approve(
        self,
        agent_name: str,
        artifacts: Dict[str, Dict[str, Any]],
        context: Dict[str, Any],
        resources_used: List[Dict[str, Any]],
        warnings: List[str],
    ) -> None:
        artifact = artifacts.get(agent_name)
        if not artifact:
            raise StudyPlanEngineError("orchestrator", f"Cannot approve missing {agent_name} output.", retryable=True)
        if artifact["status"] != "succeeded" or artifact["needs_retry"]:
            raise StudyPlanEngineError(self._stage_for(agent_name), f"{agent_name} output requested retry or failed.", retryable=True)
        if not artifact["content"]:
            raise StudyPlanEngineError(self._stage_for(agent_name), f"{agent_name} output is empty.", retryable=True)

        if agent_name == "resources":
            self._reject_syllabus_resource_claims(artifact["content"])
            has_resources = any(isinstance(r, dict) and "syllabus" not in str(r.get("name", "")).lower() for r in context.get("resources", []))
            if has_resources and not artifact.get("evidence"):
                raise StudyPlanEngineError("resources", "Resources output has no evidence from resource search.", retryable=True)
        if agent_name == "planner":
            self.verify_plan(artifact["content"], context, resources_used, warnings)
        if agent_name == "formatter":
            self.verify_plan(artifact["content"], context, resources_used, warnings)

    def _execute_tool(self, context: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        tool = action.get("tool")
        query = str(action.get("query") or "").strip()
        if tool not in {"search_resources", "search_methodology"}:
            raise StudyPlanEngineError("orchestrator", f"Unknown orchestrator tool: {tool}", retryable=False)
        if not query:
            raise StudyPlanEngineError("orchestrator", f"Tool call {tool} missing query.", retryable=True)
        if tool == "search_resources":
            results = self.resource_search.search(context.get("resources", []), query, limit=5)
            self.emit("orchestrator", f"Orchestrator searched uploaded resources for: {query}")
        else:
            results = self.methodology_search.search(query, limit=5)
            self.emit("orchestrator", f"Orchestrator searched methodology for: {query}")
        return {"tool": tool, "query": query, "results": results}

    def _prompt(
        self,
        context: Dict[str, Any],
        artifacts: Dict[str, Dict[str, Any]],
        approved: set,
        transcript: List[Dict[str, Any]],
        step: int,
    ) -> str:
        return f"""
You are the LearnMate Orchestrator Agent. Return JSON only.
You own the workflow. Delegate to specialists, approve good outputs, retry flawed outputs, and aggregate only after all specialists are approved.

Allowed actions:
{{"action": "delegate", "agent": "strategy|resources|planner|verifier|formatter", "task": "specific task"}}
{{"action": "approve", "agent": "strategy|resources|planner|verifier|formatter"}}
{{"action": "retry", "agent": "strategy|resources|planner|verifier|formatter", "feedback": "specific correction"}}
{{"action": "tool_call", "tool": "search_methodology|search_resources", "query": "specific query"}}
{{"action": "final", "content": "final verified study plan"}}

Required approvals before final: strategy, resources, planner, verifier, formatter.
Strict rules: reject unsupported resources, syllabus-as-resource recommendations, malformed sections, wrong day count, or wrong schedule constraints.

Step: {step} of {self.max_steps}
Student/session context:
{json.dumps(self._context_summary(context), ensure_ascii=True)}

Current artifacts:
{json.dumps(self._artifact_summary(artifacts), ensure_ascii=True)}

Approved agents:
{json.dumps(sorted(approved), ensure_ascii=True)}

Recent transcript:
{json.dumps(transcript[-8:], ensure_ascii=True)}
"""

    def _agent_name(self, action: Dict[str, Any]) -> str:
        agent_name = action.get("agent")
        if agent_name not in self.REQUIRED_APPROVALS:
            raise StudyPlanEngineError("orchestrator", f"Unknown specialist agent: {agent_name}", retryable=False)
        return agent_name

    def _stage_for(self, agent_name: str) -> str:
        return SpecialistAgent.STAGES.get(agent_name, "orchestrator")

    def _context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "subject": context.get("subject"),
            "study_goal": context.get("study_goal"),
            "days_until_exam": context.get("days_until_exam"),
            "hours_per_day": context.get("hours_per_day"),
            "learning_style": context.get("learning_style"),
            "difficulty_level": context.get("difficulty_level"),
            "difficult_topics": context.get("difficult_topics", []),
            "syllabus_sessions": context.get("syllabus_sessions", [])[:20],
            "resource_count": len(context.get("resources", [])),
        }

    def _artifact_summary(self, artifacts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        return {
            name: {
                "status": artifact.get("status"),
                "needs_retry": artifact.get("needs_retry"),
                "content": artifact.get("content", "")[:2500],
                "warnings": artifact.get("warnings", []),
                "evidence_count": len(artifact.get("evidence", [])),
            }
            for name, artifact in artifacts.items()
        }

    def _reject_syllabus_resource_claims(self, content: str) -> None:
        resource_section = content.split("RECOMMENDED RESOURCES:", 1)[1] if "RECOMMENDED RESOURCES:" in content else content
        for line in resource_section.splitlines():
            lowered = line.lower()
            if "syllabus" in lowered and "non-syllabus" not in lowered and "not use" not in lowered:
                raise StudyPlanEngineError("resources", "Resources output recommends the syllabus as a study resource.", retryable=True)

    def _collect_warnings(self, warnings: List[str], artifacts: Dict[str, Dict[str, Any]]) -> List[str]:
        collected = list(warnings)
        for artifact in artifacts.values():
            collected.extend(str(warning) for warning in artifact.get("warnings", []))
        return collected

    def _dedupe_hits(self, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen = set()
        for hit in hits:
            key = (hit.get("id"), hit.get("name"), hit.get("snippet"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(hit)
        return deduped


class StudyPlanEngine:
    """Bounded orchestrator-agent engine for LearnMate study-plan generation."""

    def __init__(
        self,
        llm: Optional[OllamaClient] = None,
        resource_search: Optional[ResourceSearchTool] = None,
        methodology_search: Optional[MethodologySearchTool] = None,
    ):
        self.llm = llm or OllamaClient()
        self.resource_search = resource_search or ResourceSearchTool()
        self.methodology_search = methodology_search or MethodologySearchTool()
        self.runner = AgentRunner(self.llm)

    def generate(self, context: Dict[str, Any], progress: Optional[ProgressCallback] = None) -> StudyPlanEngineResult:
        stages: List[Dict[str, Any]] = []
        warnings: List[str] = []

        def emit(stage: str, message: str) -> None:
            stages.append({"stage": stage, "message": message})
            if progress:
                progress(stage, message)

        try:
            emit("context", "Checking local Ollama and preparing session context.")
            self.llm.assert_available()
            normalized = self._normalize_context(context, warnings)
            orchestrator = OrchestratorAgent(
                self.runner,
                self.resource_search,
                self.methodology_search,
                self._verify_and_format,
                emit,
            )
            result = orchestrator.run(normalized, warnings)
            result.stages = stages
            return result
        except StudyPlanEngineError:
            raise
        except Exception as exc:
            raise StudyPlanEngineError("orchestrator", str(exc), retryable=True) from exc

    def _normalize_context(self, context: Dict[str, Any], warnings: List[str]) -> Dict[str, Any]:
        normalized = dict(context)
        normalized["subject"] = normalized.get("subject") or normalized.get("field_of_study") or "your subject"
        normalized["study_goal"] = normalized.get("study_goal") or "mastering the material"
        normalized["days_until_exam"] = self._coerce_int(
            normalized.get("days_until_exam") or normalized.get("study_days") or 7,
            "days_until_exam",
            warnings,
        )
        normalized["hours_per_day"] = self._coerce_float(normalized.get("hours_per_day") or 2, "hours_per_day", warnings)
        normalized["learning_style"] = normalized.get("learning_style") or "balanced"
        normalized["difficulty_level"] = normalized.get("difficulty_level") or "intermediate"
        normalized["resources"] = normalized.get("resources") or []
        normalized["syllabus_sessions"] = normalized.get("syllabus_sessions") or []
        normalized["difficult_topics"] = normalized.get("difficult_topics") or []
        return normalized

    def _coerce_int(self, value: Any, field_name: str, warnings: List[str]) -> int:
        try:
            parsed = int(float(value))
            if parsed <= 0:
                raise ValueError
            return min(parsed, 60)
        except (TypeError, ValueError):
            warnings.append(f"Invalid {field_name}; using 7.")
            return 7

    def _coerce_float(self, value: Any, field_name: str, warnings: List[str]) -> float:
        try:
            parsed = float(value)
            if parsed <= 0:
                raise ValueError
            return min(parsed, 12.0)
        except (TypeError, ValueError):
            warnings.append(f"Invalid {field_name}; using 2.")
            return 2.0

    def _verify_and_format(
        self,
        plan: str,
        context: Dict[str, Any],
        resources_used: List[Dict[str, Any]],
        warnings: List[str],
    ) -> str:
        if "STUDY PLAN OVERVIEW:" not in plan:
            warnings.append("Planner omitted overview heading; added it during formatting.")
            plan = "STUDY PLAN OVERVIEW:\n" + plan

        expected_days = context["days_until_exam"]
        day_numbers = {int(match) for match in re.findall(r"\bDAY\s+(\d+)\s*:", plan, flags=re.IGNORECASE)}
        missing_days = [day for day in range(1, expected_days + 1) if day not in day_numbers]
        if missing_days:
            raise StudyPlanEngineError(
                "verification",
                f"Planner output is missing required day sections: {', '.join(f'DAY {d}' for d in missing_days)}.",
                retryable=True,
            )
        extra_days = [day for day in day_numbers if day > expected_days]
        if extra_days:
            raise StudyPlanEngineError(
                "verification",
                f"Planner output includes extra day sections beyond requested schedule: {extra_days}.",
                retryable=True,
            )

        resource_section = plan.split("RECOMMENDED RESOURCES:", 1)[1] if "RECOMMENDED RESOURCES:" in plan else ""
        for line in resource_section.splitlines():
            lowered = line.lower()
            if "syllabus" in lowered and "non-syllabus" not in lowered and "not use" not in lowered:
                raise StudyPlanEngineError("verification", "Plan recommends the syllabus as a study resource.", retryable=True)

        if "RECOMMENDED RESOURCES:" not in plan:
            warnings.append("Planner omitted recommended resources heading.")
            plan += "\n\nRECOMMENDED RESOURCES:\nUse the uploaded/session resources listed in the plan.\n"
        if "IMPLEMENTATION TIPS:" not in plan:
            warnings.append("Planner omitted implementation tips heading.")
            plan += "\n\nIMPLEMENTATION TIPS:\nUse retrieval practice, short breaks, and daily review checkpoints.\n"
        if not resources_used:
            warnings.append("No uploaded non-syllabus resources were used; plan may rely on general study methods.")

        return plan.strip()


def create_engine() -> StudyPlanEngine:
    return StudyPlanEngine()
