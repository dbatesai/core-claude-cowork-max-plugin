#!/usr/bin/env bash
# Auto-register the bundled CORE MCP server in claude_desktop_config.json.
# Idempotent: existing MCP entries preserved; CORE entry added or updated.
# Creates an isolated venv at ~/.core/mcp-venv/ and installs fastmcp + the
# bundled core-mcp package into it. Registers the venv python in the config.
# See §3.1 and §12 of the max plugin spec.

set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/core-helpers.sh"

CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
BACKUP_DIR="$CORE_DATA_DIR/claude-desktop-config-backups"
LOG="$CORE_DATA_DIR/mcp-install-log.md"
RESTART_FLAG="$CORE_DATA_DIR/needs-app-restart"
VENV_DIR="$CORE_DATA_DIR/mcp-venv"
MCP_SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/mcp-server"

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG")"

# --------------------------------------------------------------------------
# Step 1: Set up isolated Python venv for CORE MCP server
# --------------------------------------------------------------------------

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

create_venv() {
  echo "[mcp-install] Creating venv at $VENV_DIR ..."
  python3 -m venv "$VENV_DIR" 2>&1 || {
    core_log_warn "mcp-server-install: venv creation failed; MCP server registration skipped"
    return 1
  }
  return 0
}

install_deps() {
  echo "[mcp-install] Installing fastmcp + core-mcp into venv ..."
  "$VENV_PIP" install --quiet --upgrade pip 2>&1 || \
    core_log_warn "mcp-server-install: pip upgrade failed (non-fatal)"
  "$VENV_PIP" install --quiet "fastmcp>=2.0,<3" 2>&1 || {
    core_log_warn "mcp-server-install: fastmcp install failed"
    return 1
  }
  "$VENV_PIP" install --quiet -e "$MCP_SERVER_DIR" 2>&1 || {
    core_log_warn "mcp-server-install: core-mcp install failed"
    return 1
  }
  return 0
}

# Create venv if missing
if [ ! -x "$VENV_PYTHON" ]; then
  create_venv || exit 1
fi

# Verify deps are installed; install if missing
if ! "$VENV_PYTHON" -c "import fastmcp, core_mcp.server" 2>/dev/null; then
  install_deps || {
    core_log_warn "mcp-server-install: dependency installation failed; will retry next session"
    # Continue to write the registration anyway — next session may succeed
  }
fi

# Verify import works post-install
if "$VENV_PYTHON" -c "import core_mcp.server" 2>/dev/null; then
  echo "[mcp-install] venv ready: $VENV_PYTHON"
  VENV_READY=1
else
  core_log_warn "mcp-server-install: core_mcp import still failing after install attempts"
  VENV_READY=0
fi

# --------------------------------------------------------------------------
# Step 2: Backup existing claude_desktop_config.json
# --------------------------------------------------------------------------

if [ -f "$CONFIG_FILE" ]; then
  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  cp "$CONFIG_FILE" "$BACKUP_DIR/config-$TS.json"
fi

# --------------------------------------------------------------------------
# Step 3: Idempotent merge of CORE MCP entry into config
# --------------------------------------------------------------------------

VENV_PYTHON_ABS="$VENV_PYTHON" \
MCP_SERVER_DIR_ABS="$MCP_SERVER_DIR" \
CONFIG_FILE_ABS="$CONFIG_FILE" \
RESTART_FLAG_ABS="$RESTART_FLAG" \
python3 <<'PYEOF'
import json, os, sys
from pathlib import Path

config_path = Path(os.environ["CONFIG_FILE_ABS"])
venv_python = os.environ["VENV_PYTHON_ABS"]
mcp_server_dir = os.environ["MCP_SERVER_DIR_ABS"]
restart_flag_path = Path(os.environ["RESTART_FLAG_ABS"])

# Load or initialize config
if config_path.exists():
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        print("[mcp-install] WARNING: existing config not valid JSON; initializing fresh.", file=sys.stderr)
        config = {}
else:
    config = {}

config.setdefault("mcpServers", {})
existing = config["mcpServers"].get("core")

new_entry = {
    "command": venv_python,
    "args": ["-m", "core_mcp.server"],
    "cwd": mcp_server_dir,
}

if existing == new_entry:
    print("[mcp-install] CORE MCP server already registered correctly; no change.")
    sys.exit(0)

config["mcpServers"]["core"] = new_entry
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(config, indent=2))
print(f"[mcp-install] CORE MCP server registered: {venv_python} -m core_mcp.server")

# Restart flag (Cowork loads claude_desktop_config.json at app start)
restart_flag_path.write_text(
    "CORE MCP server was registered. Quit Cowork (Cmd+Q) and reopen to activate live-data dashboard.\n"
)
print("[mcp-install] Restart flag written")
PYEOF

INSTALL_EXIT=$?

# --------------------------------------------------------------------------
# Step 4: Audit log entry
# --------------------------------------------------------------------------

{
  printf '## %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'MCP install check ran. Exit: %s, venv ready: %s\n' "$INSTALL_EXIT" "$VENV_READY"
  printf 'Venv path: %s\n' "$VENV_PYTHON"
  printf 'MCP server dir: %s\n' "$MCP_SERVER_DIR"
  printf 'Config backup dir: %s\n\n' "$BACKUP_DIR"
} >> "$LOG" 2>/dev/null || true

exit $INSTALL_EXIT
