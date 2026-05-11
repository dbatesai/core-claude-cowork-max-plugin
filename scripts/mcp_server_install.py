#!/usr/bin/env python3
"""
CORE Cowork Max plugin — capability probe + MCP server installer.

Three-level fallback ladder (per David's instruction 2026-05-10):

  Level 1 (best):  Node.js + CORE MCP server installed and responding
                   → live dashboard via mcp__core__* tools, no per-session click

  Level 2 (good):  Node.js missing, MCP server failed, or registration unsupported
                   → DM falls back to mcp__cowork__request_cowork_directory + file tools
                   → still a live dashboard; per-session approval required

  Level 3 (FYI):   Even fallback path unavailable (e.g., user denies request_cowork_directory)
                   → no live artifact; DM informs user via chat with install instructions

Capability is persisted to ~/.core/capability.json. The session_start.py hook reads it
and emits a marker to the DM. Re-probing happens only when level < 1 or
CORE_CAPABILITY_REPROBE=1 is set.

Note: this script does NOT install Python venv anymore. The MCP server is Node.js;
this script only registers it. Python is still the hook runtime.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import core_helpers as ch  # noqa: E402


PLUGIN_ROOT = _SCRIPT_DIR.parent
MCP_SERVER_PATH = (PLUGIN_ROOT / "mcp-server-node" / "server.mjs").resolve()
CAPABILITY_FILE = ch.CORE_DATA_DIR / "capability.json"
RESTART_FLAG = ch.CORE_DATA_DIR / "needs-app-restart"
INSTALL_LOG = ch.CORE_DATA_DIR / "mcp-install-log.md"
BACKUP_DIR = ch.CORE_DATA_DIR / "claude-desktop-config-backups"


# --------------------------------------------------------------------------
# Capability state
# --------------------------------------------------------------------------

def _write_capability(level: int, reason: str, **extra) -> None:
    payload = {
        "level": level,
        "last_probed": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        **extra,
    }
    try:
        CAPABILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        CAPABILITY_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as e:
        ch.log_warn(f"capability write failed: {e}")


def _read_capability() -> dict | None:
    if not CAPABILITY_FILE.is_file():
        return None
    try:
        return json.loads(CAPABILITY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_install_log(msg: str) -> None:
    try:
        INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with INSTALL_LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


# --------------------------------------------------------------------------
# Node detection
# --------------------------------------------------------------------------

def _find_node() -> tuple[str, str] | None:
    """Returns (node_executable_path, version_string) or None if not available."""
    node_path = shutil.which("node")
    if not node_path:
        return None
    try:
        result = subprocess.run(
            [node_path, "--version"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if result.returncode == 0:
            return (node_path, result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


# --------------------------------------------------------------------------
# MCP server handshake probe (end-to-end protocol verification, not just file exists)
# --------------------------------------------------------------------------

def _probe_mcp_server(node_path: str) -> tuple[bool, str]:
    """
    Start the MCP server, send initialize, read response, time out after 3s.
    Returns (success, reason).
    """
    if not MCP_SERVER_PATH.is_file():
        return False, f"server.mjs not found at {MCP_SERVER_PATH}"

    try:
        proc = subprocess.Popen(
            [node_path, str(MCP_SERVER_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as e:
        return False, f"failed to spawn node: {e}"

    init_msg = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
    try:
        proc.stdin.write(init_msg)
        proc.stdin.flush()

        # Wait up to 3s for a response line
        try:
            stdout, _stderr = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return False, "initialize handshake timed out (3s)"

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                continue
            if response.get("id") == 1 and response.get("result", {}).get("protocolVersion"):
                return True, f"protocol {response['result']['protocolVersion']}"
            if response.get("error"):
                return False, f"initialize returned error: {response['error']}"

        return False, "no valid initialize response received"
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except OSError:
                pass


# --------------------------------------------------------------------------
# Config registration
# --------------------------------------------------------------------------

def _backup_config(config_path: Path) -> None:
    if config_path.is_file():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        try:
            shutil.copy2(config_path, BACKUP_DIR / f"config-{ts}.json")
        except OSError as e:
            ch.log_warn(f"config backup failed: {e}")


def _register_in_config(node_path: str, config_path: Path) -> bool:
    """
    Idempotent merge of 'core' entry into mcpServers.
    Returns True if registration is now in place.
    """
    new_entry = {
        "command": node_path,
        "args": [str(MCP_SERVER_PATH)],
    }

    try:
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                ch.log_warn("existing config invalid JSON; initializing fresh")
                config = {}
        else:
            config = {}
    except OSError as e:
        ch.log_warn(f"config read error: {e}")
        return False

    if not isinstance(config, dict):
        config = {}
    config.setdefault("mcpServers", {})

    if config["mcpServers"].get("core") == new_entry:
        print("[mcp-install] CORE MCP server already registered correctly; no change.")
        return True

    config["mcpServers"]["core"] = new_entry
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except OSError as e:
        ch.log_warn(f"config write failed: {e}")
        return False

    print(f"[mcp-install] CORE MCP server registered: {node_path} {MCP_SERVER_PATH}")
    try:
        RESTART_FLAG.write_text(
            "CORE MCP server was registered. Restart Cowork "
            "(Cmd+Q on macOS, or close-and-reopen on Windows) to activate the live dashboard.\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return True


# --------------------------------------------------------------------------
# Main probe + install flow
# --------------------------------------------------------------------------

def main() -> int:
    # Honor stable Level 1 state unless re-probe explicitly requested
    existing = _read_capability()
    reprobe = os.environ.get("CORE_CAPABILITY_REPROBE", "0") == "1"
    if existing and existing.get("level") == 1 and not reprobe:
        print(f"[mcp-install] capability.json reports level 1 since {existing.get('last_probed')}; skipping re-probe (set CORE_CAPABILITY_REPROBE=1 to override).")
        return 0

    config_path = ch.claude_config_path()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)

    # ---- Step 1: Detect Node.js ----
    node_info = _find_node()
    if not node_info:
        reason = "node not in PATH — install Node.js 18+ from nodejs.org to enable the live dashboard"
        _write_capability(2, reason)
        _write_install_log(
            f"## {datetime.now(timezone.utc).isoformat()}\nOS: {ch.SYSTEM}\nResult: Node missing → capability level 2 (file-tool fallback)\n"
        )
        print(f"[mcp-install] {reason}")
        return 0  # Not an error — Level 2 is a valid fallback

    node_path, node_version = node_info
    print(f"[mcp-install] Found Node.js: {node_path} ({node_version})")

    # ---- Step 2: Probe MCP server end-to-end (initialize handshake) ----
    handshake_ok, handshake_reason = _probe_mcp_server(node_path)
    if not handshake_ok:
        reason = f"MCP server handshake failed: {handshake_reason}"
        _write_capability(2, reason, node_version=node_version, node_path=node_path)
        _write_install_log(
            f"## {datetime.now(timezone.utc).isoformat()}\nOS: {ch.SYSTEM}\nNode: {node_version}\nResult: MCP handshake failed → capability level 2 (file-tool fallback)\nReason: {handshake_reason}\n"
        )
        print(f"[mcp-install] {reason}")
        return 0  # Level 2 fallback

    print(f"[mcp-install] MCP server handshake OK ({handshake_reason})")

    # ---- Step 3: Backup + register in claude_desktop_config.json ----
    if ch.DRY_RUN:
        print(f"[mcp-install] CORE_DRY_RUN=1 — skipping config write to {config_path}")
        _write_capability(
            1,
            "MCP server registered and verified (dry-run; config NOT written)",
            node_version=node_version,
            node_path=node_path,
            server_path=str(MCP_SERVER_PATH),
            config_path_target=str(config_path),
            dry_run=True,
        )
        return 0

    _backup_config(config_path)
    if not _register_in_config(node_path, config_path):
        reason = "MCP server works but config registration failed"
        _write_capability(2, reason, node_version=node_version, node_path=node_path)
        _write_install_log(
            f"## {datetime.now(timezone.utc).isoformat()}\nResult: config write failed → level 2\nConfig: {config_path}\n"
        )
        return 1

    # ---- Step 4: Persist Level 1 capability ----
    _write_capability(
        1,
        "MCP server registered and verified",
        node_version=node_version,
        node_path=node_path,
        server_path=str(MCP_SERVER_PATH),
        config_path=str(config_path),
    )
    _write_install_log(
        f"## {datetime.now(timezone.utc).isoformat()}\nOS: {ch.SYSTEM}\nNode: {node_version}\nResult: capability level 1 (MCP-backed live dashboard)\nServer: {MCP_SERVER_PATH}\nConfig: {config_path}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
