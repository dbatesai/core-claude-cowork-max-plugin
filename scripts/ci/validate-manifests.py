#!/usr/bin/env python3
"""Validate plugin.json and hooks/hooks.json manifests."""
import json, sys

PLUGIN_REQUIRED = ["name", "version", "description", "author", "license"]
HOOK_REQUIRED_EVENTS = ["SessionStart", "SessionEnd"]


def validate_plugin():
    try:
        data = json.load(open(".claude-plugin/plugin.json", encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"plugin.json: error: {e}")
        return False
    missing = [f for f in PLUGIN_REQUIRED if f not in data]
    if missing:
        print(f"plugin.json: missing fields: {missing}")
        return False
    print(f"plugin.json OK: name={data['name']}, version={data['version']}")
    return True


def validate_hooks():
    try:
        data = json.load(open("hooks/hooks.json", encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"hooks.json: error: {e}")
        return False
    hooks = data.get("hooks", {})
    missing = [e for e in HOOK_REQUIRED_EVENTS if e not in hooks]
    if missing:
        print(f"hooks.json: missing hook events: {missing}")
        return False
    print("hooks.json OK: SessionStart + SessionEnd present")
    return True


if __name__ == "__main__":
    ok = validate_plugin() and validate_hooks()
    sys.exit(0 if ok else 1)
