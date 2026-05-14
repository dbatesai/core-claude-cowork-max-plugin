# Startup Protocol

Read this at the start of every `/core` session before accepting any task.

---

## Phase 0: First-Time Initialization

Run these checks on every startup. Skip creation steps if artifacts already exist.

1. Check `~/.core/` exists. If not, create it.
2. Check `~/.core/index.json` exists. If not, create with empty array `[]`.
3. Check `~/.core/dm-profile.md` exists. If not, create with skeleton sections and pick a name — following the same creative naming convention as `agents/base-protocol.md` (evocative, meaningful, not generic). The profile holds cross-project patterns only — **no project-specific facts**.
4. If `dm-profile.md` exists but has no name, pick one now and persist it.

---

## Phase 0.5: Capability Level Resolution

When running inside a sandboxed harness (Cowork), `~/.core/` writes via Write/Edit may be blocked by the harness's folder-scope policy. Resolve the session's write capability before any phase that writes to `~/.core/`.

1. Read `~/.core/capability.json`. If the file does not exist, treat as `{ "level": 3 }` (chat-only — no host writes).
2. Read environment variable `CLAUDE_CODE_IS_COWORK`. If unset → not Cowork; capability resolution is informational only (Write/Edit works on Claude Code CLI regardless of level).
3. Persist `core_capability_level` (one of `"L1"`, `"L2"`, `"L3"`, `"direct"`) as a session-local value for the rest of the session. Do not re-probe mid-session; capability does not flip during a session.

| `CLAUDE_CODE_IS_COWORK` | `capability.json.level` | `core_capability_level` | What this means |
|---|---|---|---|
| `"1"` | `1` | `"L1"` | Cowork + MCP write tools live. Route `~/.core/` writes through `mcp__core__*` write tools. |
| `"1"` | `2` | `"L2"` | Cowork without MCP. Folder-scoped file tool cannot reach `~/.core/`. Escalate user-visibly on `~/.core/` write attempts; do NOT silently retry Write/Edit (empirically fails per F1). |
| `"1"` | `3` (or missing) | `"L3"` | Cowork with no plugin runtime. Same escalation as L2. |
| unset | (any) | `"direct"` | Claude Code CLI (or other non-Cowork harness). Use Write/Edit as today. |

See `data-storage.md` §"Cowork capability-driven write routing" for the L1 → MCP-tool mapping that governs which write tool to use for each `~/.core/` surface.

---

## Phase 0.7: Backup Auto-Compaction Check

(Added 2026-05-13 per DC-46 BM-DC46-3 — backup trigger for the three-layer compaction architecture. The primary trigger lives in `finalize/SKILL.md` Step 4.7; this phase is the failsafe in case last session's `/finalize` missed it.)

**Purpose.** Detect size overflows on in-scope files BEFORE Phase 1 / Phase 3A tries to read them. If `PROJECT.md` or `IMPROVEMENT_LOG.md` is over-threshold, slice-read for classification and auto-MIGRATE per file-shape, so Phase 3A's "Read `PROJECT.md` in full" precondition holds.

### Procedure

For each in-scope file (`<project>/PROJECT.md`, `<project>/IMPROVEMENT_LOG.md`, plus any file matching the file-shape classifier in `data-storage.md`):

1. **Compute estimated tokens:**
   - `file_size_chars = wc -c <file>` (or `os.path.getsize` equivalent)
   - `per_file_ratio` = lookup last persisted ratio from BM-DC46-7 reports keyed by file path, else `0.30` default
   - `estimated_tokens = file_size_chars × per_file_ratio`
   - `effective_cap = env(CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS) ?? 25000`
   - `threshold = 0.8 × effective_cap`

2. **If `estimated_tokens > threshold`:**
   - Consult `data-storage.md §"File-shape classifier"` for the file's shape.
   - For shapes marked **auto-MIGRATE**: slice-read the file with `Read` offset/limit to classify entries; identify the oldest entries whose removal brings the file under threshold; MIGRATE them to `<file>-ARCHIVE.md` (or `DECISIONS.md` for PROJECT.md §D&R); rewrite the primary file without those entries.
   - For shapes marked **user-gated** (e.g., `~/.core/dm-profile.md`): stage the proposal; do NOT migrate silently; surface at Phase 6 readiness for explicit approval.
   - Write a BM-DC46-7 effectiveness report (`~/.core/swarm-effectiveness/auto-compaction-<workspace-id>-<YYYY-MM-DD>.md`) with `trigger: proactive_startup`. See `finalize/SKILL.md` Step 4.7 for the required report fields.

3. **Surface-as-blocked failsafe.** If `file_size_chars > 100K` (4× the default cap) OR slice-read returns errors during classification, do NOT attempt MIGRATE blindly:
   - Note in Phase 6 readiness: *"Cannot auto-compact `<file>` (`file_size_chars` exceeds 4× cap or slice-read failed); manual re-compaction required at next `/finalize` Step 4.7."*
   - DM proceeds without compaction; the user is informed; Phase 3A may slice-read `PROJECT.md` to extract `§State` for orientation, with the residual disclosed.

### Visibility — show entries, not counts

Path (a) visibility requirement: Phase 6 readiness renders the MIGRATE list as **entries**, not aggregate counts. Format:

> **Auto-MIGRATE performed at startup (Phase 0.7):**
> - `PROJECT.md §D&R` → `DECISIONS.md`: `DC-21: Architecture principles will be expressed as 12 numbered properties…`
> - `PROJECT.md §D&R` → `DECISIONS.md`: `DC-20: README.md, ARCHITECTURE.md, INSTALL.md drop from publish-skill.sh rsync exclusion list.`
> - `IMPROVEMENT_LOG.md` → `IMPROVEMENT_LOG-ARCHIVE.md`: `2026-04-12 — Initial backlog audit.`

Counts alone hide what moved. Entries make the autonomous path honest.

### Routing by `core_capability_level` (Phase 0.5)

- **`"direct"`** — proceed inline; Write/Edit on `<project>/*` and `~/.core/swarm-effectiveness/` works directly.
- **`"L1"`** — `<project>/*` writes go via Write/Edit (project folder is connected); `~/.core/swarm-effectiveness/auto-compaction-*.md` writes route through MCP per `data-storage.md` (currently no `mcp__core__write_swarm_effectiveness` tool — escalate visibly if the BM-DC46-7 report can't be written, but proceed with the MIGRATE on the project file).
- **`"L2"` / `"L3"`** — `<project>/*` Write/Edit still works (project folder is connected per Cowork model); skip the BM-DC46-7 report write with a user-visible warning ("auto-compaction effectiveness report skipped — capability level cannot reach `~/.core/`") and proceed with the MIGRATE.

### What this phase does NOT do

- **Does not run Branch A (content-relevance PRUNE).** Content-relevance triggers fire only at `/finalize` Step 4.7 because they require user approval — Phase 0.7 fires before the user is in the loop on the agenda. If `§State` violates the present-tense rule at startup, surface it as a flag in Phase 6 readiness and let `/finalize` handle it next session.
- **Does not read archives.** Per DC-42 archive-exclusion rule (Phase 3A), `PROJECT-ARCHIVE.md`, `IMPROVEMENT_LOG-ARCHIVE.md`, and `<file>-ARCHIVE.md` are not read at bootstrap. They are WRITE-only from this phase's perspective.

---

## Phase 1: Load Global Identity

1. Read `~/.core/dm-profile.md` in full. This is cross-project only — personality, user relationship patterns, portfolio observations.
2. Read auto-memory from `~/.claude/projects/*/memory/MEMORY.md`. Treat it as scratch cache, not authoritative project state. If auto-memory references project-specific facts, they are verified against `PROJECT.md` in Phase 3A before being acted on.
3. You are now "yourself" — one continuous DM.

---

## Phase 2: Resolve Workspace

Determine which workspace this session belongs to. Resolve deterministically when possible; ask the user only when genuinely ambiguous.

**Resolution order:**
1. Check for `workspace.json` in current working directory → if found, use it (Phase 3A)
2. Check `~/.core/index.json` for workspaces whose `path` matches current directory (prefix match). If exactly one match → Phase 3A. Multiple matches → step 4.
3. If `index.json` has only one workspace → use it (Phase 3A).
4. Multiple workspaces could apply. Sort by `last_active` descending. Ask: *"Last session was on **[workspace name]**. Continuing there, or switching to [other workspace(s)]?"* → Phase 3A after confirmation.
5. No match, no workspaces → Phase 3B (New Workspace).

After resolution: update `last_active` in `index.json`. **Routing per `core_capability_level`** (set in Phase 0.5):
- `"L1"` → call `mcp__core__update_workspace_last_active({workspace_id, timestamp})`.
- `"direct"` → Write/Edit `~/.core/index.json` as today.
- `"L2"` / `"L3"` → escalate: surface a one-line warning to the user explaining that workspace `last_active` cannot be updated in this session (capability level prevents `~/.core/` writes) and continue without the update. Do not silently retry Write/Edit.

**Workspace layer separation:** Project synthesis lives in the project folder (`<project>/PROJECT.md`). Workspace operational meta lives at `~/.core/workspaces/<id>/`. The `workspace.json` in the project folder is a pointer; the full manifest is at `~/.core/workspaces/<id>/workspace.json`.

---

## Phase 3A: Returning Workspace

1. Read `workspace.json` (project-folder pointer) to get the workspace ID and data path.
2. **Read `<project>/PROJECT.md` in full.** This is the DM's sole authoritative read surface for project facts — identity, state, people, moves, decisions, risks, notes. Every section counts.
3. **Read `<project>/inbox.md` if it exists.** Raw pending items — promote worthwhile facts into `PROJECT.md` on user review, then strike/delete the inbox entries.
4. Read `~/.core/workspaces/<id>/workspace.json` manifest for cross-project metadata (last-session date, timestamps) only. Do **not** read project facts from here — there aren't any.
5. **Legacy-file exclusion rule:** `~/.core/workspaces/<id>/` may contain `raid-log.md`, `decision-log.md`, `next-session.md`, or `handoffs/` from the pre-2026-04-21 structure. **Do not read these.** If they exist and `PROJECT.md` does not, surface the mismatch to the user and offer to migrate before proceeding. Legacy files are archival only — not project state.
6. **Archive exclusion rule (DC-42, 2026-05-13):** `<project>/PROJECT-ARCHIVE.md` and `<project>/IMPROVEMENT_LOG-ARCHIVE.md` (if present) are **not read at bootstrap**. They are single-WRITE surfaces created by `/finalize` Step 4.7 to preserve historically-significant entries that the user chose to retain when §State / §Moves / IMPROVEMENT_LOG were compacted. `PROJECT.md` remains the sole authoritative read surface for project facts; `IMPROVEMENT_LOG.md` remains the sole authoritative read surface for skill-evolution context. The archives hold what the user chose to migrate; they are not project state and they are never read at orient. Per DC-19 read-side singularity: only the read side matters; write-side siblings are fine.
7. **Do not read handoff bodies at bootstrap.** Handoffs in `<project>/handoffs/` are narrative logs for the human reader. Facts worth keeping were promoted into `PROJECT.md` at session close. Reading handoffs re-anchors the DM on narrative framing and can resurrect user-deleted facts.
8. Check-in with user: summarize the state you read from `PROJECT.md` (not from handoffs, not from auto-memory). Confirm scope is unchanged. Surface elapsed-time signals from Phase 5. Present §Moves top priorities as the session agenda.

---

## Phase 3B: New Workspace

1. **Interview the user** — do not skip or abbreviate:
   - Problem or task? Scope? Timeline? What does success look like?
   - Constraints? Stakeholders? What has already been tried?
2. **Scaffold the project-folder synthesis** — create `<project>/PROJECT.md` with the six sections populated from the interview:
   - **§What & Why** — one paragraph capturing identity, outcome, constraints, deadline, owner.
   - **§State** — current status; if solo or no external systems, declare thin sections here.
   - **§People** — stakeholders from the interview. Solo projects omit and declare in §State.
   - **§Moves** — initial priorities as a checkbox list. Reference external tracker if backlog is large.
   - **§Decisions & Risks** — initial constraints and known risks from the interview, dated.
   - **§Notes** — architectural principles, constraints, or context that doesn't fit elsewhere.
3. Optionally create `<project>/inbox.md` if the user expects external-source pulls.
4. Create `<project>/workspace.json` pointer (project-folder write; no capability routing needed — Cowork's folder-scoped file tool reaches the project folder):
   ```json
   {
     "workspace_id": "<generated-id>",
     "name": "<descriptive name>",
     "created": "<timestamp>",
     "data_path": "~/.core/workspaces/<workspace-id>/"
   }
   ```
5. Create the full manifest at `~/.core/workspaces/<workspace-id>/workspace.json` (see `schemas/workspace.md` for required fields). **Routing per `core_capability_level`:**
   - `"L1"` → call `mcp__core__write_workspace_manifest({workspace_id, manifest})`.
   - `"direct"` → Write the file directly.
   - `"L2"` / `"L3"` → escalate user-visibly; the workspace scaffold cannot complete in this session.
6. Create `~/.core/workspaces/<workspace-id>/swarm-narrative.md` (empty — populated after first swarm). **Routing per `core_capability_level`:**
   - `"L1"` → call `mcp__core__write_swarm_narrative({workspace_id, content: "", append: false})`.
   - `"direct"` → Write the file directly.
   - `"L2"` / `"L3"` → escalate.
7. Register in `~/.core/index.json`. **Routing per `core_capability_level`:**
   - `"L1"` → call `mcp__core__register_workspace({workspace_id, name, path, last_active})`.
   - `"direct"` → Read `index.json`, append the new entry, Write it back.
   - `"L2"` / `"L3"` → escalate.
8. **Do not scaffold** `raid-log.md`, `decision-log.md`, `next-session.md`, or `handoffs/` under `~/.core/workspaces/<id>/`. These no longer exist as separate files — their content is §State, §Moves, §Decisions & Risks in `PROJECT.md`, and project-folder `handoffs/`.

---

## Phase 3C: Session Agenda

The session agenda is `PROJECT.md §Moves`. There is no separate `next-session.md` — that was the pre-2026-04-21 structure.

**Agenda maintenance is continuous:**
- At session start: read §Moves, present top priorities as the agenda, resolve high-priority items before implementation work.
- During session: when new risks, decisions, open questions, or commitments emerge, update `PROJECT.md` directly (the right section for the fact type). The session can update synthesis in real time.
- At session end: ensure §Moves reflects next-session priorities for the DM to pick up.

**Steps:**
1. From `PROJECT.md §Moves`, identify the top 3–5 active priorities (checkbox items without deferral notes).
2. Cross-reference §Decisions & Risks for any risk with a stale `last-reviewed` date (see Phase 5). Add to agenda.
3. Present the agenda during Phase 6 (Confirm Readiness). It is the first thing the user sees after workspace identity — before accepting any task.
4. Resolve high-priority agenda items before implementation work. The user can defer explicitly, but the DM does not skip silently.

**Calendar integration:** If MCP tools provide access to the user's calendar, the DM may suggest scheduling regular sessions. The DM proposes — the user approves.

**Agenda sources:** `PROJECT.md §Moves`, stale risks in §Decisions & Risks, user-promoted items from `inbox.md`, elapsed-time escalations from Phase 5, cross-workspace observations from `dm-profile.md`.

---

## Phase 4: Reconcile Between-Session Activity

| Source | Check |
|---|---|
| Notification responses | Check for user responses to between-session notifications |
| External monitoring | Check MCP-connected tools for workspace-relevant updates; stage raw pulls to `<project>/inbox.md` for review |
| Elapsed time signals | Calculate and apply time-based signals (see Phase 5) |

---

## Phase 5: Apply Elapsed Time Signals

Read `last-reviewed` dates from `PROJECT.md §Decisions & Risks` and session timestamps from `~/.core/workspaces/<id>/workspace.json`.

| Signal | Calculation | Effect |
|---|---|---|
| Time since last session | `now - last_session_end` | >7 days: re-confirm priorities. >30 days: treat as near-new, re-interview. |
| Time until next deadline | `next_deadline - now` | <2 sessions of time: escalate urgency. Past deadline: surface immediately, do not bury. |
| Time since risk last reviewed | `now - risk.last_reviewed` | >3 sessions or >14 days: flag as stale, force re-evaluation before proceeding. |
| Time since assumption validated | `now - assumption.last_validated` | >5 sessions or >14 days: confidence decays. Surface for revalidation. |
| External-source-derived claim age | `now - source.fetched_at` | Task tracker / chat: >24h, disclose and consider re-fetch. Document store: >14d, disclose. See `data-storage.md` staleness table. |

Apply before presenting readiness. If any signal triggers escalation, lead with it.

---

## Phase 6: Confirm Readiness

Make workspace identity obvious. Present:
1. Workspace name and ID
2. What `PROJECT.md` currently says in §State (one or two sentences — not a recap of every section)
3. Active risks from §Decisions & Risks (count and top priority by impact)
4. Elapsed time signals that triggered escalation (from Phase 5)
5. Session agenda — top §Moves priorities
6. **Auto-compaction performed at startup** (from Phase 0.7, if any) — entries (not counts) of what moved, per path (a) visibility rule. Skip this line if Phase 0.7 found no over-threshold files.
7. **Ready for task** — only after agenda topics are resolved or explicitly deferred

Narrate what you found: *"Picking up on [workspace]. Last session closed on [date]. `PROJECT.md` says we're at [state]. Top of §Moves is [X]. One stale risk flagged: [Y]. Ready."*

If Phase 0.7 auto-MIGRATEd entries, append the entries (not aggregate counts) immediately after the agenda line — see Phase 0.7 §Visibility for the format.

**What NOT to say:** Do not recite handoff content. Do not reference auto-memory as authoritative. Do not read-and-summarize session logs. The DM's report on project state comes from `PROJECT.md` — that is the user-controlled surface.

---

## Phase 7: Early Handoff (Long/Autonomous/Complex Sessions)

Write a handoff stub **immediately after completing orientation** — before beginning substantive work — when any of these apply:

- Session is explicitly autonomous (user unavailable for questions)
- Session will process multiple large files or spawn complex swarms
- Session involves many sequential tasks where auto-compact could interrupt mid-flow
- User explicitly requests an early handoff

**When to write it:** After Phase 6, before the first Write/Edit/Task tool call that produces a durable artifact.

**What the stub must contain:**

```
# Session Handoff — [date] ([session letter — b, c, d…])

> **Status:** Early handoff stub — written before auto-compact, will be updated at session close.

## What Was Done (at time of writing)
[Orientation findings, key decisions read, probe results, etc.]

## Key Findings / State
[The highest-value context that would be hard to reconstruct after compaction]

## In Progress
[What's being worked on right now]

## Open Questions
[Empirical unknowns, deferred decisions, items needing David's input]

## Next Steps
[If session is interrupted here, what the next session should do first]
```

**Naming:** `handoffs/handoff-<YYYY-MM-DD><letter>.md` — use the next available letter suffix (e.g., if `handoff-2026-05-09d.md` exists, write `handoff-2026-05-09e.md`).

**Update during session:** Append findings as they emerge. The stub is a living document until `/finalize` replaces it with the full session-close handoff.

**What NOT to do:** Don't treat the stub as the final handoff. `/finalize` still runs at session end and overwrites/upgrades the stub with the complete record.
