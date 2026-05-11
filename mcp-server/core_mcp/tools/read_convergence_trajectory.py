"""read_convergence_trajectory — extract convergence tracking data from session logs."""

import re
from pathlib import Path
from typing import Any


def _extract_convergence_table(text: str) -> list[dict]:
    """
    Parse the convergence tracking table:
    | Finding | Agent1 | Agent2 | ... | Confidence |
    """
    rows = []
    in_table = False

    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"\|\s*Finding\s*\|", stripped, re.IGNORECASE):
            in_table = True
            continue
        if in_table:
            if stripped.startswith("|---") or stripped.startswith("| ---"):
                continue
            if not stripped.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2 and cells[0]:
                rows.append({
                    "finding": cells[0],
                    "agents": cells[1:-1] if len(cells) > 2 else [],
                    "confidence": cells[-1] if cells[-1] else "",
                })

    return rows


def read_convergence_trajectory_impl(workspace_id: str = "", session_date: str = "") -> dict[str, Any]:
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

    all_rows: list[dict] = []
    sources: list[str] = []

    for log_path in logs:
        content = log_path.read_text(encoding="utf-8")
        rows = _extract_convergence_table(content)
        if rows:
            all_rows.extend(rows)
            sources.append(log_path.name)

    # Summarize convergence: count findings with multiple agents in agreement
    convergent = [r for r in all_rows if len(r.get("agents", [])) >= 2]

    return {
        "found": True,
        "workspace_path": str(ws_path),
        "session_date": session_date or "most recent",
        "sources": sources,
        "findings": all_rows,
        "finding_count": len(all_rows),
        "convergent_findings": len(convergent),
        "convergence_ratio": round(len(convergent) / len(all_rows), 2) if all_rows else 0.0,
    }
