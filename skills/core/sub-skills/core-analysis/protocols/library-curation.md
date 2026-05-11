# Library Curation Protocol

The mandatory bookend process for every `/core-analysis` invocation (both Synthesis and Investigation modes). Skipping either phase is a protocol violation.

The research library lives at `~/.core/research/` with structure:
```
~/.core/research/
├── index.json
├── topics/<topic-slug>/<topic-slug>-v<N>.md
├── topics/<topic-slug>/meta.json
└── archive/
```

---

## Bookend Open (Step 1)

Execute at the START of every analysis, before any source processing.

1. **Read `~/.core/research/index.json`.**

2. **If the file does not exist, perform first-run bootstrap:**
   - Create directories: `~/.core/research/`, `~/.core/research/topics/`, `~/.core/research/archive/`
   - Write skeleton `index.json` with version 1, zero stats, empty documents array, empty topic_index
   - Report: "Research library bootstrapped — first run."

3. **Filter existing documents by relevance to the incoming topic:**
   - **Exact topic match** → load full document content
   - **Tag overlap (2+ shared tags)** → load frontmatter + summary only
   - **Related topic (1 shared tag or semantic relation)** → load summary only
   - **No relation** → skip (do not load)

4. **Build the Library Context Brief:**
   - Total library state: document count, topic count, average composite score
   - Relevant documents: list with title, version, score, tags, summary
   - Stale documents flagged (see staleness heuristic below)
   - Potential conflicts: where existing library content may contradict incoming sources

5. **Present the Library Context Brief to the user.** The user can direct attention to specific documents, request loading additional context, or acknowledge and proceed.

---

## Bookend Close (Step 9)

Execute at the END of every analysis, after convergence synthesis and quality scoring.

1. **Persist the new synthesis:**
   - Determine: new topic or new version of existing topic
   - **New topic:** Create `~/.core/research/topics/<topic-slug>/`, write `<topic-slug>-v1.md` with full frontmatter per `schemas/research-document.md`, create `meta.json`
   - **Existing topic:** Increment version number, write `<topic-slug>-v<N>.md`, update `meta.json` version history
   - **Supersession:** If new version supersedes old: set `superseded_by` on old document's frontmatter, update old document's status to `archived`, move to `archive/` if fully superseded, update `meta.json`

2. **Library curation sweep:**
   - Check all active topics for overlapping content using tag intersection + summary comparison (keyword overlap heuristic — NOT semantic similarity, which is unreliable without embeddings)
   - **Overlap > 60% AND new doc scores higher** → flag for merge or supersession, present both options to user with reasoning
   - **Conflict detected** (same topic area, contradictory findings) → present explicitly with both positions, recommend resolution approach
   - **Stale documents** → flag for user review, suggest archive

3. **Update `index.json`** with all changes: new documents, version increments, status transitions, score updates, stats recalculation.

4. **Update organic signals** for every document that was referenced (loaded, cited, or consulted) during this analysis:
   - Increment `times_referenced`
   - Set `last_referenced` to current ISO-8601 timestamp
   - If the new synthesis explicitly cites an existing document, also increment `citation_count`

5. **Report all library changes to the user:**
   - "Added: [title] (score: X.X)"
   - "Updated: [title] v1 → v2"
   - "Archived: [title] (reason: superseded by [new title])"
   - "Flagged: N stale documents for review"
   - "Referenced: N existing documents (signals updated)"

---

## Staleness Heuristic

A document is flagged as stale when ALL of these conditions are met:
- `last_referenced` is null OR more than 60 days ago
- `composite_score` < 3.5
- `citation_count` == 0

Stale documents are flagged for user review — never automatically archived. The user decides disposition.

---

## Supersession Rules

- **Same topic, newer version** → new version supersedes old. Old version is archived with `superseded_by` pointing to new.
- **Overlapping topics, new doc higher score** → propose merge to the user. Present both documents, explain the overlap, let the user decide whether to merge, keep both, or archive one.
- **Conflicting findings across documents** → present both positions explicitly. Recommend a resolution approach (re-analysis, additional research, user judgment). Never silently resolve conflicts.
