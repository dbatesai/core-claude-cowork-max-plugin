# Source Classification Protocol

How to classify and weight incoming source documents in `/core-analysis`. Used primarily in Synthesis mode when the user provides documents, but also applicable to Investigation mode when classifying discovered sources.

---

## Classification Table

| Source Type | Authority Level | Treatment |
|------------|----------------|-----------|
| **User-authored direct input** | Highest | Direct instruction and requirements. User intent is authoritative. |
| **`PROJECT.md`** (project synthesis) | Authoritative project truth | The six-section synthesis (What & Why / State / People / Moves / Decisions & Risks / Notes). Read first. User-controlled; trust unless explicitly contradicted by user feedback. |
| **Other internal project artifacts** (`CLAUDE.md`, `requirements/`, `docs/`) | Authoritative, scoped | Project truth within their domain. Trust unless contradicted by `PROJECT.md` or user feedback. |
| **Session handoffs** (`handoffs/`) | Narrative log — not a fact source | Written for the human reader. Facts worth keeping were promoted to `PROJECT.md` at session close. Do not treat as current project state; do not re-read at bootstrap. |
| **Issue tracker / backlog entries** | Actionable | Extract action items and track state. Not analytical authority. |
| **Academic / industry research** | Technical grounding | Evidence base. Cite for support. Evaluate methodology before trusting conclusions. |
| **Web sources** | Reference | Verify before trusting. Check recency. Cross-reference where possible. |

---

## Key Principles

**Source authority affects weighting in convergence analysis but never silences a source entirely.** A low-authority source that provides a unique insight still contributes to the synthesis. Document its authority level and adjust confidence accordingly, but do not discard it.

**Never silently discard a source.** If a source is low-quality, shallow, or off-topic, document why and reduce its weight. The user should be able to see every source's disposition.

---

## Conflict Resolution Hierarchy

When sources conflict, resolve using this hierarchy:

1. **User feedback** — always takes precedence
2. **`PROJECT.md` synthesis** — authoritative project truth. §State, §Decisions & Risks, and §Moves override other internal artifacts when they differ.
3. **Other internal project artifacts** (`CLAUDE.md`, `requirements/`, `docs/`) — scoped project truth
4. **Research evidence** — empirical and academic grounding

Session handoffs are narrative logs, not a conflict-resolution source. If a handoff contradicts `PROJECT.md`, `PROJECT.md` wins — facts that survived session close were intentionally promoted there.

Document which hierarchy rule was applied when resolving any conflict. The user should see transparent reasoning, not silent judgments.

---

## Source Inventory Requirements

For each source, the inventory must capture:

- **Origin:** Which LLM, system, tool, or author produced this document
- **Date:** When it was created or last modified
- **Size:** Approximate length (lines, words, or pages)
- **Focus area:** Primary topic or domain covered
- **Preliminary relevance:** How directly it relates to the analysis task
- **Classification:** Which row from the table above applies
- **Quality flag:** Any concerns about accuracy, recency, or completeness
