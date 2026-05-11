# CORE for Cowork — Max Plugin

**Delivery intelligence for your Cowork projects.** CORE gives you a persistent Delivery Manager (DM) who remembers your project across sessions, runs adversarial reasoning swarms on hard problems, and surfaces risks before they become blockers — all inside Cowork.

The max plugin is the full Cowork-native experience: Live Artifact dashboards, scheduled sessions, connector-aware project setup, and a DM Workshop where your DM has a persistent visual presence.

**Source:** `dbatesai/core-skill` — the underlying CORE skill is open source.  
**Companion:** [dbatesai/core-skill](https://github.com/dbatesai/core-skill) — use that repo to customize the skill or report skill behavior issues.

---

## Install

Three channels — pick whichever fits your setup:

| Channel | Who it's for | How |
|---|---|---|
| **Anthropic plugin marketplace** | Anyone with Cowork | Open Cowork → Settings → Plugins → search "CORE max" → Install |
| **SharePoint** | Teams behind a corporate firewall | Ask your IT admin to add the plugin zip from your org's SharePoint site; or get the URL from your CORE admin |
| **GitHub releases** | Power users, CI, air-gap installs | [Releases page](https://github.com/dbatesai/core-claude-cowork-max-plugin/releases) → download `core-claude-cowork-max-plugin-vX.Y.Z.zip` → verify SHA256 → install via Cowork admin |

**Verify your download (recommended for GitHub + SharePoint installs):**
```bash
shasum -a 256 -c core-claude-cowork-max-plugin-vX.Y.Z.SHA256SUMS
```

**PGP signature (optional, for highest assurance):**
```bash
gpg --verify core-claude-cowork-max-plugin-vX.Y.Z.zip.asc core-claude-cowork-max-plugin-vX.Y.Z.zip
```
The signing key is published at `https://github.com/dbatesai.gpg`.

---

## First session

1. **Open any Cowork session** in the folder you want to manage with CORE.
2. **Your DM introduces themselves** and opens a three-minute setup wizard. Answer a few questions — what kind of project, who's involved, which connectors you use.
3. **The wizard creates your project's `PROJECT.md`** — the single source of truth for project state, risks, and priorities.
4. **Quit Cowork (Cmd+Q) and reopen.** This activates the CORE MCP server so the live dashboard can read real-time project state.
5. **From here, every session opens with your dashboard** showing project health, active risks, and the DM's session agenda.

No manual configuration. No files to edit. The DM handles everything.

---

## What you get

| Feature | What it does |
|---|---|
| **Persistent DM** | One Delivery Manager who remembers your project across every session. Gives you a name (its own choice), not "the AI." |
| **Trust Strip Dashboard** | Persistent Live Artifact showing project state, active risks, swarm activity, and convergence health. Updates as the session progresses. |
| **Swarm Live View** | Real-time visualization of adversarial reasoning swarms — which agents are running, what they're finding, where tension is highest. |
| **DM Workshop** | The DM's visual presence — a persistent illustration that reflects project state (session age, swarm activity, project health). |
| **Onboarding wizard** | Touch-friendly first-session setup. No typing required beyond your project description. |
| **Adversarial swarms** | `/core` spawns expert persona swarms that challenge each other's conclusions. GAN-style loops with a 84.5% sycophancy-flip baseline. |
| **Project templates** | Six PROJECT.md scaffolds for software delivery, marketing, research, decisions, personal projects, and generic use. |
| **Connector integration** | Calendar, Slack, Drive, and Linear connectors surface context the DM uses to keep `PROJECT.md` current. |
| **Scheduled sessions** | The DM can schedule risk reviews, retrospectives, and follow-ups (v1.0: flag-gated; see §11 Q1). |
| **Skill self-improvement** | The improvement queue applies tested refinements to the bundled CORE skill automatically, session by session, up to a configurable cap. |

---

## Connectors

The max plugin works with any subset of connectors. The more you enable, the more the DM can infer without asking:

| Connector | What CORE uses it for |
|---|---|
| **Calendar** | Auto-detect project team from meeting patterns; suggest retrospective timing |
| **Slack** | Pull channel membership for §People; surface mentions as project signals |
| **Drive** | Link Drive folders as project References; pull document changes as inbox items |
| **Linear** | Surface issue velocity and blocking issues in project state |

None are required. Enable whichever you have. Full docs in `connectors/`.

---

## Which plugin should I install?

Under the current release scope, **this is the one plugin for all Cowork users.** If additional plugin variants become available, the install matrix will expand:

| Use case | Install (current) | Notes |
|---|---|---|
| Cowork, non-technical user, wants full experience | **`core-claude-cowork-max-plugin`** (this) | Active |
| Cowork, technical user, wants generic cross-harness UX | **`core-claude-cowork-max-plugin`** (only option) | Standard variant deferred |
| Claude Code only | Not yet supported | Deferred |

---

## Supply chain notice

This plugin installs hooks that run on your macOS host at session start and end. Those hooks:

- Read `~/.claude/skills/` to inject the CORE skill into each session
- Write to `~/.core/` (your project state and DM memory) — gated behind a one-click `request_cowork_directory` approval each session
- On first session, register the CORE MCP server in `~/Library/Application Support/Claude/claude_desktop_config.json` — backing up the existing config first

The CORE skill is open source at `dbatesai/core-skill`. The MCP server tools are read-only — no tool modifies external state. SHA256 checksums and an optional PGP signature accompany every release for artifact verification. CDN resources in Live Artifacts are pinned to specific commit SHAs and verified at CI time.

---

## Troubleshooting

**Dashboard not showing live state?** Quit Cowork (Cmd+Q) and reopen — the MCP server loads at app start, not session start. One restart after install is required.

**Wizard opened again unexpectedly?** The plugin detected no `PROJECT.md` in your current folder. Either use the wizard to set up this folder, or open Cowork in the folder where your existing project lives.

**Improvement queue over cap?** You'll see a `CORE-QUEUE-OVER-CAP` marker in the DM's first message. Review `~/.core/improvement-queue.md` manually and delete or apply entries. The default cap is 5 (set `CORE_IMPROVEMENT_QUEUE_CAP=<n>` env var to override).

**MCP registration failed?** The DM will note this and run in snapshot mode (dashboard shows last-session state, not live state). Check `~/.core/mcp-install-log.md` for the error. Set `CORE_MCP_INSTALL_MANUAL=1` to disable auto-registration and manage the config manually.

---

## License

MIT — see `LICENSE`.
