#!/usr/bin/env python3
"""
CORE Cowork Max plugin — SessionEnd hook (cross-platform Python).

Responsibilities:
  - Atomic dm-profile write (mkdir-based lock; works on macOS/Win/Linux)
  - Dream-cycle synthesis apply
  - Session end log entry
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import core_helpers as ch  # noqa: E402


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lock_dir = ch.CORE_DATA_DIR / "dm-profile.lock.d"
    dm_profile = ch.CORE_DATA_DIR / "dm-profile.md"
    pending_profile = ch.CORE_DATA_DIR / "dm-profile-pending.md"
    dream_pending = ch.CORE_DATA_DIR / "dream-cycle-pending.md"
    session_log = ch.CORE_DATA_DIR / "logs" / "sessions.md"

    # Apply pending dm-profile write (lock-protected)
    if pending_profile.is_file():
        if ch.acquire_lock(lock_dir, timeout_seconds=5):
            try:
                if dm_profile.is_file():
                    shutil.copy2(dm_profile, dm_profile.with_name(f"dm-profile.md.bak-{ts}"))
                pending_profile.replace(dm_profile)
            except OSError as e:
                ch.log_warn(f"session_end: dm-profile write failed: {e}")
            finally:
                ch.release_lock(lock_dir)
        else:
            ch.log_warn("session_end: dm-profile lock not acquired (timeout); pending update deferred")

    # Apply pending dream-cycle synthesis
    if dream_pending.is_file():
        if ch.acquire_lock(lock_dir, timeout_seconds=5):
            try:
                applied = ch.CORE_DATA_DIR / f"dream-cycle-applied-{ts}.md"
                dream_pending.replace(applied)
                dream_log = ch.CORE_DATA_DIR / "logs" / "dream-cycle.md"
                try:
                    with dream_log.open("a", encoding="utf-8") as f:
                        f.write(f"## {ts} — dream-cycle applied\nArchived to: {applied}\n\n")
                except OSError:
                    pass
            except OSError as e:
                ch.log_warn(f"session_end: dream-cycle apply failed: {e}")
            finally:
                ch.release_lock(lock_dir)
        else:
            ch.log_warn("session_end: dm-profile lock not acquired for dream-cycle; deferred")

    # Session end log entry (no lock; append-only)
    try:
        with session_log.open("a", encoding="utf-8") as f:
            f.write(f"## {ts} — session end\n")
            f.write(f"Project root: {ch.CORE_PROJECT_ROOT}\n")
            f.write(f"OS: {ch.SYSTEM}\n")
            f.write(f"DM profile: {'present' if dm_profile.is_file() else 'absent'}\n\n")
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
