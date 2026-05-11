"""read_workshop_state — aggregate state for the DM Workshop Live Artifact."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _count_open_risks(project_md_content: str) -> int:
    """Count open risk rows in §Decisions & Risks section."""
    section_match = re.search(
        r"^## Decisions & Risks.*?\n(.*?)(?=^## |\Z)",
        project_md_content,
        re.MULTILINE | re.DOTALL,
    )
    if not section_match:
        return 0
    section = section_match.group(1)
    # Count rows that aren't headers, dividers, or empty — approximate
    risk_rows = [
        ln for ln in section.splitlines()
        if ln.strip().startswith("| R-") or ln.strip().startswith("| DC-")
    ]
    return len(risk_rows)


def _session_age_days(workspace_id: str) -> int | None:
    """Days since last session for the workspace."""
    index_path = Path.home() / ".core" / "index.json"
    if not index_path.exists():
        return None
    try:
        workspaces = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    for ws in workspaces:
        if not workspace_id or ws.get("workspace_id") == workspace_id:
            last_active = ws.get("last_active", "")
            if last_active:
                try:
                    last_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
                    delta = datetime.now(timezone.utc) - last_dt
                    return delta.days
                except ValueError:
                    pass
            break
    return None


def _last_swarm_date(ws_path: Path) -> str | None:
    """Find the most recent session date with swarm logs."""
    sessions_dir = ws_path / "sessions"
    if not sessions_dir.exists():
        return None
    date_dirs = sorted(
        [d for d in sessions_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    for d in date_dirs:
        if any(d.glob("*-log.md")):
            return d.name
    return None


def read_workshop_state_impl(workspace_id: str = "") -> dict[str, Any]:
    from core_mcp.tools.read_project_md import _resolve_workspace_path
    from core_mcp.tools.read_dm_profile import read_dm_profile_impl
    from core_mcp.tools.read_vibe_log import read_vibe_log_impl

    ws_path = _resolve_workspace_path(workspace_id)
    dm_profile = read_dm_profile_impl()
    vibe_data = read_vibe_log_impl(limit=1)

    project_name = None
    state_summary = None
    active_risk_count = 0

    if ws_path:
        project_md = ws_path / "PROJECT.md"
        if project_md.exists():
            content = project_md.read_text(encoding="utf-8")
            # Extract project name from "## What & Why" first line
            what_match = re.search(r"^## What & Why\s*\n+(.+)", content, re.MULTILINE)
            if what_match:
                project_name = what_match.group(1).strip().lstrip("#").strip()
            # Extract state summary (first bullet in §State)
            state_match = re.search(r"^## State\s*\n+[-*]\s*\*\*(.+?)\*\*", content, re.MULTILINE)
            if state_match:
                state_summary = state_match.group(1).strip()
            active_risk_count = _count_open_risks(content)

    return {
        "dm_name": dm_profile.get("dm_name"),
        "project_name": project_name,
        "project_state_summary": state_summary,
        "active_risk_count": active_risk_count,
        "session_age_days": _session_age_days(workspace_id),
        "last_swarm_date": _last_swarm_date(ws_path) if ws_path else None,
        "vibe_label": vibe_data.get("most_recent_vibe"),
        "workspace_count": _count_workspaces(),
        "workspace_path": str(ws_path) if ws_path else None,
    }


def _count_workspaces() -> int:
    index_path = Path.home() / ".core" / "index.json"
    if not index_path.exists():
        return 0
    try:
        ws = json.loads(index_path.read_text(encoding="utf-8"))
        return len(ws) if isinstance(ws, list) else 0
    except (json.JSONDecodeError, OSError):
        return 0
