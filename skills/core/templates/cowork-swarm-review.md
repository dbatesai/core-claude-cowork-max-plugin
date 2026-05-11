# CORE Swarm Template: Review (Cowork)

> **Cowork variant.** Uses `Agent` + `Task*` primitives. `TeamCreate` is not available in Cowork. For Claude Code, use `templates/swarm-review.md`.

## Purpose

Read-only adversarial analysis of any task, document, or codebase. Produces high-quality recommendations through structured generator-critic dialogue. The adversarial process forces generators to defend proposals against substantive challenges.

## Cowork-Specific Mechanics

### Spawning Agents in Parallel

Send multiple `Agent` tool calls in a **single message** — the harness executes them concurrently:

```
# One message, multiple Agent calls = parallel execution
Agent({subagent_type: "general-purpose", name: "Sentinel", prompt: "..."})
Agent({subagent_type: "general-purpose", name: "Generator-A", prompt: "..."})
Agent({subagent_type: "general-purpose", name: "Critic", prompt: "..."})
```

Each agent returns an `agentId`. Use `SendMessage({to: agentId, message: ...})` to resume a running agent or deliver cross-pollination content mid-round.

### Task Tracking

Use `Task*` for phase state and round counting — not team metadata:

```
TaskCreate({title: "Review Phase 1: Baseline", status: "in_progress"})
TaskUpdate({title: "Review Phase 1: Baseline", status: "completed"})
TaskCreate({title: "Review Phase 2: Analysis Round 1", status: "in_progress"})
```

### Context Budget

Every agent result returns to **the DM's main conversation context** (there is no separate team context). With 4-5 agents each returning 1000-3000 tokens per round, the budget fills faster than in Claude Code. Mitigations:
- Summarize each agent's output into a 200-400 word synthesis before spawning the next phase
- In the agent prompt, instruct: "Return findings in structured form only; no narrative preamble"
- Prefer fewer, focused rounds over many broad-sweep rounds

---

## Default Roster

- **1 Quality Sentinel** (Phase 1, spawned first)
- **2-3 Generators** (Phase 2, spawned in parallel)
- **1-2 Critics** (Phase 2, spawned in parallel with generators but given different framing — anti-anchoring is preserved because each Agent starts with no context from other agents)
- **Monitor** (optional; DM performs monitoring inline instead of via dedicated agent)

**Hardware recommendation (M5 Pro 24GB):** 2 generators + 1 critic + 1 sentinel = 4 agents total. This is the right ceiling for a Cowork review swarm given shared context budget.

---

## Phases

### Phase 1: Quality Baseline

**TaskCreate** "Phase 1 — Quality Baseline".

Spawn the Quality Sentinel **alone, before generators**:

```
Agent({
  subagent_type: "general-purpose",
  name: "Sentinel",
  prompt: "[base-protocol] + [sentinel role] + 'Read source material. Establish measurable standards. Return: standard name, metric, pass/fail threshold. No narrative.'"
})
```

When Sentinel returns: **summarize its standards into ≤10 bullet points** in the DM's working notes. Mark Phase 1 complete. **TaskUpdate** status = completed.

### Phase 2: Independent Analysis (Anti-Anchoring)

**TaskCreate** "Phase 2 — Independent Analysis".

Spawn Critics first, in isolation, before spawning Generators. Anti-anchoring is preserved because each Agent invocation starts with no context from other agents:

**Message 1 (Critics only):**
```
Agent({name: "Critic", prompt: "[base-protocol] + [critic role] + 'Read source material. Form your OWN assessment BEFORE seeing any generator output. Return: your 5 strongest critique points with evidence. No narrative.'"})
```

Wait for Critic to return. Note agentId. **Do not yet spawn Generators.**

**Message 2 (Generators, parallel):**
```
Agent({name: "Generator-A", prompt: "[base-protocol] + [generator-A role] + 'Read source material. Form proposals from your domain expertise. Return: top 5 proposals with evidence. No narrative.'"})
Agent({name: "Generator-B", prompt: "[base-protocol] + [generator-B role] + 'Read source material. Form proposals from your domain expertise. Return: top 5 proposals with evidence. No narrative.'"})
```

**TaskUpdate** Phase 2 = completed when all generators return.

### Phase 3: Cross-Pollination

**TaskCreate** "Phase 3 — Cross-Pollination".

The DM reads all generator outputs and compresses them into a single cross-pollination brief (≤400 words). Send this brief to the Critic via SendMessage:

```
SendMessage({
  to: critic_agentId,
  message: "Generator proposals:\n[compressed brief]\n\nChallenge each proposal with your strongest critique. Identify the weakest claims. Return structured challenges only — no narrative."
})
```

Generators receive the Critic's independent assessment (from Phase 2) via SendMessage in parallel:

```
SendMessage({to: generator_a_agentId, message: "Critic's independent assessment: [compressed critic brief]. Defend your proposals or concede with specific evidence."})
SendMessage({to: generator_b_agentId, message: "..."})
```

**TaskUpdate** Phase 3 = completed when all agents respond.

### Phase 4: Adversarial Challenge (Minimum 2 Rounds)

**TaskCreate** "Phase 4 — Adversarial Round 1".

Challenge round structure:

1. DM reads all Phase 3 responses. Notes convergent areas and contested areas.
2. For each contested claim: send a follow-up challenge to the defending agent via `SendMessage`.
3. Defending agent responds; DM logs concessions in the Persuasion Log.
4. If all agents agree after one round: **flag as premature convergence**. Force a second round targeted at the weakest surviving claim.

**TaskUpdate** per round. Minimum 2 rounds. Mark Phase 4 = completed only after DM is satisfied the surviving proposals are genuinely defensible.

### Phase 5: Quality Arbitration

**TaskCreate** "Phase 5 — Quality Arbitration".

Send surviving proposals to the Sentinel via SendMessage:

```
SendMessage({
  to: sentinel_agentId,
  message: "Proposals reaching arbitration:\n[compressed proposals]\n\nEvaluate each against your Phase 1 standards. Return: PASS/FAIL per standard per proposal. No narrative."
})
```

Sentinel's verdict is binding on measurable standards. Failing proposals are MUST FIX regardless of generator-critic consensus.

**TaskUpdate** Phase 5 = completed.

### Phase 6: Rolling Synthesis

**TaskCreate** "Phase 6 — Synthesis".

Begin synthesis as FIRST phase reports arrive. Do not wait for all phases to complete. Build the synthesis document incrementally:
- Convergent findings → MUST FIX tier
- Contested-but-surviving → SHOULD FIX tier
- Single-agent-only → CONSIDER tier
- Persuasion Log → Mind Changes section

Write to `sessions/YYYY-MM-DD/{swarm-name}-synthesis.md` using the Write tool (not bash).

**TaskUpdate** Phase 6 = completed.

### Phase 7: Fresh-Eyes Reflection

DM meta-analysis after all agent results collected. Ask:
- "What did I learn that no single agent could see?"
- "What findings converge from genuinely different analytical lenses?"
- "Where did the adversarial pressure produce a better proposal — what changed?"
- "What risks survived the entire process? Why?"

This reflection becomes the opening section of the output document.

---

## Premature Convergence Watch

If the Persuasion Log and Mind Changes fields are empty after Phase 4: the adversarial process probably didn't work. Possible causes:
- Critic anchored on generator output despite anti-anchoring framing
- Agents prompts were too similar (same training, similar framing)
- Scope too narrow for genuine disagreement

Intervention: spawn a new Critic with explicitly adversarial framing ("Your job is to find the worst-case scenario this proposal misses"). Run one more challenge round.

---

## Guard

NOT needed for review swarms. Review is read-only.

---

## Output

Prioritized recommendation document with:
- DM's Phase 7 fresh-eyes reflection (top)
- Findings organized by tier: MUST FIX / SHOULD FIX / CONSIDER
- Confidence per finding (source: which agents converged, from what analytical angle)
- Convergent findings table (agents, analytical lenses, diversity basis)
- Persuasion Log / Mind Changes (what changed under adversarial pressure)
- Full agent reports as appendix evidence base

---

## Context Management

After each phase, summarize agent outputs into compressed working notes before spawning the next phase. This is mandatory in Cowork — unlike Claude Code where team agents have separate contexts, every agent result lands in the DM's main context. If the context fills before synthesis, write a mid-swarm checkpoint to `sessions/YYYY-MM-DD/{swarm-name}-checkpoint.md` before continuing.
