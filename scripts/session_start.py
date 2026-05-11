#!/usr/bin/env python3
"""
CORE Cowork Max plugin — SessionStart hook (cross-platform Python).

Runs on macOS / Windows / Linux host with full filesystem privilege.
Outputs markers to stdout; Cowork injects stdout into the DM's session context.

Invoked by hooks.json. The .sh / .cmd shims in this directory are thin
wrappers that exec this script.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow this script to be invoked from anywhere; import sibling module.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import core_helpers as ch  # noqa: E402


def main() -> int:
    # 1. Standard bootstrap (skill, dm-profile, project state, hints)
    try:
        ch.session_start_bootstrap_minus_queue()
    except Exception as e:
        ch.log_warn(f"session_start: bootstrap failed: {e}")
        return 1

    # 2. Improvement queue (TM-2 mitigation, M-MAX-15 QUEUE_CAP)
    queue = ch.CORE_DATA_DIR / "improvement-queue.md"
    queue_log_dir = ch.CORE_DATA_DIR / "improvement-log"
    if queue.is_file():
        try:
            content = queue.read_text(encoding="utf-8")
            entries = sum(1 for line in content.splitlines() if line.startswith("## "))
        except OSError:
            entries = 0
        cap_str = os.environ.get("CORE_IMPROVEMENT_QUEUE_CAP", "5")
        try:
            cap = int(cap_str)
        except ValueError:
            cap = 5

        if entries > cap:
            ch.marker("QUEUE-OVER-CAP", f"{entries} > {cap} — auto-apply skipped; review {queue} manually")
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            try:
                with (queue_log_dir / "over-cap.md").open("a", encoding="utf-8") as f:
                    f.write(f"## {ts} — queue over-cap\nEntries: {entries}  Cap: {cap}\nAction: auto-apply skipped\n\n")
            except OSError:
                pass
        elif entries > 0:
            if not ch.apply_improvement_queue(queue, queue_log_dir):
                ch.log_warn("improvement-queue application failed; queue preserved for next session")

    # 3. Capability probe + MCP server registration (idempotent; runs unless explicitly disabled).
    # Three levels per David's fallback ladder:
    #   L1 = Node.js + MCP server live → full MCP-backed dashboard
    #   L2 = Node missing or MCP failed → DM uses request_cowork_directory + file tools
    #   L3 = even fallback unavailable → DM informs user via chat (FYI)
    if os.environ.get("CORE_MCP_INSTALL_MANUAL", "0") != "1":
        installer = _SCRIPT_DIR / "mcp_server_install.py"
        if installer.is_file():
            try:
                subprocess.run(
                    [sys.executable, str(installer)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            except subprocess.TimeoutExpired:
                ch.log_warn("mcp_server_install.py timed out (15s)")
            except Exception as e:
                ch.log_warn(f"mcp_server_install.py invocation failed: {e}")

    # 3b. Emit capability marker for the DM (based on ~/.core/capability.json written by the installer)
    cap_path = ch.CORE_DATA_DIR / "capability.json"
    if cap_path.is_file():
        try:
            import json as _json
            cap = _json.loads(cap_path.read_text(encoding="utf-8"))
            level = cap.get("level", 3)
            reason = cap.get("reason", "")

            if level == 1:
                restart_pending = (ch.CORE_DATA_DIR / "needs-app-restart").exists()
                if restart_pending:
                    ch.marker("CAPABILITY-LEVEL", "1-pending-restart — MCP server registered; restart Cowork to activate live dashboard")
                else:
                    ch.marker("CAPABILITY-LEVEL", f"1 — full live dashboard via CORE MCP server ({reason})")
            elif level == 2:
                ch.marker("CAPABILITY-LEVEL", f"2 — live dashboard via file tools (no MCP); reason: {reason}. DM should use request_cowork_directory + Read/Write file tools, parse PROJECT.md in-session, push HTML via mcp__cowork__update_artifact.")
            else:
                ch.marker("CAPABILITY-LEVEL", f"3 — no live dashboard available; reason: {reason}. DM should inform the user via chat: 'The live dashboard isn't available in this environment. CORE still works for chat-based delivery management and adversarial swarms. To enable the live dashboard: install Node.js 18+ from https://nodejs.org and restart Cowork.'")
        except (OSError, ValueError) as e:
            ch.log_warn(f"capability.json read failed: {e}")
            ch.marker("CAPABILITY-LEVEL", "3 — capability state unreadable; dashboard unavailable")
    else:
        ch.marker("CAPABILITY-LEVEL", "3 — capability probe didn't run; dashboard unavailable. The hook may have failed to invoke the installer.")

    # 4. First-session detection
    if not (ch.CORE_PROJECT_ROOT / "PROJECT.md").is_file():
        ch.marker(
            "FIRST-SESSION",
            f"no PROJECT.md at {ch.CORE_PROJECT_ROOT} — run onboarding wizard to set up this project",
        )

    # 5. Connector enumeration hint
    cdir = ch.connectors_dir()
    if cdir.is_dir():
        try:
            names = sorted(p.name for p in cdir.iterdir() if not p.name.startswith("."))
            ch.marker("CONNECTORS-AVAILABLE", ",".join(names) if names else "none-detected")
        except OSError:
            ch.marker("CONNECTORS-AVAILABLE", "none-detected")
    else:
        ch.marker("CONNECTORS-AVAILABLE", "none-detected")

    # 6. Scheduled tasks flag (M-MAX-7 TM-10)
    if os.environ.get("CORE_SCHEDULED_TASKS_ENABLED", "0") == "1":
        ch.marker("SCHEDULED-TASKS-ENABLED", "CORE_SCHEDULED_TASKS_ENABLED=1; observe Q1 behavior at first fire")
    else:
        ch.marker(
            "SCHEDULED-TASKS-DISABLED",
            "set CORE_SCHEDULED_TASKS_ENABLED=1 to enable scheduled sessions (v1.0 default: OFF)",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
