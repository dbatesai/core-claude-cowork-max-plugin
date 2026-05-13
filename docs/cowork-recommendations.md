# Cowork Recommendations — Empirical Findings From the CORE Plugin

> **Audience:** Anthropic's Cowork team.
> **Author:** David Bates (`dbatesai`), via the CORE plugin (`core-plugin`).
> **Status:** Seed draft, Session s (2026-05-12). Sections marked **TBD-F9** await the verdict of the F9 `/core` adversarial review (briefing at [`outputs/2026-05-12/f9-install-time-permissions-briefing.md`](../../CORE/outputs/2026-05-12/f9-install-time-permissions-briefing.md) in the CORE source repo). All other sections are empirically grounded and ready for filing.
>
> **Why this doc exists:** building, packaging, and iterating the CORE plugin across four Cowork test passes (2026-05-09 → 2026-05-12) surfaced API + permission-model gaps that affect any plugin author targeting non-technical Cowork users. The recommendations below are framed as constraints to relax, not as bugs in the current implementation — they describe what a plugin can't do today and what shipping the relaxations would unlock.

---

## 1. Confirmed Empirically — Ready to File

These recommendations come from iteration-1 → iteration-4 Cowork tests with concrete reproduction evidence.

### 1.1 Auto-unwrap MCP envelope in `window.cowork.callMcpTool`

**Today:** `window.cowork.callMcpTool('mcp__core__list_workspaces', {})` returns the standard MCP envelope shape `{ content: [{ type: "text", text: "<stringified JSON>" }] }`. Every artifact author must write an `unwrap()` helper that walks `content[0].text` and `JSON.parse` it.

**Empirical confirmation:** `f4-envelope-probe` Live Artifact built 2026-05-12 in the test-core-plugin workspace, verdict pill rendered **STILL WRAPPED** on first open. The CORE plugin ships a shared `unwrap()` in `live-artifacts/shared/helpers.js` so its own artifacts don't repeat the pattern, but every external artifact author hits the same gap.

**Recommendation:** auto-unwrap the envelope in `window.cowork.callMcpTool` so the returned value is the tool's structured result directly. Backwards compatibility: artifact authors who today call `JSON.parse(result.content[0].text)` could be migrated via a deprecation period, or the unwrap could be a per-call opt-in flag.

**What unlocks:** plugin authors get clean per-tool return shapes; the `unwrap()` helper becomes vestigial and removable.

### 1.2 Expose `window.cowork.projectRoot` to artifacts

**Today:** artifacts can't tell which Cowork project they're rendered in. The CORE plugin's DM Workshop artifact had to call `window.cowork.askClaude()` with a 6-mode robust path-extraction prompt to figure out the project folder. Latency: ~2s per session per artifact-load (Q7 probe verdict, 2026-05-10).

**Recommendation:** expose `window.cowork.projectRoot` (string, host-side absolute path of the Cowork project's folder) on the bridge surface. Artifact-side code can be project-aware without the `askClaude` round-trip.

**What unlocks:** project-rooted artifact UX (per-project dashboards, per-project state). Latency reduction (~2s saved per artifact load). Removes one indirect-prompt-injection surface (per TM-14 in the max plugin spec).

### 1.3 Document the `window.cowork.*` API surface

**Today:** `window.cowork.callMcpTool`, `window.cowork.askClaude`, `window.cowork.sample`, `window.cowork.runScheduledTask` were all discovered empirically through paste-in probes (iter-1 + Q1 + Q7). None are documented in the Cowork user-facing docs or the Anthropic plugin reference.

**Recommendation:** publish documentation for the bridge surface — at minimum signatures, return shapes, error semantics, and which methods are gated by Cowork-internal-MCP restrictions. The four methods CORE depends on (above) plus any others.

**What unlocks:** plugin authors stop reverse-engineering the bridge surface from MCP envelope shapes. Reduces probe-design overhead for any feature that depends on artifact-side behavior.

---

## 2. Permission Model — Plugin-Side Mitigation Limits (TBD-F9)

The F9 finding (iter-3 + iter-4 Cowork tests, classified HIGH-severity / dealbreaker for non-technical users) identifies install-time permission UX as the gating UX issue for plugin distribution to non-technical Cowork users. F9 `/core` adversarial review is pending; once verdict lands, this section will enumerate the structural recommendations.

Provisional list (subject to /core verdict refinement):

### 2.1 `permissions` field in plugin manifest **(TBD-F9)**

Plugin declares required scopes at install time: filesystem paths, tool families (`Read`, `Edit`, `Write`, `Bash`), MCP server access, connector access. User sees a single permission summary at the plugin-enable dialog and approves once.

**Current state:** `plugin.json` has no `permissions` or `scopes` field. Anthropic plugin reference (`docs.claude.com/en/docs/claude-code/plugins-reference`) lists `userConfig` (for prompted values like API keys) and bundled `settings.json` (limited to `agent` and `subagentStatusLine` keys) — neither solves install-time permission grants.

### 2.2 Install-time grant flow that survives sessions **(TBD-F9)**

Once user approves plugin permissions at install time, no per-session re-approval for the declared scopes.

**Current state in Cowork:** `request_cowork_directory` requires per-session user approval. Tool family approvals (Read/Edit/Write/Bash via Claude Code's permission system) may or may not persist across sessions — empirical verification needed.

### 2.3 Per-tool-family approval persistence **(TBD-F9)**

Tool family grants (Read, Edit, Write, Bash) persist beyond the current session for plugin-declared scopes.

### 2.4 MCP tool schema auto-load when plugin declares the server **(TBD-F9)**

Today: deferred-schema MCP tools require `ToolSearch` to load schemas before first call. For a plugin bundling its own MCP server, the user's first invocation of `mcp__<plugin>__*` triggers a `ToolSearch` round-trip even though the plugin's `.mcp.json` already declares the server.

Recommendation: when a plugin's `.mcp.json` lists a bundled MCP server, its tool schemas should be in-context at session start without requiring `ToolSearch`.

### 2.5 `request_cowork_directory` grants survive sessions **(TBD-F9)**

Cowork-specific. Once user approves a folder for a plugin's declared scope at install time (or first session), subsequent sessions don't re-prompt for the same folder + same plugin.

### 2.6 `PermissionRequest` hook semantics documentation **(TBD-F9)**

The Anthropic plugin reference lists `PermissionRequest` as a hook event ("When a permission dialog appears", plugins-reference.md:192) but doesn't document return semantics — can the hook customize the dialog message? Auto-approve known plugin-declared scopes? Log the request for audit? Documentation gap blocks Option 5 of the F9 briefing (PermissionRequest hook customization).

---

## 3. Evidence Trail

Concrete evidence references for the recommendations above. Useful for the Cowork team when validating reproduction.

| Recommendation | Empirical source | Date |
|---|---|---|
| 1.1 Auto-unwrap | `f4-envelope-probe` Live Artifact verdict pill | 2026-05-12 |
| 1.2 projectRoot | DM Workshop `getProjectRoot()` 6-mode extraction code | 2026-05-11 |
| 1.3 API surface doc | Q1 + Q7 + Q8 paste-in probe findings | 2026-05-10 |
| 2.1 permissions field | `.claude-plugin/plugin.json` inspection (no scopes field) | 2026-05-12 |
| 2.2 grant flow | F9 finding in `iteration-3-cowork-test.md` + `iteration-4-cowork-test.md` | 2026-05-11 / 12 |
| 2.3 tool family persistence | F9 finding, Read blocked on `~/.core/vibes/vibe-log.md` mid-session | 2026-05-12 |
| 2.4 MCP schema auto-load | iteration-3 finding F9 mention of `ToolSearch` deferred-schema loads | 2026-05-11 |
| 2.5 cowork_directory persistence | DC-29 paste-in probe `cowork-scope-test` session | 2026-05-10 |
| 2.6 PermissionRequest semantics | Anthropic plugin reference plugins-reference.md:192 | (reference doc, undated) |

All four iteration feedback packets are at `<test-core-plugin-project>/feedback/iteration-{1,2,3,4}-cowork-test.md`; the F9 briefing is at `<CORE-repo>/outputs/2026-05-12/f9-install-time-permissions-briefing.md`.

---

## 4. Notes for the Cowork Team

- **The CORE plugin is single-author / single-installer today.** David Bates is sole user. The recommendations above generalize beyond a single plugin (every plugin author distributing to non-technical Cowork users hits the F9 class of problem), but the empirical evidence comes from CORE specifically. Treat the artifact + permission findings as representative of the problem class, not as bug reports against this one plugin.
- **The CORE plugin pattern is reusable.** Diagnostic Live Artifacts (`f4-envelope-probe` shape) are a cheap way for Cowork to validate API behavior changes — single-page artifact, one open, one verdict pill. Worth borrowing for Cowork's own regression suite.
- **BBLens-relevant dimension.** If/when the BBLens overlay (T-Mobile Broadband internal wrapper around CORE) ships as a Cowork plugin (`bblens-plugin`, not yet built), the F9 class of problem affects T-Mobile Broadband non-technical-user distribution via SharePoint + Confluence. The fixes above unlock that distribution path.

---

*Maintained as part of the CORE plugin release. Updated when new empirical findings land; major changes follow the plugin's release cadence (`CHANGELOG.md`).*
