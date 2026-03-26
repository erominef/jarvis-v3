# tools/infra.py — Infrastructure monitoring and service control.
#
# system_health: psutil on PC + ping Xeon memory service /health
# docker_restart: allowlisted PC services only via subprocess

import subprocess
from pathlib import Path

import httpx

_TIMEOUT = 5.0

# Allowlist: service name → compose directory on PC
_SERVICE_DIRS = {
    "jarvis-memory":  None,  # on Xeon — not restartable from PC
    "searxng":        Path.home() / "jarvis-v2" / "infra" / "pc-services",
    "playwright":     Path.home() / "jarvis-v2" / "infra" / "pc-services",
    "docuseal":       Path.home() / "jarvis-v2" / "infra" / "pc-services",
}

# PC-restartable services only
_PC_SERVICES = {k for k, v in _SERVICE_DIRS.items() if v is not None}


def system_health() -> str:
    lines = []

    # PC metrics
    try:
        import psutil  # type: ignore
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        lines.append(f"PC — CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% ({mem.used // (1024**3):.1f}/{mem.total // (1024**3):.1f} GB) | Disk: {disk.percent:.1f}%")
    except ImportError:
        lines.append("PC metrics unavailable — psutil not installed.")
    except Exception as e:
        lines.append(f"PC metrics error: {e}")

    # Xeon memory service health
    try:
        r = httpx.get("http://100.101.127.60:8083/health", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        lines.append(f"Xeon memory: ok | knowledge: {data.get('knowledge_count', '?')} | episodes: {data.get('episode_count', '?')}")
    except Exception:
        lines.append("Xeon memory: unreachable")

    # Code runner health
    try:
        r = httpx.get("http://100.101.127.60:8084/health", timeout=_TIMEOUT)
        r.raise_for_status()
        lines.append("Xeon code-runner: ok")
    except Exception:
        lines.append("Xeon code-runner: unreachable")

    # Email service health
    try:
        r = httpx.get("http://100.101.127.60:8085/health", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        smtp = "smtp:ok" if data.get("smtp_configured") else "smtp:not configured"
        imap = "imap:ok" if data.get("imap_configured") else "imap:not configured"
        lines.append(f"Xeon email: ok | {smtp} | {imap}")
    except Exception:
        lines.append("Xeon email: unreachable")

    return "\n".join(lines)


def docker_restart(service: str) -> str:
    service = service.strip().lower()
    if service not in _PC_SERVICES:
        allowed = ", ".join(sorted(_PC_SERVICES))
        return f"Rejected: '{service}' not in allowlist. Allowed: {allowed}"

    compose_dir = _SERVICE_DIRS[service]
    if not compose_dir or not compose_dir.exists():
        return f"Compose directory not found for '{service}': {compose_dir}"

    try:
        result = subprocess.run(
            ["docker", "compose", "restart", service],
            cwd=str(compose_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return f"Restarted '{service}'. {result.stdout.strip()}"
        return f"Restart failed for '{service}': {result.stderr.strip() or result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return f"Restart timed out for '{service}'."
    except Exception as e:
        return f"docker_restart error: {e}"
