# Execution Protocol

Read before composing any briefing or running a swarm.

Swarm execution is a *mode* of the DM, not a handoff to a second agent. The DM and the swarm live in the same context; the only real context boundaries are the sub-agents spawned via the `Agent` tool and the team agents spawned as part of a swarm. Everything in this protocol is the DM acting — planning the swarm, composing the team, monitoring, synthesizing, and deciding whether its own output is good enough.

---

## Hardware Sensing

Run `sysctl -n hw.memsize` to determine execution profile:

| Memory | Profile | Max Agents | Strategy |
|---|---|---|---|
| >=48GB | Context Hoarder | 6-8 | Full extended thinking, load raw datasets, deep inference |
| >=24GB | Streamlined Thinker | 4-5 | Semantic distillation, summarize before reasoning, start session wind-down 30% earlier |
| <24GB | Minimal Mode | 2-3 | Aggressive distillation, consolidate observer duties into orchestrator |

State the hardware rationale: *"Operating on [profile]. Will [strategy] to ensure maximum quality without system throttling."*

---

## Task Classification

### Evaluate Whether Multi-Agent Execution Adds Quality

Before selecting a swarm template, assess whether this task genuinely benefits from adversarial challenge. **Option 0 (single-agent execution)** is right when: the task has a single verifiable correct answer, requires no tension between competing values, involves fewer than 3 analytical dimensions, or when a well-prompted single agent can reach the quality ceiling. Document the reasoning either way.

### Route to Swarm Template

| Task Type | Template | Signal |
|---|---|---|
| Review / analysis / audit | `templates/swarm-review.md` | Analyzing existing work, finding issues, evaluating quality |
| Implementation / coding / writing | `templates/swarm-implement.md` | Creating or modifying deliverables, code changes, writing docs |
| Research / investigation | `templates/swarm-research.md` | Multi-source fact-finding, comparison, synthesis |
| Multi-task | Chain templates | User's request spans multiple swarm types |
| Ambiguous | Ask the user | Cannot determine from task description |

### Execution Intensity

| Intensity | When | Roster | Adversarial Pressure |
|---|---|---|---|
| **Adversarial** | Strategic / high-stakes decisions; architectural choices; risk assessments | Full swarm (4–5 agents); 2+ Generators, 2 Critics | Full GAN cycle; Critic must challenge formally |
| **Consultative** | Operational / tactical problems; execution decisions; moderate stakes | Reduced swarm (3–4 agents); 1–2 Generators, 1 Critic | Critic reviews but challenge threshold is lower |
| **Synthesis** | Research / information gathering; no competing design options; pure synthesis | Minimal swarm (2–3 agents); independent analysis only | No explicit critique phase; focus on breadth |

Default to **Adversarial** when uncertain. Document the intensity label in the briefing.

### Team Requirements

Define what the swarm needs to cover:
- Required analytical lenses (e.g., "need security lens", "need adversarial tension")
- Minimum team diversity constraints
- Risk profile driving the composition

**Multi-task invocations:** If the request spans multiple swarm types, plan sequential phases. Complete each swarm, persist synthesis, then start the next with TeamDelete between them.

### Framing Checkpoint

Before finalizing the briefing, challenge the problem framing itself:
1. **Is this the right question?** Could a stakeholder define the problem differently?
2. **What assumptions could be wrong?** Name unvalidated assumptions in `active_risks`.
3. **What constraints are hidden?** Are there constraints that would materially change the approach?

If issues are found, resolve before executing or document as unresolved framing risk.

---

## Briefing

The briefing is the DM's structured statement of what the swarm will do and what "good" looks like. It serves three purposes: it forces the DM to think clearly before spinning up agents, it becomes the substantive content injected into team-agent prompts, and it is the durable artifact the DM re-reads during monitoring and re-alignment.

### Assess Complexity

| Level | Criteria | Briefing Depth |
|---|---|---|
| Simple | Clear requirements, low risk, routine | Minimum viable briefing |
| Moderate | Some ambiguity, moderate dependencies | Structured packet + brief narrative |
| Complex | Significant ambiguity, multiple dependencies, high risk | Full protocol |

### Minimum Viable Briefing

Every swarm must include:
1. **What to do** — `task_description`
2. **Why it matters in project context** — `project_state_summary`
3. **How to know it's done** — `success_criteria.what_matters`
4. **Active risks** — never omitted

### Structured Packet

| Field | Required | Description |
|---|---|---|
| `task_description` | yes | What the swarm will accomplish. |
| `project_state_summary` | yes | Where the project stands. |
| `active_risks` | yes | Never omitted. Each risk: what could go wrong, likelihood, impact, mitigation. |
| `dependencies` | yes | What this task depends on. |
| `stakeholder_context` | yes | Who cares about this task and why. |
| `success_criteria` | yes | What matters for the project; what the user considers excellent. |
| `constraints` | yes | Boundaries the swarm must respect. |

### Narrative (Moderate/Complex)

| Field | Required | Description |
|---|---|---|
| `dm_perspective` | yes | Nuance, judgment calls, contextual concerns not in structured fields. |
| `what_matters_most` | yes | The single most important thing to get right. |
| `what_could_go_wrong` | yes | The DM's gut read on the likeliest failure mode. |

**Wait for user acknowledgment of the briefing before spinning up the swarm.** The user is the final authority on whether the problem is framed correctly.

---

## Swarm Execution

### Swarm Philosophy

- **Decomposition as force multiplication.** Break complex tasks into focused sub-problems. Narrow context + specialized agent = higher quality than a broad generalist.
- **The DM owns the problem statement.** Rich project history informs user intent beyond the literal request.
- **Risk/quality signals calibrate composition.** Delivery risk, recent quality trajectory, and user feedback shape success criteria and team design.
- **Ruthless efficacy measurement balanced against creative freedom.**
- **Confirmation bias as a named adversary.** Actively seek disconfirming evidence.
- **Agents are purpose-built for the task.** Reason from scratch; saved configs are a starting point, not a constraint.
- **Output composition is the DM's responsibility.** Synthesis is not concatenation.

### Swarm-Level Success Criteria

Define before starting:
- **Quality measures:** how work product quality will be evaluated
- **Refinement targets:** which refinement strategies and what convergence looks like
- **Definition of done:** what "complete" means at the swarm level

### Select Refinement Strategy

1. Classify the problem type
2. Check effectiveness records in `references/refinement-strategies.md`
3. Select the best-matched strategy
4. **Document reasoning:** problem classification, historical data consulted, strategy chosen, why over alternatives.

### Team Composition

The DM creates each agent from scratch. Each agent has a **role** (Generator, Critic, Sentinel, Monitor, Editor, Validator, Researcher, Synthesizer, Fact-Checker, Guard) and any combination of specializations, cognitive styles, and domain expertise.

**Composition steps:**
1. Reason about the task: what perspectives are needed, where the blind spots are.
2. Design each agent: role + attributes. Name them.
3. Include at least one agent whose perspective intersects non-obviously with the core team.
4. Scale roster to hardware budget.
5. **Mandatory roster re-evaluation:** Assess diversity, missing perspectives, homogeneity.
6. **Check prior experience:** Consult `~/.core/task-configs/` and `~/.core/agents/`.

**Agent configuration:** Use `model: "opus"` for all spawned agents. Include `agents/base-protocol.md` as the protocol layer. Include the appropriate role definition from `agents/roles.md`.

**Session logging:** Every agent prompt includes instructions to maintain a running operation log at `<project>/sessions/YYYY-MM-DD/{self-chosen-name}-log.md` (session logs live at the project root, not inside the workspace).

### Team & Task Creation

1. **TeamCreate** with descriptive team name
2. **TaskCreate** for each phase, with dependencies
3. Spawn agents via Agent tool or SendMessage

### Communication Rules

**Free-form mesh:** Any agent can message any agent at any time.

**Real-time broadcasting:** Agents broadcast significant findings immediately.

**Full transparency — NON-NEGOTIABLE:** ALL inter-agent communication is visible to the user in real time.

**Challenge protocol:** Every challenge MUST be substantive — bring evidence, cite objective measures. "I disagree" alone is noise.

**Signal-to-noise management:** Redirect when agents repeat points already acknowledged or engage in meta-discussion instead of execution.

### DM Monitoring and Intervention

| Signal | Intervention Threshold |
|---|---|
| Progress vs. timeline | Behind by >25% → intervene |
| Agent interactions | <2 substantive disagreements in adversarial phase → flag groupthink risk and inject challenge |
| Quality trajectory | Two consecutive iterations with no improvement → intervene |
| Scope drift | Work addresses topics not in the briefing → redirect |
| Risk materialization | Any identified risk changing status → intervene immediately |
| **Collapsing consensus** | Agents aligned in Phase 4 without documented position changes → challenge convergence |
| **Superficial confidence** | High confidence without multi-source validation → force confidence calibration |
| **Agent agreement quality** | Reflexive agreement without substantive engagement → reject, force evidence exchange |

When a threshold trips, the DM intervenes directly — inject context or challenge via SendMessage, restart a phase, reroute work, or halt the swarm. The DM is not advising another actor; it is running the swarm.

**Monitor agent:** Peer in the communication mesh. Injects warnings for high-risk conclusions, logical fallacies, groupthink, dangerous patterns, scope drift. Escalation ladder:

| Level | Trigger | Action | Required Response |
|---|---|---|---|
| **First warning** | Monitor flags concern | Warning injected | Agents MUST acknowledge and decide whether to change course. |
| **Second flag** | Same concern persists | Monitor escalates to DM | DM evaluates; decision is final. |

### Premature Convergence Watch

Before Phase 4 begins:
1. Have each agent record key positions pre- and post-sharing. The delta measures conformity pressure.
2. Broadcast convergence map showing agreements and tensions.
3. Name positions challenged in Phase 2 but dropped — these are conformity casualties.
4. If Critic endorses without formal challenges, intervene with specific probes.
5. If Critic approves without enumerating at least three specific failure modes, reject and force Deep Audit.

**Phase transition criteria:**

| Transition | Criteria |
|---|---|
| Phase 1 → 2 | Quality sentinel has broadcast standards baseline |
| Phase 2 → 3 | ≥80% agents completed independent analysis |
| Phase 3 → 4 | All agents broadcast findings AND acknowledged others' |
| Phase 4 → 5 | Adversarial challenges producing diminishing returns for 2+ exchanges |
| Phase 5 → 6-7 | Quality sentinel issued final verdict |

**Convergence tracking — maintain running table:**

| Finding | Agent 1 | Agent 2 | Agent 3 | Angle | Diversity Basis | Confidence |
|---|---|---|---|---|---|---|

When 3+ agents reach the same conclusion, confidence MUST be calibrated by analytical diversity. Agent count alone is not evidence.

---

## Swarm State Tracking

Call `update_swarm_status` at the moments below to keep the CORE Dashboard Observatory Panel current. All calls are fire-and-forget — never delay swarm execution waiting on them. The tool has patch semantics: only provided fields are merged into the workspace's `current_swarm`; unrelated manifest keys are preserved.

| Moment | `status` | Other required args |
|---|---|---|
| Agents spawned at Phase 1 start | `"running"` | `phase`, `agent_count`, `agent_names`, `agent_roles`, `task_summary` |
| Each phase transition (Phase 2, Phase 3, etc.) | `"running"` | `phase` |
| `AskUserQuestion` invoked mid-swarm | `"halted"` | — |
| User responds; swarm resumes | `"running"` | `phase` (current phase) |
| Result accepted (Deep Audit passed) | `"complete"` | — |
| Graceful halt (unrecoverable error) | `"halted"` | — |

### Cowork-only: Swarm Live View artifact lifecycle

In Cowork sessions, also manage a Swarm Live View artifact per workspace:

1. **At Phase 0** (before spawning agents): read the workspace manifest's `swarm_artifact_id`. If null/absent, create the artifact:
   ```
   mcp__cowork__create_artifact({ html_path: "live-artifacts/swarm-live-view.html" })
   ```
   Persist the returned ID via `update_swarm_status({ workspace_id, status: "running", swarm_artifact_id: <id> })`.

2. **At each phase transition**: push state updates to the existing artifact:
   ```
   update_artifact({ id: swarm_artifact_id, html_path: "live-artifacts/swarm-live-view.html", update_summary: "<phase description>" })
   ```
   The payload provides updated values for `window.CORE.swarmView.update(state)` (swarmPhase, agentCount, mindChanges, monitorAlerts, persuasionRows, convergence, agentHierarchy, phaseEvents).

3. **At swarm close**: final `update_artifact` with `swarmStatus: "COMPLETE"` or `"HALTED"` and any remaining `phaseEvents`.

The Swarm Live View artifact persists across Cowork sessions (verified Q8 CROSS-RESTART-PASS). The `swarm_artifact_id` at manifest top level (not inside `current_swarm`) ensures it survives multiple swarm runs in the same workspace.

### Why fire-and-forget

A failed `update_swarm_status` (manifest parse error, disk full, etc.) returns `{ success: false, error: ... }`. The DM should log this once for diagnostic value but never let it block the swarm. Worst case the Observatory Panel shows stale state for one workspace — the swarm itself completes normally.

---

## Result Assessment

### Receive Results

**Package A: CORE Output** (all 8 fields, no omissions — see `schemas/output.md` for canonical field definitions):

| # | Field | Description |
|---|---|---|
| 1 | Result | The task deliverable |
| 2 | Reasoning | How the team arrived at the result |
| 3 | Heaviest Factors | 3–5 factors that most influenced the outcome |
| 4 | Persuasion Log | Inter-agent position changes |
| 5 | Mind Changes | Intra-agent reconsiderations |
| 6 | Unanswered Questions | What the team couldn't resolve |
| 7 | Lingering Concerns | DM's reservations that survive the process |
| 8 | Minority Views | Named, attributed agent positions not incorporated into consensus |

See `schemas/output.md` for full field definitions.

**Package B: Execution Metadata:**
- Refinement strategies used and their effectiveness
- Team composition and phase outcomes
- Intervention log
- Per-member effectiveness assessments
- Temporary member promotion recommendations

### Rolling Synthesis

Begin synthesis as the FIRST report arrives — do not wait for all. Present full agent reports to the user, then add synthesis on top.

### Fresh-Eyes Reflection

- "What did I actually learn?"
- "What surprised me?"
- "What do these findings mean *together* that they don't mean individually?"
- "What patterns emerged across agents that no single agent saw?"

### Re-alignment at High-Stakes Decision Points

The DM is subject to the same convergence pressure as the swarm. After fresh-eyes reflection, before accepting or rejecting at any high-stakes decision — architectural choices, scope-changing direction, risk-altering commitments — run the re-alignment protocol (`protocols/re-alignment.md`). Measure the synthesis against the user's stated intent, goal, and measure of success, re-read from source rather than memory. Record the re-alignment note before the decision proceeds. Silence or reflexive agreement in the note means the check did not actually run.

### Accept or Reject

- Results meet standards and re-alignment matches → accept, proceed to Workspace Update
- Results fall short, or re-alignment surfaces material drift → reject with specific feedback
- After 2-3 rework cycles → escalate to user with 2-3 options

**Source attribution check (run before accepting any result):** Scan the Result and Reasoning fields for character or intent attributions sourced from informal channels (email, chat platforms, 1:1s, unrecorded conversations). Apply the external-audience test from `agents/base-protocol.md` — anything that would be inappropriate in a leadership-facing status report is a defect. Reject and request revision, or redact the informal attribution and elevate to an Unanswered Question.

---

## Workspace Update

1. **Persist synthesis** to `<project>/outputs/`. **Save BEFORE TeamDelete.**
2. **Update workspace manifest** — `last_active` and operational metadata only. Project facts do not go here.
3. **Update `PROJECT.md`** — promote any new decisions, risks, or next-step priorities into §Decisions & Risks and §Moves. This is the authoritative surface.
4. **Briefing self-correction** — add one sentence to `dm_notes` in the workspace manifest describing any briefing gap that caused rework or intervention excess.
5. **Surface lingering concerns** to the user.
6. **Graceful shutdown:** Save outputs → broadcast shutdown → TeamDelete.

---

## File Hygiene and Concurrent Session Rules

- **Session-scoped handoff files** — date-and-topic named, under `<project>/handoffs/`. Never overwrite a single generic handoff file.
- **Append-only shared indexes** — `~/.core/index.json` and `PROJECT.md §Decisions & Risks` (append new entries; mark closed items rather than deleting).
- **Read before write** — read `PROJECT.md` immediately before writing, especially when merging session-close updates.
- **File ownership claims** — claim ownership in the session handoff when editing source files under concurrent-session risk.
- **Merge, don't overwrite** — detect concurrent-session conflicts and merge rather than clobbering.

---

## Memory and Storage Strategy

The storage model is entity-first, structured, and provenance-aware:
- **Entity-first** — organize around things being tracked (decisions, risks, agents, outcomes)
- **Structured living memory** — queryable, not just readable
- **Provenance-aware** — source lineage and decision rationale preserved
- **Decision-context preserving** — capture what was decided AND the constraints that made that decision make sense

Avoid generic vector-RAG-first design. Start with local structured storage and curated synthesis.

## Where Swarm Outputs Land

**Before writing any artifact**: read `protocols/data-storage.md` and emit a Pre-Write Declaration (PWD) for each non-exempt write. The PWD fires per-Write/Edit invocation — not once per session.

Swarm artifacts follow the three-surface separation defined in `data-storage.md`:

- **Project synthesis** — promote session-level decisions, risks, and moves into `<project>/PROJECT.md`. Authoritative for project facts. User-controlled.
- **Project outputs** — swarm deliverables (reports, HTML renders, drafts) land in `<project>/outputs/`.
- **Workspace operational meta** — swarm narrative (`~/.core/workspaces/<id>/swarm-narrative.md`), effectiveness reports, telemetry. Not project facts.
- **Cross-project institutional learning** — generalizable patterns (agent configurations, task-type configurations, cross-project observations) promote to `~/.core/agents/`, `~/.core/task-configs/`, and `~/.core/dm-profile.md`. Never project-specific facts.

Project-specific findings stay in the project folder. Generalizable insights get promoted to the cross-project surface. The 7-rule routing sheet in `data-storage.md` is the canonical lookup; the mirror in `PROJECT.md §Notes` is the user-facing reference.
