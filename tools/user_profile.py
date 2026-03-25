# tools/user_profile.py — Owner profile maintenance.
#
# user_profile_update(section, observation) — appends a timestamped observation
# to the named section of workspace/USER.md. Creates the section if missing.
#
# The profile is Jarvis's actual picture of the owner — genuine impressions,
# character observations, and durable understanding of how they think.
# Not project facts. Not current tasks. Who they are.

from datetime import datetime, timezone
from pathlib import Path

_WORKSPACE = Path(__file__).parent.parent / "workspace"
_PROFILE_PATH = _WORKSPACE / "USER.md"

_VALID_SECTIONS = {
    "How You Think",
    "What Drives You",
    "Strengths I've Noticed",
    "Patterns and Blind Spots",
    "How We Work Best Together",
    "How You Want Decisions Handled",
    "Where You Are Right Now",
}


def user_profile_update(section: str, observation: str) -> str:
    section = section.strip()
    observation = observation.strip()

    if section not in _VALID_SECTIONS:
        valid = ", ".join(sorted(_VALID_SECTIONS))
        return f"Invalid section '{section}'. Valid sections: {valid}"

    if not observation:
        return "Error: observation cannot be empty."

    # Read existing profile
    try:
        content = _PROFILE_PATH.read_text() if _PROFILE_PATH.exists() else ""
    except Exception as e:
        return f"Error reading profile: {e}"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"- [{ts}] {observation}"
    header = f"## {section}"

    if header in content:
        # Find the section and append after it
        lines = content.splitlines()
        new_lines = []
        inserted = False
        i = 0
        while i < len(lines):
            new_lines.append(lines[i])
            if not inserted and lines[i].strip() == header:
                # Skip past any comment line immediately after the header
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("<!--"):
                    i += 1
                    new_lines.append(lines[i])
                new_lines.append(entry)
                inserted = True
            i += 1
        content = "\n".join(new_lines)
    else:
        # Append new section at end
        content = content.rstrip() + f"\n\n{header}\n{entry}\n"

    try:
        _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PROFILE_PATH.write_text(content)
    except Exception as e:
        return f"Error writing profile: {e}"

    return f"Profile updated — {section}: {observation[:80]}{'...' if len(observation) > 80 else ''}"
