# CORE Swarm Template: Research (Cowork)

> **Cowork variant.** Uses `Agent` + `Task*` primitives. `TeamCreate` is not available in Cowork. For Claude Code, use `templates/swarm-research.md`.

## Purpose

Multi-source investigation, comparison, and fact-finding. Research swarms produce integrated reports with source provenance and calibrated confidence levels.

## Cowork-Specific Mechanics

### Spawning Researchers in Parallel

Send multiple `Agent` calls in a **single message** for concurrent execution. Each researcher operates in its own context — they don't see each other's findings until the DM cross-pollinates via SendMessage:

```
# One message = parallel research
Agent({name: "Researcher-Internal", prompt: "..."})
Agent({name: "Researcher-Web", prompt: "..."})
Agent({name: "Researcher-Technical", prompt: "..."})
```

Each returns an `agentId`. Use `SendMessage({to: agentId, ...})` to deliver cross-pollination findings.

### Task Tracking

```
TaskCreate({title: "Research Phase 1: Parallel Research", status: "in_progress"})
TaskCreate({title: "Research Phase 2: Cross-Reference", status: "not_started"})
TaskCreate({title: "Research Phase 3: Fact-Check", status: "not_started"})
TaskCreate({title: "Research Phase 4: Synthesis", status: "not_started"})
```

### Context Budget

Research agents often return large outputs (full web pages, document excerpts, multi-source summaries). Compress each agent's findings into a ≤300-word structured brief before the next phase. A raw research dump from 3 agents at 2000 tokens each = 6000 tokens consumed before synthesis begins. Budget accordingly.

### Tool Access in Cowork

Researchers spawned as `general-purpose` agents have access to firecrawl-based web tools, Read/Write file tools, and bash (for workspace-relative paths only — host-wide paths require Read tool). For web research, instruct agents to use available search tools. For internal documents, instruct agents to use the Read tool with absolute host paths.

---

## Default Roster

- **2-3 Researchers** — each with a different source specialty (internal/project docs, web/external, technical documentation)
- **1 Synthesizer** — integrates verified findings into a coherent report
- **1 Fact-Checker** — verifies claims and source provenance independently

**Hardware recommendation (M5 Pro 24GB):** 2 researchers + 1 synthesizer (DM plays Fact-Checker inline). 3 agents total is the right ceiling for a Cowork research swarm given shared context budget.

---

## Phases

### Phase 1: Parallel Research

**TaskCreate** "Phase 1 — Parallel Research" = in_progress.

Spawn researchers in parallel. Each researcher is assigned distinct source territory to avoid duplication. Researchers announce their source assignments in their opening message:

```
Agent({
  name: "Researcher-Internal",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Investigate: [topic]. Your sources: project documents at [paths], session logs, handoffs. For each finding: claim, source path, confidence (High/Medium/Low). No narrative — structured findings only.'"
})
Agent({
  name: "Researcher-Web",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Investigate: [topic]. Your sources: web search, GitHub issues, official documentation. For each finding: claim, URL/source, date accessed, confidence. No narrative — structured findings only.'"
})
```

When all researchers return: **TaskUpdate** Phase 1 = completed.

### Phase 2: Cross-Reference

**TaskCreate** "Phase 2 — Cross-Reference" = in_progress.

The DM reads all researcher outputs and compresses them into a ≤500-word cross-reference brief identifying:
- **Contradictions** — where sources disagree (note specific claims and sources)
- **Convergence** — where independent sources agree (stronger signal)
- **Gaps** — information one source has that others lack entirely

Send this brief to all researchers via SendMessage, asking each to confirm: does the brief accurately represent their findings? Do they dispute any claimed contradiction? Do they know of a source that fills a gap?

```
SendMessage({to: researcher_internal_agentId, message: "Cross-reference brief: [brief]. Confirm accuracy. Dispute any misrepresentation. Fill any gap you can from your sources."})
SendMessage({to: researcher_web_agentId, message: "..."})
```

**TaskUpdate** Phase 2 = completed when all researcher responses arrive.

### Phase 3: Fact-Check

**TaskCreate** "Phase 3 — Fact-Check" = in_progress.

Spawn a Fact-Checker that did NOT participate in prior research phases. The Fact-Checker's job is independent verification:

```
Agent({
  name: "Fact-Checker",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Verify these research findings: [compressed findings from phases 1-2]. For each claim: VERIFIED (cite confirming source) / DISPUTED (cite conflicting evidence) / UNVERIFIED (source not accessible or claim not checkable). Check specifically: are sources real and accessible? Do sources actually say what researchers claim? Are any claims outdated? Return structured table only.'"
})
```

Fact-Checker checks:
- Are cited sources real and accessible?
- Do sources say what researchers claimed?
- Are there outdated claims presented as current?
- Are statistical claims properly contextualized?

**TaskUpdate** Phase 3 = completed when Fact-Checker returns.

### Phase 4: Synthesis

**TaskCreate** "Phase 4 — Synthesis" = in_progress.

Spawn the Synthesizer with the compressed, fact-checked findings:

```
Agent({
  name: "Synthesizer",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Produce an integrated research report from these verified findings: [compressed findings]. Structure: (1) Executive summary, (2) Findings by topic with source provenance + confidence level per claim, (3) Contradiction register, (4) Data void analysis, (5) Follow-up recommendations. No narrative padding.'"
})
```

When Synthesizer returns: **TaskUpdate** Phase 4 = completed.

DM performs inline quality check on the synthesis:
- Does every claim cite a source from the Phase 1-2 research?
- Are confidence levels calibrated (not uniformly High)?
- Does the contradiction register surface genuine disputes?
- Are data voids honest rather than glossed over?

Write final report to `sessions/YYYY-MM-DD/{swarm-name}-research-report.md` via Write tool.

---

## Source Priority (Configure Per Deployment)

Establish source priority for the specific research question. General principle:

- **Internal/project sources** (PROJECT.md, session logs, handoffs, decision log) = "Current Truth" — recent decisions and context
- **External/reference sources** (web, GitHub Issues, official docs) = "Technical Grounding" — documentation and community knowledge

When sources conflict, prefer the more recent source unless the older source has stronger technical grounding. Surface the conflict in the report — do not silently choose.

**For Cowork-specific research:** internal sources live in the mounted project folder (Read tool reachable) + host paths (Read tool reachable via absolute path). GitHub Issues and web sources are available via search tools in `general-purpose` agents.

---

## Context Economics

If a researcher returns a large document (e.g., a full scraped webpage), use Programmatic Extraction: spawn a temporary extractor agent to summarize the document into JSON key facts before injecting into downstream agents. This prevents context window bloat.

```
Agent({
  name: "Extractor",
  subagent_type: "general-purpose",
  prompt: "Extract the following from this document: [document]. Return ONLY a JSON object with keys: [key1, key2, key3]. No other output."
})
```

---

## Guard

NOT needed. Research swarms are read-only.

---

## Output

Research report containing:
- Executive summary (DM's synthesis framing)
- Integrated findings by topic (claim, source, confidence per finding)
- Contradiction register (where sources disagreed, how resolved or left open)
- Data void analysis (what information is missing that would strengthen the report)
- Follow-up research recommendations (specific gaps with suggested source approach)
