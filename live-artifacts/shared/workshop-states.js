/**
 * CORE Cowork Max — DM Workshop state → visual mapping.
 * Maps three state axes to visual states for the workshop illustration.
 *
 * Axes:
 *   session_age_days  → lamp brightness (0=bright, 14+=dim)
 *   swarm_activity    → hearth burn state (0=cold, 3+=roaring)
 *   project_state     → sky/window frame (planning/active/blocked/complete)
 */

const WorkshopStates = (() => {
  "use strict";

  // Lamp brightness: session age in days → frame index (0=brightest, 4=dimmest)
  function lampFrame(sessionAgeDays) {
    if (sessionAgeDays === null || sessionAgeDays === undefined) return 2;
    if (sessionAgeDays <= 0) return 0;
    if (sessionAgeDays <= 1) return 1;
    if (sessionAgeDays <= 3) return 2;
    if (sessionAgeDays <= 7) return 3;
    return 4;
  }

  // Hearth burn: number of swarm agents active recently → frame index (0=cold, 4=roaring)
  function hearthFrame(agentCount) {
    if (!agentCount) return 0;
    if (agentCount <= 1) return 1;
    if (agentCount <= 3) return 2;
    if (agentCount <= 5) return 3;
    return 4;
  }

  // Sky/window: project state string → frame key
  function skyFrame(projectStateStr) {
    if (!projectStateStr) return "neutral";
    const s = projectStateStr.toLowerCase();
    if (s.includes("complete") || s.includes("done") || s.includes("shipped")) return "dawn";
    if (s.includes("block") || s.includes("risk") || s.includes("stall")) return "storm";
    if (s.includes("active") || s.includes("sprint") || s.includes("progress")) return "clear";
    if (s.includes("plan") || s.includes("start") || s.includes("init")) return "morning";
    return "neutral";
  }

  // Map a full workshop_state MCP result to CSS class names for the SVG overlays
  function resolveClasses(workshopState) {
    if (!workshopState) return { lamp: "lamp-2", hearth: "hearth-0", sky: "sky-neutral" };
    return {
      lamp:   `lamp-${lampFrame(workshopState.session_age_days)}`,
      hearth: `hearth-${hearthFrame(workshopState.agent_count || 0)}`,
      sky:    `sky-${skyFrame(workshopState.project_state_summary)}`,
    };
  }

  // DM name display (emergent — read from MCP, never hardcoded)
  function dmDisplayName(workshopState) {
    return (workshopState && workshopState.dm_name) || "Your DM";
  }

  return { resolveClasses, dmDisplayName, lampFrame, hearthFrame, skyFrame };
})();
