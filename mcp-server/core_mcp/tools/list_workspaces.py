"""list_workspaces — read ~/.core/index.json and return workspace registry."""

import json
from pathlib import Path
from typing import Any


def list_workspaces_impl() -> dict[str, Any]:
    index_path = Path.home() / ".core" / "index.json"

    if not index_path.exists():
        return {
            "workspaces": [],
            "count": 0,
            "note": "~/.core/index.json not found — no workspaces registered yet",
        }

    try:
        raw = index_path.read_text(encoding="utf-8")
        workspaces = json.loads(raw)
        if not isinstance(workspaces, list):
            return {"error": "index.json is not a list", "raw": raw[:500]}
    except json.JSONDecodeError as e:
        return {"error": f"index.json parse error: {e}", "raw": raw[:500]}

    # Sort by last_active descending; workspaces without the field sort to end
    sorted_ws = sorted(
        workspaces,
        key=lambda w: w.get("last_active", ""),
        reverse=True,
    )

    return {
        "workspaces": sorted_ws,
        "count": len(sorted_ws),
        "most_recent": sorted_ws[0] if sorted_ws else None,
    }
