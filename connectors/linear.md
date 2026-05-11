# Connector: Linear (also: Jira, Asana via MCP)

**Connector type:** Linear — with notes on Jira and Asana support via MCP.

**CORE uses Linear bidirectionally: reads issues into §Moves; checking a §Moves item updates the Linear issue.**

---

## What CORE reads from Linear

| Signal | How CORE uses it |
|---|---|
| Issues assigned to user or matching project labels | Synced as §Moves checkboxes |
| Issue status (open, in progress, done, cancelled) | Reflected in §Moves checkbox state |
| Issue blockers and dependencies | Surfaced in §Risks if a blocker is unresolved |
| Cycle velocity | DM uses to calibrate §Moves priority and deadline realism |

**PROJECT.md surfaces populated:**
- `§Moves` — Linear issues sync as bidirectional checkboxes with the issue ID noted
- `§Risks` — blocked or stalled issues flagged as risks with Linear issue link

---

## Bidirectional sync

CORE supports opt-in bidirectional sync per §Moves item:

1. **Issue → §Moves:** Linear issue status change → DM updates §Moves checkbox on next SessionStart.
2. **§Moves → issue:** User checks a §Moves item → DM confirms ("Mark LIN-42 done in Linear?") → DM calls Linear write with user confirmation.

Write is **explicit confirmation only** — DM always confirms before updating a Linear issue.

---

## Configuration

**During onboarding wizard:** the DM probes Linear by listing teams/projects. Detected projects matching workspace name or keywords are surfaced as "I found these Linear projects — should I connect them?" No project IDs needed from the user.

**Narrowing:** by default, CORE scans all Linear teams/projects the user has access to. To narrow, tell the DM "only sync from the `Alpha` Linear project for this workspace."

---

## Jira and Asana

Linear is the first-class integration for v1.0. If you use Jira or Asana instead:
- Check if Cowork has an MCP connector for your tracker.
- If yes: the DM can query it using the same read patterns; bidirectional sync depends on the connector's write capabilities.
- If no: tell the DM your tracker URL and issue format; the DM will note issue references in §Moves as text links and update manually when you confirm status changes.

---

## What CORE does NOT do with Linear

- **No batch issue creation.** The DM may propose creating an issue ("Want me to file this risk as a Linear issue?") but waits for explicit confirmation.
- **No editing issue bodies.** CORE updates status only; it doesn't rewrite your issue descriptions.
- **No deleting or archiving issues.**

---

## Troubleshooting

**§Moves and Linear are out of sync:** Ask the DM to "re-sync §Moves from Linear." DM will probe current Linear state and reconcile.

**DM is pulling the wrong Linear project:** Tell the DM "don't connect `<project name>` to Linear — use `<correct project name>` instead."

**Linear probe returning no results:** The Linear connector may not be approved. Check Cowork Settings → Connectors. Some Linear workspaces require API key configuration at the Cowork admin level.
