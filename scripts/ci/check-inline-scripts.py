#!/usr/bin/env python3
"""Check syntax of inline <script> blocks in an HTML file using node --check."""
import re, subprocess, sys, tempfile, os

def check(html_path):
    content = open(html_path, encoding="utf-8").read()
    scripts = re.findall(
        r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',
        content, re.DOTALL | re.IGNORECASE
    )
    for i, script in enumerate(scripts):
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write(script)
            tmpname = f.name
        result = subprocess.run(["node", "--check", tmpname], capture_output=True, text=True)
        os.unlink(tmpname)
        if result.returncode != 0:
            print(f"FAIL: script block {i+1} in {html_path}")
            print(result.stderr)
            return False
    print(f"OK (inline scripts): {html_path}")
    return True

if __name__ == "__main__":
    ok = all(check(p) for p in sys.argv[1:])
    sys.exit(0 if ok else 1)
