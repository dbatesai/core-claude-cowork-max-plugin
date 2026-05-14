#!/usr/bin/env python3
"""
Unit test for permission_request.py augmentation hook (v1.2.1, DC-45).

Covers two registered events:
  - PermissionRequest — audit-log only. Stdout markers retired in v1.2.1
                        (synthesis §1.1: PermissionRequest "retained for audit-log-only").
                        Fires for file tools and MCP calls in Cowork; carries
                        `permission_suggestions` field (the only event that does).
  - PreToolUse        — emits hookSpecificOutput.additionalContext if the tool
                        is plausibly permission-risky per shape-based pre-gate
                        (M-Lath-1). Suppresses for Bash, WebFetch, etc.

Pay-to-play discipline assertions: no event path may print a decision verb.

Run:
    python3 scripts/test_permission_request.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parent / "permission_request.py"
_PY = sys.executable


# --------------------------------------------------------------------------
# Fixtures — PermissionRequest payloads (with permission_suggestions).
# Captured verbatim (minus session-id noise) from Q-F9-1 + v114 probes.
# --------------------------------------------------------------------------

PR_READ_OUTSIDE = {
    "session_id": "test-fixture",
    "transcript_path": "/tmp/test.jsonl",
    "cwd": "/tmp",
    "permission_mode": "default",
    "hook_event_name": "PermissionRequest",
    "tool_name": "Read",
    "tool_input": {"file_path": "/Users/dbates/.zshrc"},
    "permission_suggestions": [
        {
            "type": "addRules",
            "rules": [{"toolName": "Read", "ruleContent": "//Users/dbates/**"}],
            "behavior": "allow",
            "destination": "session",
        }
    ],
}

PR_COWORK_REQUEST_DIRECTORY = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "mcp__cowork__request_cowork_directory",
    "tool_input": {"path": "~/.core/"},
    "permission_suggestions": [
        {
            "type": "addRules",
            "rules": [{"toolName": "mcp__cowork__request_cowork_directory"}],
            "behavior": "allow",
            "destination": "localSettings",
        }
    ],
}

PR_WRITE_OUTSIDE = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "Write",
    "tool_input": {"file_path": "/Users/dbates/test-probe-target.md", "content": "hello"},
    "permission_suggestions": [
        {"type": "setMode", "mode": "acceptEdits", "destination": "session"},
        {"type": "addDirectories", "directories": ["/Users/dbates"], "destination": "session"},
    ],
}

PR_BASH = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "Bash",
    "tool_input": {"command": "date"},
    "permission_suggestions": [],
}

PR_GENERIC = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "WebFetch",
    "tool_input": {"url": "https://example.com"},
    "permission_suggestions": [],
}

PR_MISSING_TOOL_NAME = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_input": {},
    "permission_suggestions": [],
}


# --------------------------------------------------------------------------
# Fixtures — PreToolUse payloads (NO permission_suggestions field per v114
# probe findings 12/12 absent). Payload shape from `v114-probe-findings.md` §2.
# --------------------------------------------------------------------------

PTU_READ_OUTSIDE = {
    "session_id": "test-fixture",
    "transcript_path": "/tmp/test.jsonl",
    "cwd": "/tmp",
    "permission_mode": "default",
    "hook_event_name": "PreToolUse",
    "tool_name": "Read",
    "tool_input": {"file_path": "/Users/dbates/.zshrc"},
    "tool_use_id": "toolu_test_001",
}

PTU_WRITE_OUTSIDE = {
    "session_id": "test-fixture",
    "hook_event_name": "PreToolUse",
    "tool_name": "Write",
    "tool_input": {"file_path": "/Users/dbates/test-probe-target.md", "content": "hello"},
    "tool_use_id": "toolu_test_002",
}

PTU_COWORK_REQUEST_DIR = {
    "session_id": "test-fixture",
    "hook_event_name": "PreToolUse",
    "tool_name": "mcp__cowork__request_cowork_directory",
    "tool_input": {"path": "/Users/dbates/Desktop"},
    "tool_use_id": "toolu_test_003",
}

PTU_BASH = {
    "session_id": "test-fixture",
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "date -u"},
    "tool_use_id": "toolu_test_004",
}

PTU_WEBFETCH = {
    "session_id": "test-fixture",
    "hook_event_name": "PreToolUse",
    "tool_name": "WebFetch",
    "tool_input": {"url": "https://example.com"},
    "tool_use_id": "toolu_test_005",
}

PTU_UNKNOWN_EVENT = {
    "session_id": "test-fixture",
    "hook_event_name": "SessionStart",
    "tool_name": "Read",
    "tool_input": {"file_path": "/etc/hosts"},
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _run(payload: dict | None, *, is_cowork: bool = True, raw_stdin: str | None = None, data_dir: Path | None = None) -> subprocess.CompletedProcess:
    """Invoke the hook script as a subprocess; capture stdout/stderr."""
    env = os.environ.copy()
    env["CLAUDE_CODE_IS_COWORK"] = "1" if is_cowork else "0"
    if data_dir:
        env["CORE_DATA_DIR"] = str(data_dir)
    if raw_stdin is None:
        stdin_text = json.dumps(payload) if payload is not None else ""
    else:
        stdin_text = raw_stdin
    return subprocess.run(
        [_PY, str(_SCRIPT)],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _assert_in(needle: str, haystack: str, label: str) -> None:
    if needle not in haystack:
        print(f"FAIL: {label}: expected substring not found.")
        print(f"  expected: {needle!r}")
        print(f"  in: {haystack!r}")
        sys.exit(1)


def _assert_not_in(needle: str, haystack: str, label: str) -> None:
    if needle in haystack:
        print(f"FAIL: {label}: forbidden substring present.")
        print(f"  forbidden: {needle!r}")
        print(f"  in: {haystack!r}")
        sys.exit(1)


def _parse_hook_output(stdout: str, label: str) -> dict:
    """Parse JSON output and assert hookSpecificOutput shape."""
    stripped = stdout.strip()
    if not stripped:
        print(f"FAIL: {label}: expected JSON output, got empty.")
        sys.exit(1)
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as e:
        print(f"FAIL: {label}: stdout is not valid JSON ({e}).")
        print(f"  stdout: {stdout!r}")
        sys.exit(1)
    return obj


# --------------------------------------------------------------------------
# PermissionRequest path tests — audit-log only in v1.2.1.
# --------------------------------------------------------------------------

def test_pr_read_writes_audit_log_no_stdout() -> None:
    """PermissionRequest Read → audit log entry; no stdout block in v1.2.1."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PR_READ_OUTSIDE, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        _assert_not_in("[[CORE-PERMISSION-CONTEXT-BEGIN]]", r.stdout, "pr-read: stdout markers retired in v1.2.1")
        log = Path(td) / "logs" / "permission-events.md"
        assert log.is_file(), f"audit log not created at {log}"
        content = log.read_text(encoding="utf-8")
        _assert_in("Read", content, "pr-read: audit tool name")
        _assert_in("rule-grant-required", content, "pr-read: audit reason slug")
        _assert_in(".zshrc", content, "pr-read: audit tool_input captured")
    print("  PASS  test_pr_read_writes_audit_log_no_stdout")


def test_pr_cowork_mcp_writes_audit_log() -> None:
    """PermissionRequest mcp__cowork__request_cowork_directory → audit log."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PR_COWORK_REQUEST_DIRECTORY, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        log = Path(td) / "logs" / "permission-events.md"
        content = log.read_text(encoding="utf-8")
        _assert_in("mcp__cowork__request_cowork_directory", content, "pr-cowork: audit tool name")
        _assert_in("cowork-mcp-approval", content, "pr-cowork: audit reason slug")
    print("  PASS  test_pr_cowork_mcp_writes_audit_log")


def test_pr_write_picks_add_directories_in_audit() -> None:
    """PermissionRequest Write with setMode + addDirectories → addDirectories wins → outside-connected-folders."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PR_WRITE_OUTSIDE, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        log = Path(td) / "logs" / "permission-events.md"
        content = log.read_text(encoding="utf-8")
        _assert_in("Write", content, "pr-write: audit tool name")
        _assert_in("outside-connected-folders", content, "pr-write: audit reason (addDirectories priority)")
    print("  PASS  test_pr_write_picks_add_directories_in_audit")


def test_pr_bash_writes_audit_log() -> None:
    """PermissionRequest Bash with empty suggestions → audit log with bash-approval reason."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PR_BASH, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        log = Path(td) / "logs" / "permission-events.md"
        content = log.read_text(encoding="utf-8")
        _assert_in("Bash", content, "pr-bash: audit tool name")
        _assert_in("bash-approval", content, "pr-bash: audit reason slug")
    print("  PASS  test_pr_bash_writes_audit_log")


def test_pr_generic_writes_audit_log() -> None:
    """PermissionRequest unknown family + no suggestions → permission-required fallback in audit."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PR_GENERIC, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        log = Path(td) / "logs" / "permission-events.md"
        content = log.read_text(encoding="utf-8")
        _assert_in("WebFetch", content, "pr-generic: audit tool name")
        _assert_in("permission-required", content, "pr-generic: audit reason slug")
    print("  PASS  test_pr_generic_writes_audit_log")


# --------------------------------------------------------------------------
# PreToolUse path tests — hookSpecificOutput.additionalContext + shape gate.
# --------------------------------------------------------------------------

def test_ptu_file_read_emits_advisory_json() -> None:
    """PreToolUse Read (file tool) → JSON output with additionalContext."""
    r = _run(PTU_READ_OUTSIDE)
    assert r.returncode == 0, r.stderr
    obj = _parse_hook_output(r.stdout, "ptu-read")
    hso = obj.get("hookSpecificOutput", {})
    _assert_in("PreToolUse", hso.get("hookEventName", ""), "ptu-read: hookEventName")
    _assert_in("ask", hso.get("permissionDecision", ""), "ptu-read: permissionDecision is 'ask'")
    ctx = hso.get("additionalContext", "")
    _assert_in("tool: Read", ctx, "ptu-read: advisory names tool")
    _assert_in("file-permission-required", ctx, "ptu-read: reason slug")
    _assert_in(".zshrc", ctx, "ptu-read: tool_input target")
    print("  PASS  test_ptu_file_read_emits_advisory_json")


def test_ptu_file_write_emits_advisory_json() -> None:
    """PreToolUse Write → JSON additionalContext with file-permission-required."""
    r = _run(PTU_WRITE_OUTSIDE)
    assert r.returncode == 0, r.stderr
    obj = _parse_hook_output(r.stdout, "ptu-write")
    ctx = obj["hookSpecificOutput"]["additionalContext"]
    _assert_in("tool: Write", ctx, "ptu-write: tool name")
    _assert_in("file-permission-required", ctx, "ptu-write: reason slug")
    _assert_in("test-probe-target.md", ctx, "ptu-write: file_path in tool_input")
    print("  PASS  test_ptu_file_write_emits_advisory_json")


def test_ptu_cowork_mcp_emits_advisory_json() -> None:
    """PreToolUse mcp__cowork__request_cowork_directory → cowork-mcp-approval JSON."""
    r = _run(PTU_COWORK_REQUEST_DIR)
    assert r.returncode == 0, r.stderr
    obj = _parse_hook_output(r.stdout, "ptu-cowork-mcp")
    ctx = obj["hookSpecificOutput"]["additionalContext"]
    _assert_in("mcp__cowork__request_cowork_directory", ctx, "ptu-cowork-mcp: tool name")
    _assert_in("cowork-mcp-approval", ctx, "ptu-cowork-mcp: reason slug")
    _assert_in("/Users/dbates/Desktop", ctx, "ptu-cowork-mcp: path hint")
    print("  PASS  test_ptu_cowork_mcp_emits_advisory_json")


def test_ptu_bash_suppressed() -> None:
    """PreToolUse Bash → pre-gate suppresses (Cowork doesn't dialog Bash per probe)."""
    r = _run(PTU_BASH)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", f"ptu-bash: expected empty stdout (suppressed), got {r.stdout!r}"
    print("  PASS  test_ptu_bash_suppressed")


def test_ptu_unknown_tool_suppressed() -> None:
    """PreToolUse WebFetch / unknown tool → pre-gate suppresses."""
    r = _run(PTU_WEBFETCH)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", f"ptu-webfetch: expected empty stdout (suppressed), got {r.stdout!r}"
    print("  PASS  test_ptu_unknown_tool_suppressed")


def test_ptu_does_not_write_audit_log() -> None:
    """PreToolUse path is advisory-only; audit log is reserved for PermissionRequest."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PTU_WRITE_OUTSIDE, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        log = Path(td) / "logs" / "permission-events.md"
        assert not log.exists(), f"ptu-no-audit: PreToolUse should not write audit log; found {log}"
    print("  PASS  test_ptu_does_not_write_audit_log")


# --------------------------------------------------------------------------
# Defensive / both-event tests.
# --------------------------------------------------------------------------

def test_missing_tool_name_is_silent() -> None:
    """Payload without tool_name → silent no-op."""
    r = _run(PR_MISSING_TOOL_NAME)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", "missing-tool-name: expected empty stdout"
    print("  PASS  test_missing_tool_name_is_silent")


def test_not_cowork_is_silent_pr() -> None:
    """PermissionRequest, CLAUDE_CODE_IS_COWORK != "1" → silent (Claude Code CLI guard)."""
    with tempfile.TemporaryDirectory() as td:
        r = _run(PR_READ_OUTSIDE, is_cowork=False, data_dir=Path(td))
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "", "non-cowork-pr: expected empty stdout"
        log = Path(td) / "logs" / "permission-events.md"
        assert not log.exists(), "non-cowork-pr: should not write audit log"
    print("  PASS  test_not_cowork_is_silent_pr")


def test_not_cowork_is_silent_ptu() -> None:
    """PreToolUse, CLAUDE_CODE_IS_COWORK != "1" → silent."""
    r = _run(PTU_WRITE_OUTSIDE, is_cowork=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", "non-cowork-ptu: expected empty stdout"
    print("  PASS  test_not_cowork_is_silent_ptu")


def test_empty_stdin_is_silent() -> None:
    """No stdin payload → silent."""
    r = _run(None, raw_stdin="")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", "empty-stdin: expected empty stdout"
    print("  PASS  test_empty_stdin_is_silent")


def test_malformed_json_is_silent() -> None:
    """Malformed stdin → returncode 0, no output."""
    r = _run(None, raw_stdin="{not json")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", "malformed-json: expected empty stdout"
    print("  PASS  test_malformed_json_is_silent")


def test_unknown_event_is_silent() -> None:
    """Hook fires for an event we don't handle → silent no-op (no false advisory)."""
    r = _run(PTU_UNKNOWN_EVENT)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", "unknown-event: expected empty stdout"
    print("  PASS  test_unknown_event_is_silent")


def test_pay_to_play_no_decision_directives() -> None:
    """No event path may emit a decision directive (allow/deny/approve verbs)."""
    fixtures = [
        PR_READ_OUTSIDE, PR_COWORK_REQUEST_DIRECTORY, PR_WRITE_OUTSIDE, PR_BASH,
        PTU_READ_OUTSIDE, PTU_WRITE_OUTSIDE, PTU_COWORK_REQUEST_DIR,
    ]
    for fixture in fixtures:
        r = _run(fixture)
        for line in r.stdout.splitlines():
            lower = line.lower().lstrip()
            for forbidden in ("decision:", "approve:", "deny:"):
                if lower.startswith(forbidden):
                    print(f"FAIL: pay-to-play: forbidden directive: {line!r}")
                    sys.exit(1)
        # PreToolUse JSON: permissionDecision must be "ask", never "allow"/"deny".
        if r.stdout.strip().startswith("{"):
            try:
                obj = json.loads(r.stdout)
                pd = obj.get("hookSpecificOutput", {}).get("permissionDecision", "")
                if pd not in ("", "ask"):
                    print(f"FAIL: pay-to-play: permissionDecision={pd!r} (only 'ask' allowed)")
                    sys.exit(1)
            except json.JSONDecodeError:
                pass
    print("  PASS  test_pay_to_play_no_decision_directives")


def test_pretooluse_advisory_observational_tense() -> None:
    """M-Pet-3: advisory text uses observational tense, not second-person prescriptive."""
    forbidden_phrases = ["you should", "we recommend you", "it's safe to", "you can trust"]
    for fixture in (PTU_READ_OUTSIDE, PTU_WRITE_OUTSIDE, PTU_COWORK_REQUEST_DIR):
        r = _run(fixture)
        if not r.stdout.strip():
            continue
        obj = _parse_hook_output(r.stdout, "tense-check")
        ctx = obj.get("hookSpecificOutput", {}).get("additionalContext", "").lower()
        for phrase in forbidden_phrases:
            if phrase in ctx:
                print(f"FAIL: m-pet-3: prescriptive phrase {phrase!r} in advisory.")
                print(f"  advisory: {ctx!r}")
                sys.exit(1)
    print("  PASS  test_pretooluse_advisory_observational_tense")


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

TESTS = [
    # PermissionRequest (audit-log only)
    test_pr_read_writes_audit_log_no_stdout,
    test_pr_cowork_mcp_writes_audit_log,
    test_pr_write_picks_add_directories_in_audit,
    test_pr_bash_writes_audit_log,
    test_pr_generic_writes_audit_log,
    # PreToolUse (advisory JSON + shape gate)
    test_ptu_file_read_emits_advisory_json,
    test_ptu_file_write_emits_advisory_json,
    test_ptu_cowork_mcp_emits_advisory_json,
    test_ptu_bash_suppressed,
    test_ptu_unknown_tool_suppressed,
    test_ptu_does_not_write_audit_log,
    # Defensive
    test_missing_tool_name_is_silent,
    test_not_cowork_is_silent_pr,
    test_not_cowork_is_silent_ptu,
    test_empty_stdin_is_silent,
    test_malformed_json_is_silent,
    test_unknown_event_is_silent,
    # Discipline
    test_pay_to_play_no_decision_directives,
    test_pretooluse_advisory_observational_tense,
]


def main() -> int:
    print(f"Running {len(TESTS)} tests for permission_request.py (v1.2.1)...\n")
    for t in TESTS:
        t()
    print(f"\nAll {len(TESTS)} tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
