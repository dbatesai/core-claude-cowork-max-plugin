# Connector: Slack

**Connector type:** Slack

**CORE uses Slack as a signal source. Writes are explicit-only: the user asks, the DM confirms, then posts.**

---

## What CORE reads from Slack

| Signal | How CORE uses it |
|---|---|
| Channel membership (project-related channels) | Auto-populates §People — identifies project participants |
| Threads mentioning the user in project channels | Surfaced as project signals; promotable to §Moves or §Risks |
| Pinned messages in project channels | Indexed in §Notes as persistent references |
| Decisions announced in project channels | Can be promoted to §Decisions with a Slack thread link |

**PROJECT.md surfaces populated:**
- `§People` — channel members from project-related channels
- `§Decisions` — cross-posted decisions get Slack thread links as sources
- `§Notes` — pinned messages from project channels, indexed

---

## Configuration

**During onboarding wizard:** the DM probes Slack by listing channels. The wizard surfaces channels that match the project name or keywords. No channel names or IDs required from the user.

**Narrowing:** by default, CORE scans all channels the user is a member of for project-relevance signals. To narrow to specific channels, tell the DM "only watch #project-alpha and #design-review for this project."

---

## What CORE does NOT do with Slack

- **No posting without explicit instruction.** The user must say "post this to #channel" or similar. DM confirms before posting.
- **No reading DMs.** Only public channels or channels the user has granted CORE access to.
- **No editing or deleting messages.** Write is post-only, once. Subsequent edits don't auto-update via CORE.
- **No reading message history beyond what the connector surfaces.** CORE does not batch-read channel history.

---

## Troubleshooting

**Wrong channels surfaced:** Tell the DM "don't watch #general for this project — only use #product-team." DM updates connector config for this workspace.

**DM mentions a Slack thread I can't find:** DM should include the full thread URL. If it's missing, ask "what's the link to that thread?"

**Slack probe failing:** Check that the Slack connector is approved in this Cowork session (Settings → Connectors). Slack sometimes requires re-approval after Cowork restarts.
