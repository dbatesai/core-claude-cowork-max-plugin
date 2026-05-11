/**
 * CORE Cowork Max — Live Artifact helper library.
 * Wraps window.cowork.callMcpTool for CORE MCP server calls.
 * Loaded via <script src="shared/helpers.js"> in each Live Artifact.
 *
 * MCP server tool names: mcp__core__<toolname>
 * window.cowork.callMcpTool signature (empirically validated iteration-1):
 *   callMcpTool(fullToolName, args) — 2 arguments.
 *   fullToolName = "mcp__core__<toolname>" (e.g. "mcp__core__list_workspaces")
 *   Returns a Promise wrapped in Cowork's standard MCP envelope.
 *   Use unwrap() on the result to extract the actual payload.
 */

const CoreHelpers = (() => {
  "use strict";

  // ---------------------------------------------------------------------------
  // Unwrap MCP-style response envelopes.
  // window.cowork.callMcpTool wraps results in the standard MCP content envelope.
  // The raw response may be:
  //   1. { content: [{ type: "text", text: "<JSON string>" }] }  — standard MCP shape
  //   2. { content: "<JSON string>" }                            — compact wrapper
  //   3. { result: {...} } / { data: {...} } / { value: {...} }  — common wrapper keys
  //   4. The data directly (passthrough, unlikely but handled)
  // Returns { unwrapped, shape, raw } so callers can diagnose what was found.
  // ---------------------------------------------------------------------------
  function unwrap(raw) {
    if (raw == null) return { unwrapped: raw, shape: "null" };

    // Standard MCP content array: { content: [{ type: "text", text: "..." }] }
    if (raw && Array.isArray(raw.content)) {
      const text = raw.content.map((c) => c?.text ?? "").join("");
      if (text) {
        try { return { unwrapped: JSON.parse(text), shape: "content[].text(JSON)" }; }
        catch (_) { return { unwrapped: text, shape: "content[].text(string)" }; }
      }
    }

    // content as a plain string
    if (typeof raw.content === "string") {
      try { return { unwrapped: JSON.parse(raw.content), shape: "content(JSON-string)" }; }
      catch (_) { return { unwrapped: raw.content, shape: "content(string)" }; }
    }

    // Common wrapper keys
    for (const key of ["result", "data", "value", "output"]) {
      if (raw && Object.prototype.hasOwnProperty.call(raw, key) && raw[key] !== undefined) {
        const v = raw[key];
        if (typeof v === "string") {
          try { return { unwrapped: JSON.parse(v), shape: key + "(JSON-string)" }; }
          catch (_) { return { unwrapped: v, shape: key + "(string)" }; }
        }
        return { unwrapped: v, shape: key };
      }
    }

    return { unwrapped: raw, shape: "direct" };
  }

  // ---------------------------------------------------------------------------
  // Call a CORE MCP server tool via the Cowork bridge.
  // Applies unwrap() to extract the actual payload before returning.
  // ---------------------------------------------------------------------------
  async function callTool(toolName, args = {}) {
    if (typeof window.cowork === "undefined" || !window.cowork.callMcpTool) {
      console.warn("[CORE] window.cowork.callMcpTool not available — snapshot mode");
      return null;
    }
    try {
      // Empirically validated signature: (fullName, args) — 2 args, not 3.
      const fullName = "mcp__core__" + toolName;
      const raw = await window.cowork.callMcpTool(fullName, args);
      const { unwrapped } = unwrap(raw);
      return unwrapped;
    } catch (err) {
      console.warn(`[CORE] callTool error for ${toolName}:`, err);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Convenience wrappers — read tools
  // ---------------------------------------------------------------------------
  const tools = {
    listWorkspaces:           ()              => callTool("list_workspaces"),
    readDmProfile:            ()              => callTool("read_dm_profile"),
    readProjectMd:            (wsId)          => callTool("read_project_md",            { workspace_id: wsId || "" }),
    readPersuasionLog:        (wsId, dt)      => callTool("read_persuasion_log",         { workspace_id: wsId || "", session_date: dt || "" }),
    readSwarmTopology:        (wsId, dt)      => callTool("read_swarm_topology",         { workspace_id: wsId || "", session_date: dt || "" }),
    readConvergence:          (wsId, dt)      => callTool("read_convergence_trajectory", { workspace_id: wsId || "", session_date: dt || "" }),
    readVibeLog:              (limit)         => callTool("read_vibe_log",               { limit: limit || 10 }),

    // readWorkshopState — pass projectPath (absolute filesystem path) in Cowork sessions
    // to resolve the correct workspace instead of falling back to list_workspaces().most_recent.
    readWorkshopState:        (wsId, projectPath) => callTool("read_workshop_state", {
      workspace_id: wsId || "",
      ...(projectPath ? { project_path: projectPath } : {}),
    }),

    // readWorkspaceAtPath — read workspace.json pointer + PROJECT.md from any absolute path.
    // Essential in Cowork where the project is folder-scoped and may not be in the index.
    readWorkspaceAtPath:      (path)          => callTool("read_workspace_at_path",      { path }),

    // ---------------------------------------------------------------------------
    // Write tools — route ~/ .core/ writes through MCP when in Cowork
    // (Cowork's folder-scoped file tool cannot reach ~/.core/ directly)
    // ---------------------------------------------------------------------------
    registerWorkspace:        (wsId, name, path, lastActive, deliveryRisk) =>
      callTool("register_workspace", {
        workspace_id: wsId,
        name: name || wsId,
        path: path || "",
        ...(lastActive   ? { last_active:    lastActive   } : {}),
        ...(deliveryRisk ? { delivery_risk:  deliveryRisk } : {}),
      }),

    unregisterWorkspace:      (wsId)          => callTool("unregister_workspace",        { workspace_id: wsId }),

    updateWorkspaceLastActive:(wsId, ts)      => callTool("update_workspace_last_active",{
      workspace_id: wsId,
      ...(ts ? { timestamp: ts } : {}),
    }),

    writeWorkspaceManifest:   (wsId, manifest)=> callTool("write_workspace_manifest",    { workspace_id: wsId, manifest }),

    appendDmProfileEntry:     (section, entry)=> callTool("append_dm_profile_entry",     { section, entry }),

    updateDmProfileSection:   (section, content) => callTool("update_dm_profile_section",{ section, content }),

    appendVibeLog:            (date, label, vibe, asciiArt) =>
      callTool("append_vibe_log", {
        date,
        vibe,
        ...(label    ? { label    } : {}),
        ...(asciiArt ? { ascii_art: asciiArt } : {}),
      }),

    writeSwarmNarrative:      (wsId, content, append) =>
      callTool("write_swarm_narrative", {
        workspace_id: wsId,
        content,
        ...(append !== undefined ? { append } : {}),
      }),
  };

  // ---------------------------------------------------------------------------
  // Ask the DM a question from within the artifact.
  // Returns a Promise resolving to { text: string }.
  // Latency ~2s (empirically validated Q7 probe).
  // ---------------------------------------------------------------------------
  async function askClaude(prompt) {
    if (typeof window.cowork === "undefined" || !window.cowork.askClaude) {
      console.warn("[CORE] window.cowork.askClaude not available");
      return null;
    }
    try {
      return await window.cowork.askClaude(prompt);
    } catch (err) {
      console.warn("[CORE] askClaude error:", err);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Sanitize a string for safe DOM insertion via innerHTML.
  // (textContent is always safe; use this for innerHTML use cases only.)
  // ---------------------------------------------------------------------------
  function sanitize(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------------
  // Format an ISO 8601 / YYYY-MM-DD date as a human-readable relative string.
  // ---------------------------------------------------------------------------
  function relativeDate(isoStr) {
    if (!isoStr) return "unknown";
    try {
      const d = new Date(isoStr);
      const now = new Date();
      const diff = Math.floor((now - d) / (1000 * 60 * 60 * 24));
      if (diff === 0) return "today";
      if (diff === 1) return "yesterday";
      if (diff < 7) return `${diff} days ago`;
      if (diff < 30) return `${Math.floor(diff / 7)} weeks ago`;
      return `${Math.floor(diff / 30)} months ago`;
    } catch {
      return isoStr;
    }
  }

  return { tools, askClaude, sanitize, relativeDate, unwrap };
})();
