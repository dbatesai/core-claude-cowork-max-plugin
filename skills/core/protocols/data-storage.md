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
3. **People** — flat list: `Name (role) — context, latest, commitments`. Inline; no separate file. Solo projects omit and declare in §State.
4. **Moves** — next actions with owners and dates. Checkbox list. Large backlogs (>~20 items) reference an external tracker (GitHub Issues, etc.) rather than enumerate here.
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
