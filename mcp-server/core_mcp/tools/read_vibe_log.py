"""read_vibe_log — parse ~/.core/vibes/vibe-log.md into structured JSON."""

import re
from pathlib import Path
from typing import Any


def _parse_vibe_entries(text: str) -> list[dict]:
    """
    Parse vibe-log.md entries.
    Expected format per entry:
      ## YYYY-MM-DD — <session label>
      <vibe label line>
      <ASCII art block>
    """
    entries = []
    # Split on ## date headers
    sections = re.split(r"^(?=## \d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        header_match = re.match(r"^## (\d{4}-\d{2}-\d{2})\s*[—-]?\s*(.*?)$", section, re.MULTILINE)
        if not header_match:
            continue

        date = header_match.group(1)
        label = header_match.group(2).strip()
        body = section[header_match.end():].strip()

        # First non-empty line after header is typically the vibe descriptor
        lines = body.splitlines()
        vibe_descriptor = ""
        ascii_art_lines = []
        for i, line in enumerate(lines):
            if line.strip() and not vibe_descriptor:
                vibe_descriptor = line.strip()
            elif vibe_descriptor:
                ascii_art_lines.append(line)

        entries.append({
            "date": date,
            "label": label,
            "vibe": vibe_descriptor,
            "ascii_art": "\n".join(ascii_art_lines).strip(),
        })

    return entries


def read_vibe_log_impl(limit: int = 10) -> dict[str, Any]:
    vibe_log_path = Path.home() / ".core" / "vibes" / "vibe-log.md"

    if not vibe_log_path.exists():
        return {
            "found": False,
            "note": "~/.core/vibes/vibe-log.md not found — no vibes captured yet",
            "entries": [],
        }

    content = vibe_log_path.read_text(encoding="utf-8")
    entries = _parse_vibe_entries(content)

    # Most recent first
    entries_sorted = sorted(entries, key=lambda e: e["date"], reverse=True)
    truncated = entries_sorted[:limit]

    return {
        "found": True,
        "path": str(vibe_log_path),
        "total_entries": len(entries),
        "returned": len(truncated),
        "entries": truncated,
        "most_recent_vibe": truncated[0]["vibe"] if truncated else None,
    }
