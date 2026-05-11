#!/usr/bin/env bash
# CORE Cowork Max plugin — SessionEnd hook
# Runs on macOS host after the Cowork session ends.
# Responsibilities: safe dm-profile write, dream-cycle synthesis apply.
#
# Uses mkdir-based atomic locking (portable; macOS lacks flock).

set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/core-helpers.sh"

LOCK_DIR="$CORE_DATA_DIR/dm-profile.lock.d"
DM_PROFILE="$CORE_DATA_DIR/dm-profile.md"
PENDING_PROFILE="$CORE_DATA_DIR/dm-profile-pending.md"
DREAM_PENDING="$CORE_DATA_DIR/dream-cycle-pending.md"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
SESSION_LOG="$CORE_DATA_DIR/logs/sessions.md"

# --------------------------------------------------------------------------
# Atomic lock acquisition (mkdir-based, portable across macOS + Linux)
# Returns 0 on lock acquired, 1 on timeout.
# --------------------------------------------------------------------------

acquire_lock() {
  local timeout_seconds="${1:-5}"
  local elapsed=0
  while [ $elapsed -lt $timeout_seconds ]; do
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      # Stale-lock cleanup if our process dies: lock dir contains our PID
      echo "$$" > "$LOCK_DIR/pid"
      return 0
    fi
    # Check if existing lock is stale (process no longer running)
    if [ -f "$LOCK_DIR/pid" ]; then
      local stale_pid; stale_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null)"
      if [ -n "$stale_pid" ] && ! kill -0 "$stale_pid" 2>/dev/null; then
        # Stale lock — remove and retry
        rm -rf "$LOCK_DIR" 2>/dev/null
        continue
      fi
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

release_lock() {
  rm -rf "$LOCK_DIR" 2>/dev/null
}

# --------------------------------------------------------------------------
# Apply pending dm-profile write (lock-protected)
# --------------------------------------------------------------------------

if [ -f "$PENDING_PROFILE" ]; then
  if acquire_lock 5; then
    if [ -f "$DM_PROFILE" ]; then
      cp "$DM_PROFILE" "$DM_PROFILE.bak-$TS"
    fi
    mv "$PENDING_PROFILE" "$DM_PROFILE"
    release_lock
  else
    core_log_warn "session-end: dm-profile lock not acquired (timeout); pending update deferred"
  fi
fi

# --------------------------------------------------------------------------
# Apply pending dream-cycle synthesis (lock-protected)
# --------------------------------------------------------------------------

if [ -f "$DREAM_PENDING" ]; then
  if acquire_lock 5; then
    DREAM_APPLIED="$CORE_DATA_DIR/dream-cycle-applied-$TS.md"
    mv "$DREAM_PENDING" "$DREAM_APPLIED"
    {
      printf '## %s — dream-cycle applied\n' "$TS"
      printf 'Archived to: %s\n\n' "$DREAM_APPLIED"
    } >> "$CORE_DATA_DIR/logs/dream-cycle.md" 2>/dev/null || true
    release_lock
  else
    core_log_warn "session-end: dm-profile lock not acquired for dream-cycle; deferred"
  fi
fi

# --------------------------------------------------------------------------
# Session end log entry (no lock needed — append-only file)
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
