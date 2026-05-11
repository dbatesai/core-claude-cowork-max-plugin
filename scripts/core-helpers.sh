#!/usr/bin/env bash
# CORE Cowork Max plugin — shared helper library.
#
# Source this from hook scripts: . "$SCRIPT_DIR/core-helpers.sh"
#
# Provides: core_log_warn, core_marker, core_session_start_bootstrap_minus_queue,
#           core_apply_improvement_queue
# Sets: CORE_PROJECT_ROOT, CORE_DATA_DIR

# --------------------------------------------------------------------------
# Environment resolution
# --------------------------------------------------------------------------

# CORE_PROJECT_ROOT: host-side project root (where PROJECT.md lives).
# Resolution order: CLAUDE_CODE_WORKSPACE_HOST_PATHS (first entry) →
#                   CLAUDE_PROJECT_DIR → PWD.
_core_resolve_project_root() {
  local paths="${CLAUDE_CODE_WORKSPACE_HOST_PATHS:-}"
  if [ -n "$paths" ]; then
    printf '%s' "${paths%%:*}"   # first colon-separated path
    return 0
  fi
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s' "$CLAUDE_PROJECT_DIR"
    return 0
  fi
  printf '%s' "$PWD"
}

export CORE_PROJECT_ROOT="${CORE_PROJECT_ROOT:-$(_core_resolve_project_root)}"
export CORE_DATA_DIR="${CORE_DATA_DIR:-$HOME/.core}"

mkdir -p "$CORE_DATA_DIR/logs" "$CORE_DATA_DIR/improvement-log" 2>/dev/null || true

# --------------------------------------------------------------------------
# Logging (stderr + append to ~/.core/logs/warn.md)
# --------------------------------------------------------------------------

core_log_warn() {
  local msg="$1"
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '[CORE WARN %s] %s\n' "$ts" "$msg" >&2
  printf '## %s\n%s\n\n' "$ts" "$msg" >> "$CORE_DATA_DIR/logs/warn.md" 2>/dev/null || true
}

# --------------------------------------------------------------------------
# Stdout injection markers
# Cowork reads hook stdout into the DM's session context.
# Convention: [[CORE-<NAME>]] <value>
# --------------------------------------------------------------------------

core_marker() {
  local name="$1"
  local value="${2:-}"
  printf '[[CORE-%s]] %s\n' "$name" "$value"
}

# --------------------------------------------------------------------------
# Skill path resolution
# Prefer host-side ~/.claude/skills/<name>/ over bundled snapshot.
# --------------------------------------------------------------------------

_core_skill_dir() {
  local skill_name="$1"
  local host_path="$HOME/.claude/skills/$skill_name"
  local bundled_path="${CLAUDE_PLUGIN_ROOT:-__no_plugin_root__}/skills/$skill_name"

  if [ -d "$host_path" ]; then
    printf '%s' "$host_path"
  elif [ -d "$bundled_path" ]; then
    printf '%s' "$bundled_path"
  else
    printf ''
  fi
}

# --------------------------------------------------------------------------
# File content injection (stdout, with begin/end markers and line limit)
# --------------------------------------------------------------------------

_core_inject_file() {
  local marker_name="$1"
  local file_path="$2"
  local max_lines="${3:-200}"

  if [ ! -f "$file_path" ]; then
    core_log_warn "_core_inject_file: $file_path not found; skipping"
    return 0
  fi

  printf '[[CORE-%s-BEGIN]]\n' "$marker_name"
  head -n "$max_lines" "$file_path"
  printf '[[CORE-%s-END]]\n' "$marker_name"
}

# --------------------------------------------------------------------------
# Standard bootstrap (minus improvement-queue application)
#
# Outputs to stdout (DM session context):
#   - Harness + project root markers
#   - CORE SKILL.md content (DM entry point — host-side preferred, bundled fallback)
#   - Companion skill registration markers (orient, finalize, vibecheck)
#   - DM profile content (~/.core/dm-profile.md)
#   - Project state excerpt (PROJECT.md, first 150 lines)
#   - VM-mount-hint marker (§6 Path Semantics discipline)
# --------------------------------------------------------------------------

core_session_start_bootstrap_minus_queue() {
  # 1. Harness detection
  local is_cowork="${CLAUDE_CODE_IS_COWORK:-0}"
  core_marker "HARNESS" "cowork=${is_cowork}"

  # 2. Project root
  core_marker "PROJECT-ROOT" "$CORE_PROJECT_ROOT"

  # 3. CORE skill (DM protocol entry point)
  local skill_dir; skill_dir="$(_core_skill_dir "core")"
  if [ -n "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
    _core_inject_file "SKILL" "$skill_dir/SKILL.md" 500
    core_marker "SKILL-SOURCE" "$skill_dir"
  else
    core_marker "SKILL-MISSING" "CORE SKILL.md not found at host or bundled path — DM lacks protocol content"
    core_log_warn "CORE skill not found; checked: $HOME/.claude/skills/core and ${CLAUDE_PLUGIN_ROOT:-n/a}/skills/core"
  fi

  # 4. Companion skill registration (markers only — content loaded on demand via /orient etc.)
  for skill in orient finalize vibecheck; do
    local sdir; sdir="$(_core_skill_dir "$skill")"
    if [ -n "$sdir" ]; then
      core_marker "COMPANION-SKILL-${skill^^}" "$sdir"
    fi
  done

  # 5. DM profile
  local dm_profile="$CORE_DATA_DIR/dm-profile.md"
  if [ -f "$dm_profile" ]; then
    _core_inject_file "DM-PROFILE" "$dm_profile" 100
  else
    core_marker "DM-PROFILE-MISSING" "first session — DM should initialize dm-profile.md per startup protocol"
  fi

  # 6. Project state excerpt (PROJECT.md)
  local project_md="$CORE_PROJECT_ROOT/PROJECT.md"
  if [ -f "$project_md" ]; then
    _core_inject_file "PROJECT-STATE" "$project_md" 150
  else
    core_marker "PROJECT-MISSING" "no PROJECT.md at $CORE_PROJECT_ROOT — run onboarding wizard to create it"
  fi

  # 7. VM-mount hint (§6 Path Semantics discipline)
  # Hook runs on host. VM mount path for ~/.core/ is determined by Cowork after hook fires
  # and is returned as plain text by mcp__cowork__request_cowork_directory.
  # Inject the known host path so DM knows what to pass to that tool.
  core_marker "VM-MOUNT-HINT" "host=$CORE_DATA_DIR — pass to mcp__cowork__request_cowork_directory; tool returns VM-side mount path"

  return 0
}

# --------------------------------------------------------------------------
# Improvement queue application
#
# Usage: core_apply_improvement_queue <queue_file> <log_dir>
#
# Processes entries in the queue file (each starts with "## ").
# v1.0 implementation: moves queue to .applied-<timestamp> so it won't
# re-fire next session. Logs the application for DM review. The DM handles
# any skill-content patches on the next session after reading the log.
#
# Future: parse "Target: <path>" + "Patch:" blocks and apply as file writes.
# --------------------------------------------------------------------------

core_apply_improvement_queue() {
  local queue_file="$1"
  local log_dir="$2"
  local ts; ts="$(date -u +%Y%m%dT%H%M%SZ)"
  local applied_file="${queue_file%.md}.applied-${ts}.md"

  mkdir -p "$log_dir" 2>/dev/null || true

  local entry_count; entry_count="$(grep -c '^## ' "$queue_file" 2>/dev/null || echo 0)"

  if [ "$entry_count" -eq 0 ]; then
    return 0
  fi

  # Log before moving (preserve the original content in the log)
  {
    printf '## %s — queue-apply: %d entries consumed\n\n' "$ts" "$entry_count"
    cat "$queue_file"
    printf '\n---\n\n'
  } >> "$log_dir/applications.md" 2>/dev/null || true

  # Rename so it won't re-trigger next session
  if mv "$queue_file" "$applied_file" 2>/dev/null; then
    core_marker "QUEUE-APPLIED" "$entry_count entries consumed; archived as $(basename "$applied_file")"
  else
    core_log_warn "core_apply_improvement_queue: mv failed; queue preserved at $queue_file"
    return 1
  fi

  return 0
}
