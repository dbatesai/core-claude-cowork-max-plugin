#!/usr/bin/env python3
"""
Unit test for permission_request.py augmentation hook.

Simulates the four PermissionRequest payloads captured in the Q-F9-1 probe
2026-05-13 (outputs/2026-05-12/q-f9-1-findings.md in the CORE dev repo) plus
a few synthetic edge cases. Spawns permission_request.py as a subprocess with
CLAUDE_CODE_IS_COWORK=1 set and a payload piped to stdin; asserts the stdout
emission contains the expected [[CORE-PERMISSION-CONTEXT-BEGIN/END]] block
with the right tool_name, reason slug, and advisory shape.

Pay-to-play discipline assertions: the hook must NEVER print "approve" or
"deny" or "decision"; output is structured context only.

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
# Fixtures — payloads captured verbatim (minus session-id noise) from Q-F9-1.
# --------------------------------------------------------------------------

PAYLOAD_READ_OUTSIDE_WORKSPACE = {
    "session_id": "test-fixture",
    "transcript_path": "/tmp/test.jsonl",
    "cwd": "/tmp",
    "permission_mode": "default",
    "effort": {"level": "xhigh"},
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

PAYLOAD_COWORK_REQUEST_DIRECTORY = {
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

PAYLOAD_WRITE_OUTSIDE_WORKSPACE = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "Write",
    "tool_input": {"file_path": "/Users/dbates/test-probe-target.md", "content": "hello"},
    "permission_suggestions": [
        {"type": "setMode", "mode": "acceptEdits", "destination": "session"},
        {"type": "addDirectories", "directories": ["/Users/dbates"], "destination": "session"},
    ],
}

PAYLOAD_BASH = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "Bash",
    "tool_input": {"command": "date"},
    "permission_suggestions": [],
}

PAYLOAD_GENERIC_NO_SUGGESTIONS = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_name": "WebFetch",
    "tool_input": {"url": "https://example.com"},
    "permission_suggestions": [],
}

PAYLOAD_MISSING_TOOL_NAME = {
    "session_id": "test-fixture",
    "hook_event_name": "PermissionRequest",
    "tool_input": {},
    "permission_suggestions": [],
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


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_read_outside_workspace() -> None:
    """Read outside workspace → addRules suggestion → rule-grant advisory."""
    r = _run(PAYLOAD_READ_OUTSIDE_WORKSPACE)
    assert r.returncode == 0, r.stderr
    _assert_in("[[CORE-PERMISSION-CONTEXT-BEGIN]]", r.stdout, "read: begin marker")
    _assert_in("[[CORE-PERMISSION-CONTEXT-END]]", r.stdout, "read: end marker")
    _assert_in("tool: Read", r.stdout, "read: tool name")
    _assert_in("reason: rule-grant-required", r.stdout, "read: reason slug")
    _assert_in("/Users/dbates/.zshrc", r.stdout, "read: tool_input contains file path")
    _assert_in("advisory: ", r.stdout, "read: advisory field present")
    print("  PASS  test_read_outside_workspace")


def test_cowork_mcp_request_directory() -> None:
    """mcp__cowork__request_cowork_directory → addRules → cowork-mcp-approval."""
    r = _run(PAYLOAD_COWORK_REQUEST_DIRECTORY)
    assert r.returncode == 0, r.stderr
    _assert_in("tool: mcp__cowork__request_cowork_directory", r.stdout, "cowork: tool name")
    _assert_in("reason: cowork-mcp-approval", r.stdout, "cowork: reason slug")
    _assert_in("user will see a dialog", r.stdout, "cowork: advisory mentions dialog")
    print("  PASS  test_cowork_mcp_request_directory")


def test_write_outside_workspace_picks_add_directories() -> None:
    """Write with setMode + addDirectories → addDirectories wins priority."""
    r = _run(PAYLOAD_WRITE_OUTSIDE_WORKSPACE)
    assert r.returncode == 0, r.stderr
    _assert_in("tool: Write", r.stdout, "write: tool name")
    _assert_in("reason: outside-connected-folders", r.stdout, "write: reason slug (addDirectories wins)")
    _assert_in("/Users/dbates", r.stdout, "write: advisory mentions the directory")
    _assert_in("request_cowork_directory", r.stdout, "write: advisory names request_cowork_directory")
    print("  PASS  test_write_outside_workspace_picks_add_directories")


def test_bash_no_suggestions() -> None:
    """Bash with empty suggestions → bash-approval generic advisory."""
    r = _run(PAYLOAD_BASH)
    assert r.returncode == 0, r.stderr
    _assert_in("tool: Bash", r.stdout, "bash: tool name")
    _assert_in("reason: bash-approval", r.stdout, "bash: reason slug")
    print("  PASS  test_bash_no_suggestions")


def test_generic_tool_no_suggestions() -> None:
    """Unknown tool family with no suggestions → permission-required fallback."""
    r = _run(PAYLOAD_GENERIC_NO_SUGGESTIONS)
    assert r.returncode == 0, r.stderr
    _assert_in("tool: WebFetch", r.stdout, "generic: tool name")
    _assert_in("reason: permission-required", r.stdout, "generic: reason slug")
    print("  PASS  test_generic_tool_no_suggestions")


def test_missing_tool_name_is_silent() -> None:
    """Payload without tool_name → hook emits nothing (no advisory possible)."""
    r = _run(PAYLOAD_MISSING_TOOL_NAME)
    assert r.returncode == 0, r.stderr
    _assert_not_in("[[CORE-PERMISSION-CONTEXT-BEGIN]]", r.stdout, "missing-tool: no context block")
    print("  PASS  test_missing_tool_name_is_silent")


def test_not_cowork_is_silent() -> None:
    """CLAUDE_CODE_IS_COWORK != "1" → hook does nothing (CLI degradation guard)."""
    r = _run(PAYLOAD_READ_OUTSIDE_WORKSPACE, is_cowork=False)
    assert r.returncode == 0, r.stderr
    _assert_not_in("[[CORE-PERMISSION-CONTEXT-BEGIN]]", r.stdout, "non-cowork: no context block")
    print("  PASS  test_not_cowork_is_silent")


def test_empty_stdin_is_silent() -> None:
    """No stdin payload → hook returns 0 silently (defensive)."""
    r = _run(None, raw_stdin="")
    assert r.returncode == 0, r.stderr
    _assert_not_in("[[CORE-PERMISSION-CONTEXT-BEGIN]]", r.stdout, "empty-stdin: no context block")
    print("  PASS  test_empty_stdin_is_silent")


def test_malformed_json_is_silent() -> None:
    """Malformed stdin → hook returns 0 + log_warn, no context block."""
    r = _run(None, raw_stdin="{not json")
    assert r.returncode == 0, r.stderr
    _assert_not_in("[[CORE-PERMISSION-CONTEXT-BEGIN]]", r.stdout, "malformed-json: no context block")
    print("  PASS  test_malformed_json_is_silent")


def test_pay_to_play_no_decision_words() -> None:
    """Pay-to-play discipline: stdout MUST NOT contain decision verbs."""
    for fixture in (PAYLOAD_READ_OUTSIDE_WORKSPACE, PAYLOAD_COWORK_REQUEST_DIRECTORY,
                    PAYLOAD_WRITE_OUTSIDE_WORKSPACE, PAYLOAD_BASH):
        r = _run(fixture)
        for verb in ("approve", "deny", "decision", "block", "auto-approve"):
            # Tolerance: "approval" (noun) is allowed; only verb forms are forbidden.
            # Check that no line starts a decision directive.
            for line in r.stdout.splitlines():
                lower = line.lower()
                if lower.startswith("decision:") or lower.startswith("approve:") or lower.startswith("deny:"):
                    print(f"FAIL: pay-to-play: forbidden decision directive in output: {line!r}")
                    sys.exit(1)
    print("  PASS  test_pay_to_play_no_decision_words")


def test_audit_log_writes() -> None:
    """Audit log must capture the event under CORE_DATA_DIR/logs/."""
    with tempfile.TemporaryDirectory() as td:
        data_dir = Path(td)
        r = _run(PAYLOAD_READ_OUTSIDE_WORKSPACE, data_dir=data_dir)
        assert r.returncode == 0, r.stderr
        log = data_dir / "logs" / "permission-events.md"
        assert log.is_file(), f"audit log not created at {log}"
        content = log.read_text(encoding="utf-8")
        _assert_in("Read", content, "audit: tool name")
        _assert_in("rule-grant-required", content, "audit: reason slug")
        _assert_in(".zshrc", content, "audit: tool_input captured")
    print("  PASS  test_audit_log_writes")


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

TESTS = [
    test_read_outside_workspace,
    test_cowork_mcp_request_directory,
    test_write_outside_workspace_picks_add_directories,
    test_bash_no_suggestions,
    test_generic_tool_no_suggestions,
    test_missing_tool_name_is_silent,
    test_not_cowork_is_silent,
    test_empty_stdin_is_silent,
    test_malformed_json_is_silent,
    test_pay_to_play_no_decision_words,
    test_audit_log_writes,
]


def main() -> int:
    print(f"Running {len(TESTS)} tests for permission_request.py...\n")
    for t in TESTS:
        t()
    print(f"\nAll {len(TESTS)} tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
