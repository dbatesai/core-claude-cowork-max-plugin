# Connector: Drive (Google Drive / OneDrive)

**Connector type:** Drive (Google Drive or OneDrive — whichever Cowork has approved)

**CORE uses Drive as a read-only reference source. CORE never writes to your Drive.**

---

## What CORE reads from Drive

| Signal | How CORE uses it |
|---|---|
| Folders designated as project folders (set during wizard or by user) | Files within those folders indexed as project references |
| File metadata (name, last-modified, owner) | Surfaced in §Notes as an auto-indexed reference list |
| File content (on explicit request) | DM reads specific docs when user asks ("what does the design spec say about X?") |

**PROJECT.md surfaces populated:**
- `§Notes → References` — auto-indexed file list with last-modified timestamps; user can promote specific files to canonical references with a simple instruction ("make the design spec a canonical reference")

---

## Configuration

**During onboarding wizard:** the DM does NOT ask which Drive folder is the project folder — this avoids vocabulary mismatch. Instead, the wizard skips Drive entirely for pane 3. After onboarding, the DM surfaces a *"I found these Drive folders that look project-relevant"* panel based on file-name + keyword heuristics, and the user picks zero or more.

**Setting project folders post-onboarding:** tell the DM "use the `Project Alpha / Design` folder in Drive as my project folder." DM updates the connector config.

---

## What CORE does NOT do with Drive

- **No writes.** CORE never creates, edits, or deletes Drive files.
- **No reading content by default.** CORE reads file metadata (names, dates) by default; reading actual file content requires an explicit user request.
- **No bulk indexing of large folder trees.** CORE scans one level of a designated project folder by default. For deeper scans, tell the DM explicitly.
- **No sharing Drive data externally.** All Drive signals stay within the CORE session context.

---

## Troubleshooting

**DM can't find my project folder:** Either the folder isn't in a Drive location the connector has access to, or the folder name doesn't match the project keywords. Tell the DM the exact folder path: "My project files are in `Shared Drives / Product / Alpha / 2026`."

**Reference list is stale:** DM refreshes Drive references at SessionStart. If a file is missing, it may have been moved or renamed. Ask the DM to re-probe: "re-scan my project folder for updated references."

**Drive connector not approved:** Check Cowork Settings → Connectors. Drive connectors are often org-level and may require IT approval for first use.
