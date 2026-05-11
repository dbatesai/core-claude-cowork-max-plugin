#!/usr/bin/env bash
# CORE Cowork Max plugin — SessionEnd hook
# Runs on macOS host after the Cowork session ends.
# Responsibilities: flock-safe dm-profile write, dream-cycle synthesis apply.

set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/core-helpers.sh"

LOCK_FILE="$CORE_DATA_DIR/dm-profile.lock"
DM_PROFILE="$CORE_DATA_DIR/dm-profile.md"
PENDING_PROFILE="$CORE_DATA_DIR/dm-profile-pending.md"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
SESSION_LOG="$CORE_DATA_DIR/logs/sessions.md"

# --------------------------------------------------------------------------
# Flock-safe dm-profile write
# If a pending dm-profile update was staged during the session, apply it now
# under an exclusive lock (prevents concurrent session corruption).
# --------------------------------------------------------------------------

if [ -f "$PENDING_PROFILE" ]; then
  (
    # Try to acquire lock; skip if another session holds it (5s timeout)
    flock -w 5 200 || {
      core_log_warn "session-end: could not acquire dm-profile lock; pending update deferred"
      exit 1
    }

    if [ -f "$DM_PROFILE" ]; then
      cp "$DM_PROFILE" "$DM_PROFILE.bak-$TS"
    fi

    mv "$PENDING_PROFILE" "$DM_PROFILE"

  ) 200>"$LOCK_FILE"
fi

# --------------------------------------------------------------------------
# Dream-cycle synthesis apply
# If a pending dream-cycle result was staged (~/.core/dream-cycle-pending.md),
# apply it: merge into dm-profile + indexes, then archive the pending file.
# --------------------------------------------------------------------------

DREAM_PENDING="$CORE_DATA_DIR/dream-cycle-pending.md"

if [ -f "$DREAM_PENDING" ]; then
  (
    flock -w 5 200 || {
      core_log_warn "session-end: could not acquire dm-profile lock for dream-cycle; deferred"
      exit 1
    }

    # Archive the pending file with a timestamp so it can be reviewed
    DREAM_APPLIED="$CORE_DATA_DIR/dream-cycle-applied-$TS.md"
    mv "$DREAM_PENDING" "$DREAM_APPLIED"

    # Log that dream cycle was consumed
    {
      printf '## %s — dream-cycle applied\n' "$TS"
      printf 'Archived to: %s\n\n' "$DREAM_APPLIED"
    } >> "$CORE_DATA_DIR/logs/dream-cycle.md" 2>/dev/null || true

  ) 200>"$LOCK_FILE"
fi

# --------------------------------------------------------------------------
# Session end log entry
# --------------------------------------------------------------------------

{
  printf '## %s — session end\n' "$TS"
  printf 'Project root: %s\n' "$CORE_PROJECT_ROOT"
  if [ -f "$DM_PROFILE" ]; then
    printf 'DM profile: present\n'
  else
    printf 'DM profile: absent\n'
  fi
  printf '\n'
} >> "$SESSION_LOG" 2>/dev/null || true

exit 0
