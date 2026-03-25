# tools/self_improve.py — Self-improvement logging tools.
#
# log_learning(content) — append a timestamped learning to workspace/LEARNINGS.md
# log_error(content)    — append a timestamped error note to workspace/ERRORS.md
#
# Both are pure file operations — no Xeon service required.
# workspace/ path is derived relative to this file's location.

from datetime import datetime, timezone
from pathlib import Path

_WORKSPACE = Path(__file__).parent.parent / "workspace"


def _append_to_log(filename: str, content: str) -> str:
    path = _WORKSPACE / filename
    content = content.strip()
    if not content:
        return "Error: content cannot be empty."

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"- [{ts}] {content}"

    try:
        _WORKSPACE.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = path.read_text()
        else:
            existing = f"# {filename[:-3]}\n\n"
        updated = existing.rstrip() + "\n" + entry + "\n"
        path.write_text(updated)
    except Exception as e:
        return f"Error writing {filename}: {e}"

    return f"Logged to {filename}: {content[:80]}{'...' if len(content) > 80 else ''}"


def log_learning(content: str) -> str:
    """Append a learning, correction, or better approach to workspace/LEARNINGS.md."""
    return _append_to_log("LEARNINGS.md", content)


def log_error(content: str) -> str:
    """Append an unexpected error or tool failure note to workspace/ERRORS.md."""
    return _append_to_log("ERRORS.md", content)
