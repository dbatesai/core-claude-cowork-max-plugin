# Workspace Management Protocol

Read when: creating a new workspace, managing wind-down, handling reactivation, or completing a project.

---

## What the Workspace Is (and Is Not)

The delivery workspace at `~/.core/workspaces/<id>/` is the DM's **operational meta** — how the DM has been working on the project. It holds manifest identity, cross-session DM observations, and pointers to session logs.

**Project truth lives in `<project>/PROJECT.md`.** State, people, moves, decisions, risks, and notes belong in the authoritative six-section synthesis at the project root, never in the workspace. `PROJECT.md` is user-controlled; the workspace is DM-owned. When project facts and workspace notes disagree, `PROJECT.md` wins.

The DM reads `PROJECT.md` at every session start. The workspace is supplemental.

---

## Always-Live Principle

Workspaces are always live. There are no "paused," "inactive," or "archived-in-place" states. Do not set a workspace state label.

**DM infers activity from signals:**
- Recency of engagement (`last_active` on the workspace manifest; latest dated entry in `PROJECT.md §State`)
- Frequency of sessions
- Delivery pressure — taken from `PROJECT.md §Moves` and §Decisions & Risks, not from the workspace
- Open items — again, read from `PROJECT.md §Moves` and §Decisions & Risks
- User engagement patterns observed across sessions

If you find yourself wanting to mark a workspace "inactive," instead update `PROJECT.md §State` with a dated note describing the current signals: *"2026-04-21 — no engagement in 3 weeks; no open deadlines; 2 low-priority moves still open."*

---

## Progressive Wind-Down

As engagement signals decrease, progressively reduce proactive activity:
- High engagement → full proactivity: updates, suggestions, risk alerts
- Declining → reduce frequency, focus on critical items only
- Low engagement → minimal: only surface urgent risks or deadline warnings
- No engagement → silent: stop proactive activity entirely

Wind-down is continuous, not stepped. When approaching silence, use judgment on whether to send a final check-in based on delivery risk (read from `PROJECT.md §Decisions & Risks`), open moves, and the user's engagement pattern.

---

## Reactivation

When the user returns after inactivity:
1. Read `PROJECT.md` fresh — do not resume from memory of the prior session alone.
2. Surface what has become stale: aging decisions, unreviewed risks, moves whose target dates have passed.
3. Apply elapsed-time signals per `protocols/startup.md`.
4. Recalibrate proactivity to current engagement level.

Do not re-read handoff bodies at reactivation. Handoffs are narrative logs written for the human reader; facts worth keeping were already promoted into `PROJECT.md` at the prior session's close. Reading handoffs can resurrect user-deleted facts.

---

## Cross-Workspace Awareness

The DM has access to every workspace registered in `~/.core/index.json`, but context boundaries are a discipline, not a data boundary. Anchor to the workspace resolved at bootstrap (typically inferred from cwd — see `protocols/startup.md`). Cross-workspace reference is DM-initiated when it clearly adds value (a similar risk in another project, a reusable pattern), never user-prompted. For the full discipline — how to label pivots, when to stay silent, ambiguity resolution — see `protocols/dm-identity.md §Project-Context Discipline`.

---

## Completion and Retrospective

A workspace is never truly closed — if the project resurfaces, continue in the same workspace with full history. **Optional archiving** is user-initiated housekeeping: removes from active view, preserves all history. The user can unarchive anytime.

When the user indicates completion:
1. Present objective status pulled from `PROJECT.md` — deliverables done/outstanding, open moves, remaining risks, quality assessment.
2. Run a retrospective scaled to project complexity.
3. Promote generalizable learnings — patterns that apply across projects — to `~/.core/dm-profile.md §Cross-Project Learnings`. Never promote project-specific facts to the DM profile; those stay in `PROJECT.md`.
4. Leave `PROJECT.md` as the durable record of what happened on this project. The workspace's `dm_notes` can carry DM-side operational observations about how the work was run, but the project's story lives in `PROJECT.md`.
