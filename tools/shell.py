# tools/shell.py — Restricted shell command execution.
#
# Security order (CRITICAL — do NOT reorder):
#   1. Metacharacter check FIRST: reject |;&`$()<>\n\r# unconditionally.
#   2. THEN whitelist check.
#
# python3 intentionally excluded — use code_execute tool instead.

import re
import subprocess

_META_RE = re.compile(r'[|;&`$()<>\n\r#]')

_ALLOWED_PATTERNS = [
    re.compile(r"^ls(\s|$)"),
    re.compile(r"^cat\s+\S+\.(?:md|txt|json|log)$"),
    re.compile(r"^echo\s+.{0,200}$"),
    re.compile(r"^pwd$"),
    re.compile(r"^date$"),
    re.compile(r"^df\s+-h$"),
    re.compile(r"^free\s+-h$"),
    re.compile(r"^uptime$"),
    re.compile(r"^whoami$"),
    re.compile(r"^hostname$"),
    re.compile(r"^uname\s+-[a-z]+$"),
    re.compile(r"^curl\s+-s\s+https://\S+$"),
]

_TIMEOUT = 10


def shell_run(command: str) -> str:
    command = command.strip().replace("\r", "").replace("\n", "")

    if _META_RE.search(command):
        return "Rejected: command contains unsafe characters."

    if not any(p.match(command) for p in _ALLOWED_PATTERNS):
        return f"Rejected: '{command[:80]}' is not in the allowed command list."

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=_TIMEOUT)
        output = result.stdout.strip()
        if result.returncode != 0:
            err = result.stderr.strip()
            return f"Exit {result.returncode}: {err or '(no stderr)'}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Timeout: command exceeded {_TIMEOUT}s."
    except Exception as e:
        return f"Error: {e}"
