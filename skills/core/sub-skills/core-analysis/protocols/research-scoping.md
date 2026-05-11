# Research Scoping Protocol

How the Research Director decomposes a broad topic into structured, parallel-ready research questions with source assignments and scope boundaries. Used in `/core-analysis` Investigation mode.

---

## 1. Topic Decomposition

Break the user's research topic into **3-5 specific research questions**. Each question must satisfy three criteria:

- **Specific enough to research.** A researcher should be able to start investigating with available tools (WebSearch, Read, Grep, WebFetch) without needing further clarification. "How does X work?" is researchable. "What is everything about X?" is not.
- **Broad enough to be useful.** The answer should be referenceable by future agents investigating related topics. A question that produces a one-sentence answer is too narrow. A question that produces a multi-section finding with sources and confidence levels is the right granularity.
- **Independent enough for parallel work.** Researchers assigned to different questions should be able to work simultaneously without blocking each other. If Question 3 requires the answer to Question 2, they aren't independent — restructure so each stands alone.

**Decomposition heuristic:** Start with the user's prompt. Identify the implicit sub-topics: What is it? How does it work? What are the trade-offs? What does the evidence say? What's missing from current understanding? Select 3-5 of these that best serve the user's intent.

---

## 2. Source Domain Identification

For each research question, identify which source domains are most likely to yield answers:

| Domain | What it covers | Tools | Best for |
|--------|---------------|-------|----------|
| **Web** | Documentation, blogs, forums, release notes, tutorials | WebSearch, WebFetch | Technical how-to, current state, community consensus |
| **Academic** | Papers, studies, formal publications, standards bodies | WebSearch (scholar), WebFetch | Theoretical grounding, empirical evidence, methodology |
| **Internal** | Project files, git history, existing research library, codebase | Read, Grep, Glob | Project-specific context, prior decisions, implementation details |

**Assignment principle:** Each researcher gets a primary source domain. Overlap is acceptable for cross-referencing, but primary assignments should be distinct. If two researchers are both primarily searching the web, one of them is redundant — give them different domains or different sub-questions.

---

## 3. Existing Library Gap Analysis

Before finalizing scope, check `~/.core/research/index.json` for existing research.

**Three outcomes:**

| Match Type | Library State | Action |
|-----------|--------------|--------|
| **Exact match** | Same topic slug exists with active document | Supersession candidate. Read the existing document. Scope the new research to deepen, update, or correct — not to repeat. New version number. |
| **Partial overlap** | Related topics exist (check tags, `related_topics` in meta.json) | Reference and extend. Cite existing library entries as internal sources. Scope the new research to fill gaps, not duplicate coverage. |
| **No match** | Nothing related in the library | New territory. Full scoping latitude. Note this is the first library entry on the topic. |

**Cross-reference check:** When partial overlap exists, read the related documents' data voids sections. These are pre-identified gaps that the new research might fill — and they save the researchers from re-covering ground that's already well-documented.

---

## 4. Scope Boundaries

Research without boundaries expands indefinitely. The Research Director sets explicit boundaries based on:

- **The user's prompt** — what did they actually ask for? Resist the temptation to investigate adjacent fascinating topics.
- **The existing library state** — if related research already covers sub-topic X, exclude it from scope and reference the existing document.
- **The practical limits of a single session** — a research session should produce one high-quality document, not three shallow ones.

**Boundary format:**

```
IN SCOPE:
- [Specific sub-topic or question]
- [Specific sub-topic or question]

OUT OF SCOPE (potential follow-ups):
- [Adjacent topic — why excluded, potential future /core-analysis invocation]
- [Adjacent topic — why excluded]
```

Boundaries are presented to the user during scoping and are binding once approved. If researchers discover something compelling but out of scope, it goes in the Recommendations section as a follow-up — not into the current investigation.

---

## 5. Token Budget Estimation

Rough estimates for planning and post-session comparison:

| Configuration | Estimated Tokens | When to Use |
|--------------|-----------------|-------------|
| 2 researchers + fact-checker + synthesizer | 40-80K | Standard topics, well-defined questions |
| 3 researchers + fact-checker + synthesizer | 60-100K | Broad topics, multiple source domains |
| Full swarm + cross-domain surprise | 80-120K | Complex/architectural topics, >=48GB machines |
| Single researcher (degraded mode) | 15-30K | Parent skill unavailable, quick investigation |

**Budget variables:** These are rough guides, not caps. Deep source material (long documents requiring Programmatic Extraction), high contradiction rates (more cross-reference rounds), and complex synthesis (many findings to integrate) all increase token usage. The Research Director logs actual vs. estimated in Step 7 for future calibration.
