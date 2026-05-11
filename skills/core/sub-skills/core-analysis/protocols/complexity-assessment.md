# Complexity Assessment Protocol

The three-tier adaptive swarm model for `/core-analysis`. In Synthesis mode, assessed after source inventory. In Investigation mode, assessed based on question count and topic complexity (defaults to at least Standard tier).

---

## Tier 1: Lightweight

**Criteria:**
- 1-2 source documents
- Familiar topic with existing library coverage
- Routine library curation or single-document ingestion
- No architectural significance

**Execution:** DM performs synthesis directly. No swarm spawned. Same rigor applies — every claim must trace to a source.

**Token budget:** ~10-20K tokens

**Examples:** Single document ingestion, library maintenance, quick topic summary, updating an existing research document with one new source.

---

## Tier 2: Standard

**Criteria:**
- 3-5 source documents
- Moderate complexity requiring cross-referencing
- Multiple perspectives to integrate
- No high-stakes architectural decisions

**Execution:** 2-3 agent swarm (2 Source Researchers + 1 Synthesizer). Researchers split sources by type: one handles external/LLM sources, one handles internal/project sources.

**Token budget:** ~30-60K tokens

**Examples:** Multi-document synthesis, comparing external analyses against project state, moderate-depth topic exploration across several sources.

---

## Tier 3: Full CORE

**Criteria:**
- 6+ source documents
- Architectural topics or design trade-offs
- High-stakes decisions with significant consequences
- Deep contradictions expected across sources

**Execution:** 4-5 agent swarm (2 Source Researchers + Fact-Checker + Synthesizer + Adversarial Critic). Full GAN-style generator-critic loop where the Adversarial Critic challenges the synthesis.

**Token budget:** ~60-120K tokens

**Examples:** Full independent-analysis synthesis across many external perspectives, architecture review, strategic analysis, framework design decisions.

---

## Override Rules

- **User override:** The user can always escalate or simplify the tier. User judgment takes precedence.
- **Architecture escalation:** Topics touching CORE architecture or framework design always get at least Standard tier, regardless of source count.
- **Mid-execution escalation:** If the DM detects during analysis that the topic warrants deeper treatment, it can recommend escalation to the user. Never silently escalate — present the reasoning and let the user decide.
- **Hardware cap:** Systems with < 24 GB RAM are constrained to Lightweight regardless of complexity assessment. Inform the user of the constraint.
