#!/usr/bin/env node
// CORE MCP server — zero-dependency Node.js implementation
// JSON-RPC 2.0 over stdio per the MCP spec (newline-delimited messages)
// 8 read-only tools. Reads from ~/.core/ and project folders. Never writes.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join, basename } from "node:path";
import readline from "node:readline";

const PROTOCOL_VERSION = "2024-11-05";
const SERVER_NAME = "core";
const SERVER_VERSION = "1.0.0";
const CORE_DATA_DIR = process.env.CORE_DATA_DIR || join(homedir(), ".core");

// --- JSON-RPC plumbing (stderr-only logging; stdout reserved for responses) ---

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}
function ok(id, result) {
  send({ jsonrpc: "2.0", id, result });
}
function rpcError(id, code, message, data) {
  const e = { code, message };
  if (data !== undefined) e.data = data;
  send({ jsonrpc: "2.0", id, error: e });
}
function log(...parts) {
  process.stderr.write("[core-mcp] " + parts.join(" ") + "\n");
}

// --- Helpers shared across tools ---

function readJSON(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch (e) {
    return { _parseError: e.message };
  }
}

function readText(path) {
  if (!existsSync(path)) return null;
  try {
    return readFileSync(path, "utf-8");
  } catch {
    return null;
  }
}

function resolveWorkspacePath(workspaceId) {
  const index = readJSON(join(CORE_DATA_DIR, "index.json"));
  if (!Array.isArray(index)) return null;
  if (workspaceId) {
    return index.find((w) => w?.workspace_id === workspaceId)?.path ?? null;
  }
  const sorted = [...index].sort((a, b) =>
    (b?.last_active ?? "").localeCompare(a?.last_active ?? "")
  );
  return sorted[0]?.path ?? null;
}

function extractSection(markdown, sectionName) {
  if (!markdown) return "";
  const escaped = sectionName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^## ${escaped}\\s*\\n([\\s\\S]*?)(?=^## |$)`, "m");
  const m = markdown.match(re);
  return m ? m[1].trim() : "";
}

function listSessionLogs(wsPath, sessionDate) {
  const sessionsDir = join(wsPath, "sessions");
  if (!existsSync(sessionsDir)) return [];
  let dateDirs;
  if (sessionDate) {
    dateDirs = [join(sessionsDir, sessionDate)];
  } else {
    dateDirs = readdirSync(sessionsDir, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => join(sessionsDir, d.name))
      .sort()
      .reverse();
  }
  const logs = [];
  for (const dir of dateDirs.slice(0, 3)) {
    if (!existsSync(dir)) continue;
    const dirLogs = readdirSync(dir).filter((f) => f.endsWith("-log.md"));
    logs.push(...dirLogs.map((f) => join(dir, f)));
    if (logs.length) break;
  }
  return logs;
}

// --- Tool implementations ---

function tool_list_workspaces() {
  const index = readJSON(join(CORE_DATA_DIR, "index.json"));
  if (!Array.isArray(index)) {
    return { workspaces: [], count: 0, note: "~/.core/index.json missing or invalid" };
  }
  const sorted = [...index].sort((a, b) =>
    (b?.last_active ?? "").localeCompare(a?.last_active ?? "")
  );
  return { workspaces: sorted, count: sorted.length, most_recent: sorted[0] ?? null };
}

function tool_read_dm_profile() {
  const path = join(CORE_DATA_DIR, "dm-profile.md");
  const content = readText(path);
  if (content === null) {
    return { exists: false, note: "~/.core/dm-profile.md not found — DM not yet initialized" };
  }
  const nameMatch = content.match(/\*\*Name:\*\*\s*(.+)/);
  return {
    exists: true,
    dm_name: nameMatch ? nameMatch[1].trim() : null,
    content,
    path,
  };
}

function tool_read_project_md(args) {
  const workspace_id = (args && args.workspace_id) || "";
  const wsPath = resolveWorkspacePath(workspace_id);
  if (!wsPath) return { found: false, note: "no workspace resolved" };
  const projectMd = join(wsPath, "PROJECT.md");
  const content = readText(projectMd);
  if (content === null) {
    return { found: false, workspace_path: wsPath, note: `PROJECT.md not found at ${projectMd}` };
  }
  return {
    found: true,
    workspace_path: wsPath,
    path: projectMd,
    content,
    sections: {
      state: extractSection(content, "State"),
      moves: extractSection(content, "Moves"),
      decisions_and_risks: extractSection(content, "Decisions & Risks"),
      people: extractSection(content, "People"),
      notes: extractSection(content, "Notes"),
    },
  };
}

function parsePersuasionEntries(text) {
  const entries = [];
  const m = text.match(/Persuasion Log[\s\S]*?\n([\s\S]*?)(?=^#|$)/im);
  if (!m) return entries;
  const section = m[1];
  const rowRe = /\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|/g;
  let row;
  while ((row = rowRe.exec(section)) !== null) {
    const cells = [row[1].trim(), row[2].trim(), row[3].trim(), row[4].trim()];
    if (cells[0].toLowerCase() === "agent" || cells[0].startsWith("---") || !cells[0]) continue;
    entries.push({ agent: cells[0], position_from: cells[1], position_to: cells[2], trigger: cells[3] });
  }
  return entries;
}

function tool_read_persuasion_log(args) {
  const wid = (args && args.workspace_id) || "";
  const date = (args && args.session_date) || "";
  const wsPath = resolveWorkspacePath(wid);
  if (!wsPath) return { found: false, note: "no workspace resolved" };
  const logs = listSessionLogs(wsPath, date);
  if (!logs.length) return { found: false, workspace_path: wsPath, note: "no session logs found" };
  const allEntries = [];
  const sources = [];
  for (const logPath of logs) {
    const content = readText(logPath);
    if (!content) continue;
    const entries = parsePersuasionEntries(content);
    if (entries.length) {
      allEntries.push(...entries);
      sources.push(basename(logPath));
    }
  }
  return {
    found: true,
    workspace_path: wsPath,
    session_date: date || "most recent",
    sources,
    entries: allEntries,
    count: allEntries.length,
    has_persuasion: allEntries.length > 0,
  };
}

function tool_read_swarm_topology(args) {
  const wid = (args && args.workspace_id) || "";
  const date = (args && args.session_date) || "";
  const wsPath = resolveWorkspacePath(wid);
  if (!wsPath) return { found: false, note: "no workspace resolved" };
  const logs = listSessionLogs(wsPath, date);
  if (!logs.length) return { found: false, workspace_path: wsPath, note: "no session logs found" };
  const agents = new Set();
  const phases = [];
  const sources = [];
  for (const logPath of logs) {
    const content = readText(logPath);
    if (!content) continue;
    sources.push(basename(logPath));
    for (const m of content.matchAll(/^#+\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*$/gm)) {
      const n = m[1].trim();
      if (n.length > 2 && !["Phase", "Summary", "Notes", "Output", "Findings"].includes(n)) {
        agents.add(n);
      }
    }
    for (const m of content.matchAll(/\*\*([A-Z][a-z]+):\*\*/g)) agents.add(m[1]);
    if (!phases.length) {
      for (const m of content.matchAll(/^#+\s+(Phase\s+\d+[^\n]*)$/gim)) {
        phases.push({ phase: m[1].trim() });
      }
    }
  }
  return {
    found: true,
    workspace_path: wsPath,
    session_date: date || "most recent",
    agents: [...agents].sort(),
    agent_count: agents.size,
    phases,
    phase_count: phases.length,
    sources,
  };
}

function parseConvergenceTable(text) {
  const rows = [];
  let inTable = false;
  for (const line of text.split("\n")) {
    const stripped = line.trim();
    if (/^\|\s*Finding\s*\|/i.test(stripped)) {
      inTable = true;
      continue;
    }
    if (!inTable) continue;
    if (/^\|\s*---/.test(stripped)) continue;
    if (!stripped.startsWith("|")) {
      inTable = false;
      continue;
    }
    const cells = stripped.replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
    if (cells.length >= 2 && cells[0]) {
      rows.push({
        finding: cells[0],
        agents: cells.length > 2 ? cells.slice(1, -1) : [],
        confidence: cells[cells.length - 1] ?? "",
      });
    }
  }
  return rows;
}

function tool_read_convergence_trajectory(args) {
  const wid = (args && args.workspace_id) || "";
  const date = (args && args.session_date) || "";
  const wsPath = resolveWorkspacePath(wid);
  if (!wsPath) return { found: false, note: "no workspace resolved" };
  const logs = listSessionLogs(wsPath, date);
  if (!logs.length) return { found: false, workspace_path: wsPath, note: "no session logs found" };
  const all = [];
  const sources = [];
  for (const logPath of logs) {
    const content = readText(logPath);
    if (!content) continue;
    const rows = parseConvergenceTable(content);
    if (rows.length) {
      all.push(...rows);
      sources.push(basename(logPath));
    }
  }
  const convergent = all.filter((r) => Array.isArray(r.agents) && r.agents.length >= 2);
  return {
    found: true,
    workspace_path: wsPath,
    session_date: date || "most recent",
    sources,
    findings: all,
    finding_count: all.length,
    convergent_findings: convergent.length,
    convergence_ratio: all.length ? Math.round((convergent.length / all.length) * 100) / 100 : 0,
  };
}

function parseVibeEntries(text) {
  const entries = [];
  const sections = text.split(/^(?=## \d{4}-\d{2}-\d{2})/m);
  for (const sec of sections) {
    const s = sec.trim();
    if (!s) continue;
    const header = s.match(/^## (\d{4}-\d{2}-\d{2})\s*[—-]?\s*(.*?)$/m);
    if (!header) continue;
    const body = s.slice(header.index + header[0].length).trim();
    const lines = body.split("\n");
    let vibe = "";
    const ascii = [];
    for (const ln of lines) {
      if (ln.trim() && !vibe) vibe = ln.trim();
      else if (vibe) ascii.push(ln);
    }
    entries.push({
      date: header[1],
      label: header[2].trim(),
      vibe,
      ascii_art: ascii.join("\n").trim(),
    });
  }
  return entries;
}

function tool_read_vibe_log(args) {
  const limit = (args && typeof args.limit === "number") ? args.limit : 10;
  const path = join(CORE_DATA_DIR, "vibes", "vibe-log.md");
  const content = readText(path);
  if (content === null) {
    return { found: false, note: "~/.core/vibes/vibe-log.md not found — no vibes captured yet", entries: [] };
  }
  const entries = parseVibeEntries(content);
  const sorted = [...entries].sort((a, b) => b.date.localeCompare(a.date));
  const truncated = sorted.slice(0, Math.min(limit, 50));
  return {
    found: true,
    path,
    total_entries: entries.length,
    returned: truncated.length,
    entries: truncated,
    most_recent_vibe: truncated[0]?.vibe ?? null,
  };
}

function countOpenRisks(content) {
  if (!content) return 0;
  const m = content.match(/^## Decisions & Risks[\s\S]*?\n([\s\S]*?)(?=^## |$)/m);
  if (!m) return 0;
  return m[1].split("\n").filter((ln) => ln.trim().startsWith("| R-") || ln.trim().startsWith("| DC-")).length;
}

function sessionAgeDays(workspaceId) {
  const index = readJSON(join(CORE_DATA_DIR, "index.json"));
  if (!Array.isArray(index)) return null;
  const ws = workspaceId ? index.find((w) => w.workspace_id === workspaceId) : index[0];
  const last = ws?.last_active;
  if (!last) return null;
  try {
    const d = new Date(last.replace("Z", "+00:00"));
    return Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function lastSwarmDate(wsPath) {
  const dir = join(wsPath, "sessions");
  if (!existsSync(dir)) return null;
  const entries = readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort()
    .reverse();
  for (const name of entries) {
    const subdir = join(dir, name);
    const files = readdirSync(subdir).filter((f) => f.endsWith("-log.md"));
    if (files.length) return name;
  }
  return null;
}

function tool_read_workshop_state(args) {
  const wid = (args && args.workspace_id) || "";
  const wsPath = resolveWorkspacePath(wid);
  const dm = tool_read_dm_profile();
  const vibe = tool_read_vibe_log({ limit: 1 });

  let projectName = null;
  let stateSummary = null;
  let activeRiskCount = 0;

  if (wsPath) {
    const projectMd = readText(join(wsPath, "PROJECT.md"));
    if (projectMd) {
      const whatMatch = projectMd.match(/^## What & Why\s*\n+(.+)/m);
      if (whatMatch) projectName = whatMatch[1].trim().replace(/^#+/, "").trim();
      const stateMatch = projectMd.match(/^## State\s*\n+[-*]\s*\*\*(.+?)\*\*/m);
      if (stateMatch) stateSummary = stateMatch[1].trim();
      activeRiskCount = countOpenRisks(projectMd);
    }
  }

  let workspaceCount = 0;
  const index = readJSON(join(CORE_DATA_DIR, "index.json"));
  if (Array.isArray(index)) workspaceCount = index.length;

  return {
    dm_name: dm.dm_name ?? null,
    project_name: projectName,
    project_state_summary: stateSummary,
    active_risk_count: activeRiskCount,
    session_age_days: sessionAgeDays(wid),
    last_swarm_date: wsPath ? lastSwarmDate(wsPath) : null,
    vibe_label: vibe.most_recent_vibe ?? null,
    workspace_count: workspaceCount,
    workspace_path: wsPath ?? null,
  };
}

// --- Tool registry ---

const TOOLS = {
  list_workspaces: {
    description: "List CORE workspaces from ~/.core/index.json with last-active timestamps.",
    inputSchema: { type: "object", properties: {}, required: [] },
    handler: tool_list_workspaces,
  },
  read_dm_profile: {
    description: "Read the DM's persistent profile from ~/.core/dm-profile.md.",
    inputSchema: { type: "object", properties: {}, required: [] },
    handler: tool_read_dm_profile,
  },
  read_project_md: {
    description: "Read PROJECT.md for the given workspace (or most-recently-active). Returns content + parsed section extracts.",
    inputSchema: {
      type: "object",
      properties: { workspace_id: { type: "string", description: "Optional workspace ID" } },
      required: [],
    },
    handler: tool_read_project_md,
  },
  read_persuasion_log: {
    description: "Parse persuasion log entries from recent swarm session logs.",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id: { type: "string" },
        session_date: { type: "string", description: "YYYY-MM-DD; defaults to most recent" },
      },
      required: [],
    },
    handler: tool_read_persuasion_log,
  },
  read_swarm_topology: {
    description: "Extract agent roster + phase timeline from session logs.",
    inputSchema: {
      type: "object",
      properties: { workspace_id: { type: "string" }, session_date: { type: "string" } },
      required: [],
    },
    handler: tool_read_swarm_topology,
  },
  read_convergence_trajectory: {
    description: "Extract convergence tracking table + ratio from session logs.",
    inputSchema: {
      type: "object",
      properties: { workspace_id: { type: "string" }, session_date: { type: "string" } },
      required: [],
    },
    handler: tool_read_convergence_trajectory,
  },
  read_vibe_log: {
    description: "Parse ~/.core/vibes/vibe-log.md into structured JSON entries.",
    inputSchema: {
      type: "object",
      properties: { limit: { type: "integer", description: "Max entries (default 10, max 50)" } },
      required: [],
    },
    handler: tool_read_vibe_log,
  },
  read_workshop_state: {
    description: "Aggregate state for the DM Workshop Live Artifact.",
    inputSchema: {
      type: "object",
      properties: { workspace_id: { type: "string" } },
      required: [],
    },
    handler: tool_read_workshop_state,
  },
};

// --- JSON-RPC dispatch ---

function handle(req) {
  if (!req || typeof req !== "object") return;
  const { id, method, params } = req;

  if (method === "initialize") {
    return ok(id, {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: { tools: {} },
      serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
    });
  }

  if (id === undefined || id === null) {
    return;
  }

  if (method === "ping") return ok(id, {});

  if (method === "tools/list") {
    return ok(id, {
      tools: Object.entries(TOOLS).map(([name, t]) => ({
        name,
        description: t.description,
        inputSchema: t.inputSchema,
      })),
    });
  }

  if (method === "tools/call") {
    const name = params?.name;
    const tool = TOOLS[name];
    if (!tool) return rpcError(id, -32602, `Unknown tool: ${name}`);
    try {
      const result = tool.handler(params?.arguments || {});
      return ok(id, {
        content: [{ type: "text", text: JSON.stringify(result) }],
      });
    } catch (e) {
      return rpcError(id, -32603, `Tool error: ${e.message}`, { tool: name });
    }
  }

  return rpcError(id, -32601, `Method not found: ${method}`);
}

// --- Main loop ---

log(`starting (proto=${PROTOCOL_VERSION}, name=${SERVER_NAME}, version=${SERVER_VERSION})`);

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
  if (!line.trim()) return;
  let req;
  try {
    req = JSON.parse(line);
  } catch (e) {
    return rpcError(null, -32700, `Parse error: ${e.message}`);
  }
  handle(req);
});
rl.on("close", () => {
  log("stdin closed; exiting");
  process.exit(0);
});
