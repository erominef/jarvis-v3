# tools/git_tools.py — Git operations via Gitea REST API.
#
# Read actions (list_repos, get_repo, list_files, read_file, log) — auto-approved.
# Write actions (create_repo, write_file, delete_repo) — caller should confirm intent.
#
# Env vars: GITEA_URL, GITEA_TOKEN

import base64
import os

import httpx

_TIMEOUT = 20.0


def _gitea_url() -> str:
    return os.getenv("GITEA_URL", "http://100.101.127.60:3030").rstrip("/")


def _headers() -> dict:
    token = os.getenv("GITEA_TOKEN", "")
    return {"Authorization": f"token {token}", "Content-Type": "application/json"}


def _not_configured() -> str | None:
    if not os.getenv("GITEA_TOKEN", ""):
        return "Git not configured — set GITEA_URL and GITEA_TOKEN in .env"
    return None


def git_op(action: str, **kwargs) -> str:
    err = _not_configured()
    if err:
        return err

    gitea = _gitea_url()

    try:
        with httpx.Client(timeout=_TIMEOUT) as c:
            if action == "list_repos":
                r = c.get(f"{gitea}/api/v1/repos/search?limit=20", headers=_headers())
                r.raise_for_status()
                repos = r.json().get("data", [])
                if not repos:
                    return "No repos found."
                return "\n".join(
                    f"• {repo['full_name']} — {repo.get('description','')[:60]} [{repo['visibility']}]"
                    for repo in repos
                )

            elif action == "get_repo":
                repo = kwargs.get("repo", "")
                r = c.get(f"{gitea}/api/v1/repos/{repo}", headers=_headers())
                if r.status_code == 404:
                    return f"Repo not found: {repo}"
                r.raise_for_status()
                d = r.json()
                return (
                    f"Repo: {d['full_name']}\n"
                    f"Description: {d.get('description','')}\n"
                    f"Stars: {d['stars_count']} | Forks: {d['forks_count']}\n"
                    f"Default branch: {d['default_branch']}\n"
                    f"URL: {d['html_url']}"
                )

            elif action == "list_files":
                repo = kwargs.get("repo", "")
                path = kwargs.get("path", "")
                ref = kwargs.get("ref", "main")
                r = c.get(f"{gitea}/api/v1/repos/{repo}/contents/{path}?ref={ref}", headers=_headers())
                if r.status_code == 404:
                    return f"Path not found in {repo}: {path}"
                r.raise_for_status()
                items = r.json()
                if isinstance(items, list):
                    return "\n".join(
                        f"{'[dir]' if i['type']=='dir' else '[file]'} {i['name']} ({i.get('size',0)} bytes)"
                        for i in items
                    )
                return f"File: {items['name']} ({items.get('size',0)} bytes)"

            elif action == "read_file":
                repo = kwargs.get("repo", "")
                path = kwargs.get("path", "")
                ref = kwargs.get("ref", "main")
                r = c.get(f"{gitea}/api/v1/repos/{repo}/contents/{path}?ref={ref}", headers=_headers())
                if r.status_code == 404:
                    return f"File not found: {path} in {repo}"
                r.raise_for_status()
                data = r.json()
                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
                if len(content) > 3000:
                    content = content[:3000] + "\n[truncated]"
                return f"File: {path}\n\n{content}"

            elif action == "log":
                repo = kwargs.get("repo", "")
                limit = kwargs.get("limit", 10)
                r = c.get(f"{gitea}/api/v1/repos/{repo}/commits?limit={limit}", headers=_headers())
                if r.status_code == 404:
                    return f"Repo not found: {repo}"
                r.raise_for_status()
                commits = r.json()
                lines = []
                for commit in commits:
                    sha = commit["sha"][:7]
                    msg = commit["commit"]["message"].splitlines()[0][:72]
                    author = commit["commit"]["author"]["name"]
                    date = commit["commit"]["author"]["date"][:10]
                    lines.append(f"{sha} {date} [{author}] {msg}")
                return "\n".join(lines) if lines else "No commits."

            elif action == "create_repo":
                name = kwargs.get("name", "")
                description = kwargs.get("description", "")
                private = kwargs.get("private", True)
                if not name:
                    return "Error: repo name required."
                r = c.post(
                    f"{gitea}/api/v1/user/repos",
                    headers=_headers(),
                    json={"name": name, "description": description, "private": private, "auto_init": True},
                )
                if r.status_code == 409:
                    return f"Repo already exists: {name}"
                r.raise_for_status()
                d = r.json()
                return f"Created repo: {d['full_name']} — {d['html_url']}"

            elif action == "write_file":
                repo = kwargs.get("repo", "")
                path = kwargs.get("path", "")
                content = kwargs.get("content", "")
                message = kwargs.get("message", "Update via Jarvis")
                if not (repo and path and content):
                    return "Error: repo, path, and content required."
                encoded = base64.b64encode(content.encode()).decode()
                sha = ""
                check = c.get(f"{gitea}/api/v1/repos/{repo}/contents/{path}", headers=_headers())
                if check.status_code == 200:
                    sha = check.json().get("sha", "")
                payload = {"message": message, "content": encoded}
                if sha:
                    payload["sha"] = sha
                r = c.post(f"{gitea}/api/v1/repos/{repo}/contents/{path}", headers=_headers(), json=payload)
                r.raise_for_status()
                action_done = "Updated" if sha else "Created"
                return f"{action_done} {path} in {repo}: {message}"

            elif action == "delete_repo":
                repo = kwargs.get("repo", "")
                r = c.delete(f"{gitea}/api/v1/repos/{repo}", headers=_headers())
                if r.status_code == 404:
                    return f"Repo not found: {repo}"
                r.raise_for_status()
                return f"Deleted repo: {repo}"

            else:
                return (
                    f"Unknown git action: '{action}'. "
                    "Valid: list_repos, get_repo, list_files, read_file, log, create_repo, write_file, delete_repo"
                )

    except httpx.ConnectError:
        return f"Git service unavailable — Gitea not running at {gitea}"
    except httpx.HTTPStatusError as e:
        return f"Git API error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Git error: {e}"
