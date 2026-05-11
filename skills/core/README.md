# CORE

**The vendor dependency everyone assumed was stable had been deprecated for six months. CORE flagged it at session start. Nobody had asked.**

---

## What CORE Does

CORE reads your project's accumulated record — documents, decisions, conversations, changes — at the start of each session and surfaces what the status report flattened. At session close, a reflection pass updates what the framework knows.

One constraint: one person cannot hold every project signal in working memory simultaneously. CORE can.

Five capability areas define what this means in practice.

---

## Five Capability Areas

CORE's functional surface divides into five capability areas. Three are implemented today. Two describe behaviors the framework produces but does not yet schedule as instrumented mechanisms — implementation status is shown for each.

| Area | What It Does | Status |
|---|---|---|
| **Persistent Memory** | Retains decisions, rationale, and context across the project lifespan | Implemented |
| **Decision Intelligence** | Produces structured analysis from project signals for the audience that needs it | Implemented |
| **Adversarial Challenge** | Pressure-tests findings through multiple specialist perspectives before they reach you | Implemented |
| **Risk Intelligence** | Predicts emerging problems from current signals | Aspirational — produced behaviorally at session bootstrap; no standing prediction mechanism |
| **Continuous Monitoring** | Watches for changes, drift, and elapsed-time signals without being prompted | Aspirational — monitoring happens at session start and during swarms; no between-session daemon |

---

## How You Work With It

**Natural language is the interface.** The project's terminology — the names you use for risks, dependencies, decisions — lives in memory. CORE reads it and uses it back.

CORE supports four interaction patterns:

- **Proactive alerts** — surfaces risks and signals at session start without being asked
- **Conversational** — answers questions, explores what-ifs, drafts messaging
- **Scheduled synthesis** — produces structured reports on a set cadence
- **Independent action** — monitors continuously between sessions *(aspirational — see Continuous Monitoring above)*

---

## What Makes It Reliable

First-pass answers can be confidently wrong. CORE produces answers that survive challenge.

Every analysis passes through multiple specialist perspectives before it reaches you. One agent builds the case. Another is assigned to find every way it can fail. A third monitors whether the first two are genuinely disagreeing or performing agreement. The output is structured: you see the result and reasoning, the factors weighed most heavily, what shifted opinions during the analysis, what could not be resolved with the evidence available, and what dissent was preserved after losing the argument. If the record of position changes is empty after adversarial phases, the process did not work — and the output says so.

The DM runs a reflection pass every 3–5 sessions — auditing memory for stale or contradictory entries, checking whether recent agent identities earned their slot, and updating both based on what worked. This is the dream cycle. It makes future sessions smarter. It does not update model weights; it updates what the framework remembers about your project and which agent designs to reuse.

---

## One Analysis, Multiple Lenses

The same session analysis can be presented differently depending on who needs it. The swarm runs once; the DM frames the output for the audience.

The following are illustrative — they describe how the analysis might be consumed, not distinct output modes the system produces on command.

- **Executive Lens** — portfolio health, cross-project risks, decisions needed
- **Delivery Lens** — dependencies, timeline risks, stale assumptions, next actions
- **Technical Lens** — architecture impacts, integration risks, requirement gaps
- **Stakeholder Lens** — commitments, milestones, and what external partners need to do next

---

## Getting Started

Clone CORE into your agent harness's skills directory. For Claude Code:

```bash
git clone https://github.com/dbatesai/core-skill.git ~/.claude/skills/core
```

Then in any session:

```
/core
```

To update, run `git pull` inside the skill directory.

**Other harnesses.** CORE is markdown only — any harness that supports custom skills or instruction files can load it. Point your harness at `SKILL.md` as the entry point.

---

## Learn More

- [ARCHITECTURE.md](ARCHITECTURE.md) — technical reference. How CORE works and why it's built the way it is.

---

## License

[MIT](LICENSE)
