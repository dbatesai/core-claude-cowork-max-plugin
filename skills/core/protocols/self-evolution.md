# Self-Evolution Protocol

Read when: end of session, dream cycle trigger, or writing a swarm effectiveness report.

---

## Universal Self-Improvement (Architectural Invariant)

Universal self-improvement is NOT a feature. It is an architectural invariant. Every protocol, process, and component MUST be self-improving. If you add a new component without a self-improvement mechanism, it is incomplete.

---

## Tier 1: Auto-Memory (Every Session)

**Auto-memory is scratch cache, not authoritative state.** The harness writes it (`~/.claude/projects/<hash>/memory/`). The DM treats it as a fast-access summary of what was learned — but on every bootstrap, auto-memory is re-verified against `PROJECT.md` (for project facts) and `dm-profile.md` (for cross-project patterns). If auto-memory disagrees with synthesis, synthesis wins and auto-memory is updated.

**Why it's scratch cache:** the user's control over the DM's project knowledge runs through `PROJECT.md`. If auto-memory were treated as authoritative, the user could delete a fact from synthesis and the DM would still "remember" it — breaking the user-control invariant. Auto-memory's role is acceleration, not persistence.

**Capture automatically after every session:**
1. Save key insights to auto-memory (user, feedback, reference types). **Do not save project-specific facts as authoritative** — those go to `PROJECT.md`. Auto-memory may carry a pointer or summary, but synthesis is the source of truth.
2. **Save effective agent configurations** — if an agent design proved particularly effective, save it to `~/.core/agents/<name>.md` for future reuse. (Operational, cross-project.)
3. **Save effective swarm configurations by task type** — save a brief configuration note to `~/.core/task-configs/<type>.md`. When composing a new swarm, check `~/.core/task-configs/` for prior configurations before reasoning from scratch. (Operational, cross-project.)
4. Record strategy effectiveness per problem type.
5. Sync **cross-project** learnings to `dm-profile.md` — user preferences, personality refinements, portfolio patterns. **Never project-specific facts.** (See `dm-identity.md` for the schema restriction.)
6. Update `PROJECT.md` §Decisions & Risks, §Moves, §Notes, §People as the session close step. Any fact worth keeping that is *specific to this project* lands here. Auto-memory may mirror it; synthesis is authoritative.

**Bootstrap invariant:** On the next session start, if auto-memory contains a project-specific fact not present in `PROJECT.md`, the DM treats the fact as deleted-by-user and rebuilds auto-memory from current synthesis. This is the structural enforcement of the user-control invariant (modulo the prompt-cache residual disclosed in `data-storage.md`).

---

## Session-End Self-Evolution

1. Evaluate session conversation history — learn from it
2. Make self-improvement recommendations
3. Write improvement summary to screen for the user

---

## Swarm Efficacy Narrative

After running a swarm, the DM appends to an ongoing, human-readable narrative log at `~/.core/workspaces/<id>/swarm-narrative.md`. This is NOT a mechanical record — it is a reflective account written by the DM for its own future swarm runs in this workspace. Each entry captures: what this swarm revealed about agent effectiveness, what the DM chose to eliminate and why, what it preserved and why, and what questions remain open. The narrative is workspace-scoped — it stays distinct from the DM's session-end cross-workspace learnings.

---

## Swarm Effectiveness Report

After every substantial swarm, the DM writes a structured effectiveness report to `~/.core/swarm-effectiveness/<workspace-id>-<YYYY-MM-DD>.md`.

**Required sections:**

| Section | What to cover |
|---|---|
| Strategy choice | Which strategy was selected, why, how it performed against alternatives |
| Team composition | Who was on the team, what value each member delivered, which assignments were well-matched |
| Failure mode audit | Explicit assessment against all four named failure modes (see below) |
| Process signals | Measurable signals where possible — confidence deltas, estimate drift, phase quality scores |
| What worked | Specific, not generic. What techniques produced signal this run. |
| What failed | What was tried, what didn't hold up, why |
| Wish I Had | Concrete experiments for the next run |
| Improvement tracking | Status of prior "Wish I Had" items tested this run: tested / improved outcome / no difference / made things worse |

**Named failure modes — assess each explicitly:**
- **Premature convergence:** Agreement arrived before sufficient adversarial pressure or independent reasoning
- **Collapsing consensus:** Positions abandoned due to social pressure or narrative momentum rather than evidence
- **Superficial confidence:** Claims stated with more confidence than their evidence warranted
- **Agent agreement quality:** Whether agreement was earned through evidence and challenge, or merely reflexive

**The strongest historical signal: superficial confidence was the #1 recurring quality risk.** Every report must address it specifically.

**The DM reads recent effectiveness reports before composing a new swarm.** Prior reports are direct calibration input.

---

## Self-Improvement Risk Tiers

| Risk Level | Examples | Approval Path |
|---|---|---|
| **Low** | Effectiveness score updates, strategy ranking adjustments, memory additions, minor optimizations | Apply autonomously. Report to user at session end. |
| **Medium** | Composition rule changes, phase sequencing modifications, strategy ranking changes | Present to user with rationale and risks BEFORE applying. User approves, modifies, or rejects. |
| **High** | Protocol modifications, behavioral shifts, execution flow changes, architectural decisions | Present to user with full risk analysis BEFORE applying. User approves, modifies, or rejects. |

When in doubt, escalate. Changes that affect how CORE processes ALL future tasks — or changes to the self-improvement mechanism itself — are High risk by default.

---

## Tier 2: Dream Cycle (Every 3-5 Sessions)

Read `references/dream-cycle.md` for the full protocol. Trigger: perform semantic distillation of session logs, resolve contradictions, promote validated patterns, archive stale entries.

---

## Context Window Check

If <30% context remaining: generate `HANDOFF.md` for session restart before shutdown.
