#!/usr/bin/env bash
# CORE Cowork Max plugin — SessionStart hook
# Runs on macOS host with full filesystem privilege.
# Outputs markers to stdout; Cowork injects stdout into the DM's session context.

set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/core-helpers.sh"

# Standard bootstrap: skill injection, dm-profile, project state, path-semantics hints.
# Improvement-queue application is handled explicitly below with QUEUE_CAP check (M-MAX-15).
core_session_start_bootstrap_minus_queue || exit 1

# --------------------------------------------------------------------------
# Improvement queue — TM-2 mitigation with QUEUE_CAP check (M-MAX-15)
# --------------------------------------------------------------------------

QUEUE="$CORE_DATA_DIR/improvement-queue.md"
QUEUE_LOG_DIR="$CORE_DATA_DIR/improvement-log"
mkdir -p "$QUEUE_LOG_DIR" 2>/dev/null || true

if [ -f "$QUEUE" ]; then
  QUEUE_ENTRIES="$(grep -c '^## ' "$QUEUE" 2>/dev/null || echo 0)"
  QUEUE_CAP="${CORE_IMPROVEMENT_QUEUE_CAP:-5}"

  if [ "$QUEUE_ENTRIES" -gt "$QUEUE_CAP" ]; then
    # Over-cap: skip auto-apply, surface marker, log for review.
    core_marker "QUEUE-OVER-CAP" "$QUEUE_ENTRIES > $QUEUE_CAP — auto-apply skipped; review $QUEUE manually"
    TS="$(date -u +%Y%m%dT%H%M%SZ)"
    {
      printf '## %s — queue over-cap\n' "$TS"
      printf 'Entries: %s  Cap: %s\n' "$QUEUE_ENTRIES" "$QUEUE_CAP"
      printf 'Action: auto-apply skipped\n\n'
    } >> "$QUEUE_LOG_DIR/over-cap.md" 2>/dev/null || true
  elif [ "$QUEUE_ENTRIES" -gt 0 ]; then
    # Under cap: apply queue entries (renames to .applied-<ts>).
    core_apply_improvement_queue "$QUEUE" "$QUEUE_LOG_DIR" || \
      core_log_warn "improvement-queue application failed; queue preserved for next session"
  fi
fi

# --------------------------------------------------------------------------
# MCP server registration (idempotent)
# --------------------------------------------------------------------------

if [ "${CORE_MCP_INSTALL_MANUAL:-0}" != "1" ]; then
  if "$SCRIPT_DIR/mcp-server-install.sh"; then
    # Check if MCP tools are now available (post-registration / post-restart)
    # Heuristic: if the registration ran clean and this isn't the first session
    # after installation, MCP tools are loaded.
    if [ -f "$CORE_DATA_DIR/needs-app-restart" ]; then
      core_marker "MCP-RESTART-PENDING" "MCP server registered; Cowork restart required to activate live-data dashboard"
    else
      core_marker "MCP-SERVER-AVAILABLE" "CORE MCP server registered and (likely) active"
    fi
  else
    core_log_warn "MCP server registration failed; live-data dashboard will run in snapshot mode"
    core_marker "MCP-INSTALL-FAILED" "see ~/.core/mcp-install-log.md; dashboard will show last-session state"
  fi
fi

# --------------------------------------------------------------------------
# First-session detection
# --------------------------------------------------------------------------

if [ ! -f "$CORE_PROJECT_ROOT/PROJECT.md" ]; then
  core_marker "FIRST-SESSION" "no PROJECT.md at $CORE_PROJECT_ROOT — run onboarding wizard to set up this project"
fi

# --------------------------------------------------------------------------
# Connector enumeration hint
# List connectors approved in ~/Library/Application Support/Claude/connectors/ if visible.
# --------------------------------------------------------------------------

CONNECTOR_LIST="$(ls -1 "$HOME/Library/Application Support/Claude/connectors/" 2>/dev/null \
  | tr '\n' ',' | sed 's/,$//')"
core_marker "CONNECTORS-AVAILABLE" "${CONNECTOR_LIST:-none-detected}"

# --------------------------------------------------------------------------
# Scheduled tasks gate (M-MAX-7 TM-10 — flag-gated for v1.0)
# --------------------------------------------------------------------------

if [ "${CORE_SCHEDULED_TASKS_ENABLED:-0}" = "1" ]; then
  core_marker "SCHEDULED-TASKS-ENABLED" "CORE_SCHEDULED_TASKS_ENABLED=1; observe Q1 behavior at first fire"
else
  core_marker "SCHEDULED-TASKS-DISABLED" "set CORE_SCHEDULED_TASKS_ENABLED=1 to enable scheduled sessions (v1.0 default: OFF)"
fi

exit 0
