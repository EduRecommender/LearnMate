# LearnMate

LearnMate is a study-planning web application built with FastAPI, Next.js, SQLite, and local Ollama. It lets a student create study sessions, upload course material, keep chat history, and generate a structured plan that is grounded in the session context and uploaded resources.

The main engineering focus is the study-plan workflow. Instead of treating the model as a one-shot answer generator, LearnMate runs a bounded orchestrator agent that delegates work to specialist agents, lets agents use scoped retrieval tools, validates intermediate outputs, streams progress to the frontend, and fails explicitly when the workflow cannot produce a grounded result.

## Core Capabilities

- User registration, login, and preference storage.
- Study-session CRUD with persisted chat history.
- Resource and syllabus upload support.
- Asynchronous study-plan generation through job status records.
- Server-sent progress events with polling fallback.
- Bounded orchestrator workflow with specialist agent delegation.
- Local resource search over uploaded/session content.
- Repo-local methodology search for study techniques and schedule design.
- Explicit failure states for unavailable Ollama, malformed agent output, invalid actions, retry exhaustion, and validation failures.

## Architecture

```text
frontend/
  Next.js app router pages and chat UI

backend/
  FastAPI application, auth/session routes, persistence, uploads, and planning services

backend/app/services/study_plan_engine.py
  Orchestrator runtime, specialist agents, JSON protocol parsing, validation, and Ollama adapter

backend/app/services/job_store.py
  Small file-backed job store for queued/running/succeeded/failed request state and progress events

backend/app/services/resource_search.py
  Local search over resources already attached to the session

backend/app/services/methodology_search.py
  Search over curated study-method notes in backend/app/knowledge/methodology/
```

The backend keeps public API routes stable while moving long-running planning work behind a job interface. The frontend starts a chat generation job, subscribes to progress events, and falls back to polling if event streaming is unavailable.

## Agent Workflow

Study-plan generation is handled by `StudyPlanEngine`, which wraps a bounded `OrchestratorAgent`.

The orchestrator can emit one JSON action at a time:

- `delegate` - assign a task to a specialist agent.
- `tool_call` - run an allowed backend search tool directly.
- `approve` - approve a specialist result after validation.
- `retry` - ask a specialist to revise its output with feedback.
- `final` - produce the final answer after all required approvals.

Specialist agents return structured JSON:

```json
{
  "status": "succeeded",
  "content": "agent output",
  "evidence": [],
  "warnings": [],
  "needs_retry": false
}
```

The required specialist stages are:

- `strategy` - chooses study methods and learning approach using session context and methodology search.
- `resources` - finds grounded resources from uploaded/session material.
- `planner` - creates the day-by-day plan using constraints, strategy, resources, and planning heuristics.
- `verifier` - checks schedule constraints, sections, and resource grounding.
- `formatter` - prepares the final response for the chat UI.

The workflow is intentionally bounded:

- Maximum orchestrator steps: `12`
- Maximum retries per specialist: `2`
- Maximum tool calls per specialist run: `3`

If those bounds are exceeded, the job fails with a stage-specific error rather than returning a generic plan.

## Grounding and Validation

LearnMate separates model decisions from backend validation.

Specialist agents may request retrieval through approved tools, but the backend executes those tools and records the observations. This gives the model autonomy over what to ask for while keeping file access, search behavior, and validation under application control.

The verifier and backend checks reject common failure modes:

- Missing required study-plan sections.
- Missing or extra day sections for the requested schedule.
- Plans that ignore hour/day constraints.
- Syllabus-only recommendations presented as study resources.
- Resource claims that are not grounded in uploaded/session material.
- Malformed JSON from the orchestrator or specialists.
- Unknown actions, unknown tools, and empty agent outputs.

## API Overview

The main API prefix is `/api/v1`.

Authentication:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `PUT /auth/preferences`

Sessions:

- `GET /sessions`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `PUT /sessions/{session_id}`
- `DELETE /sessions/{session_id}`

Resources and syllabus:

- `POST /sessions/{session_id}/resources`
- `DELETE /sessions/{session_id}/resources/{resource_id}`
- `POST /sessions/{session_id}/syllabus`
- `GET /sessions/{session_id}/resources/{resource_id}/download`

Chat and planning:

- `GET /sessions/{session_id}/chat`
- `POST /sessions/{session_id}/chat/start`
- `GET /sessions/{session_id}/chat/status/{request_id}`
- `GET /sessions/{session_id}/chat/{request_id}/events`
- `POST /sessions/{session_id}/chat`
- `DELETE /sessions/{session_id}/chat`

Health:

- `GET /health`
- `GET /api/v1/sessions/{session_id}/metrics`

## Request Lifecycle

1. The frontend posts a message to `POST /sessions/{session_id}/chat/start`.
2. The backend creates one request record with status `queued`.
3. The background task marks the request `running` and emits progress events.
4. The orchestrator delegates specialist work and emits stage updates.
5. The job finishes as `succeeded` with a final result or `failed` with an error object.
6. The frontend renders the final assistant message or a clear failure card.

Job states:

- `queued`
- `running`
- `succeeded`
- `failed`

Planning stages:

- `context`
- `orchestrator`
- `strategy`
- `resources`
- `planning`
- `verification`
- `formatting`

## Configuration

Configuration is environment-driven through `backend/app/core/config.py`.

Common backend variables:

```bash
DATABASE_URL=sqlite:///./study_sessions.db
SECRET_KEY=replace-this-for-deployment
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
LEARNMATE_DATA_DIR=./data
LEARNMATE_JOB_REQUEST_DIR=./data/chat_requests
LEARNMATE_METRICS_PATH=./data/metrics/processing_metrics.jsonl
LEARNMATE_UPLOAD_DIR=./uploads
```

SQLite is the default development database. `DATABASE_URL` can be changed for another SQLAlchemy-compatible database without changing route code.

## Runtime Data

The backend writes mutable runtime state to configured directories:

- SQLite database files.
- Uploaded resources and syllabi.
- Generated chat request JSON.
- Metrics JSONL files.

These paths are ignored by git because they contain local user data or generated state. Deleting them is not required to run the app, and existing SQLite data remains readable across code changes.

## Requirements

- Python 3.12
- Node.js 20+
- npm
- Ollama
- Ollama model: `llama3:8b`

## Backend Setup

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3:8b
uvicorn app.main:app --reload
```

The backend runs at `http://127.0.0.1:8000` by default.

Check health:

```bash
curl http://127.0.0.1:8000/health
```

## Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

## Ollama

The study-plan engine uses Ollama through the local HTTP API.

```bash
ollama pull llama3:8b
ollama run llama3:8b
```

Keep Ollama running while generating study plans.

If Ollama is unavailable, study-plan jobs fail with an explicit `context` error. The app does not return a generic fallback plan as a successful result.

## Testing

Backend unit tests, run from the repository root with the backend virtual environment active:

```bash
source backend/.venv/bin/activate
python -m pytest tests/test_study_plan_engine.py tests/test_job_store.py
```

Frontend production build:

```bash
cd frontend
npm run build
```

The backend tests cover orchestrator delegation, retries, malformed JSON, unknown actions/tools, resource search, methodology search, schedule validation, syllabus-as-resource rejection, and explicit Ollama-unavailable failure.

## Design Notes

The project favors a deterministic application boundary around model behavior:

- The model decides which allowed action to take next.
- The backend validates JSON shape, allowed tools, retry limits, stage transitions, and final plan requirements.
- Search is exposed as a tool protocol, but file/resource access remains controlled by backend services.
- Progress is visible through job events rather than hidden inside one long request.
- Failures are part of the API contract, not silently converted into generic successful responses.

This structure makes the planning workflow easier to debug, test, and extend while preserving local-first execution with Ollama.
