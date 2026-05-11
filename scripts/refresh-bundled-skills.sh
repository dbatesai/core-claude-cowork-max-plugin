#!/usr/bin/env bash
# Refresh bundled skill snapshots from canonical host-side skill checkouts.
# Run before tagging a release; CI will refuse to publish if snapshots drift.
# See §12.3 of docs/specs/2026-05-10-core-claude-cowork-max-plugin-spec.md

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST_SKILLS="$HOME/.claude/skills"

for skill in core orient finalize vibecheck; do
  if [ ! -d "$HOST_SKILLS/$skill" ]; then
    echo "ERROR: $HOST_SKILLS/$skill missing — cannot refresh." >&2
    exit 1
  fi
  echo "Refreshing skills/$skill from $HOST_SKILLS/$skill ..."
  rsync -a --delete \
    --exclude='.git' --exclude='node_modules' --exclude='*.pyc' \
    "$HOST_SKILLS/$skill/" "$PLUGIN_ROOT/skills/$skill/"
done

# Compute checksums for CI parity check
( cd "$PLUGIN_ROOT" && find skills -type f -not -name 'CHECKSUMS.txt' -print0 \
  | sort -z | xargs -0 shasum -a 256 ) \
  > "$PLUGIN_ROOT/skills/CHECKSUMS.txt"

echo "Done. Bundled snapshots refreshed; skills/CHECKSUMS.txt updated."
echo "Next: commit + tag + push to trigger release CI."
