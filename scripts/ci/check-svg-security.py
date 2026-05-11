#!/usr/bin/env python3
"""Check SVG files for external refs, embedded scripts, and foreignObject."""
import glob, re, sys

def check(svg_dir):
    failures = []
    paths = sorted(glob.glob(f"{svg_dir}/*.svg"))
    if not paths:
        print(f"No SVG files found in {svg_dir} — skipping")
        return True
    for path in paths:
        content = open(path, encoding="utf-8").read()
        if re.search(r'xlink:href\s*=\s*["\']https?://', content):
            failures.append(f"{path}: external xlink:href found")
        if re.search(r'href\s*=\s*["\']https?://', content):
            failures.append(f"{path}: external href found")
        if re.search(r'<script', content, re.IGNORECASE):
            failures.append(f"{path}: embedded <script> found")
        if re.search(r'<foreignObject', content, re.IGNORECASE):
            failures.append(f"{path}: <foreignObject> found")
        if not failures or failures[-1].split(":")[0] != path:
            print(f"OK: {path}")
    if failures:
        print("\nSVG security check FAILED:")
        for f in failures:
            print(f"  {f}")
        return False
    return True

if __name__ == "__main__":
    ok = check(sys.argv[1] if len(sys.argv) > 1 else "live-artifacts/workshop-assets/")
    sys.exit(0 if ok else 1)
