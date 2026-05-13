#!/usr/bin/env node
// CORE MCP server — zero-dependency Node.js implementation
// JSON-RPC 2.0 over stdio per the MCP spec (newline-delimited messages)
// 8 read-only tools + 9 write tools + read_workspace_at_path.
// Reads from ~/.core/ and project folders. Writes are restricted to CORE_DATA_DIR.

import { existsSync, readFileSync, readdirSync, writeFileSync, mkdirSync, appendFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, basename, resolve, dirname } from "node:path";
import readline from "node:readline";

const PROTOCOL_VERSION = "2024-11-05";
const SERVER_NAME = "core";
const SERVER_VERSION = "1.1.3";
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
  // §? handles the CORE PROJECT.md convention "## §State" alongside plain "## State".
  // No `m` flag: `\n## ` and `$` give true end-of-section markers — `m`-mode `$` matched
  // every newline and truncated section content to the first line.
  const re = new RegExp(`(?:^|\\n)## §?\\s*${escaped}\\s*\\n([\\s\\S]*?)(?=\\n## |$)`);
  const m = markdown.match(re);
  return m ? m[1].trim() : "";
}

// --- Write helpers ---

function ensureDir(dirPath) {
  if (!existsSync(dirPath)) mkdirSync(dirPath, { recursive: true });
}

function safeWritePath(targetPath) {
  const resolved = resolve(targetPath);
  const coreDir = resolve(CORE_DATA_DIR);
  if (resolved !== coreDir && !resolved.startsWith(coreDir + "/")) {
    throw new Error(`Write blocked: '${resolved}' is outside CORE_DATA_DIR '${coreDir}'`);
  }
  return resolved;
}

function auditLog(operation, targetPath, detail) {
  const ts = new Date().toISOString();
  const entry = `- ${ts} | ${operation} | ${targetPath}${detail ? " | " + detail : ""}\n`;
  try {
    const logPath = join(CORE_DATA_DIR, "mcp-write-log.md");
    appendFileSync(logPath, entry, "utf-8");
  } catch (e) {
    log(`audit-log write failed: ${e.message}`);
  }
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
  // F8 fix: trust file order. append_vibe_log prepends new entries, so entries[0]
  // is always the most recently written vibe. Date-string sort produced stale
  // most_recent_vibe on same-date ties (parseVibeEntries returns file-order, and
  // a stable date-sort preserved oldest-first among ties — surfacing the wrong entry).
  const entries = parseVibeEntries(content);
  const truncated = entries.slice(0, Math.min(limit, 50));
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
  const m = content.match(/(?:^|\n)## §?\s*Decisions & Risks\s*\n([\s\S]*?)(?=\n## |$)/);
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

function tool_read_dashboard_state(args) {
  const wid = (args && args.workspace_id) || "";
  const projectPath = (args && args.project_path) || null;

  // If a project_path is provided, resolve the workspace from the filesystem directly.
  // This is required in Cowork where the session is folder-scoped and the workspace
  // may not yet be registered in index.json (F1 root cause).
  let wsPath;
  let resolvedWid = wid;
  let pointer = null;
  if (projectPath) {
    const resolved = resolve(projectPath);
    if (existsSync(resolved)) {
      wsPath = resolved;
      pointer = readJSON(join(resolved, "workspace.json"));
      if (pointer && pointer.workspace_id) resolvedWid = pointer.workspace_id;
    }
  }
  if (!wsPath) wsPath = resolveWorkspacePath(resolvedWid);
  if (!pointer && wsPath) pointer = readJSON(join(wsPath, "workspace.json"));

  const dm = tool_read_dm_profile();
  const vibe = tool_read_vibe_log({ limit: 1 });

  let projectName = null;
  let stateSummary = null;
  let activeRiskCount = 0;

  if (wsPath) {
    const projectMd = readText(join(wsPath, "PROJECT.md"));
    if (projectMd) {
      // F6b fix: project_name resolves from workspace pointer's `name` (index-
      // attested) first, then PROJECT.md H1 title. Previous behavior grabbed the
      // first prose line after `## §What & Why`, which returned description text
      // rather than the project's name.
      if (pointer && pointer.name) {
        projectName = pointer.name;
      } else {
        const h1Match = projectMd.match(/^# (.+)$/m);
        if (h1Match) projectName = h1Match[1].trim();
      }

      // F6b fix: project_state_summary uses extractSection (§-aware) and takes
      // the first non-empty bullet's leading content. Previous regex required
      // `- **bold**` first bullet which is the CORE PROJECT.md convention but
      // returned null on §-prefixed PROJECT.md files without that exact format.
      // Backwards-compatible: if the first bullet IS `**bold**`-led (CORE
      // convention), still extract the bold content as the summary.
      const stateContent = extractSection(projectMd, "State");
      if (stateContent) {
        const lines = stateContent.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
        const firstBullet = lines.find((l) => l.startsWith("-") || l.startsWith("*")) || lines[0];
        if (firstBullet) {
          const cleaned = firstBullet.replace(/^[-*]\s+/, "");
          const boldMatch = cleaned.match(/^\*\*(.+?)\*\*/);
          if (boldMatch) {
            stateSummary = boldMatch[1].trim();
          } else {
            const sentEnd = cleaned.search(/[.!?](?=\s|$)/);
            stateSummary = (sentEnd > 0 ? cleaned.slice(0, sentEnd) : cleaned.slice(0, 120)).trim();
          }
        }
      }

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
    session_age_days: sessionAgeDays(resolvedWid),
    last_swarm_date: wsPath ? lastSwarmDate(wsPath) : null,
    vibe_label: vibe.most_recent_vibe ?? null,
    workspace_count: workspaceCount,
    workspace_path: wsPath ?? null,
  };
}

// --- Write tool implementations ---

function tool_register_workspace(args) {
  const { workspace_id, name, path: wsPath, last_active, delivery_risk } = args || {};
  if (!workspace_id) return { success: false, error: "workspace_id required" };
  const indexPath = safeWritePath(join(CORE_DATA_DIR, "index.json"));
  let index = [];
  if (existsSync(indexPath)) {
    try { index = JSON.parse(readFileSync(indexPath, "utf-8")); } catch (_) {}
  }
  if (!Array.isArray(index)) index = [];
  const existing = index.findIndex((w) => w?.workspace_id === workspace_id);
  const entry = {
    workspace_id,
    name: name || workspace_id,
    path: wsPath || "",
    last_active: last_active || new Date().toISOString(),
    ...(delivery_risk ? { delivery_risk } : {}),
  };
  if (existing >= 0) {
    index[existing] = { ...index[existing], ...entry };
    auditLog("register_workspace(update)", indexPath, workspace_id);
  } else {
    index.push(entry);
    auditLog("register_workspace(create)", indexPath, workspace_id);
  }
  writeFileSync(indexPath, JSON.stringify(index, null, 4), "utf-8");
  return { success: true, workspace_id, created: existing < 0, path: indexPath };
}

function tool_unregister_workspace(args) {
  const { workspace_id } = args || {};
  if (!workspace_id) return { success: false, error: "workspace_id required" };
  const indexPath = safeWritePath(join(CORE_DATA_DIR, "index.json"));
  if (!existsSync(indexPath)) return { success: false, error: "index.json not found" };
  let index;
  try { index = JSON.parse(readFileSync(indexPath, "utf-8")); } catch (e) {
    return { success: false, error: "index.json parse error: " + e.message };
  }
  if (!Array.isArray(index)) return { success: false, error: "index.json is not an array" };
  const before = index.length;
  index = index.filter((w) => w?.workspace_id !== workspace_id);
  if (index.length === before) return { success: false, error: `workspace_id '${workspace_id}' not found` };
  writeFileSync(indexPath, JSON.stringify(index, null, 4), "utf-8");
  auditLog("unregister_workspace", indexPath, workspace_id);
  return { success: true, workspace_id, removed: true, remaining: index.length };
}

function tool_update_workspace_last_active(args) {
  const { workspace_id, timestamp } = args || {};
  if (!workspace_id) return { success: false, error: "workspace_id required" };
  const indexPath = safeWritePath(join(CORE_DATA_DIR, "index.json"));
  if (!existsSync(indexPath)) return { success: false, error: "index.json not found" };
  let index;
  try { index = JSON.parse(readFileSync(indexPath, "utf-8")); } catch (e) {
    return { success: false, error: "index.json parse error: " + e.message };
  }
  if (!Array.isArray(index)) return { success: false, error: "index.json is not an array" };
  const ws = index.find((w) => w?.workspace_id === workspace_id);
  if (!ws) return { success: false, error: `workspace_id '${workspace_id}' not found` };
  const ts = timestamp || new Date().toISOString();
  ws.last_active = ts;
  writeFileSync(indexPath, JSON.stringify(index, null, 4), "utf-8");
  auditLog("update_workspace_last_active", indexPath, `${workspace_id} → ${ts}`);
  return { success: true, workspace_id, last_active: ts };
}

function tool_write_workspace_manifest(args) {
  const { workspace_id, manifest } = args || {};
  if (!workspace_id || !manifest || typeof manifest !== "object") {
    return { success: false, error: "workspace_id and manifest object required" };
  }
  const wsDir = safeWritePath(join(CORE_DATA_DIR, "workspaces", workspace_id));
  ensureDir(wsDir);
  const manifestPath = join(wsDir, "workspace.json");
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf-8");
  auditLog("write_workspace_manifest", manifestPath, workspace_id);
  return { success: true, workspace_id, path: manifestPath };
}

const VALID_SWARM_STATUSES = new Set(["idle", "running", "halted", "complete"]);

function tool_update_swarm_status(args) {
  const {
    workspace_id, status, phase, agent_count,
    agent_names, agent_roles, task_summary, swarm_artifact_id
  } = args || {};

  if (!workspace_id) return { success: false, error: "workspace_id required" };
  if (status !== undefined && !VALID_SWARM_STATUSES.has(status)) {
    return { success: false, error: `invalid status "${status}"; must be idle|running|halted|complete` };
  }

  const wsDir = safeWritePath(join(CORE_DATA_DIR, "workspaces", workspace_id));
  ensureDir(wsDir);
  const manifestPath = join(wsDir, "workspace.json");

  let manifest = {};
  if (existsSync(manifestPath)) {
    try {
      manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
    } catch (e) {
      return {
        success: false,
        error: `manifest parse error at ${manifestPath}: ${e.message}`,
      };
    }
  }

  const now = new Date().toISOString();
  const prev = manifest.current_swarm || {};
  const swarm = { ...prev };

  if (status       !== undefined) swarm.status       = status;
  if (phase        !== undefined) swarm.phase        = phase;
  if (agent_count  !== undefined) swarm.agent_count  = agent_count;
  if (agent_names  !== undefined) swarm.agent_names  = agent_names;
  if (agent_roles  !== undefined) swarm.agent_roles  = agent_roles;
  if (task_summary !== undefined) swarm.task_summary = task_summary;
  swarm.updated_at = now;

  // Detect fresh swarm start: status transitioning to "running" from a terminal
  // state (complete/idle) or from no prior swarm. Reset lifecycle timestamps so
  // the new run is not contaminated by the previous run's timeline.
  const isFreshStart =
    status === "running" &&
    (prev.status === undefined || prev.status === "complete" || prev.status === "idle");
  if (isFreshStart) {
    swarm.started_at   = now;
    swarm.completed_at = null;
  }

  // started_at: set on first running write only (mid-lifetime guard; fresh-start
  // branch above handles the cross-run case).
  if (status === "running" && !swarm.started_at) swarm.started_at = now;

  // completed_at: set when reaching terminal states; ensure key exists otherwise.
  if (status === "complete" || status === "idle") swarm.completed_at = now;
  else if (swarm.completed_at === undefined) swarm.completed_at = null;

  manifest.current_swarm = swarm;
  if (swarm_artifact_id !== undefined) manifest.swarm_artifact_id = swarm_artifact_id;

  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf-8");
  auditLog("update_swarm_status", manifestPath, `${workspace_id} → ${status ?? "patch"}`);
  return { success: true, workspace_id, status: swarm.status };
}

function tool_append_dm_profile_entry(args) {
  const { section, entry } = args || {};
  if (!section || !entry) return { success: false, error: "section and entry required" };
  const profilePath = safeWritePath(join(CORE_DATA_DIR, "dm-profile.md"));
  let text = existsSync(profilePath) ? (readText(profilePath) || "") : "";
  const escaped = section.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const sectionRe = new RegExp(`(^## ${escaped}[\\s\\S]*?)(?=^## |$)`, "m");
  const entryLine = `- ${entry.trim()}`;
  if (sectionRe.test(text)) {
    text = text.replace(sectionRe, (match) => match.trimEnd() + "\n" + entryLine + "\n\n");
  } else {
    text = text.trimEnd() + `\n\n## ${section}\n\n${entryLine}\n`;
  }
  writeFileSync(profilePath, text, "utf-8");
  auditLog("append_dm_profile_entry", profilePath, section);
  return { success: true, section, entry: entryLine, path: profilePath };
}

function tool_update_dm_profile_section(args) {
  const { section, content } = args || {};
  if (!section || content === undefined) return { success: false, error: "section and content required" };
  const profilePath = safeWritePath(join(CORE_DATA_DIR, "dm-profile.md"));
  let text = existsSync(profilePath) ? (readText(profilePath) || "") : "";
  const escaped = section.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const sectionRe = new RegExp(`(^## ${escaped}\\s*\\n)([\\s\\S]*?)(?=^## |$)`, "m");
  if (sectionRe.test(text)) {
    text = text.replace(sectionRe, `$1${content.trim()}\n\n`);
  } else {
    text = text.trimEnd() + `\n\n## ${section}\n\n${content.trim()}\n`;
  }
  writeFileSync(profilePath, text, "utf-8");
  auditLog("update_dm_profile_section", profilePath, section);
  return { success: true, section, path: profilePath };
}

function tool_append_vibe_log(args) {
  const { date, label, vibe, ascii_art } = args || {};
  if (!date || !vibe) return { success: false, error: "date and vibe required" };
  const vibesDir = safeWritePath(join(CORE_DATA_DIR, "vibes"));
  ensureDir(vibesDir);
  const logPath = join(vibesDir, "vibe-log.md");
  const header = `## ${date}${label ? " — " + label : ""}`;
  const block = `${header}\n${vibe}${ascii_art ? "\n" + ascii_art : ""}\n\n`;
  // F8 fix: prepend to the top of the file (newest-first convention) so
  // read_vibe_log.most_recent_vibe is always the entry that was just written,
  // regardless of date-string ties or backfill inserts. File order IS recency.
  const existing = readText(logPath) ?? "";
  writeFileSync(logPath, block + existing.replace(/^\s+/, ""), "utf-8");
  auditLog("append_vibe_log", logPath, `${date}: ${vibe.slice(0, 60)}`);
  return { success: true, date, path: logPath };
}

function tool_write_swarm_narrative(args) {
  const { workspace_id, content, append: doAppend } = args || {};
  if (!workspace_id || content === undefined) {
    return { success: false, error: "workspace_id and content required" };
  }
  const wsDir = safeWritePath(join(CORE_DATA_DIR, "workspaces", workspace_id));
  ensureDir(wsDir);
  const narrativePath = join(wsDir, "swarm-narrative.md");
  if (doAppend && existsSync(narrativePath)) {
    appendFileSync(narrativePath, "\n" + content, "utf-8");
  } else {
    writeFileSync(narrativePath, content, "utf-8");
  }
  auditLog("write_swarm_narrative", narrativePath, workspace_id);
  return { success: true, workspace_id, path: narrativePath, appended: !!(doAppend) };
}

// --- Read tool: workspace at arbitrary path (read-only, no CORE_DATA_DIR restriction) ---

function tool_read_workspace_at_path(args) {
  const { path: targetPath } = args || {};
  if (!targetPath) return { found: false, error: "path required" };
  const resolvedPath = resolve(targetPath);
  if (!existsSync(resolvedPath)) {
    return { found: false, error: `path not found: ${resolvedPath}` };
  }
  const pointer = readJSON(join(resolvedPath, "workspace.json"));
  const projectMd = readText(join(resolvedPath, "PROJECT.md"));
  return {
    found: !!(pointer || projectMd),
    path: resolvedPath,
    workspace_pointer: pointer,
    workspace_id: pointer?.workspace_id ?? null,
    project_md_content: projectMd,
    sections: projectMd ? {
      state: extractSection(projectMd, "State"),
      moves: extractSection(projectMd, "Moves"),
      decisions_and_risks: extractSection(projectMd, "Decisions & Risks"),
      people: extractSection(projectMd, "People"),
      notes: extractSection(projectMd, "Notes"),
    } : null,
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
  read_dashboard_state: {
    description: "Aggregate state for the CORE Dashboard Live Artifact. Pass project_path (absolute path to the Cowork project folder) to resolve the correct workspace in Cowork sessions.",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id: { type: "string" },
        project_path: { type: "string", description: "Absolute path to project folder (Cowork: use instead of workspace_id)" },
      },
      required: [],
    },
    handler: tool_read_dashboard_state,
  },
  register_workspace: {
    description: "Add or update a workspace entry in ~/.core/index.json. Safe to call repeatedly (upsert).",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id: { type: "string", description: "Unique workspace identifier" },
        name: { type: "string", description: "Human-readable workspace name" },
        path: { type: "string", description: "Absolute path to the project folder" },
        last_active: { type: "string", description: "ISO 8601 timestamp (defaults to now if omitted)" },
        delivery_risk: { type: "string", description: "Risk level: low | medium | high" },
      },
      required: ["workspace_id"],
    },
    handler: tool_register_workspace,
  },
  unregister_workspace: {
    description: "Remove a workspace entry from ~/.core/index.json.",
    inputSchema: {
      type: "object",
      properties: { workspace_id: { type: "string" } },
      required: ["workspace_id"],
    },
    handler: tool_unregister_workspace,
  },
  update_workspace_last_active: {
    description: "Update the last_active timestamp for a workspace in ~/.core/index.json.",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id: { type: "string" },
        timestamp: { type: "string", description: "ISO 8601 timestamp (defaults to now if omitted)" },
      },
      required: ["workspace_id"],
    },
    handler: tool_update_workspace_last_active,
  },
  write_workspace_manifest: {
    description: "Write or replace the workspace manifest at ~/.core/workspaces/<id>/workspace.json. Creates the directory if needed.",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id: { type: "string" },
        manifest: { type: "object", description: "Full manifest object (see schemas/workspace.md)" },
      },
      required: ["workspace_id", "manifest"],
    },
    handler: tool_write_workspace_manifest,
  },
  update_swarm_status: {
    description: "Patch current_swarm in a workspace manifest. Call at swarm spawn (running), phase transitions, user-block (halted), and close (complete/idle). Patch-safe: only provided keys are merged into the existing current_swarm object. swarm_artifact_id is stored at manifest top-level, not inside current_swarm.",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id:      { type: "string", description: "Workspace ID matching ~/.core/index.json entry" },
        status:            { type: "string", enum: ["idle","running","halted","complete"] },
        phase:             { type: "string", description: "Current phase label e.g. 'Phase 2: Critic Analysis'" },
        agent_count:       { type: "number" },
        agent_names:       { type: "array",  items: { type: "string" } },
        agent_roles:       { type: "object", description: "Map of agent name → role (generator/critic/monitor/guard)" },
        task_summary:      { type: "string", description: "One-line task description for Observatory display" },
        swarm_artifact_id: { type: "string", description: "Cowork artifact ID for Swarm Live View — persisted at manifest top level" }
      },
      required: ["workspace_id"],
    },
    handler: tool_update_swarm_status,
  },
  append_dm_profile_entry: {
    description: "Append a bullet-point entry to a named section in ~/.core/dm-profile.md.",
    inputSchema: {
      type: "object",
      properties: {
        section: { type: "string", description: "Section heading without ## (e.g. 'Evolution Log')" },
        entry: { type: "string", description: "Entry text without leading '- '" },
      },
      required: ["section", "entry"],
    },
    handler: tool_append_dm_profile_entry,
  },
  update_dm_profile_section: {
    description: "Replace the full content of a named section in ~/.core/dm-profile.md.",
    inputSchema: {
      type: "object",
      properties: {
        section: { type: "string", description: "Section heading without ## (e.g. 'Cross-Project Learnings')" },
        content: { type: "string", description: "New section content (markdown, without the ## heading line)" },
      },
      required: ["section", "content"],
    },
    handler: tool_update_dm_profile_section,
  },
  append_vibe_log: {
    description: "Append a vibe entry to ~/.core/vibes/vibe-log.md. Creates the file and directory if needed.",
    inputSchema: {
      type: "object",
      properties: {
        date: { type: "string", description: "YYYY-MM-DD" },
        label: { type: "string", description: "Short session label (e.g. 'iteration-2 build')" },
        vibe: { type: "string", description: "One-line vibe description" },
        ascii_art: { type: "string", description: "Optional ASCII art block" },
      },
      required: ["date", "vibe"],
    },
    handler: tool_append_vibe_log,
  },
  write_swarm_narrative: {
    description: "Write or append to ~/.core/workspaces/<id>/swarm-narrative.md. Creates the workspace directory if needed.",
    inputSchema: {
      type: "object",
      properties: {
        workspace_id: { type: "string" },
        content: { type: "string", description: "Narrative content (markdown)" },
        append: { type: "boolean", description: "If true, append to existing file; otherwise overwrite (default: false)" },
      },
      required: ["workspace_id", "content"],
    },
    handler: tool_write_swarm_narrative,
  },
  read_workspace_at_path: {
    description: "Read workspace.json pointer and PROJECT.md from an absolute project folder path, independent of the index. Essential for Cowork where the project root is folder-scoped.",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string", description: "Absolute filesystem path to the project folder" },
      },
      required: ["path"],
    },
    handler: tool_read_workspace_at_path,
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
