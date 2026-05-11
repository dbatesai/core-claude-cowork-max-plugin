#!/usr/bin/env bash
# Auto-register the bundled CORE MCP server in claude_desktop_config.json.
# Idempotent: existing MCP entries preserved; CORE entry added or updated.
# See §3.1 and §12 of the max plugin spec.

set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/core-helpers.sh"

CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
BACKUP_DIR="$CORE_DATA_DIR/claude-desktop-config-backups"
LOG="$CORE_DATA_DIR/mcp-install-log.md"
RESTART_FLAG="$CORE_DATA_DIR/needs-app-restart"

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG")"

# Backup current config (no-op if file is absent)
if [ -f "$CONFIG_FILE" ]; then
  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  cp "$CONFIG_FILE" "$BACKUP_DIR/config-$TS.json"
fi

# Idempotent merge using python3 (jq not always available on end-user Macs)
python3 <<PYEOF
import json, os, sys
from pathlib import Path

config_path = Path(os.path.expanduser("$CONFIG_FILE"))
plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
mcp_server_dir = os.path.join(plugin_root, "mcp-server") if plugin_root else ""

if not mcp_server_dir or not os.path.isdir(mcp_server_dir):
    # Fallback: script is in scripts/, mcp-server is sibling
    script_dir = os.path.dirname(os.path.abspath("$0"))
    mcp_server_dir = os.path.join(os.path.dirname(script_dir), "mcp-server")

# Load or initialize config
if config_path.exists():
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        print("[mcp-install] WARNING: existing config is not valid JSON; initializing fresh.", file=sys.stderr)
        config = {}
else:
    config = {}

config.setdefault("mcpServers", {})
existing = config["mcpServers"].get("core")

new_entry = {
    "command": "python3",
    "args": ["-m", "core_mcp.server"],
    "cwd": mcp_server_dir,
}

if existing == new_entry:
    print("[mcp-install] CORE MCP server already registered correctly; no change.")
    sys.exit(0)

# Write updated config
config["mcpServers"]["core"] = new_entry
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(config, indent=2))
print(f"[mcp-install] CORE MCP server registered at {mcp_server_dir}")

# Write the needs-restart flag (Q4 finding: Cowork loads config at app start, not session start)
needs_restart_path = Path(os.path.expanduser("$RESTART_FLAG"))
needs_restart_path.write_text(
    "CORE MCP server was registered. Quit Cowork (Cmd+Q) and reopen to activate live-data dashboard.\n"
)
print("[mcp-install] Restart flag written to ~/.core/needs-app-restart")
PYEOF

INSTALL_EXIT=$?

# Audit log entry
{
  printf '## %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'MCP install check ran. Exit: %s\n' "$INSTALL_EXIT"
  printf 'Backup dir: %s\n\n' "$BACKUP_DIR"
} >> "$LOG" 2>/dev/null || true

exit $INSTALL_EXIT
