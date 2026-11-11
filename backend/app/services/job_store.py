import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.config import settings


TERMINAL_STATUSES = {"succeeded", "failed"}


class JobStore:
    """Small in-memory/file-backed store for long-running chat jobs."""

    def __init__(self, base_dir: str = settings.JOB_REQUEST_DIR):
        self.base_dir = base_dir
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        os.makedirs(self.base_dir, exist_ok=True)

    def create(self, request_id: str, *, session_id: int, user_id: int, message: str) -> Dict[str, Any]:
        job = {
            "request_id": request_id,
            "session_id": session_id,
            "user_id": user_id,
            "message": message,
            "status": "queued",
            "stage": "context",
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
            "events": [],
        }
        with self._lock:
            self._jobs[request_id] = job
            self._persist_unlocked(request_id)
        return job

    def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if request_id not in self._jobs:
                self._load_unlocked(request_id)
            job = self._jobs.get(request_id)
            return dict(job) if job else None

    def event(self, request_id: str, *, stage: str, message: str, status: str = "running") -> None:
        event = {
            "type": "progress",
            "status": status,
            "stage": stage,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            job = self._jobs.get(request_id)
            if not job:
                return
            job["status"] = status
            job["stage"] = stage
            job["updated_at"] = event["timestamp"]
            job.setdefault("events", []).append(event)
            self._persist_unlocked(request_id)

    def succeed(self, request_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(request_id)
            if not job:
                return
            now = datetime.now().isoformat()
            job["status"] = "succeeded"
            job["stage"] = "formatting"
            job["result"] = result
            job["error"] = None
            job["completed_at"] = now
            job["updated_at"] = now
            job.setdefault("events", []).append({
                "type": "complete",
                "status": "succeeded",
                "stage": "formatting",
                "message": "Study assistant response is ready.",
                "timestamp": now,
            })
            self._persist_unlocked(request_id)

    def fail(self, request_id: str, *, stage: str, message: str, retryable: bool = True) -> None:
        with self._lock:
            job = self._jobs.get(request_id)
            if not job:
                return
            now = datetime.now().isoformat()
            error = {"stage": stage, "message": message, "retryable": retryable}
            job["status"] = "failed"
            job["stage"] = stage
            job["error"] = error
            job["completed_at"] = now
            job["updated_at"] = now
            job.setdefault("events", []).append({
                "type": "error",
                "status": "failed",
                "stage": stage,
                "message": message,
                "retryable": retryable,
                "timestamp": now,
            })
            self._persist_unlocked(request_id)

    def events_since(self, request_id: str, index: int) -> List[Dict[str, Any]]:
        job = self.get(request_id)
        if not job:
            return []
        return job.get("events", [])[index:]

    def _path(self, request_id: str) -> str:
        return os.path.join(self.base_dir, f"{request_id}.json")

    def _persist_unlocked(self, request_id: str) -> None:
        with open(self._path(request_id), "w") as f:
            json.dump(self._jobs[request_id], f)

    def _load_unlocked(self, request_id: str) -> None:
        path = self._path(request_id)
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            self._jobs[request_id] = json.load(f)


job_store = JobStore()
