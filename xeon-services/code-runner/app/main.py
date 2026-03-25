# main.py — Sandboxed Python code execution service.
#
# Runs on Xeon in Docker. Executes Python code in a subprocess.
# Container has network_mode: none — no outbound network access.
#
# Security:
#   - AST import scan: only stdlib allowlist permitted
#   - 30s timeout hard limit
#   - Output truncated at 4000 chars
#
# Endpoint: POST /run {code, timeout=30} -> {success, stdout, stderr, error}

import ast
import subprocess
import sys

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="jarvis-code-runner")

_ALLOWED_IMPORTS = frozenset({
    "math", "json", "re", "datetime", "collections", "itertools",
    "functools", "statistics", "decimal", "random", "string",
    "textwrap", "hashlib", "base64", "urllib.parse", "fractions",
    "operator", "copy", "pprint", "io", "struct", "enum", "typing",
})


class RunRequest(BaseModel):
    code: str
    timeout: int = 30


def _check_imports(code: str) -> str | None:
    """Return error message if code imports any non-allowlisted module."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in _ALLOWED_IMPORTS:
                    return f"Blocked: import '{alias.name}' is not allowed."
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if top not in _ALLOWED_IMPORTS:
                return f"Blocked: 'from {module} import ...' is not allowed."

    return None


@app.post("/run")
def run_code(req: RunRequest):
    if not req.code.strip():
        return {"success": False, "error": "code is empty"}

    import_error = _check_imports(req.code)
    if import_error:
        return {"success": False, "error": import_error, "stdout": "", "stderr": ""}

    timeout = max(1, min(req.timeout, 30))

    try:
        result = subprocess.run(
            [sys.executable, "-c", req.code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = result.stdout[:4000]
        stderr = result.stderr[:1000]
        success = result.returncode == 0
        error = "" if success else f"exit code {result.returncode}"
        return {"success": success, "stdout": stdout, "stderr": stderr, "error": error}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timeout after {timeout}s", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


@app.get("/health")
def health():
    return {"status": "ok"}
