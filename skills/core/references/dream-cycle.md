# CORE Dream Cycle: Semantic Distillation Protocol

The dream cycle is CORE's memory curation mechanism. It reviews accumulated memory, session logs, and project notes to consolidate knowledge, resolve contradictions, and promote validated insights to permanent storage.

## Two-Tier Data Lifecycle

The dream cycle is **Tier 2** of CORE's two-tier data lifecycle:

- **Tier 1: Auto-Memory** — Fires every session automatically. Captures immediate learnings, user feedback, and session-level decisions.
- **Tier 2: Dream Cycle** — Runs every 3-5 sessions (this document). Curates, distills, and consolidates accumulated knowledge.

## When to Run

- After significant sessions (3+ agents, complex findings)
- When memory files exceed ~20 entries
- When the DM detects contradictions between memory entries
- Periodically (every 3-5 sessions) as maintenance
- When explicitly requested by the user

## The Four Phases

### Phase 1: Memory Inventory

Read all memory files in the project's memory directory (`~/.claude/projects/*/memory/`) and any cross-project store (e.g., `~/.claude/memory/`):

1. **Index custody (do this first).** For each store, list every memory file on disk and compare to the store's index file (`MEMORY.md`, `memory.md`, etc.). Any orphan file (on disk but not indexed) gets an index entry added or moved to `archived/` if no longer relevant. Any indexed entry pointing at a missing file gets removed from the index. The store's index must accurately reflect what exists; otherwise retrieval fails silently and the rest of the dream cycle operates on a wrong map.
2. List every memory file with its type, name, and last-modified date.
3. Read each file's content.
4. Catalog: what topics are covered, what's recent, what's potentially stale.

If an index has grown too large to load eagerly (the cross-project `memory.md` reads in full per the PreToolUse hook; the per-project `MEMORY.md` is auto-injected up to 200 lines), surface the over-growth and split topic content into sub-files or sub-folders so the index stays index-only.

### Phase 2: Semantic Distillation

For each memory entry, assess:
- **Still accurate?** — Does this match the current state of the codebase/project? Read relevant files to verify.
- **Still relevant?** — Is this information useful for future sessions, or was it only relevant to a completed task?
- **Redundant?** — Does another memory entry cover the same ground? If so, merge into the stronger entry.
- **Needs updating?** — Has the underlying fact changed since this was written?

Actions:
- **Promote**: Transient observations that proved true across multiple sessions → upgrade to permanent project knowledge
- **Merge**: Duplicate or overlapping entries → consolidate into one comprehensive entry
- **Archive**: Information that was useful but is no longer relevant → move to an `archived/` subdirectory with a note about why
- **Delete**: Information that turned out to be wrong or is now captured in code/docs → remove
- **Update**: Information that's mostly right but needs correction → edit in place

**Workspace field curation:** Also review the `dm_notes` field in each workspace's `workspace.json`. If it contains more than ~10 one-line self-correction entries, consolidate them into a brief paragraph summarizing recurring briefing patterns, then remove the individual entries. The field should remain readable and useful — not a growing wall of one-liners.

### Phase 3: Contradiction Resolution

Identify pairs of memory entries that contradict each other:
1. List the contradiction explicitly: "Memory A says X, Memory B says Y"
2. Investigate which is correct by reading current project state
3. Resolve: update or remove the incorrect entry
4. If both are partially correct, create a new entry that captures the nuanced truth

### Phase 4: Pattern Synthesis

Look across all surviving memory entries for meta-patterns:
- What themes recur across sessions?
- What feedback has the user given consistently?
- What project patterns have emerged?
- Are there insights that no single memory captures but the collection implies?

If a new meta-pattern is identified, create a new memory entry to capture it.

### Phase 5: Agent Refresh

Review agent files for agents that participated in recent swarms. Agent files live at `~/.core/agents/<kebab-case-name>.md` — the filename matches the agent's name as used in swarm briefings (e.g., an agent introduced as "Adversarial Consistency Auditor" maps to `adversarial-consistency-auditor.md`).

1. For each agent that was used, check if the execution produced notable observations about its effectiveness — from swarm effectiveness reports or the DM's own observations.
2. If patterns emerge across uses, update the agent's Identity, Analytical Lens, or Blind Spots to reflect what was learned.
3. Retire any agent that has consistently underperformed or whose niche is now covered by a better-designed agent. When retiring: move the file to `~/.core/agents/retired/` rather than deleting it — the configuration retains reference value. Annotate any `~/.core/task-configs/` entries that reference the retired agent so the DM knows to substitute during future swarm composition.

This does not require a full audit of all agents — only those that participated in sessions since the last dream cycle.

---

## Output

The dream cycle produces:
1. Updated memory files (modified, merged, archived, or deleted)
2. A dream cycle retrospective at `~/.core/dream-cycles/<YYYY-MM-DD>.md` documenting all changes (per the data-storage protocol's Self-Evolution Artifacts table)
3. Updated MEMORY.md index reflecting any additions/removals
