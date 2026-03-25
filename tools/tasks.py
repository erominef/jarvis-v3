# tools/tasks.py — Task tracking, persisted to workspace/tasks.json.
#
# Simplified for v3 (no autonomy loop FSM).
# Tasks are plain JSON objects with id, title, status, created_at, updated_at.


def task_manager(action: str, **kwargs) -> str:
    """
    Manage tasks stored in workspace/tasks.json.

    action:
      list_pending                      — tasks with status pending or in_progress
      list_recent(limit)                — most recently updated tasks
      create(title, description)        — create new task
      update_progress(id, status, note) — update task; status: done | failed
    """
    raise NotImplementedError
