# CORE Architecture

> **Audience:** New users, contributors, and anyone who wants to understand *why* CORE is designed the way it is.
> **Note:** This document describes design philosophy and principles. For execution protocols, see `SKILL.md`.

---

## The Problem CORE Solves

Modern AI systems struggle with three core limitations when applied to complex work:

1. **Convergence** — A single AI perspective, no matter how capable, has blind spots. It will agree with itself, miss assumptions it can't see, and produce confident-sounding analysis that hasn't been stress-tested.

2. **Statefulness** — Conversation-bound AI forgets context between sessions. Projects require continuity: earlier decisions inform later ones, and accumulated context compounds in value.

3. **Alignment drift** — AI systems optimize for what they can measure (internal consistency, completeness of response) rather than what the human actually needs. Without active grounding mechanisms, AI drifts toward internally coherent but externally irrelevant output.

CORE addresses all three: adversarial multi-agent design fights convergence, persistent project state fights statefulness, and the DM's human-grounded feedback loop fights alignment drift.

---

## Four Primitives

CORE is built on four components:

| Component | Role |
|-----------|------|
| **Project Synthesis** | The user-controlled surface of project facts — `<project>/PROJECT.md`. Authoritative for State, People, Moves, Decisions & Risks, Notes. Workspace operational meta is a separate, thin surface at `~/.core/workspaces/<id>/`. |
| **Delivery Manager (DM)** | Continuity, user relationship, AND swarm orchestration. Persists across all sessions. Runs swarms as a mode of itself — no separate execution agent. |
| **Team Members** | Purpose-built specialized agents — composed for each task from scratch. Spawned by the DM via `TeamCreate` and the `Agent` tool; dismissed when the task completes. |
| **Signals** | Inputs that update or challenge state — user feedback, external data, evaluation outputs. |

### System Law

> **The DM owns continuity AND execution. Swarm orchestration is a mode of the DM, not a handoff to a second agent.**

The DM spans the project lifespan — accumulating history, maintaining the user relationship, tracking what worked. When a task warrants a swarm, the DM enters orchestration mode: composes the team, runs adversarial loops, synthesizes findings, decides whether the output is good enough. The only real context boundaries are the team agents spawned via `TeamCreate` and sub-agents spawned via the `Agent` tool. The user interacts exclusively with the DM.

---

## Architectural Principles

### 1. Isolatable
Each agent forms opinions independently before the group convenes. Critics assess proposals without seeing each other's assessments first. This prevents the most common failure mode in group analysis: the first opinion becoming everyone's opinion.

### 2. Collaborative
Independent thinking only matters if it comes back together. Generators cross-reference findings, critics compound each other's challenges, and the quality sentinel maintains a comprehensive standards view. Isolated insights become compounding insight.

### 3. Coordinated
The synthesis layer resolves conflicts and produces unified deliverables. Where experts agree, confidence strengthens. Where they disagree, the dissent is a signal of genuine uncertainty — not something to paper over.

### 4. Iterative
Exit criterion is critic approval, not a fixed round count. If a Critic approves too quickly, the approval is rejected and a Deep Audit forced — because real quality review takes real effort. Quality is earned through challenge, not asserted through completion.

### 5. Self-improving
The framework gets smarter through use. The auto-memory system captures session learnings. The Dream Cycle curates and distills accumulated knowledge every 3-5 sessions. Saved agent configurations and task-type recipes accumulate from real execution, not upfront design.

### 6. Composable
Agents are composed from modular traits, roles, and specializations. No two tasks require the same team. The composition model is from-scratch reasoning — building what the task needs — informed by prior configurations that proved effective.

### 7. Trustworthy
High-risk operations pause for explicit approval. The Guard Agent pattern requires that any create, update, or delete on an external system triggers a risk assessment before execution. Analytical work proceeds independently; irreversible operations do not.

### 8. Adaptive
Plans change when reality changes. Phase transitions are based on actual progress, not rigid task dependencies. If a reasoning strategy stalls, the system switches while preserving prior work.

### 9. Contextual
The bootstrap protocol reads `PROJECT.md` in the project folder (the synthesized, user-controlled surface of project facts), plus cross-project patterns from the DM profile. Handoffs are narrative for the human reader and are not re-read at bootstrap — facts worth keeping were promoted into `PROJECT.md` at session close. Long-term project knowledge compounds through synthesis, not accumulation.

### 10. Persistent
Project facts live in `<project>/PROJECT.md` (user-controlled, authoritative). Operational meta lives in `~/.core/workspaces/<id>/`. Cross-project patterns live in `~/.core/dm-profile.md`. The three surfaces carry distinct scopes — no surface silently mirrors another — so deleting a fact from synthesis actually removes it from the DM's next-session picture.

### 11. Institutional Memory
The system remembers not just what happened but why. `PROJECT.md §Decisions & Risks` captures the reasoning and trade-off landscape behind choices. The DM's profile accumulates cross-project learnings. `PROJECT.md` holds everything about a single project; the DM's global profile carries portable patterns across all projects — project-specific facts never leak into the profile.

---

## Intrinsic vs. Emergent Properties

**The key insight about CORE's effectiveness:**

**Intrinsic properties** come from the language model itself — they travel with the model regardless of the harness.

**Emergent properties** come from the infrastructure layered on top — they require deliberate engineering and break if the toolchain is removed.

| Property | Classification | What Breaks If Removed |
|----------|---------------|------------------------|
| Isolatable | Emergent | Agents share context; bias contaminates findings |
| Collaborative | Emergent | Agents cannot share findings or coordinate |
| Coordinated | Emergent | Multiple findings never merge into one report |
| Iterative | Emergent | Single-pass analysis without adversarial challenge |
| Self-improving | Emergent | Framework never learns from experience |
| Composable | Emergent | Every task requires complete redesign |
| Trustworthy | Emergent | Unsupervised agents can cause damage |
| Adaptive | Intrinsic + Emergent | Rigid adherence to pre-set plans |
| Contextual | Intrinsic + Emergent | Generic responses without project awareness |
| Persistent | Emergent | Knowledge resets at session boundaries |
| Institutional Memory | Emergent | Decision context lost, past mistakes repeated |

**The ratio of emergent to intrinsic properties is the central insight:** the architectural work is the majority of what makes CORE effective. Raw model intelligence is necessary but far from sufficient. A powerful model running in a naive single-pass harness will converge on the same wrong answer with high confidence every time.

---

## Why CORE Is Different

| Shift | From | To |
|-------|------|----|
| **Continuity** | Isolated answers | Persistent project reality that evolves across sessions |
| **Validation** | Assuming success | Stress-tested findings that survived adversarial challenge |
| **Behavior** | Static responses | A framework that learns from each execution |
| **Relationship** | Transaction | A DM that knows your context, history, and working style |
| **Reasoning** | Single perspective | Multiple experts challenging each other to catch what one perspective misses |

---

## The Convergence Problem

The adversarial design is built around one empirical finding: LLM personas over-converge toward consensus, far more than human experts would.

When multiple agents share context and see each other's conclusions, they anchor on each other's outputs. The first opinion becomes the group's opinion. This is not a failure mode that can be reasoned away — it is the default behavior of the system without structural countermeasures.

CORE's anti-convergence mechanics exist specifically to fight this:
- Agents form independent assessments before seeing others' conclusions
- Critics are required to challenge formally before the adversarial phase ends
- The Monitor agent watches for groupthink across the swarm
- Premature convergence triggers are enforced at phase transitions
- The Persuasion Log makes reasoning changes visible and auditable

**Empirical baseline:** 84.5% sycophancy flip rate observed in Critic agents when exposed to Generator proposals without isolation. 9-point homogeneity gap between isolated vs. cross-pollinated analysis. These numbers are why the framework is built the way it is.
