"""read_swarm_topology — extract agent roster + phase timeline from session logs."""

import re
from pathlib import Path
from typing import Any


def _extract_agent_names(text: str) -> list[str]:
    """Find agent names referenced in a log file."""
    # Agent names are typically in "## <Name>" headers or "**<Name>:**" bold labels
    names = set()
    for match in re.finditer(r"^#+\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*$", text, re.MULTILINE):
        name = match.group(1).strip()
        if len(name) > 2 and name not in ("Phase", "Summary", "Notes", "Output", "Findings"):
            names.add(name)
    for match in re.finditer(r"\*\*([A-Z][a-z]+):\*\*", text):
        names.add(match.group(1))
    return sorted(names)


def _extract_phases(text: str) -> list[dict]:
    """Extract phase headers and their brief descriptions."""
    phases = []
    for match in re.finditer(r"^#+\s+(Phase\s+\d+.*?)$", text, re.MULTILINE | re.IGNORECASE):
        phases.append({"phase": match.group(1).strip()})
    return phases


def read_swarm_topology_impl(workspace_id: str = "", session_date: str = "") -> dict[str, Any]:
    from core_mcp.tools.read_project_md import _resolve_workspace_path
    from core_mcp.tools.read_persuasion_log import _find_session_logs

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

    agents: set[str] = set()
    phases: list[dict] = []
    sources: list[str] = []

    for log_path in logs:
        content = log_path.read_text(encoding="utf-8")
        agents.update(_extract_agent_names(content))
        if not phases:
            phases = _extract_phases(content)
        sources.append(log_path.name)

    return {
        "found": True,
        "workspace_path": str(ws_path),
        "session_date": session_date or "most recent",
        "agents": sorted(agents),
        "agent_count": len(agents),
        "phases": phases,
        "phase_count": len(phases),
        "sources": sources,
    }
