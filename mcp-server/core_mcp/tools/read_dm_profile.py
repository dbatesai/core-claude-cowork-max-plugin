"""read_dm_profile — read ~/.core/dm-profile.md."""

from pathlib import Path
from typing import Any
import re


def read_dm_profile_impl() -> dict[str, Any]:
    profile_path = Path.home() / ".core" / "dm-profile.md"

    if not profile_path.exists():
        return {
            "exists": False,
            "note": "~/.core/dm-profile.md not found — DM not yet initialized",
        }

    content = profile_path.read_text(encoding="utf-8")

    # Extract name from "## Identity" section if present
    dm_name: str | None = None
    name_match = re.search(r"\*\*Name:\*\*\s*(.+)", content)
    if name_match:
        dm_name = name_match.group(1).strip()

    return {
        "exists": True,
        "dm_name": dm_name,
        "content": content,
        "path": str(profile_path),
    }
