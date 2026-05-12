# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-05-11

Iteration-2 release. Addresses four of the five findings from the iteration-1
empirical Cowork test (F2, F4, F5 fully; F1 partially — write-tool
infrastructure complete, skill-layer write-routing protocol still under
adversarial review).

### Added — iteration-2 work

- **9 new MCP tools** in `mcp-server-node/server.mjs` (8 write + 1 read):
  - `register_workspace` / `unregister_workspace` / `update_workspace_last_active` — manage `~/.core/index.json` entries
  - `write_workspace_manifest` — write `~/.core/workspaces/<id>/workspace.json`
  - `append_dm_profile_entry` / `update_dm_profile_section` — DM profile mutations
  - `append_vibe_log` — append to `~/.core/vibes/vibe-log.md`
  - `write_swarm_narrative` — write per-workspace swarm narrative
  - `read_workspace_at_path` (read) — read workspace.json pointer + PROJECT.md from absolute path; essential for Cowork's folder-scoped resolution
- All write tools are **path-validated** (resolve symlinks, block `..` traversal, require `startsWith(CORE_DATA_DIR)`) and **audit-logged** to `~/.core/mcp-write-log.md`.
- **`getProjectRoot()`** in `live-artifacts/dm-workshop.html` — uses `window.cowork.askClaude()` (Q7 confirmed, ~2s) to resolve Cowork project folder path. 6-mode robust path extraction handles plain, backtick-wrapped, quote-wrapped, `Path:` prefix, sentence prefix, and trailing-punctuation responses.
- **`unwrap()`** in `live-artifacts/shared/helpers.js` — extracts payload from Cowork's standard MCP envelope (`content[].text(JSON)`) and 3 fallback shapes. Applied to every `callTool` result.
- **JS wrappers** in `helpers.js` for all 17 MCP tools (8 read + 9 new).

### Changed — iteration-2 work

- **`mcp-server-node/server.mjs` SERVER_VERSION 1.0.0 → 1.1.0.**
- **`read_workshop_state` accepts optional `project_path` parameter** — when supplied, resolves the workspace from the filesystem directly instead of falling back to `list_workspaces().most_recent`. Closes iteration-1 F5.
- **`live-artifacts/shared/helpers.js` `callTool()` corrected to 2-arg `callMcpTool(fullName, args)` signature** (was incorrect 3-arg form). The 2-arg form is empirically validated against iteration-1 dm-workshop.html. Closes iteration-1 F4 on the call-site.

### Iteration-1 Findings Status

- **F1 (HIGH) `~/.core/` writes blocked by Cowork policy** — write-tool infrastructure complete (this release); skill-layer Cowork detection + write-routing (in `protocols/startup.md` + `protocols/data-storage.md`) still BLOCKED pending `/core` adversarial review. Briefing drafted at `outputs/2026-05-11/cowork-write-routing-review-briefing.md` (CORE dev repo).
- **F2 (MEDIUM) MCP server read-only** — closed.
- **F3 (POSITIVE) Live Artifact pipeline works** — unchanged; no regression.
- **F4 (DOCS GAP) `callMcpTool` envelope wrapping** — closed.
- **F5 (UX/ARCH) DM Workshop shows wrong workspace** — closed.

### Changed — carried from prior session-n work

- **MCP server rewritten in Node.js** (`mcp-server-node/server.mjs`) — zero dependencies, vanilla Node using only built-in modules (`fs`, `os`, `path`, `readline`). Replaces the Python/FastMCP implementation as the primary runtime.
- **Three-level capability fallback ladder** (per David's instruction 2026-05-10):
  - **L1**: Node.js + MCP server live → full live dashboard via `mcp__core__*` tools
  - **L2**: Node missing or MCP handshake failed → DM falls back to `mcp__cowork__request_cowork_directory` + file tools; live dashboard with per-session approval
  - **L3**: Even fallback unavailable → DM informs user via chat with install instructions
- **`mcp_server_install.py`** now probes Node availability + end-to-end MCP handshake (3s timeout) instead of installing a Python venv. Capability state persisted to `~/.core/capability.json`; re-probe gated by `CORE_CAPABILITY_REPROBE=1` env var to keep working installs stable.
- **`session_start.py`** emits `[[CORE-CAPABILITY-LEVEL]]` marker so the DM knows which mode to operate in.

### Added — carried from prior session-n work

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
