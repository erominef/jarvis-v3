# tools/infra.py — Infrastructure monitoring and service control.
#
# system_health: PC metrics + health check all 9 Xeon services
# docker_restart: calls Xeon restart API (10.0.0.2:8087)

import os

import httpx

from config import RESTART_API_URL, RESTART_API_TOKEN

_TIMEOUT = 5.0

# Known restartable services (for error messaging)
_KNOWN_SERVICES = {
    "memory", "code-runner", "email", "browser-session",
    "playwright", "searxng", "comfyui", "n8n", "gitea", "restart-api",
}


def system_health() -> str:
    lines = []

    # ── PC metrics ────────────────────────────────────────────────────────────
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        lines.append(
            f"PC — CPU: {cpu:.1f}% | "
            f"RAM: {mem.percent:.1f}% ({mem.used // (1024**3):.1f}/{mem.total // (1024**3):.1f} GB) | "
            f"Disk: {disk.percent:.1f}%"
        )
    except ImportError:
        lines.append("PC metrics unavailable — psutil not installed.")
    except Exception as e:
        lines.append(f"PC metrics error: {e}")

    lines.append("")

    # ── Xeon services ─────────────────────────────────────────────────────────
    xeon = "http://10.0.0.2"

    def ping(label: str, url: str, detail_fn=None) -> str:
        try:
            r = httpx.get(url, timeout=_TIMEOUT)
            r.raise_for_status()
            if detail_fn:
                return f"{label}: ok | {detail_fn(r)}"
            return f"{label}: ok"
        except Exception:
            return f"{label}: unreachable"

    lines.append(ping(
        "memory", f"{xeon}:8083/health",
        lambda r: f"knowledge: {r.json().get('knowledge_count', '?')} | episodes: {r.json().get('episode_count', '?')}",
    ))
    lines.append(ping("code-runner",     f"{xeon}:8084/health"))
    lines.append(ping(
        "email", f"{xeon}:8085/health",
        lambda r: f"smtp: {'ok' if r.json().get('smtp_configured') else 'not configured'} | imap: {'ok' if r.json().get('imap_configured') else 'not configured'}",
    ))
    lines.append(ping("browser-session", f"{xeon}:8086/health"))
    lines.append(ping("playwright",      f"{xeon}:8082/health"))
    lines.append(ping("searxng",         f"{xeon}:8081/"))
    lines.append(ping("comfyui",         f"{xeon}:8188/"))
    lines.append(ping("n8n",             f"{xeon}:5678/healthz"))
    lines.append(ping("gitea",           f"{xeon}:3030/api/healthz"))
    lines.append(ping("restart-api",     f"{xeon}:8087/health"))

    return "\n".join(lines)


def docker_restart(service: str) -> str:
    service = service.strip().lower()
    if not RESTART_API_TOKEN:
        return "docker_restart: RESTART_API_TOKEN not configured."
    try:
        r = httpx.post(
            f"{RESTART_API_URL}/restart/{service}",
            headers={"X-Token": RESTART_API_TOKEN},
            timeout=35.0,
        )
        if r.status_code == 403:
            return "Restart rejected: bad token."
        if r.status_code == 400:
            return f"Unknown service '{service}'. Allowed: {', '.join(sorted(_KNOWN_SERVICES))}"
        r.raise_for_status()
        data = r.json()
        return f"Restarted {data['service']} ({data['container']})."
    except httpx.ConnectError:
        return f"Restart API unreachable at {RESTART_API_URL}. Is restart-api running on Xeon?"
    except Exception as e:
        return f"docker_restart error: {e}"
