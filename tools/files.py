# tools/files.py — Workspace file operations.
#
# All paths scoped to workspace/ only. Path traversal rejected.
# Resolves symlinks before checking prefix to prevent escape.

from pathlib import Path

_WORKSPACE = (Path(__file__).parent.parent / "workspace").resolve()


def _safe_path(path: str):
    """Resolve path and assert it's inside workspace/. Returns Path or error str."""
    clean = path.strip()
    if clean.startswith("workspace/"):
        clean = clean[len("workspace/"):]
    if not clean:
        return "Error: path must not be empty."
    candidate = (_WORKSPACE / clean).resolve()
    try:
        candidate.relative_to(_WORKSPACE)
    except ValueError:
        return "Rejected: path is outside workspace/."
    return candidate


def file_read(path: str) -> str:
    p = _safe_path(path)
    if isinstance(p, str):
        return p
    if not p.exists():
        return f"File not found: workspace/{path.strip()}"
    if not p.is_file():
        return f"Not a file: {path}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > 4000:
            return content[:4000] + "\n[truncated]"
        return content or "(empty file)"
    except Exception as e:
        return f"Read error: {e}"


def file_write(path: str, content: str) -> str:
    p = _safe_path(path)
    if isinstance(p, str):
        return p
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written to workspace/{path.strip().lstrip('/')} ({len(content)} chars)."
    except Exception as e:
        return f"Write error: {e}"


def file_list(subpath: str = "") -> str:
    if subpath:
        base = _safe_path(subpath)
        if isinstance(base, str):
            return base
    else:
        base = _WORKSPACE

    if not base.exists():
        return f"Directory not found: {subpath or 'workspace/'}"
    if not base.is_dir():
        return f"Not a directory: {subpath}"

    try:
        items = sorted(base.iterdir(), key=lambda x: (x.is_file(), x.name))
        if not items:
            return f"Empty: {'workspace/' + subpath if subpath else 'workspace/'}"
        lines = []
        for item in items:
            rel = item.relative_to(_WORKSPACE)
            if item.is_dir():
                lines.append(f"[dir]  {rel}/")
            else:
                size = item.stat().st_size
                size_str = f"{size} B" if size < 1024 else f"{size // 1024} KB"
                lines.append(f"[file] {rel} ({size_str})")
        return "\n".join(lines)
    except Exception as e:
        return f"List error: {e}"
