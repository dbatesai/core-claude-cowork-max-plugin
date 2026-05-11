#!/usr/bin/env python3
"""Verify CDN URL SHA256 pins from cdn-checksums.txt."""
import hashlib, sys, urllib.request

def verify(checksum_file):
    failures = []
    try:
        lines = open(checksum_file, encoding="utf-8").readlines()
    except FileNotFoundError:
        print(f"ERROR: {checksum_file} not found")
        return False

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        expected, url = parts
        if "PLACEHOLDER" in expected:
            print(f"SKIP (placeholder): {url}")
            continue
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                content = resp.read()
            actual = hashlib.sha256(content).hexdigest()
            if actual != expected:
                failures.append(f"SHA256 mismatch:\n  url: {url}\n  expected: {expected}\n  actual:   {actual}")
            else:
                print(f"OK: {url}")
        except Exception as e:
            failures.append(f"Fetch error for {url}: {e}")

    if failures:
        print("\nCDN pin verification FAILED:")
        for f in failures:
            print(f)
        return False
    return True

if __name__ == "__main__":
    ok = verify(sys.argv[1])
    sys.exit(0 if ok else 1)
