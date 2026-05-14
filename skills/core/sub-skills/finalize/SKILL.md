---
name: finalize
description: DM closing skill — perform fresh-eyes session review, write handoff, update memory, sync and publish skill changes
user-invocable: true
---

# `/finalize` — Session Closing Protocol

You are performing the DM session closing sequence. This is not optional cleanup. Session value is only real if it survives the context window.

**Execute every step in order. Do not skip steps.**

---

## Step 0: Harness Resolution

Several later steps write to host-wide paths (`~/.claude/skills/`, `~/.claude/projects/<id>/memory/`, `~/.core/dream-cycles/`, host-side `core-skill/` mirror) that Cowork's folder-scoped file tool cannot reach. Detect the harness here so blocked steps surface explicitly in the handoff rather than failing silently.

**Detection** (same precedent as `/core` startup Phase 0.5, DC-41):

1. Read environment variable `CLAUDE_CODE_IS_COWORK`.
   - **Unset** → `core_capability_level = "direct"` (Claude Code CLI or any non-Cowork harness). All steps proceed normally; skip to Step 1.
2. **Set** → read `~/.core/capability.json` (treat as `{ "level": 3 }` if absent).
   - `level: 1` → `"L1"` (Cowork + MCP write tools live).
   - `level: 2` → `"L2"` (Cowork without MCP).
   - `level: 3` (or missing) → `"L3"` (Cowork with no plugin runtime).

3. Initialize an empty `blocked_steps` list. Each later step appends an entry `(step name, reason, pending content)` when it cannot complete in the current harness. The list is surfaced in the handoff (Step 2) and the closing declaration. **Do not silently skip a blocked step** — capture what would have been written so the next compatible-harness session can pick it up.

The point of explicit detection is honesty: the next session must be able to see what didn't get done and why, not infer it from silence. This step sets the precedent any future harness-aware finalize work (e.g., DC-42's eventual prune step) should reuse.

---

## Step 1: Fresh-Eyes Review

Before writing anything, re-read the session from the top with fresh eyes and re-synthesize the context with your understanding of the operator intent, goal, and measure of success. Ask:

- What did we actually accomplish vs. what we set out to do?
- What decisions were made? Are they captured somewhere durable?
- Did changes in direction during the session cause you to miss something important?
- What was left incomplete? Is it tracked in the backlog or open questions?
- What surprised us? What did we learn that wasn't expected?
- Did anything break or degrade that we didn't fix?
- Is the project better than we found it?

Write a one-paragraph honest assessment. This goes into the handoff.

---

## Step 2: Write Session Handoff

Write a handoff document to `handoffs/` in the project source data directory (check `workspace.json` or `~/.core/workspaces/<id>/` for the path).

Use the naming convention: `handoffs/handoff-<YYYY-MM-DD>.md` (use today's date).

**Handoff structure:**

```markdown
# Session Handoff — <YYYY-MM-DD>

## What Was Done
[Bullet list of completed work — specific, not vague]

## Current State
[Where the project stands right now — what's live, what's wired up, what's deployed]

## Decisions Made
[Any architectural, design, or priority decisions made this session with rationale]

## Open Work
[Incomplete items — be specific about what's left, not just "finish X"]

## Open Questions
[Unresolved questions — list with any partial context already gathered]

## Active Risks
[Any new or escalated risks surfaced this session]

## Next Session: Read First
[The 3-5 most important things the next DM needs to know before touching anything]

## Next Session: Recommended Start
[Specific recommended first action for the next session]
```

**If `blocked_steps` is non-empty** (Step 0 set up the list; Steps 3, 4, 4.5, 6 may have appended), add this section to the handoff:

```markdown
## Steps That Could Not Complete

The following finalize steps could not complete in this session's harness. The next compatible-harness session should pick them up.

- **<step name>:** <reason>. Pending content:
  <what would have been written if the step had been able to complete>
```

Capture the pending content concretely (the actual log entry text, the actual memory file edits, the list of skill files needing sync). Vague "pending memory updates" doesn't survive the next bootstrap.

---

## Step 3: Update Improvement Log

If any changes were made to SKILL.md files or skill protocols this session:

1. **Identify the canonical log location.**
   - For CORE skill / framework work: `<project>/IMPROVEMENT_LOG.md` (per `CLAUDE.md`; lives in project root, not skill dir).
   - For other skills that maintain their own log: `~/.claude/skills/<skill-name>/IMPROVEMENT_LOG.md`.

2. **Routing by `core_capability_level` (set in Step 0):**

   | Level | Action |
   |---|---|
   | `"direct"` | Edit the canonical log file directly. |
   | `"L1"` / `"L2"` / `"L3"` | Project-root logs (`<project>/IMPROVEMENT_LOG.md`) work — the project folder is connected in Cowork. **Host-wide logs** (`~/.claude/skills/<name>/IMPROVEMENT_LOG.md`) cannot be written from Cowork's folder-scoped file tool; append `("Step 3: improvement log update", "host-wide skill dir not connected in Cowork", <pending entry text>)` to `blocked_steps` and continue. |

3. Add an entry with date, what changed, and why. Be specific — future sessions should be able to reconstruct the reasoning.

If no skill files changed, write a one-line entry: `<date> — No skill changes this session.`

---

## Step 4: Update Durable Memory

Review what was learned this session. Memory files live at `~/.claude/projects/<project-id>/memory/`:

- New user preferences or feedback → `feedback_*.md`
- New project context → `project_*.md`
- Changed understanding of the user → `user_profile.md`

Check `MEMORY.md` to see if any existing memories need updating based on new information from this session.

**Routing by `core_capability_level` (set in Step 0):**

| Level | Action |
|---|---|
| `"direct"` | Write/Edit memory files directly under `~/.claude/projects/<project-id>/memory/`. Update `MEMORY.md` index in the same operation. |
| `"L1"` / `"L2"` / `"L3"` | `~/.claude/projects/` is outside Cowork's connected folders, and no `mcp__core__*` write tool covers project memory today. Capture the intended memory updates (file name, frontmatter, full body, `MEMORY.md` index line) in the handoff under "Memory Updates Pending" so the next CLI session can apply them verbatim. Append `("Step 4: memory update", "project memory dir not connected in Cowork; no MCP write tool yet", <pending entries>)` to `blocked_steps`. |

**Memory hygiene** (apply in any harness — captured content must already reflect these decisions):
- Update stale memories rather than adding duplicates
- Remove memories that were proven wrong
- Keep `MEMORY.md` index current

---

## Step 4.5: Dream Cycle Cadence Check

**Routing by `core_capability_level` (set in Step 0):**

| Level | Action |
|---|---|
| `"direct"` | Proceed with the cadence check below — read the most recent file in `~/.core/dream-cycles/` and surface per the table. |
| `"L1"` / `"L2"` / `"L3"` | `~/.core/dream-cycles/` is not exposed by any `mcp__core__*` read tool today. Append `("Step 4.5: dream cycle cadence check", "no MCP read tool for `~/.core/dream-cycles/`", "cadence status unavailable in this harness")` to `blocked_steps` and surface a one-line note in the handoff: *"Dream cycle cadence unavailable in current harness; next CLI session should run Step 4.5 fresh."* Then continue to Step 5. (Future MCP tool: `mcp__core__read_dream_cycle_latest` would close this gap.) |

Read the most recent file in `~/.core/dream-cycles/` (filename is `YYYY-MM-DD.md`). Calculate days elapsed since that date.

| Days since last cycle | Action |
|---|---|
| ≤ 7 | Silent — cadence on track. |
| 8 – 14 | Surface to user: "Last dream cycle was N days ago. Recommend running one before close (or at the start of the next session)." |
| > 14 | Surface stronger: "Dream cycle is overdue (N days; cadence target is every 3-5 sessions). Recommend running before close unless there's a reason not to." |

If no cycles exist at `~/.core/dream-cycles/`: surface "No dream cycles on record yet — recommend running one now."

The DM does not run the dream cycle silently. Surface the recommendation; let the user decide. Dream cycles are user-acknowledged work, not background tasks — but they must not silently slip past their cadence either, which is what the SessionStart watch alone cannot prevent (the watch output scrolls past in bootstrap).

If the user accepts: invoke the dream cycle protocol at `~/.claude/skills/core/references/dream-cycle.md` before completing /finalize, then continue to Step 4.7. If the user defers: note the deferral in the handoff so the next session sees the outstanding cadence debt.

**Why this step exists:** prior to its addition (2026-05-10 dream cycle), the SessionStart `[Dream Cycle Watch]` hook output was the only cadence signal. It scrolled past in bootstrap and got silently dropped during long sessions. Result: 14-day gap between dream cycles 2026-04-26 and 2026-05-10 despite 5+ substantial sessions in that window. This step makes the cadence enforceable at session close rather than hoping the bootstrap reminder gets acted on.

---

## Step 4.7: Compaction Sweep — content-relevance + size-driven

(Added 2026-05-13 per DC-42; extended same day per DC-46 to add size-driven autonomous MIGRATE alongside DC-42's content-relevance PRUNE. Primary trigger layer of the three-layer compaction architecture documented in `protocols/data-storage.md §"Auto-Compaction Strategy"`.)

**Why this step exists:** PROJECT.md and IMPROVEMENT_LOG grow monotonically across sessions. By 30 sessions in, the files exceed harness read limits (default 25K-token Read cap) and bootstrap silently slides from authoritative-read to slice-read. The user-control invariant has an unstated precondition — *the DM can read the whole synthesis file at orient* — that bloat empirically falsifies. This step has two distinct branches: content-relevance compaction (DC-42, user-approved PRUNE because the info lives elsewhere) and size-driven compaction (DC-46, autonomous MIGRATE because entries are preserved in the archive).

### Triggers — two branches, fire independently

**Branch A — Content-relevance (DC-42, user-approved PRUNE).** Any one fires Branch A:
- §State has >5 bullets
- Any §State bullet leads with a past-tense session verb ("shipped," "landed," "completed," "ran," "added," "verified," "documented," "fixed," "resolved")
- §Moves has any `[x]` checked items still in the file
- IMPROVEMENT_LOG.md has >15 entries (count-based; calibrate per project after first rotation)

**Branch B — Size-driven (DC-46, autonomous MIGRATE for auto-MIGRATE files; user-gated for cross-project files).** Fires per file:
- `file_size_chars × per_file_ratio > 0.8 × effective_cap`
- Where `effective_cap = env(CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS) ?? 25000`, `per_file_ratio` is the persisted measured ratio (default 0.30; see `data-storage.md §"Auto-Compaction Strategy"` for measurement primitive).
- In-scope files: `PROJECT.md`, `IMPROVEMENT_LOG.md`, and any other file matching the file-shape classifier in `data-storage.md`.

**Routing by `core_capability_level` (Step 0):** identical to Step 4.5 — `"direct"` proceeds inline; `"L1"`/`"L2"`/`"L3"` append `("Step 4.7: compaction sweep", "PROJECT.md edits require Write/Edit access to project folder", "queue for next CLI session")` to `blocked_steps` only if the project folder isn't connected. In Cowork L1 sessions where the project folder IS a connected Cowork folder, file-tool writes work; proceed inline.

### Branch A: Content-relevance PRUNE (user-approved)

```
For §State:
  if entry count > 5 OR any entry violates present-tense rule:
    classify each entry:
      - KEEP   — current-truth, present-tense lead, ≤40 words
      - PRUNE  — past-tense session-event narrative (info lives in handoff)
      - REWRITE — mixed: extract current-truth nugget, prune the narrative
      - MIGRATE — explicit user choice: preserve in PROJECT-ARCHIVE.md
    default for past-tense-leading entries: PRUNE
    default for present-tense-leading entries: KEEP
    present classified list to user
    require explicit user approval before any deletion/migration
    apply approved actions

For §Moves:
  for each [x] checked item:
    default: PRUNE (handoff already records the completion)
    user may override → MIGRATE (PROJECT-ARCHIVE.md) or KEEP (rare)
    present list to user with defaults
    require explicit approval

For IMPROVEMENT_LOG.md:
  if entry count > 15:
    keep most recent N entries (default N=10; user can tune)
    rotate older entries to IMPROVEMENT_LOG-ARCHIVE.md (append-only,
    never read at bootstrap, single-WRITE)
    present cut-point to user; require explicit approval before rotating
    apply approved rotation
```

### Branch B: Size-driven MIGRATE (autonomous per path (a), DC-46)

```
For each in-scope file:
  consult data-storage.md §"File-shape classifier":
    if shape is "Synthesis (cross-project)":
      USER-GATED: surface proposed entries; require explicit approval
    if shape is "Synthesis (project)" or "Append-only log":
      AUTO-MIGRATE per path (a):
        identify oldest entries whose removal brings the file under threshold
        for PROJECT.md §D&R: migrate oldest dated decisions to DECISIONS.md
        for PROJECT.md §State / §Moves: defer to Branch A (content-relevance)
        for IMPROVEMENT_LOG.md: rotate oldest entries to IMPROVEMENT_LOG-ARCHIVE.md
        for other append-only logs: rotate oldest entries to <file>-ARCHIVE.md
        write entries to archive (single-WRITE, never read at bootstrap)
        remove from primary file
        write BM-DC46-7 effectiveness report (see below)
        on first compaction of a previously-unmeasured file:
          compute measured_ratio = error_token_count / file_char_count (if available)
          persist to effectiveness report keyed by file path
```

**No info loss.** MIGRATE preserves entries in `<file>-ARCHIVE.md`. The user's explicit DELETE action is required to permanently remove a fact — see `data-storage.md §"DELETE procedure"`.

### §D&R graduation check (BM-DC46-6)

After Branch A and Branch B fire (if either did): if `PROJECT.md §Decisions & Risks` exceeds ~100 lines, trigger the graduation rule documented in `data-storage.md §"When to split PROJECT.md into siblings"`:
- Move §D&R body to `<project>/DECISIONS.md` sibling at project root.
- Replace section body with a two-line summary + link.
- One-line grep stubs for older entries remain in `PROJECT.md` per DC-48 stub-every-archived-entry pattern.

### BM-DC46-7 effectiveness report (load-bearing — do not drop)

Per `~/.claude/skills/core/SKILL.md` universal-self-improvement architectural invariant. After any Branch B fire, write `~/.core/swarm-effectiveness/auto-compaction-<workspace-id>-<YYYY-MM-DD>.md` with:
- File path that was compacted
- Trigger: `proactive_finalize` (this step) or `proactive_startup` (Phase 0.7) or `reactive_error` (defense-in-depth)
- `file_size_chars` before
- `per_file_ratio` used (measured or default)
- `effective_cap` and `threshold`
- Entries migrated: list of `(entry_id_or_date, first_line, archive_destination)`
- `file_size_chars` after
- False positives observed (if any — e.g., entry migrated but user immediately re-promoted)

The dream cycle (Phase 3) scans these reports across sessions, surfaces tuning candidates, and fires the path-(a)→(b) re-decision trigger if cumulative MIGRATE entries exceed 5 since last review surface.

### Closing Declaration

Append to the /finalize Closing Declaration:

> **Compaction sweep:**
> **Branch A (PRUNE):** §State pruned N, migrated M, kept K, rewrote R. §Moves pruned P, migrated Q. IMPROVEMENT_LOG rotated R entries to archive.
> **Branch B (MIGRATE):** [list each migrated entry as `<file>: <first-line of entry> → <archive destination>`; show entries, not counts, per path (a) visibility requirement.]
> **§D&R graduation:** triggered / not triggered.
> **Effectiveness report:** `~/.core/swarm-effectiveness/auto-compaction-<workspace-id>-<YYYY-MM-DD>.md` written / no Branch B fires this session.

### What this preserves

- **User-control invariant.** Branch A (PRUNE) requires explicit user approval — default-PRUNE is *prescription*, not action; user sees the list and approves before any deletion. Branch B (MIGRATE) is autonomous but entries are preserved in archive — no info loss; only the user's explicit DELETE removes a fact permanently. Per `~/.claude/skills/core/SKILL.md` Architectural Invariants, deleted facts stay deleted; the DM cannot resurrect them via auto-archive read.
- **Read-side singularity.** `PROJECT-ARCHIVE.md`, `IMPROVEMENT_LOG-ARCHIVE.md`, `DECISIONS.md`, and any `<file>-ARCHIVE.md` are **single-WRITE / never-read-at-bootstrap** (DECISIONS.md is read on explicit user request only). They preserve history for the user's eyes; the DM treats them as out of scope per `startup.md` Phase 3A archive-exclusion rule. Per DC-19, only the read-side singularity of `PROJECT.md` matters; write-side siblings are fine.
- **Schema compliance.** The 3–5 bullet §State cap is documented in `data-storage.md` Project Folder schema; this step enforces what was already prescribed but unenforced for 30+ sessions.
- **Visibility over silence.** Branch B is autonomous but entries (not counts) appear in the Closing Declaration. Path (a)'s honesty requirement is that the user can always see what was moved — silent ≠ hidden.

---

## Step 5: Update PROJECT.md

Update the authoritative project synthesis at `<project>/PROJECT.md` (find the path from `workspace.json` or `~/.core/workspaces/<id>/workspace.json`):

- **§State** — update to reflect current deployed state, any newly completed work, or status changes
- **§Moves** — ensure the next-session priorities are accurate; mark completed items `[x]`; add any newly surfaced work items
- **§Decisions & Risks** — append any decisions made this session (dated, append-only); update risk entries if mitigations changed or risks closed

---

## Step 6: Sync and Publish (If Skill Files Changed)

**Routing by `core_capability_level` (set in Step 0):**

| Level | Action |
|---|---|
| `"direct"` | If any SKILL.md files under `~/.claude/skills/` were modified, run the sync/publish flow below. |
| `"L1"` / `"L2"` / `"L3"` | Sync/publish operates on host-side paths and shell scripts that Cowork cannot execute against host paths. Skill edits originating in a Cowork session must flow back through a Claude Code CLI session for sync. Append `("Step 6: sync and publish", "Cowork cannot execute host-path sync/publish; defer to next CLI session", <list of modified skill files>)` to `blocked_steps`. |

**Sync/publish flow** (run only in `"direct"` harness):

1. Rsync to `core-skill/` mirror (public-release skill content):
   ```bash
   rsync -av --delete ~/.claude/skills/core/ ~/Documents/Projects/core-skill/
   ```
2. Refresh plugin-bundled skill snapshots (for plugin-bundled skills like `orient`/`finalize`/`vibecheck`/`core`):
   ```bash
   python3 ~/Documents/Projects/core-claude-cowork-max-plugin/scripts/refresh_bundled_skills.py
   ```
3. Run the publish script if this is a CORE project session:
   ```bash
   .claude/scripts/publish-skill.sh "Brief description of what changed"
   ```

---

## Closing Declaration

After all steps complete, declare:

> Session closed. Handoff written. Memory updated.

**If `blocked_steps` is non-empty**, name each blocked step explicitly in the declaration:

> Session closed. Handoff written. Steps blocked by harness limitations and captured in the handoff: <comma-separated step names>. Next compatible-harness session should pick them up.

If anything else couldn't be completed, name it explicitly — don't silently skip it.
