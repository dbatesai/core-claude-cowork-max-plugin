#!/usr/bin/env python3
"""Validate connector docs against the supported connector list."""
import glob, os, sys

SUPPORTED = {"calendar", "slack", "drive", "linear"}

def validate(connectors_dir):
    paths = sorted(glob.glob(f"{connectors_dir}/*.md"))
    found = set()
    failures = []
    for path in paths:
        name = os.path.basename(path).replace(".md", "").lower()
        if name not in SUPPORTED:
            failures.append(f"{path}: unsupported connector '{name}'")
        else:
            found.add(name)
            print(f"OK: {path}")
    for connector in SUPPORTED:
        if connector not in found:
            failures.append(f"{connectors_dir}/{connector}.md: missing (required)")
    if failures:
        print("\nConnector validation FAILED:")
        for f in failures:
            print(f"  {f}")
        return False
    print(f"\nConnector validation OK (4/4 supported connectors documented)")
    return True

if __name__ == "__main__":
    ok = validate(sys.argv[1] if len(sys.argv) > 1 else "connectors/")
    sys.exit(0 if ok else 1)
