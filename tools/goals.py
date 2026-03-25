# tools/goals.py — Goal CRUD, persisted to workspace/goals.json.
#
# Simplified for v3 (no autonomy loop, no complex FSM).
# Goals are plain JSON objects with id, title, description, status, created_at.


def goal_manager(action: str, **kwargs) -> str:
    """
    Manage goals stored in workspace/goals.json.

    action:
      list                              — all goals with status
      get(id)                           — single goal detail
      add(title, description)           — create new goal
      update(id, status?, description?) — update fields
    """
    raise NotImplementedError
