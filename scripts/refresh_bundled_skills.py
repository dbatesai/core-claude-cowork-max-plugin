#!/usr/bin/env python3
"""
Refresh bundled skill snapshots from canonical host-side skill checkouts.

Cross-platform Python replacement for refresh-bundled-skills.sh (which used rsync —
not standard on Windows). Uses shutil.copytree for cross-platform recursive copy.

Run before tagging a release; CI refuses to publish if snapshots drift.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

SKILLS = ("core", "vibecheck")
EXCLUDE_NAMES = {".git", "node_modules", "__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}


def _is_excluded(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def _copytree_filtered(src: Path, dst: Path) -> None:
    """
    Cross-platform recursive copy with exclude filter.
    Mirrors rsync -a --delete semantics: dst is wiped first, then src copied in.
    """
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    def _walk_copy(s: Path, d: Path) -> None:
        for child in s.iterdir():
            if _is_excluded(child):
                continue
            target = d / child.name
            if child.is_symlink():
                # Resolve symlink and copy contents (avoid host-specific symlinks
                # leaking into the bundled snapshot)
                resolved = child.resolve()
                if resolved.is_dir():
                    target.mkdir()
                    _walk_copy(resolved, target)
                elif resolved.is_file():
                    shutil.copy2(resolved, target)
            elif child.is_dir():
                target.mkdir()
                _walk_copy(child, target)
            elif child.is_file():
                shutil.copy2(child, target)

    _walk_copy(src, dst)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    plugin_root = Path(__file__).resolve().parent.parent
    host_skills = Path.home() / ".claude" / "skills"

    for skill in SKILLS:
        src = host_skills / skill
        dst = plugin_root / "skills" / skill
        if not src.is_dir():
            print(f"ERROR: {src} missing — cannot refresh.", file=sys.stderr)
            return 1
        print(f"Refreshing skills/{skill} from {src} ...")
        _copytree_filtered(src, dst)

    # Compute deterministic checksums (forward-slash paths for cross-OS consistency)
    skills_dir = plugin_root / "skills"
    files = sorted(
        p for p in skills_dir.rglob("*")
        if p.is_file() and p.name != "CHECKSUMS.txt"
    )
    checksums_path = skills_dir / "CHECKSUMS.txt"
    with checksums_path.open("w", encoding="utf-8") as f:
        for p in files:
            rel = p.relative_to(plugin_root).as_posix()
            f.write(f"{_file_sha256(p)}  {rel}\n")

    print(f"Done. Bundled snapshots refreshed; {checksums_path.relative_to(plugin_root)} updated.")
    print("Next: commit + tag + push to trigger release CI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
