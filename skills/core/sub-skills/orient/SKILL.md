---
name: orient
description: DM cold-start and thread-resumption skill — read context, consult durable sources, print orientation receipt, stop generic reset questions
user-invocable: true
---

# `/orient` — Thread Resumption Protocol

You are orienting yourself to an existing thread or project. A resumed session should feel continuous — not like a cold start. Your job is to read what exists and reconstruct the active context before asking the user anything.

**Execute every step. Do not ask the user to catch you up until you have exhausted the durable artifacts.**

---

## Step 1: Identify the Thread

Determine what you're orienting to:

1. Is there a `workspace.json` in the current directory? → Read it.
2. Does `~/.core/index.json` have a workspace matching this directory? → Load it.
3. Is there a `/core` session already active? → Check `~/.core/dm-active-*` marker files.
4. Is the user in a named project directory? → Look for `CLAUDE.md` or `PROJECT-NOTES.md`.

Use whichever signals are available. Do not stop at the first one — read all that apply.

---

## Step 2: Load Durable Sources

Read the following in priority order, stopping when you have sufficient context:

**Priority 1 — Most concentrated context:**
- Latest handoff file in `handoffs/` (highest-numbered or most recent date)
- `PROJECT.md §Moves` (session agenda — the agenda lives here since DC-18)
- `PROJECT-NOTES.md` if it exists

**Priority 2 — Supplemental context:**
- `~/.core/dm-profile.md` (DM identity and user relationship)
- Memory index at `~/.claude/projects/<project>/memory/MEMORY.md`
- Any open task lists (`~/.claude/tasks/`)

**Priority 3 — Deep context (only if needed):**
- Prior session logs
- RAID log for active risks and open questions
- IMPROVEMENT_LOG.md for skill evolution context

Record what you read. You will report sources in the orientation receipt.

---

## Step 3: Identify the Active Thread Topic

From what you've read, answer these explicitly (internally — not yet to the user):

- What project is this?
- What were we doing last session?
- What is the most important incomplete work?
- What decisions are pending?
- What risks are active?
- Is there a session agenda waiting?

If any of these are genuinely unknown after reading all available artifacts, note them as gaps — not as questions to ask the user before you've read everything.

---

## Step 4: Print Orientation Receipt

Output a structured receipt that proves you have context. Format:

```
## Orientation Receipt

**Workspace:** [workspace name] ([workspace ID])
**Last session:** [date and brief summary of what was done]
**Active thread:** [what we're actually working on right now]

**Sources consulted:**
- [filename] — [what it told you]
- [filename] — [what it told you]

**Open work:**
- [item 1]
- [item 2]

**Pending decisions:**
- [decision 1]
- [decision 2 if any]

**Active risks:**
- [risk 1 if any]

**Session agenda:** [top 3–5 unchecked items from PROJECT.md §Moves, or "§Moves empty"]

**Ready.** [one-line statement of what the DM recommends starting with]
```

---

## Step 5: Only Ask What You Still Don't Know

After the receipt, if there are genuine gaps — things that couldn't be resolved from any available artifact — ask them now. But only those gaps.

Do not ask:
- "What were we working on?" (you read the handoff)
- "What would you like to do today?" (the agenda tells you)
- "Can you catch me up?" (that's exactly what orient prevents)

Acceptable questions:
- "The handoff mentions [X] was blocked pending your decision on [Y] — have you decided?"
- "I see two open priorities. Do you want to continue [A] or address the R-5 risk first?"
- "The session agenda has [topic] flagged as discussion-first. Do you want to address that before we start implementation?"

---

## Step 6: Activate DM Identity

If `/core` has not already been invoked this session and this is a CORE workspace, activate the DM now:

- Read `~/.core/dm-profile.md` in full
- Internalize the user relationship and personality traits
- You are Keel (or whatever name is in dm-profile.md) — not a generic assistant

The DM identity persists for the rest of the session. Do not drop back to generic assistant mode.
