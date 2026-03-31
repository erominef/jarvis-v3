# restart-api/app.py — Xeon-side Docker restart service.
#
# POST /restart/{service}  — restart a named Jarvis container
# GET  /health             — liveness check
#
# Mounts /var/run/docker.sock to run docker commands on the host.
# Requires X-Token header matching RESTART_TOKEN env var.

import os
import subprocess

from fastapi import FastAPI, HTTPException, Header

app = FastAPI()

_TOKEN = os.environ.get("RESTART_TOKEN", "")

# Friendly name → actual Docker container name
_CONTAINER_MAP = {
    "memory":           "memory-jarvis-memory-1",
    "code-runner":      "code-runner-jarvis-code-runner-1",
    "email":            "email-jarvis-email-1",
    "browser-session":  "browser-session-jarvis-browser-session-1",
    "playwright":       "jarvis-playwright",
    "searxng":          "jarvis-searxng",
    "comfyui":          "comfyui-jarvis-comfyui-1",
    "n8n":              "xeon-n8n",
    "gitea":            "xeon-gitea",
    "restart-api":      "restart-api-jarvis-restart-api-1",
}


@app.get("/health")
def health():
    return {"status": "ok", "services": sorted(_CONTAINER_MAP.keys())}


@app.post("/restart/{service}")
def restart(service: str, x_token: str = Header(...)):
    if not _TOKEN or x_token != _TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token.")

    container = _CONTAINER_MAP.get(service)
    if not container:
        allowed = ", ".join(sorted(_CONTAINER_MAP.keys()))
        raise HTTPException(status_code=400, detail=f"Unknown service '{service}'. Allowed: {allowed}")

    try:
        result = subprocess.run(
            ["docker", "restart", container],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"docker restart failed: {result.stderr.strip()}")
        return {"success": True, "service": service, "container": container}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Restart timed out for '{container}'.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
