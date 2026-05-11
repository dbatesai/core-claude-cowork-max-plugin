#!/usr/bin/env python3
"""Validate project templates against the PROJECT.md six-section schema."""
import glob, re, sys

REQUIRED_SECTIONS = [
    "## What & Why",
    "## State",
    "## People",
    "## Moves",
    "## Decisions & Risks",
    "## Notes",
]
REQUIRED_PATTERNS = [
    (r"\*\*Recommended connectors", "recommended-connectors block"),
    (r"\*\*Best for", "best-for example"),
]

def validate(templates_dir):
    paths = sorted(glob.glob(f"{templates_dir}/*.md"))
    if not paths:
        print(f"No templates found in {templates_dir}")
        sys.exit(1)
    failures = []
    for path in paths:
        content = open(path, encoding="utf-8").read()
        for section in REQUIRED_SECTIONS:
            if section not in content:
                failures.append(f"{path}: missing section '{section}'")
        for pattern, desc in REQUIRED_PATTERNS:
            if not re.search(pattern, content, re.IGNORECASE):
                failures.append(f"{path}: missing {desc}")
        if not failures or not failures[-1].startswith(path):
            print(f"OK: {path}")
    if failures:
        print("\nTemplate validation FAILED:")
        for f in failures:
            print(f"  {f}")
        return False
    print(f"\nTemplate validation OK ({len(paths)} templates)")
    return True

if __name__ == "__main__":
    ok = validate(sys.argv[1] if len(sys.argv) > 1 else "templates/project-types/")
    sys.exit(0 if ok else 1)
