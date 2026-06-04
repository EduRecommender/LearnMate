from backend.app.services.job_store import JobStore


def test_job_store_creates_queued_job(tmp_path):
    store = JobStore(base_dir=str(tmp_path))

    job = store.create("req-1", session_id=10, user_id=20, message="create a study plan")

    assert job["status"] == "queued"
    assert job["stage"] == "context"
    assert job["result"] is None
    assert job["error"] is None
    assert store.get("req-1")["session_id"] == 10


def test_job_store_records_progress_and_success(tmp_path):
    store = JobStore(base_dir=str(tmp_path))
    store.create("req-2", session_id=10, user_id=20, message="create a study plan")

    store.event("req-2", stage="orchestrator", message="Orchestrator delegated work.", status="running")
    store.succeed("req-2", {"content": "done", "engine": "multi_agent"})
    job = store.get("req-2")

    assert job["status"] == "succeeded"
    assert job["stage"] == "formatting"
    assert job["result"]["content"] == "done"
    assert [event["type"] for event in job["events"]] == ["progress", "complete"]


def test_job_store_records_failed_stage_error(tmp_path):
    store = JobStore(base_dir=str(tmp_path))
    store.create("req-3", session_id=10, user_id=20, message="create a study plan")

    store.fail("req-3", stage="resources", message="Malformed JSON", retryable=True)
    job = store.get("req-3")

    assert job["status"] == "failed"
    assert job["stage"] == "resources"
    assert job["error"] == {"stage": "resources", "message": "Malformed JSON", "retryable": True}
    assert job["events"][-1]["type"] == "error"
