# tools/tasks.py — Task tracking, persisted to workspace/tasks.json.
#
# Simplified for v3 (no autonomy loop FSM).
# Tool: task_manager(action, **kwargs)

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_TASKS_FILE = Path(__file__).parent.parent / "workspace" / "tasks.json"


def _load() -> list:
    if not _TASKS_FILE.exists():
        return []
    try:
        return json.loads(_TASKS_FILE.read_text())
    except Exception:
        return []


def _save(tasks: list) -> None:
    _TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def task_manager(action: str, **kwargs) -> str:
    try:
        if action == "list_pending":
            tasks = _load()
            pending = [t for t in tasks if t["status"] in ("pending", "in_progress")]
            if not pending:
                return "No pending tasks."
            return json.dumps(pending, indent=2)

        elif action == "list_recent":
            tasks = _load()
            recent = sorted(tasks, key=lambda t: t.get("created_at", ""), reverse=True)[:10]
            return json.dumps(recent, indent=2) if recent else "No tasks."

        elif action == "create":
            title = kwargs.get("title", "").strip()
            if not title:
                return "Error: title required."
            t = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": kwargs.get("description", ""),
                "status": "pending",
                "progress": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
            }
            tasks = _load()
            tasks.append(t)
            _save(tasks)
            return json.dumps(t, indent=2)

        elif action == "update_progress":
            task_id = kwargs.get("task_id") or kwargs.get("id", "")
            note = kwargs.get("note", "")
            if not task_id:
                return "Error: task_id required."
            tasks = _load()
            t = next((t for t in tasks if t["id"] == task_id), None)
            if not t:
                return f"Task not found: {task_id}"
            t["progress"] = note
            if kwargs.get("status") in ("done", "completed"):
                t["status"] = "done"
                t["completed_at"] = datetime.now(timezone.utc).isoformat()
            elif kwargs.get("status") == "failed":
                t["status"] = "failed"
                t["completed_at"] = datetime.now(timezone.utc).isoformat()
            _save(tasks)
            return json.dumps(t, indent=2)

        else:
            return f"Unknown action: {action}. Valid: list_pending, list_recent, create, update_progress"

    except Exception as e:
        return f"task_manager error: {e}"
