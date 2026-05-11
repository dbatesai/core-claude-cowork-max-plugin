"""read_project_md — read PROJECT.md for a workspace with section extracts."""

import json
import re
from pathlib import Path
from typing import Any


def _resolve_workspace_path(workspace_id: str) -> Path | None:
    """Return the project path for the given workspace ID (or most recent)."""
    index_path = Path.home() / ".core" / "index.json"
    if not index_path.exists():
        return None

    try:
        workspaces = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(workspaces, list):
        return None

    if workspace_id:
        for ws in workspaces:
            if ws.get("workspace_id") == workspace_id:
                project_path = ws.get("path", "")
                return Path(project_path) if project_path else None
        return None

    # Most recently active
    sorted_ws = sorted(workspaces, key=lambda w: w.get("last_active", ""), reverse=True)
    if sorted_ws:
        project_path = sorted_ws[0].get("path", "")
        return Path(project_path) if project_path else None

    return None


def _extract_section(content: str, section_name: str) -> str:
    """Extract a ## Section from markdown content."""
    pattern = rf"^## {re.escape(section_name)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def read_project_md_impl(workspace_id: str = "") -> dict[str, Any]:
    ws_path = _resolve_workspace_path(workspace_id)

    if ws_path is None:
        return {
            "found": False,
            "note": "No workspace found. Either no workspaces registered or workspace_id not found.",
        }

    project_md = ws_path / "PROJECT.md"
    if not project_md.exists():
        return {
            "found": False,
            "workspace_path": str(ws_path),
            "note": f"PROJECT.md not found at {project_md}",
        }

    content = project_md.read_text(encoding="utf-8")

    return {
        "found": True,
        "workspace_path": str(ws_path),
        "path": str(project_md),
        "content": content,
        "sections": {
            "state": _extract_section(content, "State"),
            "moves": _extract_section(content, "Moves"),
            "decisions_and_risks": _extract_section(content, "Decisions & Risks"),
            "people": _extract_section(content, "People"),
            "notes": _extract_section(content, "Notes"),
        },
    }
