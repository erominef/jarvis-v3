# tools/crm.py — Client/account management.
#
# Filesystem-based CRM. Each client gets workspace/clients/{slug}/
# with profile.json, notes.md, and subdirectories for documents and images.
# All paths scoped to workspace/clients/ — no external access.
#
# crm_op(action, **kwargs) -> str
# Actions: create, get, update, add_note, list, search

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_WORKSPACE = (Path(__file__).parent.parent / "workspace").resolve()
_CLIENTS = _WORKSPACE / "clients"


def _slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "client"


def _client_dir(identifier: str) -> Path | None:
    """Find a client directory by slug, name, or company (fuzzy). Returns None if not found."""
    _CLIENTS.mkdir(parents=True, exist_ok=True)
    slug = _slug(identifier)

    # Exact slug match first
    exact = _CLIENTS / slug
    if exact.exists() and exact.is_dir():
        return exact

    # Fuzzy match against name/company in profile.json
    query = identifier.lower()
    for d in _CLIENTS.iterdir():
        if not d.is_dir():
            continue
        p = d / "profile.json"
        if not p.exists():
            continue
        try:
            profile = json.loads(p.read_text())
            if query in profile.get("name", "").lower() or query in profile.get("company", "").lower():
                return d
        except Exception:
            continue
    return None


def _load_profile(client_dir: Path) -> dict:
    p = client_dir / "profile.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def _save_profile(client_dir: Path, profile: dict) -> None:
    (client_dir / "profile.json").write_text(json.dumps(profile, indent=2))


def crm_op(action: str, **kwargs) -> str:
    _CLIENTS.mkdir(parents=True, exist_ok=True)

    if action == "create":
        name = kwargs.get("name", "").strip()
        if not name:
            return "Error: name is required."
        slug = _slug(kwargs.get("company") or name)
        client_dir = _CLIENTS / slug
        if client_dir.exists():
            return f"Client already exists at workspace/clients/{slug}/. Use update to modify."
        client_dir.mkdir(parents=True)
        (client_dir / "documents").mkdir()
        (client_dir / "images").mkdir()
        profile = {
            "name": name,
            "company": kwargs.get("company", ""),
            "email": kwargs.get("email", ""),
            "phone": kwargs.get("phone", ""),
            "status": kwargs.get("status", "prospect"),
            "tags": kwargs.get("tags", []),
            "created": datetime.now(timezone.utc).isoformat(),
        }
        _save_profile(client_dir, profile)
        (client_dir / "notes.md").write_text(f"# {name}\n\n")
        return (
            f"Client created: {name}\n"
            f"Directory: workspace/clients/{slug}/\n"
            f"Subdirectories: documents/, images/"
        )

    elif action == "get":
        identifier = kwargs.get("client", "").strip()
        if not identifier:
            return "Error: client name or company is required."
        d = _client_dir(identifier)
        if not d:
            return f"Client not found: {identifier}"
        profile = _load_profile(d)
        notes_path = d / "notes.md"
        notes = notes_path.read_text().strip() if notes_path.exists() else ""
        docs = sorted(f.name for f in (d / "documents").iterdir() if f.is_file()) if (d / "documents").exists() else []
        imgs = sorted(f.name for f in (d / "images").iterdir() if f.is_file()) if (d / "images").exists() else []

        lines = [f"**{profile.get('name', d.name)}**"]
        for k in ("company", "email", "phone", "status", "tags", "created"):
            v = profile.get(k)
            if v:
                lines.append(f"{k}: {v}")
        if docs:
            lines.append(f"documents: {', '.join(docs)}")
        if imgs:
            lines.append(f"images: {', '.join(imgs)}")
        lines.append("")
        lines.append(notes if notes else "(no notes yet)")
        return "\n".join(lines)

    elif action == "update":
        identifier = kwargs.get("client", "").strip()
        if not identifier:
            return "Error: client is required."
        d = _client_dir(identifier)
        if not d:
            return f"Client not found: {identifier}"
        profile = _load_profile(d)
        updated = []
        for field in ("name", "company", "email", "phone", "status", "tags"):
            if field in kwargs:
                profile[field] = kwargs[field]
                updated.append(field)
        if not updated:
            return "No fields to update. Provide: name, company, email, phone, status, or tags."
        _save_profile(d, profile)
        return f"Updated {profile.get('name', d.name)}: {', '.join(updated)}"

    elif action == "add_note":
        identifier = kwargs.get("client", "").strip()
        note = kwargs.get("note", "").strip()
        if not identifier:
            return "Error: client is required."
        if not note:
            return "Error: note is required."
        d = _client_dir(identifier)
        if not d:
            return f"Client not found: {identifier}"
        profile = _load_profile(d)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        author = kwargs.get("author", "").strip()
        author_str = f" — {author}" if author else ""
        entry = f"\n## {ts}{author_str}\n{note}\n"
        with open(d / "notes.md", "a") as f:
            f.write(entry)
        return f"Note added to {profile.get('name', d.name)}."

    elif action == "list":
        status_filter = kwargs.get("status", "").strip()
        entries = []
        for d in sorted(_CLIENTS.iterdir()):
            if not d.is_dir():
                continue
            profile = _load_profile(d)
            if status_filter and profile.get("status") != status_filter:
                continue
            name = profile.get("name") or d.name
            parts = [f"- {name}"]
            if profile.get("company"):
                parts.append(f"({profile['company']})")
            if profile.get("status"):
                parts.append(f"[{profile['status']}]")
            entries.append(" ".join(parts))
        if not entries:
            msg = "No clients found."
            if status_filter:
                msg += f" Status filter: {status_filter}"
            return msg
        return f"{len(entries)} client(s):\n" + "\n".join(entries)

    elif action == "search":
        query = kwargs.get("query", "").lower().strip()
        if not query:
            return "Error: query is required."
        results = []
        for d in sorted(_CLIENTS.iterdir()):
            if not d.is_dir():
                continue
            profile = _load_profile(d)
            haystack = " ".join(str(v) for v in profile.values()).lower()
            notes_path = d / "notes.md"
            if notes_path.exists():
                haystack += " " + notes_path.read_text().lower()
            if query in haystack:
                name = profile.get("name") or d.name
                parts = [f"- {name}"]
                if profile.get("company"):
                    parts.append(f"({profile['company']})")
                if profile.get("status"):
                    parts.append(f"[{profile['status']}]")
                results.append(" ".join(parts))
        if not results:
            return f"No clients found matching: {query}"
        return f"{len(results)} match(es) for '{query}':\n" + "\n".join(results)

    else:
        return f"Unknown action: {action}. Valid actions: create, get, update, add_note, list, search"
