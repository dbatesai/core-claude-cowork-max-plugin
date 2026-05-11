# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — 2026-05-11

### Changed

- **MCP server rewritten in Node.js** (`mcp-server-node/server.mjs`) — zero dependencies, ~600 lines of vanilla Node using only built-in modules (`fs`, `os`, `path`, `readline`). Replaces the Python/FastMCP implementation as the primary runtime.
- **Three-level capability fallback ladder** (per David's instruction 2026-05-10):
  - **L1**: Node.js + MCP server live → full live dashboard via `mcp__core__*` tools
  - **L2**: Node missing or MCP handshake failed → DM falls back to `mcp__cowork__request_cowork_directory` + file tools; live dashboard with per-session approval
  - **L3**: Even fallback unavailable → DM informs user via chat with install instructions
- **`mcp_server_install.py`** now probes Node availability + end-to-end MCP handshake (3s timeout) instead of installing a Python venv. Capability state persisted to `~/.core/capability.json`; re-probe gated by `CORE_CAPABILITY_REPROBE=1` env var to keep working installs stable.
- **`session_start.py`** emits `[[CORE-CAPABILITY-LEVEL]]` marker so the DM knows which mode to operate in.

### Added

- `CORE_DRY_RUN=1` env var on `mcp_server_install.py` for testing without mutating the user's `claude_desktop_config.json`.
- `CORE_CLAUDE_CONFIG_PATH` env var override (testing aid).

### Deprecated

- Python `mcp-server/` retained in this commit for rollback; will be removed in a follow-up commit after the Node implementation is validated in a Cowork session.

---

## [1.0.0] — 2026-05-10

### Added

- First release of the CORE Cowork-native max plugin.
- **Plugin infrastructure**: `plugin.json`, `hooks/hooks.json`, `scripts/`, `mcp-server/`, `live-artifacts/`, `templates/`, `connectors/`.
- **SessionStart hook**: project state injection, improvement-queue application with QUEUE_CAP check (M-MAX-15), CORE MCP server auto-registration, first-session detection.
- **SessionEnd hook**: flock-safe dm-profile write, dream-cycle synthesis apply.
- **CORE MCP server** (FastMCP, Python): 8 read-only tools (`read_project_md`, `read_dm_profile`, `read_persuasion_log`, `read_swarm_topology`, `read_convergence_trajectory`, `read_vibe_log`, `read_workshop_state`, `list_workspaces`). Registered on first session via `mcp-server-install.sh`.
- **Live Artifacts**: onboarding wizard (first-session project setup), Trust Strip Dashboard (persistent session dashboard), Swarm Live View (real-time swarm visualization), DM Workshop (DM visual presence — name resolved from `dm-profile.md` at render time).
- **Six project templates**: Software delivery / Marketing campaign / Research initiative / Decision in flight / Personal project / Generic.
- **Four connector docs**: Calendar, Slack, Drive, Linear.
- **Three-channel distribution**: Anthropic plugin marketplace + SharePoint + GitHub releases. Per-asset CI matrix gates release. All-or-none publish semantics.
- **Bundled skill snapshots**: `core`, `orient`, `finalize`, `vibecheck` skills bundled at release time. `scripts/refresh-bundled-skills.sh` keeps snapshots current.
- **Supply-chain mitigations**: improvement-queue QUEUE_CAP, MCP auto-registration audit log, `cdn-checksums.txt` pin verification, SVG strict ruleset (no external refs, no embedded scripts).

### Architecture Decisions

- DC-29 Branch B-1: per-session `request_cowork_directory` approval for `~/.core/` access (empirically validated).
- DC-35: active development is max plugin only; standard + Claude Code plugin scopes deferred.
- DM-broker dashboard pattern: DM pulls state from CORE MCP server DM-side, pushes to Live Artifact via `update_artifact` (no artifact-initiated MCP calls).
- CORE_SCHEDULED_TASKS_ENABLED flag defaults OFF for v1.0 (Q1 behavior unconfirmed; see §11 row 1).
