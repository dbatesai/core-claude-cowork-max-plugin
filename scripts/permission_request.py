#!/usr/bin/env python3
"""
CORE Cowork Max plugin — PermissionRequest augmentation hook (Option 5(a), v1.1.3).

Fires when Claude Code's permission system surfaces a request (file tool, MCP tool,
bash, etc.). Empirically verified to fire inside Cowork sessions for Read / Write /
Edit / Glob / Grep / mcp__cowork__* dialogs per Q-F9-1 probe findings 2026-05-13
(see outputs/2026-05-12/q-f9-1-findings.md in the CORE dev repo).

What this hook does:
    1. Reads the stdin JSON payload Claude Code emits for PermissionRequest.
    2. Gates on CLAUDE_CODE_IS_COWORK=1 — silent no-op on Claude Code CLI.
    3. Examines tool_name + tool_input + permission_suggestions from the payload.
    4. Emits a structured [[CORE-PERMISSION-CONTEXT-BEGIN/END]] block to stdout
       (Cowork injects stdout into the DM's session context).
    5. The DM (Keel) uses the advisory to craft a clear plain-language message
       to the user about what just got blocked and what scope grant would unblock it.
    6. Appends an audit entry to ~/.core/logs/permission-events.md for v1.1.3
       acceptance testing.

What this hook DOES NOT do (permission pay-to-play principle — David, 2026-05-12):
    - Does NOT auto-approve any permission request.
    - Does NOT modify the permission decision (no decision field in output).
    - Does NOT block, deny, or retry the action.
    - Does NOT build alternate code paths to fake functionality on denial.

The hook is passive augmentation only. If the user denies the dialog, the action
fails normally; the DM's advisory tells the user clearly what won't work and
re-asks. Buyer beware.

Runs on macOS / Windows / Linux host. Invoked by hooks.json.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow this script to be invoked from anywhere; import sibling module.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import core_helpers as ch  # noqa: E402


# --------------------------------------------------------------------------
# Tool family classification (extends as new tools are added).
# --------------------------------------------------------------------------

FILE_READ_TOOLS = {"Read", "Glob", "Grep"}
FILE_WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
FILE_TOOLS = FILE_READ_TOOLS | FILE_WRITE_TOOLS


def _is_file_tool(tool_name: str) -> bool:
    return tool_name in FILE_TOOLS


def _is_cowork_mcp_tool(tool_name: str) -> bool:
    return tool_name.startswith("mcp__cowork__")


def _is_bash_tool(tool_name: str) -> bool:
    # Both "Bash" (Claude Code CLI) and Cowork's namespaced variant.
    return tool_name == "Bash" or tool_name.startswith("mcp__workspace__bash")


# --------------------------------------------------------------------------
# Advisory message composition.
# Each function returns (reason_slug, advisory_sentence).
# The advisory is plain-language — DM may surface it to the user verbatim,
# but is expected to wrap it in conversational voice.
# --------------------------------------------------------------------------

def _advisory_for_add_directories(tool_name: str, directories: list) -> tuple[str, str]:
    if not directories:
        return ("outside-connected-folders", "The action needs access to a folder outside the connected workspace.")
    dirs_str = ", ".join(str(d) for d in directories)
    return (
        "outside-connected-folders",
        f"The action would use {tool_name} on a path outside the connected folders. "
        f"To proceed, ask the user to grant access to {dirs_str} via "
        f"`mcp__cowork__request_cowork_directory`.",
    )


def _advisory_for_add_rules(tool_name: str, rules: list) -> tuple[str, str]:
    if not rules:
        return ("rule-grant-required", f"The action needs an allow-rule for {tool_name}.")
    # Take the first rule for the human-facing summary; full rule list is in audit log.
    rule = rules[0]
    rule_target = rule.get("ruleContent") or rule.get("toolName") or tool_name
    if _is_cowork_mcp_tool(tool_name):
        return (
            "cowork-mcp-approval",
            f"The action needs approval for the Cowork MCP tool `{tool_name}`. "
            f"The user will see a dialog; if approved, future calls in this session succeed.",
        )
    return (
        "rule-grant-required",
        f"The action would use {tool_name} on `{rule_target}`. "
        f"To proceed, the user can allow {tool_name} for that path or scope.",
    )


def _advisory_for_set_mode(tool_name: str, mode: str) -> tuple[str, str]:
    if mode == "acceptEdits":
        return (
            "edit-mode-required",
            f"The action would use {tool_name} but accept-edits mode isn't on for this session. "
            f"The user can enable accept-edits mode to proceed (broader scope) "
            f"or grant access to the specific path instead.",
        )
    return (
        "mode-change-required",
        f"The action requires switching session mode to `{mode}` to proceed.",
    )


def _compose_advisory(tool_name: str, suggestions: list) -> tuple[str, str]:
    """
    Pick the most specific suggestion shape and compose an advisory.
    Priority: addDirectories > addRules > setMode > generic fallback.
    """
    # Index suggestions by type.
    by_type: dict[str, list] = {}
    for s in suggestions or []:
        t = s.get("type")
        if t:
            by_type.setdefault(t, []).append(s)

    if "addDirectories" in by_type:
        dirs = by_type["addDirectories"][0].get("directories", [])
        return _advisory_for_add_directories(tool_name, dirs)

    if "addRules" in by_type:
        rules = by_type["addRules"][0].get("rules", [])
        return _advisory_for_add_rules(tool_name, rules)

    if "setMode" in by_type:
        mode = by_type["setMode"][0].get("mode", "")
        return _advisory_for_set_mode(tool_name, mode)

    # No structured suggestion. Generic fallback by tool family.
    if _is_file_tool(tool_name):
        return (
            "file-permission-required",
            f"The action would use {tool_name} but needs user approval. "
            f"The user will see a dialog; if denied, this action will fail.",
        )
    if _is_cowork_mcp_tool(tool_name):
        return (
            "cowork-mcp-approval",
            f"The action needs approval for `{tool_name}`. The user will see a dialog.",
        )
    if _is_bash_tool(tool_name):
        return (
            "bash-approval",
            f"The action would run a shell command but needs user approval. "
            f"The user will see a dialog.",
        )
    return (
        "permission-required",
        f"User approval needed for `{tool_name}`. The user will see a dialog.",
    )


# --------------------------------------------------------------------------
# Stdout emission — structured block matching the inject_file pattern.
# --------------------------------------------------------------------------

def _emit_context_block(tool_name: str, reason: str, tool_input: dict, advisory: str, suggestions: list) -> None:
    print("[[CORE-PERMISSION-CONTEXT-BEGIN]]")
    print(f"tool: {tool_name}")
    print(f"reason: {reason}")
    # tool_input may contain large content (e.g., Write content) — cap for context safety.
    try:
        tool_input_repr = json.dumps(tool_input, ensure_ascii=False)
    except (TypeError, ValueError):
        tool_input_repr = str(tool_input)
    if len(tool_input_repr) > 500:
        tool_input_repr = tool_input_repr[:497] + "..."
    print(f"tool_input: {tool_input_repr}")
    # Single-line advisory for clean DM ingestion.
    print(f"advisory: {advisory}")
    # Compact suggestion summary (machine-readable, for DM follow-up).
    if suggestions:
        try:
            sugg_compact = json.dumps(
                [{"type": s.get("type"), "destination": s.get("destination")} for s in suggestions],
                ensure_ascii=False,
            )
        except (TypeError, ValueError):
            sugg_compact = str(suggestions)
        print(f"suggestion_types: {sugg_compact}")
    print("[[CORE-PERMISSION-CONTEXT-END]]")


# --------------------------------------------------------------------------
# Audit log — append-only, plain markdown for diff-readability.
# --------------------------------------------------------------------------

def _audit_log(tool_name: str, reason: str, tool_input: dict, advisory: str) -> None:
    log_path = ch.CORE_DATA_DIR / "logs" / "permission-events.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"## {ts} — {tool_name} — {reason}\n")
            # tool_input snippet
            try:
                tool_input_repr = json.dumps(tool_input, ensure_ascii=False)[:300]
            except (TypeError, ValueError):
                tool_input_repr = str(tool_input)[:300]
            f.write(f"tool_input: {tool_input_repr}\n")
            f.write(f"advisory: {advisory}\n\n")
    except OSError:
        # Audit-log failure must not break the augmentation. Best-effort only.
        pass


# --------------------------------------------------------------------------
# Main entry.
# --------------------------------------------------------------------------

def main() -> int:
    # Cowork-only augmentation. On Claude Code CLI (or unset), do nothing.
    # Pay-to-play: the augmentation hook has no role outside Cowork's dialog UX.
    if os.environ.get("CLAUDE_CODE_IS_COWORK", "0") != "1":
        return 0

    # Read stdin payload (Claude Code emits JSON; missing/malformed stdin = silent no-op).
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        ch.log_warn("permission_request: stdin not valid JSON; skipping")
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    suggestions = payload.get("permission_suggestions", []) or []

    if not tool_name:
        # Nothing useful to say without tool_name.
        return 0

    reason, advisory = _compose_advisory(tool_name, suggestions)

    _emit_context_block(tool_name, reason, tool_input, advisory, suggestions)
    _audit_log(tool_name, reason, tool_input, advisory)

    return 0


if __name__ == "__main__":
    sys.exit(main())
