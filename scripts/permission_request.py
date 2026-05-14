#!/usr/bin/env python3
"""
CORE Cowork Max plugin — permission-context augmentation hook (v1.2.2, DC-45 + S5 hotfix).

Registered on TWO Claude Code events (see hooks/hooks.json):

  - PreToolUse        — fires before every tool invocation; emits advisory text
                        via `hookSpecificOutput.additionalContext` (the documented
                        context-injection path). This is the advisory-delivery
                        mechanism per DC-45 (e2). Shape-based suppression gate
                        ensures only permission-risky tools (file tools, Cowork
                        MCP) emit advisory; Bash and internal tools are silent.
  - PermissionRequest — fires when Cowork's permission system surfaces a dialog
                        (file tools, MCP). Writes to audit log only. Retained
                        for `permission_suggestions` capture (PreToolUse payloads
                        do NOT carry that field per v114-probe-findings.md 12/12).

What this hook does NOT do (permission pay-to-play principle — David, 2026-05-12):
    - Does NOT auto-approve any permission request.
    - Does NOT modify the permission decision (`permissionDecision: "ask"` is
      the documented "show the dialog as normal" pattern).
    - Does NOT block, deny, or retry the action.
    - Does NOT build alternate code paths to fake functionality on denial.

The hook is passive augmentation only. If the user denies the dialog, the action
fails normally; the DM's advisory tells the user clearly what won't work and
re-asks. Buyer beware.

DC-45 branch row 2 = (e2)-only — no (e1) backstop monitor (Cowork ignores
monitors/monitors.json per Probe B 2026-05-13).
M-Lath-1 elevation: tool-family classification (file/cowork-mcp) is the pre-gate
since `permission_suggestions` is absent from PreToolUse payloads.

Runs on macOS / Windows / Linux host. Invoked by hooks.json.
"""
from __future__ import annotations

import json
import os
import re
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
# Lines lifted from post-classification fallback to PreToolUse pre-gate per
# DC-45 M-Lath-1.
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
# Bash path-sensitivity inspection (v1.2.2 S5 hotfix).
# Probe A confirmed Bash does NOT fire PermissionRequest in Cowork, but may
# still touch host paths the user hasn't connected. The gate fires when the
# command string references either a system-sensitive prefix or any absolute
# path outside the connected workspace folders.
# --------------------------------------------------------------------------

_SYSTEM_SENSITIVE_PREFIX_RE = re.compile(
    r"^/(?:etc|private|var|usr|Library|System|opt|bin|sbin)(?:/|$)"
)

# Path token in a shell command: starts with `/`, optionally preceded by a
# shell separator. Excludes double-leading-slash (URL host-form like `//foo`).
_PATH_TOKEN_RE = re.compile(
    r"(?:^|[\s'\"=`;|&><(){}])(/(?!/)[A-Za-z0-9_./~+\-]+)"
)


def _extract_paths_from_command(command: str) -> list[str]:
    """Extract absolute path tokens from a shell command string."""
    if not command:
        return []
    paths: list[str] = []
    seen: set[str] = set()
    for m in _PATH_TOKEN_RE.finditer(command):
        p = m.group(1).rstrip(";,|&><`\"')]")
        if p and p not in seen:
            seen.add(p)
            paths.append(p)
    return paths


def _connected_folders() -> list[str]:
    """Read CLAUDE_CODE_WORKSPACE_HOST_PATHS (pipe-separated) into a list."""
    raw = os.environ.get("CLAUDE_CODE_WORKSPACE_HOST_PATHS", "")
    if not raw:
        return []
    return [p for p in raw.split("|") if p]


def _path_outside_connected(path: str, connected: list[str]) -> bool:
    """True if `path` is not under any connected folder."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    for cf in connected:
        cf_abs = os.path.abspath(os.path.expanduser(cf))
        if abs_path == cf_abs or abs_path.startswith(cf_abs + os.sep):
            return False
    return True


def _bash_path_sensitive(command: str) -> tuple[bool, list[str]]:
    """
    Return (is_sensitive, suspicious_paths). Sensitive when any path token in
    the command is (a) under a system-sensitive prefix OR (b) outside every
    connected folder.
    """
    paths = _extract_paths_from_command(command)
    if not paths:
        return False, []
    connected = _connected_folders()
    suspicious: list[str] = []
    for p in paths:
        if _SYSTEM_SENSITIVE_PREFIX_RE.match(p):
            suspicious.append(p)
        elif _path_outside_connected(p, connected):
            suspicious.append(p)
    return bool(suspicious), suspicious


# --------------------------------------------------------------------------
# PreToolUse pre-gate (M-Lath-1 elevation + v1.2.2 S5 Bash extension).
# Without `permission_suggestions`, shape classification is the only signal
# for deciding whether a tool call is plausibly permission-risky.
# --------------------------------------------------------------------------

def _should_emit_pre_tool_use(tool_name: str, tool_input: dict) -> bool:
    """
    Decide whether PreToolUse should emit an advisory. Conservative: emit only
    for tools that empirically surface a dialog or boundary-check in Cowork,
    PLUS Bash commands that reference path tokens outside the connected
    workspace folders (S5 hotfix v1.2.2).

    File tools: Cowork's file-tool boundary check may reject paths outside
    connected folders (probe-confirmed 2026-05-13); advisory helps the DM
    surface why the next tool result failed.

    Cowork MCP: `request_cowork_directory` and other mcp__cowork__* calls may
    require approval; advisory helps the DM surface the dialog context.

    Bash: allow-listed trivial commands (no paths) stay suppressed; commands
    referencing system-sensitive prefixes (/etc, /var, /Library, etc.) or
    paths outside connected folders fire an advisory so the DM can surface
    the implication before the action runs.

    Other tools: suppress.
    """
    if _is_file_tool(tool_name):
        return True
    if _is_cowork_mcp_tool(tool_name):
        return True
    if _is_bash_tool(tool_name):
        command = tool_input.get("command", "") or ""
        sensitive, _ = _bash_path_sensitive(command)
        return sensitive
    return False


# --------------------------------------------------------------------------
# Advisory message composition.
# Each function returns (reason_slug, advisory_sentence).
# The advisory is plain-language — DM may surface it to the user verbatim,
# but is expected to wrap it in conversational voice.
#
# Observational tense only — no second-person prescriptive constructions
# ("you should", "we recommend you", "it's safe to", "you can trust") per
# DC-45 M-Pet-3.
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

    Used by the PermissionRequest path (which carries `permission_suggestions`).
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


def _compose_pre_tool_use_advisory(tool_name: str, tool_input: dict) -> tuple[str, str]:
    """
    Compose an advisory from `tool_input` shape alone (no `permission_suggestions`).
    Used by the PreToolUse path per M-Lath-1.
    """
    if _is_file_tool(tool_name):
        target = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("pattern") or "(no path)"
        return (
            "file-permission-required",
            f"The action would use {tool_name} on `{target}`. "
            f"If the path is outside the connected workspace folders, the file tool "
            f"may reject the action or surface a permission dialog.",
        )
    if _is_cowork_mcp_tool(tool_name):
        path_hint = tool_input.get("path") or tool_input.get("directory") or ""
        if tool_name == "mcp__cowork__request_cowork_directory" and path_hint:
            return (
                "cowork-mcp-approval",
                f"The action requests access to the directory `{path_hint}`. "
                f"The user will see a dialog; if approved, future tool calls in the "
                f"directory succeed in this session.",
            )
        return (
            "cowork-mcp-approval",
            f"The action needs approval for `{tool_name}`. The user will see a dialog.",
        )
    if _is_bash_tool(tool_name):
        command = tool_input.get("command", "") or ""
        _, paths = _bash_path_sensitive(command)
        if paths:
            path_summary = ", ".join(f"`{p}`" for p in paths[:3])
            if len(paths) > 3:
                path_summary += f" (+{len(paths) - 3} more)"
            return (
                "bash-path-sensitive",
                f"The action runs a shell command referencing {path_summary}. "
                f"The path is either in a system-sensitive location or outside the "
                f"connected workspace folders; the result may differ from what the "
                f"user expects.",
            )
    # Unreachable given the pre-gate, but safe default.
    return (
        "permission-required",
        f"User approval may be needed for `{tool_name}`.",
    )


# --------------------------------------------------------------------------
# PreToolUse output — JSON to stdout per documented schema.
# --------------------------------------------------------------------------

def _emit_pre_tool_use_output(tool_name: str, reason: str, tool_input: dict, advisory: str) -> None:
    """Emit hookSpecificOutput.additionalContext per Anthropic plugins-reference."""
    # tool_input may contain large content; cap for context safety.
    try:
        tool_input_repr = json.dumps(tool_input, ensure_ascii=False)
    except (TypeError, ValueError):
        tool_input_repr = str(tool_input)
    if len(tool_input_repr) > 500:
        tool_input_repr = tool_input_repr[:497] + "..."

    context = (
        f"[CORE advisory]\n"
        f"tool: {tool_name}\n"
        f"reason: {reason}\n"
        f"tool_input: {tool_input_repr}\n"
        f"advisory: {advisory}"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


# --------------------------------------------------------------------------
# Audit log — append-only, plain markdown for diff-readability.
# Written by the PermissionRequest path (carries `permission_suggestions`).
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
# Event-specific handlers.
# --------------------------------------------------------------------------

def _handle_pre_tool_use(tool_name: str, tool_input: dict) -> int:
    """PreToolUse path: shape-gated; emit hookSpecificOutput.additionalContext if risky."""
    if not _should_emit_pre_tool_use(tool_name, tool_input):
        return 0
    reason, advisory = _compose_pre_tool_use_advisory(tool_name, tool_input)
    _emit_pre_tool_use_output(tool_name, reason, tool_input, advisory)
    return 0


def _handle_permission_request(tool_name: str, tool_input: dict, suggestions: list) -> int:
    """PermissionRequest path: audit-log only in v1.2.1. Stdout block retired."""
    reason, advisory = _compose_advisory(tool_name, suggestions)
    _audit_log(tool_name, reason, tool_input, advisory)
    return 0


# --------------------------------------------------------------------------
# Main entry — branch on `hook_event_name`.
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
    event = payload.get("hook_event_name", "")

    if not tool_name:
        # Nothing useful to say without tool_name.
        return 0

    if event == "PreToolUse":
        return _handle_pre_tool_use(tool_name, tool_input)
    if event == "PermissionRequest":
        suggestions = payload.get("permission_suggestions", []) or []
        return _handle_permission_request(tool_name, tool_input, suggestions)

    # Unknown event — silent no-op. The hook is registered for two specific events;
    # any other invocation is harness drift and not our problem to surface.
    return 0


if __name__ == "__main__":
    sys.exit(main())
