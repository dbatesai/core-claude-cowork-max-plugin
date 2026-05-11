"""read_persuasion_log — find and parse the most recent persuasion log from a swarm session."""

import re
from pathlib import Path
from typing import Any


def _find_session_logs(workspace_path: Path, session_date: str) -> list[Path]:
    """Return agent log files from sessions/ filtered by date (or most recent date)."""
    sessions_dir = workspace_path / "sessions"
    if not sessions_dir.exists():
        return []

    if session_date:
        date_dirs = [sessions_dir / session_date]
    else:
        date_dirs = sorted(
            [d for d in sessions_dir.iterdir() if d.is_dir()],
            reverse=True,
        )

    logs: list[Path] = []
    for date_dir in date_dirs[:3]:  # scan up to 3 most recent dates
        logs.extend(date_dir.glob("*-log.md"))
        if logs:
            break

    return logs


def _extract_persuasion_entries(text: str) -> list[dict]:
    """Parse persuasion log entries (## <agent> changed position: <from> → <to>)."""
    entries = []
    # Match entries in a Persuasion Log section
    section_match = re.search(
        r"Persuasion Log.*?\n(.*?)(?=^#|\Z)", text, re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    if not section_match:
        return entries

    section_text = section_match.group(1)
    # Each entry: | Agent | From | To | Trigger |
    for row in re.finditer(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|", section_text):
        cells = [c.strip() for c in row.groups()]
        if cells[0].lower() in ("agent", "---", ""):
            continue
        entries.append({
            "agent": cells[0],
            "position_from": cells[1],
            "position_to": cells[2],
            "trigger": cells[3],
        })

    return entries


def read_persuasion_log_impl(workspace_id: str = "", session_date: str = "") -> dict[str, Any]:
    from core_mcp.tools.read_project_md import _resolve_workspace_path

    ws_path = _resolve_workspace_path(workspace_id)
    if ws_path is None:
        return {"found": False, "note": "No workspace resolved"}

    logs = _find_session_logs(ws_path, session_date)
    if not logs:
        return {
            "found": False,
            "workspace_path": str(ws_path),
            "note": "No session logs found",
        }

    all_entries: list[dict] = []
    sources: list[str] = []
    for log_path in logs:
        content = log_path.read_text(encoding="utf-8")
        entries = _extract_persuasion_entries(content)
        if entries:
            all_entries.extend(entries)
            sources.append(str(log_path.name))

    return {
        "found": True,
        "workspace_path": str(ws_path),
        "session_date": session_date or "most recent",
        "sources": sources,
        "entries": all_entries,
        "count": len(all_entries),
        "has_persuasion": len(all_entries) > 0,
    }
