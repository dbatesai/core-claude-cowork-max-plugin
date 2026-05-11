/**
 * CORE Cowork Max — Live Artifact helper library.
 * Wraps window.cowork.callMcpTool for CORE MCP server calls.
 * Loaded via <script src="shared/helpers.js"> in each Live Artifact.
 *
 * MCP server tool names: mcp__core__<toolname>
 * All tools are read-only; none modify state.
 */

const CoreHelpers = (() => {
  "use strict";

  /**
   * Call a CORE MCP server tool via the Cowork bridge.
   * Returns a Promise resolving to the tool's JSON result.
   */
  async function callTool(toolName, args = {}) {
    if (typeof window.cowork === "undefined" || !window.cowork.callMcpTool) {
      console.warn("[CORE] window.cowork.callMcpTool not available — snapshot mode");
      return null;
    }
    try {
      const result = await window.cowork.callMcpTool(
        "core",               // MCP server name (registered as "core" in claude_desktop_config.json)
        toolName,
        args
      );
      return result;
    } catch (err) {
      console.warn(`[CORE] callTool error for ${toolName}:`, err);
      return null;
    }
  }

  // Convenience wrappers for each registered tool
  const tools = {
    listWorkspaces:             () => callTool("list_workspaces"),
    readDmProfile:              () => callTool("read_dm_profile"),
    readProjectMd:          (wsId) => callTool("read_project_md", { workspace_id: wsId || "" }),
    readPersuasionLog:   (wsId, dt) => callTool("read_persuasion_log", { workspace_id: wsId || "", session_date: dt || "" }),
    readSwarmTopology:   (wsId, dt) => callTool("read_swarm_topology", { workspace_id: wsId || "", session_date: dt || "" }),
    readConvergence:     (wsId, dt) => callTool("read_convergence_trajectory", { workspace_id: wsId || "", session_date: dt || "" }),
    readVibeLog:           (limit) => callTool("read_vibe_log", { limit: limit || 10 }),
    readWorkshopState:      (wsId) => callTool("read_workshop_state", { workspace_id: wsId || "" }),
  };

  /**
   * Ask the DM a question from within the artifact.
   * Returns a Promise resolving to { text: string }.
   */
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

  /**
   * Sanitize a string for safe DOM insertion (textContent is safe by default;
   * this is for innerHTML use cases).
   */
  function sanitize(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  /**
   * Format a date string (ISO 8601 or YYYY-MM-DD) as a readable relative date.
   */
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

  return { tools, askClaude, sanitize, relativeDate };
})();
