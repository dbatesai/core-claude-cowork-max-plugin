#!/usr/bin/env python3
"""
CORE Cowork Max plugin — MCP server installer (cross-platform Python).

Idempotent. Each session start:
  1. Creates an isolated venv at ~/.core/mcp-venv/ if missing.
  2. Installs fastmcp + the bundled core-mcp package into it.
  3. Registers the venv python in claude_desktop_config.json
     (per-OS path: macOS Application Support / Windows AppData / Linux .config).
  4. Writes a needs-app-restart flag if the registration changed.

Audit log: ~/.core/mcp-install-log.md
Config backups: ~/.core/claude-desktop-config-backups/
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import venv
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import core_helpers as ch  # noqa: E402


VENV_DIR = ch.CORE_DATA_DIR / "mcp-venv"
MCP_SERVER_DIR = (_SCRIPT_DIR.parent / "mcp-server").resolve()
RESTART_FLAG = ch.CORE_DATA_DIR / "needs-app-restart"
INSTALL_LOG = ch.CORE_DATA_DIR / "mcp-install-log.md"
BACKUP_DIR = ch.CORE_DATA_DIR / "claude-desktop-config-backups"


def _write_log(msg: str) -> None:
    try:
        with INSTALL_LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def _ensure_venv() -> bool:
    if ch.venv_python(VENV_DIR).is_file():
        return True
    print(f"[mcp-install] Creating venv at {VENV_DIR} ...")
    try:
        venv.EnvBuilder(with_pip=True, clear=False, upgrade_deps=False).create(VENV_DIR)
        return True
    except Exception as e:
        ch.log_warn(f"venv creation failed: {e}")
        return False


def _deps_installed() -> bool:
    python = ch.venv_python(VENV_DIR)
    if not python.is_file():
        return False
    try:
        result = subprocess.run(
            [str(python), "-c", "import fastmcp, core_mcp.server"],
            capture_output=True, text=True, check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def _install_deps() -> bool:
    pip = ch.venv_pip(VENV_DIR)
    if not pip.is_file():
        # Fallback: use python -m pip if pip executable wasn't created
        python = ch.venv_python(VENV_DIR)
        pip_cmd = [str(python), "-m", "pip"]
    else:
        pip_cmd = [str(pip)]

    print("[mcp-install] Installing fastmcp + core-mcp into venv ...")
    try:
        subprocess.run(pip_cmd + ["install", "--quiet", "--upgrade", "pip"],
                       check=False, capture_output=True)
        result = subprocess.run(
            pip_cmd + ["install", "--quiet", "fastmcp>=2.0,<3"],
            check=False, capture_output=True, text=True,
        )
        if result.returncode != 0:
            ch.log_warn(f"fastmcp install failed: {result.stderr[:300]}")
            return False
        result = subprocess.run(
            pip_cmd + ["install", "--quiet", "-e", str(MCP_SERVER_DIR)],
            check=False, capture_output=True, text=True,
        )
        if result.returncode != 0:
            ch.log_warn(f"core-mcp install failed: {result.stderr[:300]}")
            return False
        return True
    except OSError as e:
        ch.log_warn(f"pip invocation failed: {e}")
        return False


def _backup_config(config_path: Path) -> None:
    if config_path.is_file():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        try:
            shutil.copy2(config_path, BACKUP_DIR / f"config-{ts}.json")
        except OSError as e:
            ch.log_warn(f"config backup failed: {e}")


def _merge_config(config_path: Path, venv_python_path: Path) -> bool:
    """
    Idempotent merge: insert/update the 'core' entry in mcpServers.
    Returns True if registration is now correct (changed or already-correct).
    """
    try:
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                ch.log_warn("existing claude_desktop_config.json invalid JSON; initializing fresh")
                config = {}
        else:
            config = {}
    except OSError as e:
        ch.log_warn(f"config read error: {e}")
        return False

    if not isinstance(config, dict):
        config = {}
    config.setdefault("mcpServers", {})

    new_entry = {
        "command": str(venv_python_path),
        "args": ["-m", "core_mcp.server"],
        "cwd": str(MCP_SERVER_DIR),
    }

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

    print(f"[mcp-install] CORE MCP server registered: {venv_python_path}")
    try:
        RESTART_FLAG.write_text(
            "CORE MCP server was registered. Quit Cowork (Cmd+Q on macOS, "
            "or close-and-reopen on Windows) and reopen to activate live-data dashboard.\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return True


def main() -> int:
    config_path = ch.claude_config_path()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)

    venv_ready = _ensure_venv()
    if not venv_ready:
        _write_log(f"## {datetime.now(timezone.utc).isoformat()}  venv creation FAILED")
        return 1

    if not _deps_installed():
        if not _install_deps():
            _write_log(f"## {datetime.now(timezone.utc).isoformat()}  dep install FAILED; venv exists but missing fastmcp/core_mcp")
            return 1

    if not _deps_installed():
        _write_log(f"## {datetime.now(timezone.utc).isoformat()}  post-install verify FAILED")
        return 1

    _backup_config(config_path)
    if not _merge_config(config_path, ch.venv_python(VENV_DIR)):
        _write_log(f"## {datetime.now(timezone.utc).isoformat()}  config merge FAILED at {config_path}")
        return 1

    _write_log(
        f"## {datetime.now(timezone.utc).isoformat()}\n"
        f"OS: {ch.SYSTEM}\nConfig: {config_path}\nVenv python: {ch.venv_python(VENV_DIR)}\n"
        f"MCP server dir: {MCP_SERVER_DIR}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
