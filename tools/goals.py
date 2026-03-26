# tools/goals.py — Goal CRUD, persisted to workspace/goals.json.
#
# Simplified for v3 (no autonomy loop, no complex FSM).
# Tool: goal_manager(action, **kwargs)

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_GOALS_FILE = Path(__file__).parent.parent / "workspace" / "goals.json"


def _load() -> list:
    if not _GOALS_FILE.exists():
        return []
    try:
        return json.loads(_GOALS_FILE.read_text())
    except Exception:
        return []


def _save(goals: list) -> None:
    _GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _GOALS_FILE.write_text(json.dumps(goals, indent=2))


def goal_manager(action: str, **kwargs) -> str:
    try:
        if action == "list":
            goals = _load()
            if not goals:
                return "No goals yet."
            return json.dumps(goals, indent=2)

        elif action == "get":
            goal_id = kwargs.get("goal_id") or kwargs.get("id", "")
            goals = _load()
            g = next((g for g in goals if g["id"] == goal_id), None)
            return json.dumps(g, indent=2) if g else f"Goal not found: {goal_id}"

        elif action == "add":
            title = kwargs.get("title", "").strip()
            if not title:
                return "Error: title required."
            g = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": kwargs.get("description", ""),
                "status": "active",
                "priority": int(kwargs.get("priority", 5)),
                "progress": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            goals = _load()
            goals.append(g)
            _save(goals)
            return json.dumps(g, indent=2)

        elif action == "update":
            goal_id = kwargs.get("goal_id") or kwargs.get("id", "")
            if not goal_id:
                return "Error: goal_id required."
            goals = _load()
            g = next((g for g in goals if g["id"] == goal_id), None)
            if not g:
                return f"Goal not found: {goal_id}"
            for field in ("title", "description", "status", "progress", "priority"):
                if field in kwargs and kwargs[field] is not None:
                    g[field] = int(kwargs[field]) if field == "priority" else kwargs[field]
            _save(goals)
            return json.dumps(g, indent=2)

        else:
            return f"Unknown action: {action}. Valid: list, get, add, update"

    except Exception as e:
        return f"goal_manager error: {e}"
