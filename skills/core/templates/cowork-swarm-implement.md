# CORE Swarm Template: Implementation (Cowork)

> **Cowork variant.** Uses `Agent` + `Task*` primitives. `TeamCreate` is not available in Cowork. For Claude Code, use `templates/swarm-implement.md`.

## Purpose

Execute code changes, write deliverables, or modify external systems. Implementation swarms prioritize correct execution over adversarial dialogue. Precision matters more than breadth.

## Cowork-Specific Mechanics

### Agent Lifecycle

Each implementer is spawned via `Agent({subagent_type: "general-purpose", name: "...", prompt: "..."})`. The agent returns when complete. Its `agentId` enables resumption via `SendMessage` if a multi-step task needs mid-stream instruction.

**Parallel implementers** (non-overlapping files): send multiple `Agent` calls in a single message. They execute concurrently and return independently.

**Sequential implementers** (dependent files): await previous agent's return, then spawn the next.

### Task Tracking

`Task*` tracks phase state and per-file completion. Each file or module gets its own task:

```
TaskCreate({title: "Implement: file-a.md", status: "in_progress"})
TaskUpdate({title: "Implement: file-a.md", status: "completed"})
```

The validator awaits all implementer tasks reaching `completed` before beginning validation.

### Host-Path Constraint

The DM's **bash** cannot reach host paths (`~/.core/`, `~/.claude/skills/`, `/Users/dbates/...`). All file operations against host paths must use the **Write/Edit/Read tools** directly, not bash pipelines. Any `rm` equivalent must be done via the Edit tool (replace with empty content) or deferred to a SessionEnd hook.

---

## Modes

### Single-File Changes

- **1 Editor Agent** + DM acts as Validator + Guard
- Best for: well-specified, bounded changes to one file
- Workflow: DM writes explicit change manifest → spawns Editor → Editor signals completion via SendMessage → DM validates by reading the file

### Multi-File Changes (Parallel)

- **2-3 Implementer Agents** (one per file or module, non-overlapping) + **1 Validator Agent**
- Best for: coordinated changes across multiple files
- Workflow: DM writes change manifest → spawns implementers in parallel → each signals completion → DM spawns Validator

### Multi-File Changes (Sequential)

- **1 Editor Agent** spawned per file, one at a time
- Best for: changes where file B depends on file A's output
- Workflow: DM writes change manifest → spawns Editor for file A → awaits completion → spawns Editor for file B

---

## Guard

**Required for all write operations to external systems** (task trackers, mail, calendars, remote databases). For file-only changes within the project workspace, the DM serves as Guard. For any operation outside the mounted project folder, spawn a dedicated Guard agent to review before writing.

---

## Phases

### Phase 1: Change Manifest

**TaskCreate** "Phase 1 — Change Manifest".

The DM writes an explicit, ordered change manifest BEFORE spawning any implementer. The manifest must include:
- Specific file paths (use absolute host paths for Write/Edit tools; do NOT use bash-relative paths)
- Exact text to add, modify, or remove
- Before/after examples where the change is non-obvious
- Execution order (which changes depend on prior changes)

Comprehensive change lists beat vague instructions. An ordered list with specific line references executes correctly. "Apply the recommendations" fails.

**TaskUpdate** Phase 1 = completed.

### Phase 2: Implementation

**TaskCreate** per file: "Implement: {filename}" = in_progress.

Spawn implementers per the manifest. For parallel implementation, batch `Agent` calls in a single message:

```
Agent({
  name: "Editor-A",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Change manifest section A: [explicit changes]. When complete, your final message must be exactly: CHANGES COMPLETE — file-a.md'"
})
Agent({
  name: "Editor-B",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Change manifest section B: [explicit changes]. When complete, your final message must be exactly: CHANGES COMPLETE — file-b.md'"
})
```

When each editor returns with the `CHANGES COMPLETE` signal: **TaskUpdate** that file's task = completed.

**Context note:** Each implementer's full output lands in the DM's conversation context. For large multi-file swarms, summarize completed editor outputs into a ≤200-word checkpoint note before spawning the next phase.

### Phase 3: Completion Signal

**CRITICAL.** The implementer agent MUST signal completion explicitly. Do not rely on task status alone — task status tracks phases, not file atomicity. A task may be marked `in_progress` while the file is mid-write.

Pattern: "When complete, your final message must be exactly: `CHANGES COMPLETE — {filename}`"

The Validator reads files ONLY after this explicit signal arrives. If the signal is missing, SendMessage the implementer to confirm status before proceeding.

### Phase 4: Validation

**TaskCreate** "Phase 4 — Validation".

After ALL implementers signal `CHANGES COMPLETE`: spawn the Validator:

```
Agent({
  name: "Validator",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + 'Validate these files against the change manifest:\n[files]\n[manifest]\n\nFor each manifest item: APPLIED CORRECTLY / NOT APPLIED / PARTIALLY APPLIED. Return structured table only.'"
})
```

Validator checks:
- Was each manifest change applied correctly?
- Are there unintended side effects?
- Were any manifest items missed?

If validation finds failures: DM re-opens the specific implementer task and spawns a correction editor. Re-validate after correction.

**TaskUpdate** Phase 4 = completed when all manifest items APPLIED CORRECTLY.

### Phase 5: Guard Approval

**Required only if the implementation writes to systems outside the project workspace** (external APIs, task trackers, remote databases, other users' files).

For any external write: spawn a Guard agent that reviews the specific operation, assesses risk, and returns APPROVE or BLOCK:

```
Agent({
  name: "Guard",
  subagent_type: "general-purpose",
  prompt: "[base-protocol] + [guard role] + 'Review this operation: [operation]. Return: APPROVE with rationale, or BLOCK with specific concern. No narrative.'"
})
```

Guard has veto power. BLOCK = DM resolves the concern before proceeding. Do not bypass Guard.

### Phase 6: Commit / Delivery

When all validations pass and Guard (if needed) approves:

- **Git commit**: use `git commit -m "..."` via bash (bash CAN reach the project workspace, just not host-wide paths)
- **File delivery**: Write tool for any host-path artifacts
- **User notification**: DM summarizes what changed and what's next

---

## Completion Handshake Protocol

This is the most critical operational lesson:

1. Implementer marks their file task complete via TaskUpdate
2. Implementer sends explicit "CHANGES COMPLETE — {filename}" message
3. Validator reads the file ONLY after that message arrives

Never rely on task status alone. Never rely on the `Agent` tool's return timing alone. The explicit completion message is the only reliable signal.

---

## GAN Loop

Minimal in implementation swarms. The loop is: implement → validate → fix if needed. Do not apply review-swarm adversarial patterns here — multi-round generator-critic exchanges are over-engineered for deterministic execution. Save adversarial energy for the review swarm that preceded this one.

---

## Output

- Files modified per the change manifest
- Validation report (APPLIED CORRECTLY / NOT APPLIED / PARTIALLY APPLIED per manifest item)
- Guard approval log (for any external write operations)
- DM summary of what changed, for user and session handoff
