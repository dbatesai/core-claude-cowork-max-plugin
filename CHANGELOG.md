# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.2.0] — 2026-05-13

Observatory feature Phase 1: CORE Dashboard rename + `update_swarm_status` MCP
tool + Observatory Panel scaffolding + Swarm Live View data API. Phase 2 visual
design awaits a UI Excellence /core swarm; Phase 1 ships placeholder rendering
behind a complete data path. Bundles the DC-42 skill protocol changes (§State
present-tense entry-shape rule, archive-exclusion at bootstrap, /finalize
Step 4.7 compaction sweep).

### Breaking Changes

- `live-artifacts/dm-workshop.html` renamed to `live-artifacts/core-dashboard.html`. Existing Cowork conversations referencing the old artifact path must re-open the CORE Dashboard.
- MCP tool `read_workshop_state` renamed to `read_dashboard_state`.

### Added — Observatory feature (Phase 1)

- **`update_swarm_status` MCP tool** — patch-semantic write that lets the DM track active swarm state in workspace manifests during execution. Status lifecycle: `idle | running | halted | complete`. Lifecycle timestamps (`started_at`, `completed_at`) reset on fresh swarm starts to avoid stale state when a workspace is reused across multiple swarms. Tracked at `~/.core/workspaces/<id>/workspace.json` `current_swarm`.

- **`read_dashboard_state` extended** — now returns `workspaces_with_swarm`: a list of all workspaces with their current swarm status, sorted by attention model (halted → running → complete → idle). Borrowed from Anthropic's Agent View attention pattern.

- **`swarm_artifact_id` workspace manifest field** — top-level reference to the Cowork Swarm Live View artifact. Persists across multiple swarm runs in the same workspace; survives Cowork app restart (Q8 CROSS-RESTART-PASS).

- **CORE Dashboard Observatory Panel** — new section in `live-artifacts/core-dashboard.html` below the workspace shelf. Shows all active swarms across workspaces, halted-first. Empty state: "No active swarms." Workspace shelf sort also updated to surface halted/running workspaces first when swarm data is present.

- **Swarm Live View data API scaffolding** — `window.CORE.swarmView.update()` accepts two new fields: `agentHierarchy: [{name, role, parent}]` (DM-rooted agent tree) and `phaseEvents: [{time, event}]` (milestone log, last 20 retained, rendered newest-first). Visual design intentionally deferred to a Phase 2 UI Excellence swarm; current rendering is plain text in `<pre>` placeholders.

- **Execution protocol — Swarm State Tracking section** — `~/.claude/skills/core/protocols/execution.md` now documents the six moments where the DM calls `update_swarm_status` (Phase 1 spawn, phase transitions, halt/resume, accept, graceful halt) plus a Cowork-only sub-protocol for the Swarm Live View artifact lifecycle (create at Phase 0, update at transitions, finalize at close).

- **Workspace schema documented** — `~/.claude/skills/core/schemas/workspace.md` now has full documentation for the pointer/manifest two-file pattern, including the new `current_swarm` field and `swarm_artifact_id`. References the MCP tools by their dispatch keys (`update_swarm_status`, `read_dashboard_state`) — not the internal JS function names.

#### Phase 2 (deferred)

Visual design for CORE Dashboard Observatory Panel + Swarm Live View hierarchy/phase-log rendering awaits the UI Excellence swarm output at `outputs/2026-05-12/core-dashboard-ui-excellence-swarm-briefing.md`. Phase 1 ships the data path with placeholder rendering; Phase 2 ships the designed treatment.

---

## [1.1.3] — 2026-05-12

Rolls iteration-3 findings (F8 vibe-log ordering, F10 `finalize` harness
detection), the iteration-4 follow-up finding (F6b `read_workshop_state` regex
realignment), and the F9 install-time permission verdict (DC-43 — A-REVISED
Option 1+C1+C3 baseline with Option 5(a) PermissionRequest message-augmentation
hook) into one release. Skipped intermediate v1.1.2 since no v1.1.2 zip ever
shipped — v1.1.1 → v1.1.3 is a single release boundary.

### Added (v1.1.3 work — F9 verdict Option 5(a))

- **`PermissionRequest` augmentation hook — Q-F9-1 FAVORABLE, F9 verdict
  Option 5(a) green-lit.** New cross-platform Python hook at
  `scripts/permission_request.py` (with `.sh` and `.cmd` shims) registered in
  `hooks/hooks.json`. Fires when Claude Code surfaces a permission request inside
  a Cowork session (empirically verified for Read / Write / Edit / Glob / Grep /
  `mcp__cowork__*` per Q-F9-1 probe 2026-05-13 — payloads captured in
  `outputs/2026-05-12/q-f9-1-findings.md` in the CORE dev repo).

  **What it does:** parses the stdin JSON payload Claude Code emits (tool_name,
  tool_input, permission_suggestions), maps to a structured advisory keyed off
  the most specific suggestion shape (addDirectories → outside-connected-folders;
  addRules → rule-grant-required or cowork-mcp-approval depending on tool family;
  setMode acceptEdits → edit-mode-required; bash → bash-approval; otherwise
  generic permission-required), and emits a `[[CORE-PERMISSION-CONTEXT-BEGIN]]
  … [[CORE-PERMISSION-CONTEXT-END]]` block to stdout. Cowork injects stdout into
  the DM's session context, so the DM (Keel) sees the advisory BEFORE the
  harness's auto-refusal lands and can craft a clear plain-language message to
  the user about what scope grant would unblock the action.

  **What it deliberately does not do (pay-to-play principle, David
  2026-05-12):** never auto-approves; never blocks or denies; never modifies the
  permission decision; never builds alternate code paths to fake functionality on
  denial. Passive augmentation only. If the user denies, the action fails
  normally and the DM's advisory explains what won't work and re-asks. Buyer
  beware.

  **Cowork-only.** Gated on `CLAUDE_CODE_IS_COWORK=1`; silent no-op on Claude
  Code CLI so the augmentation doesn't degrade non-Cowork sessions. Uses
  `permission_suggestions` from the harness payload verbatim wherever possible
  — Anthropic already computes which grant would unblock; the hook lifts that
  into agent-facing copy without re-deriving it.

  **Audit log** at `~/.core/logs/permission-events.md` (append-only markdown)
  captures every fire for v1.1.3 acceptance testing — including the bounded gap
  for Bash (which did not fire in the Q-F9-1 probe; v1.1.3 acceptance probe will
  re-test from a clean settings state to determine whether sandbox bash is
  pre-approved at the harness layer or only first-ever-bash fires).

  **Test:** `scripts/test_permission_request.py` (11 assertions covering the four
  Q-F9-1 captured payloads plus synthetic edge cases — pay-to-play discipline
  check for forbidden decision verbs, missing-tool-name silence, malformed-JSON
  defense, non-Cowork silence, audit-log persistence). Runs in ~0.5s; integrated
  with the rest of the test suite. *Add to CI hook-scripts job manually:* append
  `scripts/permission_request.py scripts/test_permission_request.py` to the
  py_compile line and add a new step `python scripts/test_permission_request.py`
  with `CORE_DATA_DIR: ${{ runner.temp }}/core-permission-test` (workflow edit
  blocked by safety hook in this session; applies cleanly on retry with explicit
  approval).

### Fixed

- **`read_workshop_state` regex realignment — F6b (LOW) from Cowork iteration-4
  test.** `mcp-server-node/server.mjs` `tool_read_workshop_state` had two
  inline regexes separate from `extractSection`. The `project_name` regex
  `/^## §?\s*What & Why\s*\n+(.+)/m` grabbed the first prose line after the
  §What & Why heading — returning description text instead of the project's
  name. The `project_state_summary` regex
  `/^## §?\s*State\s*\n+[-*]\s*\*\*(.+?)\*\*/m` required the first State bullet
  to lead with `**bold**` content — which matched the CORE-project convention
  but returned `null` on §-prefixed PROJECT.md files without that exact format
  (e.g., the test-core-plugin workspace). Fix: `project_name` resolves from
  `workspace.json.name` (index-attested) first, then falls back to the
  PROJECT.md `# H1` title. `project_state_summary` uses `extractSection` (now
  §-aware) and returns the first non-empty bullet's content — preserves the
  leading `**bold**` extraction when present (backwards-compat with CORE
  convention) and otherwise returns the first sentence up to 120 chars. Unit
  test at `mcp-server-node/test-workshop-state.mjs` (6 assertions across three
  PROJECT.md shapes: §-prefixed without leading bold; §-prefixed CORE-style
  with leading bold; H1-only fallback when `workspace.json` is missing).

- **`finalize` harness detection — F10 (MEDIUM, structural) from Cowork
  iteration-3 test.** `skills/finalize/SKILL.md` gained a new "Step 0: Harness
  Resolution" that reuses the DC-41 precedent (env `CLAUDE_CODE_IS_COWORK` +
  `~/.core/capability.json`) to set `core_capability_level`. Steps 3 (improvement
  log), 4 (memory), 4.5 (dream cycle), 6 (sync/publish) gained routing tables —
  the L0 (`"direct"`) paths run unchanged; L1+/Cowork routes blocked steps to a
  `blocked_steps` list with concrete pending content. Step 2 (handoff) gained a
  conditional "Steps That Could Not Complete" section template; the closing
  declaration names blocked steps explicitly so the next compatible-harness
  session sees what didn't complete. Step 3's path was also corrected to the
  project-root `<project>/IMPROVEMENT_LOG.md` per `CLAUDE.md` (it had been
  pointing at `~/.claude/skills/core/IMPROVEMENT_LOG.md`, which doesn't exist).
  Step 6 now references the cross-platform `refresh_bundled_skills.py` for
  plugin-bundled skills alongside the existing rsync flow. This step sets the
  precedent for any future harness-aware finalize work — DC-42's eventual prune
  step should reuse the same `core_capability_level` resolution.



- **Vibe-log ordering — F8 (MEDIUM) from Cowork iteration-3 test.**
  `mcp-server-node/server.mjs` `tool_append_vibe_log` now prepends new entries
  to the top of `~/.core/vibes/vibe-log.md` instead of appending, and
  `tool_read_vibe_log` trusts file order instead of date-sorting. Together they
  guarantee `most_recent_vibe` is the entry that was just written, regardless of
  date-string ties or backfill inserts. Prior behavior: append + date-sort with
  stable file-order tiebreaker surfaced the *oldest* entry of the most-recent
  date as `most_recent_vibe`. Unit test at `mcp-server-node/test-vibe-log.mjs`
  (11 assertions; spawns the MCP server with a temp `CORE_DATA_DIR` and
  exercises `append → append (same date) → read → backfill older date → read`).
  Existing `~/.core/vibes/vibe-log.md` deployments need one-time reversal — the
  new tools cannot read meaning into pre-fix file order. (Backup before reverse:
  `vibe-log.md.pre-f8-migration.bak`.)

---

## [1.1.1] — 2026-05-11

Iteration-2 follow-up release. Addresses the two new findings from the
iteration-2 Cowork empirical test (F6 section parser, F7 vibe label) and applies
the DC-41 `/core` adversarial-review verdict (A-REVISED) for skill-protocol
write routing.

### Fixed

- **Section parser §-prefix support (Finding 6 from Cowork iteration-2 test).**
  `mcp-server-node/server.mjs` `extractSection()`, `countOpenRisks()`, and
  `read_workshop_state` inline regexes for `project_name` +
  `project_state_summary` now accept the CORE PROJECT.md convention `## §State`
  alongside plain `## State`. Same edit also fixed a multiline-`$` truncation
  bug that would have appeared as the next iteration finding once §-prefix
  matching landed.
- **Cosmetic — vibe display label rename (Finding 7(p) from Cowork iteration-2
  test).** `live-artifacts/dm-workshop.html` now renders the vibe as
  `"Latest vibe (any project) — <label>"` with a `title` attribute so the
  global-scope reality is honest. The schema-level fix (option n —
  `workspace_id` attribution on vibe entries) is deferred to the next vibe-log
  refactor.

### Changed

- **Skill protocol — Cowork capability-driven write routing (DC-41).** The
  bundled CORE skill (`skills/core/protocols/`) now routes `~/.core/` writes
  through the bundled MCP server's `mcp__core__*` write tools when running in
  Cowork at capability level 1 (per `~/.core/capability.json`). At L2/L3 or
  non-Cowork sessions, behavior is unchanged.
  - `protocols/startup.md` gains a "Phase 0.5: Capability Level Resolution"
    section that reads `~/.core/capability.json` (defaults to L3 if missing)
    and resolves `core_capability_level` for the session. Phases 2 and 3B
    consume the resolved level for `~/.core/` writes.
  - `protocols/data-storage.md` gains a "Cowork capability-driven write
    routing" subsection (canonical 7-rule sheet untouched) with the L1
    → `mcp__core__*` mapping for the 8 routed surfaces (`index.json`
    register/touch/remove, workspace manifest, swarm narrative, dm-profile
    append/replace, vibe-log).
  - `skills/vibecheck/SKILL.md` Step 4 routes `~/.core/vibes/vibe-log.md`
    writes through `mcp__core__append_vibe_log` at L1.
  - **Failure posture:** no silent fallback to Write/Edit on `~/.core/` writes
    in Cowork (empirically blocked per iteration-1 F1); escalate user-visibly
    with a one-line warning naming the tool and surface.
  - Subsection is structurally relocation-eligible if DC-39 (e) closes
    pro-hook-layer.
- **Bundled skill snapshots refreshed** (`skills/CHECKSUMS.txt` updated) to
  pick up the protocol + vibecheck changes.

### Bumped

- Plugin `version` 1.1.0 → 1.1.1.
- MCP server `SERVER_VERSION` 1.1.0 → 1.1.1.

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
