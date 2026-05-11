---
name: finalize
description: DM closing skill — perform fresh-eyes session review, write handoff, update memory, sync and publish skill changes
user-invocable: true
---

# `/finalize` — Session Closing Protocol

You are performing the DM session closing sequence. This is not optional cleanup. Session value is only real if it survives the context window.

**Execute every step in order. Do not skip steps.**

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

---

## Step 3: Update Improvement Log

If any changes were made to SKILL.md files or skill protocols this session:

1. Open `~/.claude/skills/core/IMPROVEMENT_LOG.md` (or the relevant skill's improvement log)
2. Add an entry with date, what changed, and why
3. Be specific — future sessions should be able to reconstruct the reasoning

If no skill files changed, write a one-line entry: `<date> — No skill changes this session.`

---

## Step 4: Update Durable Memory

Review what was learned this session. Update memory files at `~/.claude/projects/<project-id>/memory/`:

- New user preferences or feedback → `feedback_*.md`
- New project context → `project_*.md`
- Changed understanding of the user → `user_profile.md`

Check `MEMORY.md` to see if any existing memories need updating based on new information from this session.

**Memory hygiene:**
- Update stale memories rather than adding duplicates
- Remove memories that were proven wrong
- Keep `MEMORY.md` index current

---

## Step 4.5: Dream Cycle Cadence Check

Read the most recent file in `~/.core/dream-cycles/` (filename is `YYYY-MM-DD.md`). Calculate days elapsed since that date.

| Days since last cycle | Action |
|---|---|
| ≤ 7 | Silent — cadence on track. |
| 8 – 14 | Surface to user: "Last dream cycle was N days ago. Recommend running one before close (or at the start of the next session)." |
| > 14 | Surface stronger: "Dream cycle is overdue (N days; cadence target is every 3-5 sessions). Recommend running before close unless there's a reason not to." |

If no cycles exist at `~/.core/dream-cycles/`: surface "No dream cycles on record yet — recommend running one now."

The DM does not run the dream cycle silently. Surface the recommendation; let the user decide. Dream cycles are user-acknowledged work, not background tasks — but they must not silently slip past their cadence either, which is what the SessionStart watch alone cannot prevent (the watch output scrolls past in bootstrap).

If the user accepts: invoke the dream cycle protocol at `~/.claude/skills/core/references/dream-cycle.md` before completing /finalize, then continue to Step 5. If the user defers: note the deferral in the handoff so the next session sees the outstanding cadence debt.

**Why this step exists:** prior to its addition (2026-05-10 dream cycle), the SessionStart `[Dream Cycle Watch]` hook output was the only cadence signal. It scrolled past in bootstrap and got silently dropped during long sessions. Result: 14-day gap between dream cycles 2026-04-26 and 2026-05-10 despite 5+ substantial sessions in that window. This step makes the cadence enforceable at session close rather than hoping the bootstrap reminder gets acted on.

---

## Step 5: Update PROJECT.md

Update the authoritative project synthesis at `<project>/PROJECT.md` (find the path from `workspace.json` or `~/.core/workspaces/<id>/workspace.json`):

- **§State** — update to reflect current deployed state, any newly completed work, or status changes
- **§Moves** — ensure the next-session priorities are accurate; mark completed items `[x]`; add any newly surfaced work items
- **§Decisions & Risks** — append any decisions made this session (dated, append-only); update risk entries if mitigations changed or risks closed

---

## Step 6: Sync and Publish (If Skill Files Changed)

If any SKILL.md files in `~/.claude/skills/` were modified:

1. Rsync to `core-skill/` mirror:
   ```bash
   rsync -av --delete ~/.claude/skills/core/ ~/Documents/Projects/core-skill/
   ```
2. Run the publish script if this is a CORE project session:
   ```bash
   .claude/scripts/publish-skill.sh "Brief description of what changed"
   ```

---

## Closing Declaration

After all steps complete, declare:

> Session closed. Handoff written. Memory updated.

If anything couldn't be completed, name it explicitly — don't silently skip it.
