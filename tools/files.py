# tools/files.py — Workspace file operations.
#
# All paths scoped to workspace/ only. Path traversal rejected via
# Path.resolve() + relative_to(_WORKSPACE) — raises ValueError on escape.
#
# Tools: file_read, file_write, file_list


def file_read(path: str) -> str:
    """
    Read a file from workspace/. path is relative to workspace/.
    Returns file contents (max 4000 chars, truncated with notice if longer).
    """
    raise NotImplementedError


def file_write(path: str, content: str) -> str:
    """
    Write content to workspace/<path>. Creates parent directories as needed.
    Rejects any path that resolves outside workspace/.
    """
    raise NotImplementedError


def file_list(subpath: str = "") -> str:
    """
    List files under workspace/<subpath>.
    Returns [dir] / [file] entries with sizes.
    """
    raise NotImplementedError
