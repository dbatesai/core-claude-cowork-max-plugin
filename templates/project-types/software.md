# PROJECT.md — Software Delivery Template

> **Template:** software.md — for building or shipping a software product, service, or feature set.
>
> **Best for:** teams shipping code toward a release. Works equally for a solo developer and a cross-functional team. The DM will align §Moves with your Linear/Jira issues if that connector is approved.
>
> **Recommended connectors:** Linear (or Jira), Slack, Drive (for design docs and specs).
>
> *Fill in the bracketed placeholders. Remove any section that doesn't apply. The DM will keep this file current — your job is to keep the content honest.*

---

## What & Why

[Product/service name] — [one sentence describing what it does and who it's for.]

**Goal:** [What does "done" look like? Ship date? Feature milestone? Metric threshold?]

**Constraints:** [Timeline, team size, budget cap, or technical constraints that shape decisions.]

**Owner:** [Your name / team name]

---

## State

- **Phase:** [e.g., "Sprint 3 of 5 — core auth complete, payments in progress"]
- **Last session focus:** [What the DM worked on last session]
- **Blockers:** [Anything blocking progress right now]

---

## People

| Name | Role | Connected via |
|---|---|---|
| [Name] | [Role] | [Calendar / Slack / Manual] |

*DM auto-populates this from Calendar + Slack when those connectors are approved.*

---

## Moves

**Now (this sprint / next session):**

- [ ] [Next concrete task]
- [ ] [Second task]

**Soon (next 1–2 sprints):**

- [ ] [Upcoming milestone]

**Later:**

- [ ] [Backlog item]

*Backed by Linear/Jira if connector approved — checking here updates the tracker; tracker updates reflect here.*

---

## Decisions & Risks

| ID | Decision / Risk | Date | Status |
|---|---|---|---|
| DC-1 | [Architecture choice made] | [date] | Decided |
| R-1 | [Key technical risk] | [date] | Open |

**Decision log format:** DC-N = decision, R-N = risk. Decisions are append-only. Risks carry a `last-reviewed` date.

---

## Notes

**Tech stack:** [Languages, frameworks, major dependencies]

**Deployment model:** [Where does it run? CI/CD pipeline?]

**Architectural constraints:** [Any load-bearing decisions the DM should never override]

**Security review cadence:** [How often? Who reviews?]
