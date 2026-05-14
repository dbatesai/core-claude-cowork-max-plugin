# Data Storage Protocol

**Read before each Write/Edit/MultiEdit/NotebookEdit tool invocation** — and before any session close that will produce new files. Consult the 7-rule routing sheet first; if the artifact maps cleanly, proceed with a Pre-Write Declaration. If it doesn't map, follow the Uncovered-Type Protocol.

---

## Routing — 7-Rule Canonical Sheet

The user-facing routing rules. All 7 fit in working memory. Mirror of this table lives in `<project>/PROJECT.md §Notes`.

| If the artifact is… | It lands at… |
|---|---|
| **Project facts** — decisions, risks, people, state, notes | `<project>/PROJECT.md` (appropriate section) |
| **Handoff narrative** — session-close, human reader | `<project>/handoffs/<YYYY-MM-DD>-<topic>.md` |
| **Session log** — per-agent operational record | `<project>/sessions/<YYYY-MM-DD>/<agent>-log.md` |
| **Swarm output** — synthesis, review report, deliverable | `<project>/outputs/<swarm-type>-<topic>-<YYYY-MM-DD>.md` |
| **Dev-meta doc** — design, architecture, navigation aid, compact companion | `<project>/docs/<topic>.md` |
| **DM cross-project state** | `~/.core/` (pick subfolder: `agents/` `task-configs/` `swarm-effectiveness/` etc.) |
| **Skill product** | `~/.claude/skills/core/` — **ONLY** with declared `intent: skill-edit` |

*Three conceptual rings organizing the 7 rows:*
- **Project ring (rows 1–5):** version-controlled, user-editable, user-deletable.
- **DM meta ring (row 6):** machine-local, survives project deletion, no project-specific facts.
- **Skill ring (row 7):** read-only at runtime; written only via explicit skill-edit intent.

### Per-category artifact lists

Use these to determine which row an artifact belongs to before writing. If an artifact type is not in any list → Uncovered-Type Protocol.

| Row | Concrete artifact types |
|---|---|
| **1 — Project facts** | Decisions, risks, people updates, §Moves items, §State updates, §Notes architectural principles |
| **2 — Handoff** | Session-close narrative, context-window handoff docs, future-session briefs |
| **3 — Session log** | Per-agent session logs, DM session log, write ledger |
| **4 — Swarm output** | DM synthesis reports, adversarial review outputs, briefing documents, generated drafts, sub-skill syntheses |
| **5 — Dev-meta doc** | Design specs, architecture docs, compact companion summaries, editorial references, navigation aids, swarm-output compact |
| **6 — DM cross-project state** | Agent configs, task-type configs, swarm-effectiveness reports, dream-cycle retrospectives, research library entries, dm-profile updates |
| **7 — Skill product** | SKILL.md, protocols, schemas, agents, templates, references, scripts — anything in `~/.claude/skills/core/` |

---

## Cowork capability-driven write routing

**When does this apply.** This subsection governs `~/.core/` writes only when the session is in Cowork (`CLAUDE_CODE_IS_COWORK == "1"`). On Claude Code CLI and other non-Cowork harnesses, the canonical 7-rule sheet above is sufficient — `~/.core/` is a normal filesystem path and direct Write/Edit works. Read `protocols/startup.md` §"Phase 0.5: Capability Level Resolution" for how `core_capability_level` gets set.

**Why this subsection exists.** Cowork's folder-scoped file-tool policy classifies `~/.core/` as application-internal and blocks Write/Edit access (empirically confirmed iteration-1 F1). The bundled MCP server runs host-side and is unblocked. When the MCP server is live (capability level 1), all `~/.core/` writes route through its `mcp__core__*` write tools. When the MCP server is unavailable (L2/L3), `~/.core/` writes cannot complete in the session — escalate honestly to the user; do not silently retry Write/Edit (the empirical fallback path that does not exist).

**Routing table — L1 mapping for the `~/.core/` write surfaces:**

| `~/.core/` surface | At `core_capability_level == "L1"` use MCP tool | At `"direct"` use | At `"L2"` / `"L3"` |
|---|---|---|---|
| `~/.core/index.json` (register a workspace) | `mcp__core__register_workspace({workspace_id, name?, path?, last_active?, delivery_risk?})` | Write/Edit | escalate |
| `~/.core/index.json` (touch `last_active`) | `mcp__core__update_workspace_last_active({workspace_id, timestamp?})` | Write/Edit | escalate |
| `~/.core/index.json` (remove a workspace) | `mcp__core__unregister_workspace({workspace_id})` | Write/Edit | escalate |
| `~/.core/workspaces/<id>/workspace.json` | `mcp__core__write_workspace_manifest({workspace_id, manifest})` | Write/Edit | escalate |
| `~/.core/workspaces/<id>/swarm-narrative.md` | `mcp__core__write_swarm_narrative({workspace_id, content, append?})` | Write/Edit | escalate |
| `~/.core/dm-profile.md` (append a bullet to a section) | `mcp__core__append_dm_profile_entry({section, entry})` | Write/Edit | escalate |
| `~/.core/dm-profile.md` (replace a full section) | `mcp__core__update_dm_profile_section({section, content})` | Write/Edit | escalate |
| `~/.core/vibes/vibe-log.md` (append entry) | `mcp__core__append_vibe_log({date, vibe, label?, ascii_art?})` | Write/Edit | escalate |

**Failure posture.** If an MCP write call fails (tool returns an error, server unreachable, etc.) in a Cowork+L1 session: emit a one-line user-visible warning naming the tool, the surface that was supposed to receive the write, and the error. **Do not silently retry Write/Edit** — F1 empirically blocks Write/Edit on `~/.core/` in any Cowork session regardless of which tool the DM uses. The user-visible warning is the failure boundary; the recovery action is the user's call (re-probe with `CORE_CAPABILITY_REPROBE=1`, restart Cowork to reload MCP, file a ticket).

**Audit trail.** Every successful MCP write is logged by the server to `~/.core/mcp-write-log.md`. The DM does not need to write to that log; the MCP server handles it.

**Subsection is structurally relocation-eligible.** This subsection sits outside the canonical 7-rule sheet by design. If the DC-39 second `/core` lands option (e) (enriched hook protocol routing write surfaces at the hook layer), this entire subsection becomes the migration unit — the canonical 7-rule sheet is unaffected. Re-decision trigger preserved per DC-41.

---

## Auto-Compaction Strategy

(Added 2026-05-13 per DC-46. Generalizes DC-42's content-relevance compaction with a size-driven autonomous MIGRATE path. Path (a) — autonomous-with-visibility — selected by user 2026-05-13.)

### Three-layer compaction architecture (BM-DC46-3)

Files that grow monotonically (synthesis, append-only logs) need a mechanism that prevents bootstrap from silently sliding into slice-read when files exceed the harness's Read tool cap. Three layers, defense-in-depth:

| Layer | Where | When | Action |
|---|---|---|---|
| **Primary trigger** | `finalize/SKILL.md` Step 4.7 | session close | proactive size-check before next bootstrap; auto-MIGRATE or surface for user approval per file-shape |
| **Backup trigger** | `startup.md` Phase 0.7 | session start | failsafe if primary missed last session; slice-read + classify + MIGRATE |
| **Last-resort (reactive)** | DM Read-error rule (this section) | mid-session | surface error; DM proceeds without that file |

**Reactive trigger as DM rule.** Match regex `/File content \(\d+ tokens\) exceeds maximum allowed tokens \(\d+\)/` on Read tool errors. When this regex fires:
1. Surface the error to the user (don't bury).
2. Note that primary and backup proactive layers failed for this file — the auto-compaction system has a gap.
3. Propose manual re-compaction (`/finalize` Step 4.7 with the file path called out).
4. Write a BM-DC46-7 effectiveness report with `trigger: reactive_error` so the dream cycle can investigate.

Defense-in-depth; should rarely fire if proactive layers work.

### Measurement primitive (BM-DC46-1, BM-DC46-2)

- **Effective cap** (BM-DC46-2): `effective_cap = env(CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS) ?? 25000`. Anthropic's default Read tool cap; officially tunable via env var.
- **Threshold**: `threshold = 0.8 × effective_cap`. With the default cap, threshold = 20K tokens.
- **Per-file ratio** (BM-DC46-1): `estimated_tokens = wc -c <file> × per_file_ratio`. Default `per_file_ratio = 0.30`. **Measure per file** at first cap-overflow event: capture `error_token_count / file_char_count` from the Read tool's error envelope; persist to the BM-DC46-7 effectiveness report keyed by file path; use measured ratio thereafter. Empirical measurements so far:
  - `PROJECT.md`: 0.337 (Glean 2026-05-13)
  - Other files: unmeasured; populate after first compaction.

The 0.30 default is intentionally conservative — real headroom at the 20K threshold under default ratio is ~1.3K tokens, not 5K. The per-file mechanism prevents the default from being wrong for non-PROJECT.md content with different char-per-token profiles.

### File-shape classifier (BM-DC46-5)

Each file type has a different compaction strategy. The classifier extends the 7-rule routing sheet's conceptual model to write-time growth behavior. Primary and Backup triggers consult this table to decide auto-MIGRATE vs. user-gated.

| Shape | Examples | Auto-MIGRATE? | Strategy |
|---|---|---|---|
| **Synthesis (project)** | `<project>/PROJECT.md` | yes (auto) — §D&R only | MIGRATE oldest §D&R entries to `DECISIONS.md` sibling. §State + §Moves use content-relevance triggers (DC-42 / Branch A). |
| **Synthesis (cross-project)** | `~/.core/dm-profile.md` | **user-gated** | Cross-project visibility — surface proposed entries; require explicit approval. Not silent (cross-project surface differs from project surface in user-control implications). |
| **Append-only log (project)** | `<project>/IMPROVEMENT_LOG.md` | yes (auto) | Rotate oldest N entries to `IMPROVEMENT_LOG-ARCHIVE.md` (DC-42 count-based default N=10; size-driven uses N-to-fit-threshold). |
| **Append-only log (cross-project)** | `~/.core/workspaces/<id>/swarm-narrative.md`, `~/.core/logs/permission-events.md`, `~/.core/vibes/vibe-log.md` | yes (auto) | Rotate oldest entries to `<file>-ARCHIVE.md`. Cross-project but log-shaped — entries are operational events, not synthesis facts; auto-rotate is safe. |
| **Volatile staging** | `~/.core/index.json`, `<project>/inbox.md` | n/a | Designed to never grow large (index is a registry; inbox is drained on review). No compaction logic. If one of these ever triggers, the right fix is investigating WHY it grew, not adding a compaction rule. |

### DELETE procedure (path (a))

MIGRATE preserves entries in archive files (read-side singular per DC-19; single-WRITE; never read at bootstrap). DELETE is the user's explicit action — the user-control invariant treats DELETE as the channel that permanently removes a fact:

1. User edits `<file>-ARCHIVE.md` (or `DECISIONS.md` for graduated §D&R) directly and removes the entry.
2. User commits the change.
3. Fact is now gone from the entire write surface. Auto-memory rebuilds from current synthesis on next bootstrap; the deleted fact does not reappear.

**DM-assisted DELETE.** The user can ask "show me migrated entries from session X" → DM Bash-greps the archive and presents. Removal is still the user's edit + commit. The DM never auto-DELETEs from the archive.

**Future enhancement** (not blocking, tracked in §Moves): a `/core delete-archived` subcommand under the sub-skill layout (DC-47) for ergonomic archive management.

### BM-DC46-7 effectiveness reports

Per the universal-self-improvement architectural invariant (`SKILL.md`), auto-compaction writes per-trigger effectiveness reports to `~/.core/swarm-effectiveness/auto-compaction-<workspace-id>-<YYYY-MM-DD>.md`. The dream cycle (Phase 3) scans these reports and fires the path-(a)→(b) re-decision trigger if cumulative MIGRATE exceeds 5 entries since last review. See `finalize/SKILL.md` Step 4.7 for the report's required fields.

---

## Pre-Write Declaration (PWD)

**Before every non-exempt Write/Edit/MultiEdit/NotebookEdit call**, emit one line in user-visible chat:

```
Writing to: <abs path> — category: <routing-row-name> — naming: <convention or "ad-hoc: <reason>"> — rationale: <≤80 char>
```

When ≥2 legitimate rows apply:

```
Writing to: <abs path> — category: <row-name> — naming: <convention> — rationale: <reason> (over alternative: <alt-path>)
```

Announce + proceed immediately. No approval gate. The declaration makes the placement choice visible at the moment it's made.

### Mechanical-write exemption set

PWD is NOT required when the target path is fully determined without DM classification judgment:

1. DM's own session log (`<project>/sessions/<YYYY-MM-DD>/dm-log.md`)
2. Swarm-narrative appends (`~/.core/workspaces/<id>/swarm-narrative.md`)
3. `workspace.json` field bumps (e.g., `last_active`, `delivery_risk`)
4. Auto-memory cache writes (`~/.claude/projects/<hash>/memory/`)
5. `inbox.md` raw external pulls (provenance-inline staging; promotion decision is a separate step)
6. Edits to a file the user explicitly named in the same turn (no placement choice was made)

**Bounded-property test:** a write is exempt only if its path is determined by the artifact's own name, schema, or the user's explicit statement — not by DM classification. When in doubt, emit a PWD.

### Uncovered-type protocol

When the artifact type does not appear in any row's per-category artifact list:

**0 candidates (no legitimate row):**
```
UNCOVERED ARTIFACT TYPE: <description>
No existing row covers this. Proposed: <path> because <reason>.
Filing §Moves item to extend the closure list.
Proceeding — reply to redirect.
```

**≥2 candidates (ambiguous between rows):**
```
AMBIGUOUS PLACEMENT: <description>
Option A: <row-name> → <path> — <rationale>
Option B: <row-name> → <path> — <rationale>
Choosing A because <reason>.
```

**Skill-product HARD BLOCK:** if the proposed path is `~/.claude/skills/core/**` or `<project>/core-skill/**` AND the artifact type is uncovered OR the PWD does not contain `intent: skill-edit`:
```
BLOCKED: Skill-product surface requires declared skill-edit intent.
Add "intent: skill-edit" to the PWD or redirect to another row.
```
The write does not proceed until the PWD includes `intent: skill-edit` — or the path is changed.

---

## Principle: Project synthesis lives in the project folder

The DM's authoritative read surface for any project is a single file — `PROJECT.md` at the project root — plus an optional staging file — `inbox.md` — for raw external pulls and typed notes. Everything else under `~/.core/` is either operational meta (DM identity, agent configs, swarm effectiveness) or cross-project knowledge — not project facts.

**The user-control invariant:** If the user deletes a fact from `PROJECT.md`, the DM no longer treats that fact as known. This is enforced by *protocol*, not structural guarantee:

- The DM reads `PROJECT.md` at bootstrap and after any user edit mid-session.
- Auto-memory (`~/.claude/projects/<hash>/memory/`) is treated as scratch cache, rebuilt from current synthesis each bootstrap. Not authoritative.
- `dm-profile.md` holds cross-project patterns only — no project-specific facts.
- Handoffs in project `handoffs/` are write-only from the DM's perspective; facts worth keeping are promoted into `PROJECT.md` at session close.
- **Honest residual:** the harness's prompt cache (≤5 min TTL) and in-memory state within a single session can retain a fact past its synthesis deletion until the next bootstrap or re-read. The DM discloses this when asked and re-reads `PROJECT.md` after any user edit.

---

## Project Folder — Project Synthesis and Deliverables

The project folder is version-controlled (by default), visible, and the user's direct editing surface. Everything the user should be able to see, edit, and delete lives here.

```
<project>/
├── PROJECT.md             ← AUTHORITATIVE: DM's sole project read surface at bootstrap
├── inbox.md               ← OPTIONAL: staging for raw external pulls and typed notes (DM drains into PROJECT.md)
├── workspace.json         ← DM workspace pointer (exception: DM-owned metadata for harness resolution)
├── handoffs/              ← Narrative session logs (write-only from DM; facts already promoted to PROJECT.md)
│   └── <YYYY-MM-DD>-<topic>.md
├── sessions/              ← Session logs; per-session agent logs
│   └── YYYY-MM-DD/
│       ├── <agent>-log.md
│       └── swarm-analysis.html
├── outputs/               ← Swarm synthesis, project-specific sub-skill findings
│   └── <swarm-type>-<topic>-<YYYY-MM-DD>.md
└── docs/                  ← Architecture docs, design specs, research findings
    └── <topic>.md
```

### `PROJECT.md` — the six sections

Every project's synthesis file has the same six sections. Sections that don't apply are *declared thin* in §State rather than left empty — empty sections train the DM to ignore the schema.

1. **What & Why** — one paragraph: project identity, outcome, constraints, deadline, owner.
2. **State** — 3–5 bullets: current status, what moved recently, what's blocked. If a project is solo (no §People entries) or has no active external systems, declare it here.

   **Entry-shape rule (DC-42):** §State bullets are **present-tense statements about the project's current condition**. Entries that lead with a past-tense session verb ("shipped," "landed," "completed," "ran," "added," "verified," "documented," "fixed," "resolved") belong in `handoffs/`, not §State. Each entry ≤40 words. The "3–5 bullets" cap is enforced — when §State exceeds 5 entries OR any entry violates present-tense rule, `/finalize` Step 4.7 triggers compaction.

3. **People** — flat list: `Name (role) — context, latest, commitments`. Inline; no separate file. Solo projects omit and declare in §State.
4. **Moves** — next actions with owners and dates. Checkbox list. Large backlogs (>~20 items) reference an external tracker (GitHub Issues, etc.) rather than enumerate here.

   **Open-actions-only rule (DC-42):** §Moves holds *open* next actions only. Checked items (`[x]`) are removed at session close — either by deletion (the handoff already records what was done) or by migration to `PROJECT-ARCHIVE.md` if the user wants to preserve the history. `/finalize` Step 4.7 includes §Moves in the compaction sweep.
5. **Decisions & Risks** — dated bullets. Decisions are append-only; risks carry mitigation + last-reviewed date; closed items struck through with reason. RAID as a dedicated artifact is over-specified — this is one section.
6. **Notes** — freeform. Architectural principles, meta-learnings, harness/model notes, junk drawer.

### When to split `PROJECT.md` into siblings

Start single. Split a section into a sibling file at the project root (`DECISIONS.md`, `AGENDA.md`, `PEOPLE.md`) **only when**:

- the section exceeds ~100 lines, or
- the section's update cadence diverges sharply from the rest (append-only log vs. high-churn agenda).

On split: replace the section body in `PROJECT.md` with a two-line summary plus a link. Never pre-split — small projects have one file. Splits are a graduation, not a default.

### `inbox.md` — staging for external pulls and typed notes

Optional. Use when:

- An external task tracker, document store, or chat platform is being pulled via MCP and raw content needs a landing zone.
- The user types a chat note ("Danika's deliverable due 2026-05-01") and the DM wants an explicit promotion step rather than writing directly into synthesis.

Raw entries carry provenance inline (`— source: external task tracker, fetched 2026-04-21T14:30`). The DM drains `inbox.md` into `PROJECT.md` on review: commitment → §People + §Moves, decision → §Decisions & Risks, risk → §Decisions & Risks. The inbox entry is deleted or stricken after promotion.

Nothing in `inbox.md` is authoritative. If it hasn't been promoted, the DM doesn't treat it as known.

### `handoffs/` — narrative write-only

Session-close narrative: "what happened, what surprised me, what I'd want to know next time." The DM writes one handoff per session close, but **does not re-read handoff bodies at bootstrap** — facts worth keeping were already promoted to `PROJECT.md`. Handoffs exist for the human reader (future contributor, project review, reconstructed context after a catastrophic loss).

If a session ends and a fact lives only in the handoff, context is lost on next bootstrap. The session-close discipline is: diff the handoff against `PROJECT.md`; any fact mentioned only in the handoff must be promoted before the session closes.

---

## `~/.core/` — DM Operational Meta

Everything here serves the DM's ability to function *across projects* and across sessions. It is machine-local, not version-controlled, and survives project deletion. **No project-specific facts live here.**

```
~/.core/
├── dm-profile.md          ← Cross-project personality, portfolio observations; NO project-specific facts
├── index.json             ← Global workspace registry
├── agents/                ← Saved effective agent configurations (cross-project, reused in swarms)
│   └── <name>.md
├── task-configs/          ← Swarm configurations indexed by task type
│   └── <type>.md
├── swarm-effectiveness/   ← Post-swarm reports: strategy, composition, process signals
│   └── <workspace-id>-<YYYY-MM-DD>.md
├── dream-cycles/          ← Memory-curation retrospectives (one per dream cycle pass)
│   └── <YYYY-MM-DD>.md
├── research/              ← Cross-project knowledge library (see Cross-Project Research below)
│   └── <topic>-<YYYY-MM-DD>.md
└── workspaces/<id>/
    ├── workspace.json      ← Workspace manifest (full schema in schemas/workspace.md)
    ├── swarm-narrative.md  ← Reflective log of swarm efficacy (workspace-scoped operational meta, not project state)
    └── tracking/           ← Operational telemetry (monitor sweeps, etc.) — not project state
        └── monitor-sweeps.log
```

**The test:** If the project folder were wiped entirely, would the DM still need this file to serve *other projects* or to resume its own operational posture? If yes, it belongs here. If the answer involves "this project's decisions / risks / people / commitments," it does NOT belong here — those live in `PROJECT.md`.

### `workspace.json` — dual pointer pattern

The DM creates a `workspace.json` pointer in the project folder (for harness resolution from working directory) AND a full manifest in `~/.core/workspaces/<id>/workspace.json`. The project-folder pointer contains `workspace_id`, `name`, `created`, `data_path` — enough to resolve. The full manifest holds the rest.

### What does NOT live in `~/.core/workspaces/<id>/`

- No `raid-log.md`, `decision-log.md`, `next-session.md`, `handoffs/`, `intel/`. These were legacy workspace-scoped files; they have been absorbed into `PROJECT.md` (decisions, risks, moves) or moved to the project folder (handoffs, inbox).
- If a workspace dir contains legacy files from before this restructure, the DM does not read them. See `startup.md` for the legacy-file exclusion rule during Phase 3A.

---

## Cross-Project Research — `~/.core/research/`

Cross-project knowledge synthesized by sub-skills or accumulated through project work. Not tied to any single project.

**What belongs here:** Findings useful when working on a *different* project — generalizable synthesis about LLM patterns, persona effectiveness research, framework-level architectural findings.

**What does NOT belong here:** Project-specific findings (go to `outputs/`), external system snapshots (go to project `inbox.md`).

**On loss:** Machine-local and not backed up. If lost, entries must be re-derived from source material. Do not treat research library entries as authoritative institutional memory — they are working synthesis that can be reproduced.

**Sensitivity:** Entries inherit sensitivity from source material. Header format:

```
---
topic: <topic>
synthesized: <ISO 8601>
sources: [<source-type>, ...]
sensitivity: internal | restricted | public
derived-from-restricted: true | false
---
```

---

## Data-Type Staleness — DM Reasons, No Fixed TTL

The DM decides whether a fact needs refresh by reasoning about the data type's tendency to go stale, not by applying a fixed expiry. Different source types have different staleness profiles:

| Data type | Staleness tendency | DM behavior |
|---|---|---|
| External task tracker rows (status, assignees) | Stale within ~24h — frequent updates | Re-query at session start if synthesis relies on it; disclose age when citing |
| External chat platform thread summaries | Stale within hours — rapid turn | Re-fetch before citing; stage raw content in `inbox.md` |
| External document-store pages (architecture, policy) | Stable unless touched — low churn | Trust snapshot; re-check only if content is load-bearing for a current decision |
| User-typed notes in `inbox.md` | Stable as evidence; may supersede as context | Treat as authoritative once promoted; inbox raw is deletable |
| Decisions in `PROJECT.md §Decisions & Risks` | Never stale (decisions don't "go bad" — they get superseded) | Append new decision; reference the superseded one |
| Risks in `PROJECT.md §Decisions & Risks` | Stale after ~3 sessions or ~14 days | Re-evaluate `last-reviewed` at Phase 5 of startup; force re-review if exceeded |
| Cross-project research entries | Variable — depends on subject's real-world churn | Surface age when citing; re-derive if subject has known recent change |

**The rule:** the DM surfaces data age in outputs. A stale external-system-derived claim used in analysis must be disclosed ("this external-tracker synthesis is 3 days old"). A decision in synthesis doesn't carry age because it *is* synthesis.

**Staging pattern for external pulls:**

1. MCP (or equivalent) writes raw content to `<project>/inbox.md` with `source:` and `fetched-at:` provenance inline.
2. DM reviews on next turn or at session start.
3. Facts worth keeping are promoted to `PROJECT.md` (commitment → §People + §Moves; decision → §Decisions & Risks; risk → §Decisions & Risks).
4. Raw entry in `inbox.md` is deleted or stricken with reason.

**Reconciliation:** When an external system disagrees with `PROJECT.md` (e.g., tracker says task X is closed but §Moves lists it as open), the user decides on promotion. The DM surfaces the conflict; it does not silently overwrite.

---

## Skill / Plugin Directory — Skill Product

The installed skill product.

**Current location:** `~/.claude/skills/core/`
**Future location:** Plugin directory once CORE is packaged as a plugin. This protocol is not affected by the transition.

All skill content is read-only at runtime.

---

## `~/.claude/projects/<hash>/memory/` — Auto Memory (Scratch Cache)

Persists facts about the user, feedback, and references across conversations. **Treated as scratch cache, not authoritative.** Rebuilt from `PROJECT.md` (and cross-project `dm-profile.md`) each bootstrap.

**User-control implication:** When the user deletes a fact from `PROJECT.md`, the DM's next bootstrap rebuilds auto-memory from current synthesis — the deleted fact does not re-appear. Mid-session residual (prompt cache, in-memory state) is disclosed, not hidden.

**Path stability:** The hash is derived from the project path. If the project directory is moved or renamed, the hash changes and existing memory becomes orphaned. Do not move project directories without accepting that auto-memory will be rebuilt from synthesis (which is the correct behavior — synthesis is authoritative).

Do not write sensitive content, operational data, or deliverables here. Memory classification is behavioral.

---

## Self-Evolution Artifacts

The DM writes several artifacts as the skill learns across sessions. All live under `~/.core/` — machine-local, not version-controlled, cross-project. See `protocols/self-evolution.md` for write triggers.

| Artifact | Location | Scope | Purpose |
|---|---|---|---|
| Swarm efficacy narrative | `~/.core/workspaces/<id>/swarm-narrative.md` | Workspace operational | Reflective log of agent effectiveness; appended after each swarm. Not project state. |
| Swarm effectiveness report | `~/.core/swarm-effectiveness/<id>-<YYYY-MM-DD>.md` | Global | Structured post-swarm report: strategy, composition, failure-mode audit, process signals. Read before composing new swarms. |
| Auto-compaction effectiveness report | `~/.core/swarm-effectiveness/auto-compaction-<workspace-id>-<YYYY-MM-DD>.md` | Global | BM-DC46-7. Per-trigger report: file path, trigger (proactive_finalize / proactive_startup / reactive_error), per-file ratio measurement, entries migrated with first-line + archive destination. Dream cycle Phase 3 scans these to surface tuning candidates and fire the path-(a)→(b) re-decision trigger. |
| Dream cycle retrospective | `~/.core/dream-cycles/<YYYY-MM-DD>.md` | Global | Structured memory-curation pass: inventory, distillation, contradiction resolution, pattern synthesis, agent refresh. Read before the next dream cycle to avoid re-litigating closed decisions. |
| Agent configurations | `~/.core/agents/<name>.md` | Global | Saved effective agent designs, reused in future swarms. |
| Task-type configurations | `~/.core/task-configs/<type>.md` | Global | Effective swarm configurations indexed by task type. Consulted before composing a new swarm. |
| Auto-memory | `~/.claude/projects/<hash>/memory/` | Global | Scratch cache; see section above. |

**Why these are operational, not project-scoped:** they describe how the DM works, not what any single project is. They survive project deletion and serve the DM on every subsequent workspace.

**Distinction from session logs and handoffs:** session logs narrate *what happened in a session*; handoffs carry *narrative* forward for the human reader; self-evolution artifacts capture *what the DM learned about running swarms*.

---

## Sub-Skill Output Protocol

When `/core-research` or `/core-analysis` produces a document:

**Step 1 — Ask: would this finding be useful on a different project?**

| If... | Then... |
|-------|---------|
| Finding is specific to this project's context | → Project `outputs/` folder |
| Finding is generalizable across projects | → `~/.core/research/` |
| Finding is both (most are) | → Write project-specific synthesis to `outputs/`; extract generalizable insight as a separate entry to `~/.core/research/` |

**The heuristic for "generalizable":** Could you apply this finding on a project you haven't started yet? If yes, it's generalizable.

**Default when uncertain:** Project `outputs/` folder. Promotion to research library is deliberate.

**Sensitivity carrythrough:** If a finding was derived from restricted external content, the output (project folder or research library) must carry a matching sensitivity annotation.

---

## Data Lifecycle

| Event | Action |
|-------|--------|
| New workspace created | DM interviews user; scaffolds `<project>/PROJECT.md` (six sections populated from interview); creates `<project>/workspace.json` pointer; creates `~/.core/workspaces/<id>/` with `workspace.json` manifest + `swarm-narrative.md`; registers in `~/.core/index.json` |
| Session starts | DM reads `PROJECT.md` in full; reads `workspace.json`; applies elapsed-time signals to §Decisions & Risks (stale risks) and §Moves (deadlines); DM does NOT read handoff bodies or legacy workspace files |
| User types a note | DM either writes directly to `PROJECT.md` (for unambiguous facts) or stages to `inbox.md` (for review-gated promotion) |
| External source queried in depth | Raw content staged to `<project>/inbox.md` with provenance; DM promotes facts to `PROJECT.md` on review |
| Decision made | DM appends to `PROJECT.md §Decisions & Risks` with date, rationale, and link to relevant moves |
| Risk identified | DM appends to `PROJECT.md §Decisions & Risks` with likelihood/impact, mitigation, last-reviewed |
| Session ends | DM diffs session against `PROJECT.md`; promotes any session-only facts to synthesis; writes narrative handoff to `<project>/handoffs/<YYYY-MM-DD>-<topic>.md`; updates `PROJECT.md §Moves` with next-session priorities |
| Swarm produces output | Synthesis written to `<project>/outputs/`; DM extracts generalizable insight to `~/.core/research/` if applicable |
| Swarm completes | DM appends to `~/.core/workspaces/<id>/swarm-narrative.md`; writes structured report to `~/.core/swarm-effectiveness/`; saves any effective agent configs to `~/.core/agents/` and task configs to `~/.core/task-configs/` |
| User deletes from `PROJECT.md` | DM treats the fact as no longer known; auto-memory is rebuilt from current synthesis on next bootstrap |
| Workspace archived | Removed from `~/.core/index.json`; workspace directory retained at `~/.core/workspaces/<id>/`; project folder untouched |

---

## Naming Conventions

| File type | Convention | Example |
|-----------|-----------|---------|
| Project synthesis | `PROJECT.md` at project root | `PROJECT.md` |
| Sibling splits (when triggered) | `DECISIONS.md` / `AGENDA.md` / `PEOPLE.md` at project root | `DECISIONS.md` |
| Inbox staging | `inbox.md` at project root | `inbox.md` |
| Workspace ID | `<project-slug>` (named) or `<YYYY-MM-DD>-<topic>` (ephemeral) | `core-framework`, `2026-04-12-<topic>` |
| Handoff | `<YYYY-MM-DD>-<topic>.md` in `<project>/handoffs/` | `2026-04-21-synthesis-restructure.md` |
| Session logs | `YYYY-MM-DD/<agent-name>-log.md` in `<project>/sessions/` | `2026-04-21/dm-log.md` |
| Outputs | `<swarm-type>-<topic>-<YYYY-MM-DD>.md` in `<project>/outputs/` | `research-sycophancy-mitigations-2026-03-15.md` |
| Research library | `<topic>-<YYYY-MM-DD>.md` in `~/.core/research/` | `persona-effectiveness-research-2026-04-02.md` |
| Swarm efficacy narrative | `swarm-narrative.md` in `~/.core/workspaces/<id>/` | `swarm-narrative.md` |
| Swarm effectiveness report | `<workspace-id>-<YYYY-MM-DD>.md` in `~/.core/swarm-effectiveness/` | `core-framework-2026-04-12.md` |
| Dream cycle retrospective | `<YYYY-MM-DD>.md` in `~/.core/dream-cycles/` | `2026-04-26.md` |
| Agent config | `<name>.md` in `~/.core/agents/` | `critic-voice-auditor.md` |
| Task-type config | `<type>.md` in `~/.core/task-configs/` | `architecture-review.md` |

---

## Enforcement Posture

Most protections in this protocol are **behavioral**: sensitivity headers, disclosure requirements, staleness calls, and promotion-from-inbox steps depend on the DM following instructions.

**Structural enforcement (DC-24):** The PreToolUse hook (`pre-tool-storage-check.sh`) provides mechanical enforcement at the skill-product surface:
- Closure match → silent passthrough
- Path outside documented closures → user-visible WARN
- Skill-product path without `intent: skill-edit` in PWD → **HARD BLOCK** (non-zero exit)

Pre-commit hook (`pre-commit-check.sh`) provides defense-in-depth on git-tracked surfaces.

**The user-control invariant posture is unchanged.** Structure + protocol closes the leak channels *by discipline*, not by enforcement. The residual is disclosed: prompt cache within a 5-minute window, mid-session in-memory state. The DM states this honestly when asked.

**Known residual (LC-2):** Skill-edit intent declaration is behavioral — a DM that genuinely mis-classifies can declare `intent: skill-edit` spuriously. Defense: pre-commit checks for a matching `IMPROVEMENT_LOG.md` entry on skill-product writes.
