# tools/code_runner.py — Sandboxed Python code execution via Xeon service.
#
# Calls xeon-services/code-runner (port 8084).
# The service runs code in a subprocess with network_mode:none and an import allowlist.

import os
import httpx

_TIMEOUT = 40.0  # slightly over the service's 30s timeout


def code_execute(code: str) -> str:
    url = os.getenv("CODE_RUNNER_URL", "http://100.101.127.60:8084")
    if not code.strip():
        return "Error: code must not be empty."

    try:
        r = httpx.post(f"{url}/run", json={"code": code, "timeout": 30}, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except httpx.ConnectError:
        return f"Service unavailable: code-runner not running at {url}"
    except Exception as e:
        return f"code_execute error: {e}"

    if not data.get("success"):
        error = data.get("error", "unknown error")
        stderr = data.get("stderr", "")
        return f"Execution failed: {error}\n{stderr}".strip()

    stdout = data.get("stdout", "")
    stderr = data.get("stderr", "")
    result = stdout
    if stderr:
        result += f"\nstderr: {stderr}"
    return result.strip() or "(no output)"
