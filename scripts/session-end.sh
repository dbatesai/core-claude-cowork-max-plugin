#!/usr/bin/env bash
# Thin Unix shim — execs the cross-platform Python entry.
exec python3 "$(dirname "$0")/session_end.py" "$@"
