# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
