#!/usr/bin/env python3
"""
CORE Cowork Max plugin — shared cross-platform helper library.

Importable from session_start.py, session_end.py, etc:
    from core_helpers import CORE_PROJECT_ROOT, CORE_DATA_DIR, marker, log_warn, ...

Cross-platform: macOS, Windows, Linux. Path resolution uses pathlib;
OS branching uses platform.system().
"""
from __future__ import annotations

import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------
# OS detection
# --------------------------------------------------------------------------

SYSTEM = platform.system()                  # "Darwin" | "Windows" | "Linux"
IS_MAC = SYSTEM == "Darwin"
IS_WINDOWS = SYSTEM == "Windows"
IS_LINUX = SYSTEM == "Linux"


# --------------------------------------------------------------------------
# Path resolution (cross-platform)
# --------------------------------------------------------------------------

def _resolve_project_root() -> Path:
    """
    CORE_PROJECT_ROOT: host-side project root (where PROJECT.md lives).
    Resolution: CLAUDE_CODE_WORKSPACE_HOST_PATHS (first) → CLAUDE_PROJECT_DIR → cwd.
    """
    paths = os.environ.get("CLAUDE_CODE_WORKSPACE_HOST_PATHS", "")
    if paths:
        # Colon-separated on Unix; may be ; on Windows — try both
        sep = ";" if (IS_WINDOWS and ";" in paths) else ":"
        first = paths.split(sep, 1)[0].strip()
        if first:
            return Path(first)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir)
    return Path.cwd()


CORE_PROJECT_ROOT: Path = Path(os.environ.get("CORE_PROJECT_ROOT") or _resolve_project_root())
CORE_DATA_DIR: Path = Path(os.environ.get("CORE_DATA_DIR") or (Path.home() / ".core"))

# Ensure subdirs
(CORE_DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
(CORE_DATA_DIR / "improvement-log").mkdir(parents=True, exist_ok=True)


def claude_config_path() -> Path:
    """
    Per-OS location of Claude Desktop / Cowork MCP config file.

    Override via CORE_CLAUDE_CONFIG_PATH env var (useful for tests/dry-runs).

    macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
    Windows: %APPDATA%/Claude/claude_desktop_config.json    (TODO: verify on Windows Cowork — unconfirmed)
    Linux:   ~/.config/Claude/claude_desktop_config.json    (best-guess; unverified)
    """
    override = os.environ.get("CORE_CLAUDE_CONFIG_PATH", "")
    if override:
        return Path(override)
    home = Path.home()
    if IS_MAC:
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


DRY_RUN: bool = os.environ.get("CORE_DRY_RUN", "0") == "1"


def connectors_dir() -> Path:
    """Per-OS connectors directory (alongside claude_desktop_config.json)."""
    return claude_config_path().parent / "connectors"


def venv_python(venv_dir: Path) -> Path:
    """Per-OS venv python executable path."""
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_pip(venv_dir: Path) -> Path:
    """Per-OS venv pip executable path."""
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


# --------------------------------------------------------------------------
# Logging (stderr + ~/.core/logs/warn.md)
# --------------------------------------------------------------------------

def log_warn(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[CORE WARN {ts}] {msg}", file=sys.stderr)
    try:
        with (CORE_DATA_DIR / "logs" / "warn.md").open("a", encoding="utf-8") as f:
            f.write(f"## {ts}\n{msg}\n\n")
    except OSError:
        pass


# --------------------------------------------------------------------------
# Stdout injection markers
# Cowork reads hook stdout into the DM's session context.
# Convention: [[CORE-<NAME>]] <value>
# --------------------------------------------------------------------------

def marker(name: str, value: str = "") -> None:
    print(f"[[CORE-{name}]] {value}")


# --------------------------------------------------------------------------
# Skill path resolution
# Prefer host-side ~/.claude/skills/<name>/ over bundled snapshot.
# --------------------------------------------------------------------------

def skill_dir(skill_name: str) -> Optional[Path]:
    host_path = Path.home() / ".claude" / "skills" / skill_name
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    bundled_path = Path(plugin_root) / "skills" / skill_name if plugin_root else None

    if host_path.is_dir():
        return host_path
    if bundled_path and bundled_path.is_dir():
        return bundled_path
    return None


# --------------------------------------------------------------------------
# File content injection (stdout, with begin/end markers and line limit)
# --------------------------------------------------------------------------

def inject_file(marker_name: str, file_path: Path, max_lines: int = 200) -> None:
    if not file_path.is_file():
        log_warn(f"inject_file: {file_path} not found; skipping")
        return
    print(f"[[CORE-{marker_name}-BEGIN]]")
    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                print(line, end="")
            # Trailing newline if last line didn't have one
            print()
    except OSError as e:
        log_warn(f"inject_file: read error for {file_path}: {e}")
    print(f"[[CORE-{marker_name}-END]]")


# --------------------------------------------------------------------------
# Standard bootstrap (minus improvement-queue application)
#
# Emits to stdout (DM session context):
#   - Harness + project root + OS markers
#   - CORE SKILL.md content
#   - Companion skill registration markers
#   - DM profile content
#   - Project state excerpt
#   - VM-mount-hint marker
# --------------------------------------------------------------------------

def session_start_bootstrap_minus_queue() -> None:
    # 1. Harness + OS detection
    is_cowork = os.environ.get("CLAUDE_CODE_IS_COWORK", "0")
    marker("HARNESS", f"cowork={is_cowork}")
    marker("HOST-OS", SYSTEM)

    # 2. Project root
    marker("PROJECT-ROOT", str(CORE_PROJECT_ROOT))

    # 3. CORE skill (DM protocol entry point)
    core_dir = skill_dir("core")
    if core_dir and (core_dir / "SKILL.md").is_file():
        inject_file("SKILL", core_dir / "SKILL.md", max_lines=500)
        marker("SKILL-SOURCE", str(core_dir))
    else:
        marker("SKILL-MISSING", "CORE SKILL.md not found; DM lacks protocol content")
        log_warn("CORE skill not found at host or bundled path")

    # 4. Companion skill registration
    for skill in ("orient", "finalize", "vibecheck"):
        sdir = skill_dir(skill)
        if sdir:
            marker(f"COMPANION-SKILL-{skill.upper()}", str(sdir))

    # 5. DM profile
    dm_profile = CORE_DATA_DIR / "dm-profile.md"
    if dm_profile.is_file():
        inject_file("DM-PROFILE", dm_profile, max_lines=100)
    else:
        marker("DM-PROFILE-MISSING", "first session — DM should initialize dm-profile.md per startup protocol")

    # 6. Project state excerpt
    project_md = CORE_PROJECT_ROOT / "PROJECT.md"
    if project_md.is_file():
        inject_file("PROJECT-STATE", project_md, max_lines=150)
    else:
        marker("PROJECT-MISSING", f"no PROJECT.md at {CORE_PROJECT_ROOT} — run onboarding wizard")

    # 7. VM-mount hint (Path Semantics discipline)
    marker(
        "VM-MOUNT-HINT",
        f"host={CORE_DATA_DIR} — pass to mcp__cowork__request_cowork_directory; tool returns VM-side mount path",
    )


# --------------------------------------------------------------------------
# Improvement queue application
# --------------------------------------------------------------------------

def apply_improvement_queue(queue_file: Path, log_dir: Path) -> bool:
    """
    v1.0 implementation: archive the queue file as .applied-<timestamp>.md
    so it doesn't re-fire. Logs the application. DM consumes the log next session.

    Returns True on success, False on failure.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    applied_file = queue_file.with_name(queue_file.stem + f".applied-{ts}.md")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Count entries
    try:
        content = queue_file.read_text(encoding="utf-8")
    except OSError as e:
        log_warn(f"apply_improvement_queue: cannot read {queue_file}: {e}")
        return False

    entry_count = sum(1 for line in content.splitlines() if line.startswith("## "))
    if entry_count == 0:
        return True

    # Log
    try:
        with (log_dir / "applications.md").open("a", encoding="utf-8") as f:
            f.write(f"## {ts} — queue-apply: {entry_count} entries consumed\n\n")
            f.write(content)
            f.write("\n---\n\n")
    except OSError as e:
        log_warn(f"apply_improvement_queue: log write failed: {e}")

    # Archive (rename)
    try:
        queue_file.rename(applied_file)
        marker("QUEUE-APPLIED", f"{entry_count} entries consumed; archived as {applied_file.name}")
        return True
    except OSError as e:
        log_warn(f"apply_improvement_queue: rename failed: {e}")
        return False


# --------------------------------------------------------------------------
# Atomic lock (mkdir-based — portable macOS / Windows / Linux)
# --------------------------------------------------------------------------

def acquire_lock(lock_dir: Path, timeout_seconds: int = 5) -> bool:
    """Atomic lock via mkdir. Returns True on acquisition, False on timeout."""
    elapsed = 0
    while elapsed < timeout_seconds:
        try:
            lock_dir.mkdir(parents=False, exist_ok=False)
            (lock_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")
            return True
        except FileExistsError:
            # Check for stale lock
            pid_file = lock_dir / "pid"
            if pid_file.exists():
                try:
                    stale_pid = int(pid_file.read_text(encoding="utf-8").strip())
                    if not _process_alive(stale_pid):
                        # Stale — remove and retry
                        release_lock(lock_dir)
                        continue
                except (ValueError, OSError):
                    pass
            time.sleep(1)
            elapsed += 1
    return False


def release_lock(lock_dir: Path) -> None:
    try:
        for child in lock_dir.iterdir():
            try:
                child.unlink()
            except OSError:
                pass
        lock_dir.rmdir()
    except OSError:
        pass


def _process_alive(pid: int) -> bool:
    """Cross-platform PID liveness check."""
    if IS_WINDOWS:
        # Use OpenProcess; missing process raises OSError
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return True
            return False
        except Exception:
            return True  # Assume alive on uncertainty (conservative)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Self-test (run as a script to verify the module loads + paths resolve)
# --------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"# core_helpers self-test ({SYSTEM})")
    print(f"CORE_PROJECT_ROOT  = {CORE_PROJECT_ROOT}")
    print(f"CORE_DATA_DIR      = {CORE_DATA_DIR}")
    print(f"claude_config_path = {claude_config_path()}")
    print(f"connectors_dir     = {connectors_dir()}")
    sample_venv = CORE_DATA_DIR / "mcp-venv"
    print(f"venv_python        = {venv_python(sample_venv)}")
    print(f"venv_pip           = {venv_pip(sample_venv)}")
    print(f"core skill dir     = {skill_dir('core')}")
    print("OK")
