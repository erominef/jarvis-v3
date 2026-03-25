# tools/shell.py — Restricted shell command execution.
#
# Security order (CRITICAL — do NOT reorder):
#   1. Strip \n and \r from input
#   2. Metacharacter check — reject if any of: | ; & ` $ ( ) < > #
#   3. Allowlist check — reject if first token not in allowed set
#
# Allowed commands: ls, cat (*.md, *.txt, *.json, *.log only), echo, pwd,
#   date, df -h, free -h, uptime, whoami, hostname, uname, curl -s https://
#
# No python3 — use code_execute instead.
# shell=True is required for the allowlisted commands to work correctly.


def shell_run(command: str) -> str:
    """
    Run an allowlisted read-only shell command.
    Returns stdout + stderr combined. Timeout: 10s.
    Rejects any command containing shell metacharacters.
    """
    raise NotImplementedError
