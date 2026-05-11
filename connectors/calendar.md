# Connector: Calendar

**Connector type:** Calendar (Google Calendar, Outlook, Apple Calendar — whichever Cowork has approved)

**CORE uses Calendar as a signal source, never a write target by default.**

---

## What CORE reads from Calendar

| Signal | How CORE uses it |
|---|---|
| Events with project-related attendees | Auto-populates §People — identifies project stakeholders from recurring meeting patterns |
| Events with project-related titles | Surfaces as project-context items in §Notes; can be promoted to §Moves deadlines |
| Regular check-in patterns | DM uses cadence to suggest retrospective or risk-review timing |
| Event gaps (no meetings for N days) | DM may surface as "no scheduled review — consider a check-in" signal |

**PROJECT.md surfaces populated:**
- `§People` — stakeholders auto-detected from meeting attendees (user reviews, edits, or removes)
- `§Moves` — deadline-tagged items from events with hard dates
- `§Risks` — review cadences (if a known review meeting disappears from calendar, DM flags it)

---

## Configuration

**During onboarding wizard:** the DM probes Calendar by listing events. If Calendar returns results, the wizard surfaces detected project-stakeholders for user confirmation. No configuration vocabulary required.

**Narrowing:** by default, CORE looks at all calendars the user has approved. To narrow to specific calendars, tell the DM which ones matter ("only use my Work calendar, not Personal"). DM stores the preference in `~/.core/workspaces/<id>/` connector config.

---

## What CORE does NOT do with Calendar

- **No silent event creation.** The DM may propose creating a risk-review meeting ("Want me to schedule a check-in on Thursday?") but always waits for explicit user approval before calling the Calendar write tool.
- **No reading of event bodies/notes** unless the user explicitly asks ("what were the notes from last week's standup?").
- **No sharing calendar data externally** — all Calendar signals stay within the CORE session context.

---

## Troubleshooting

**Calendar probe returned no results:** The connector may not be approved in this Cowork session. Check Settings → Connectors in Cowork.

**DM is pulling the wrong attendees into §People:** Tell the DM "remove [name] from §People — they're not involved in this project." The DM updates §People and adjusts its attendee-matching heuristic for this workspace.

**Too many calendar events surfacing:** Tell the DM "only look at the [calendar name] calendar for this project." DM will narrow its probe.
