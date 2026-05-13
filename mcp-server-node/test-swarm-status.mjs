#!/usr/bin/env node
// Unit tests for update_swarm_status (v1.2.x Observatory feature).
// Run: node mcp-server-node/test-swarm-status.mjs

import { mkdtempSync, rmSync, mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SERVER = join(__dirname, "server.mjs");

function rpc(child, id, method, params = {}) {
  return new Promise((resolve, reject) => {
    let buffer = "";
    const onData = (chunk) => {
      buffer += chunk.toString();
      const nl = buffer.indexOf("\n");
      if (nl === -1) return;
      child.stdout.off("data", onData);
      try { resolve(JSON.parse(buffer.slice(0, nl))); }
      catch (e) { reject(e); }
    };
    child.stdout.on("data", onData);
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
}

async function callTool(child, id, name, args) {
  const resp = await rpc(child, id, "tools/call", { name, arguments: args });
  if (resp.error) throw new Error(`RPC error: ${resp.error.message}`);
  const text = resp.result?.content?.[0]?.text;
  return text ? JSON.parse(text) : null;
}

function makeWorkspace(rootDir, wsId, manifest = {}) {
  const wsDir = join(rootDir, "workspaces", wsId);
  mkdirSync(wsDir, { recursive: true });
  writeFileSync(join(wsDir, "workspace.json"), JSON.stringify(manifest, null, 2));
}

function readManifest(rootDir, wsId) {
  return JSON.parse(readFileSync(join(rootDir, "workspaces", wsId, "workspace.json"), "utf-8"));
}

async function run() {
  let pass = 0, fail = 0;
  function ok(label, cond) {
    if (cond) { console.log(`  ✓ ${label}`); pass++; }
    else       { console.error(`  ✗ ${label}`); fail++; }
  }

  const tmpDir = mkdtempSync(join(tmpdir(), "core-swarm-status-test-"));
  const env = { ...process.env, CORE_DATA_DIR: tmpDir };
  const child = spawn(process.execPath, [SERVER], { env, stdio: ["pipe","pipe","inherit"] });
  child.stdin.setEncoding("utf-8");
  let id = 1;
  await rpc(child, id++, "initialize", {
    protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "test" }
  });

  // T1: basic running write
  makeWorkspace(tmpDir, "ws1", { workspace_id: "ws1", project_path: "/foo", last_active: "2026-01-01T00:00:00Z" });
  const r1 = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws1", status: "running",
    phase: "Phase 1: Independent Analysis", agent_count: 5,
    agent_names: ["Vellum","Fold","Spar","Reed","Vex"],
    agent_roles: { Vellum:"generator",Fold:"generator",Spar:"critic",Reed:"critic",Vex:"monitor" },
    task_summary: "F9 review"
  });
  ok("T1: success=true", r1?.success === true);
  const m1 = readManifest(tmpDir, "ws1");
  ok("T1: status=running",         m1.current_swarm?.status === "running");
  ok("T1: phase set",              m1.current_swarm?.phase === "Phase 1: Independent Analysis");
  ok("T1: agent_count=5",          m1.current_swarm?.agent_count === 5);
  ok("T1: project_path preserved", m1.project_path === "/foo");
  ok("T1: last_active preserved",  m1.last_active === "2026-01-01T00:00:00Z");
  ok("T1: started_at set",         typeof m1.current_swarm?.started_at === "string");

  // T2: patch — only phase changes; agent_names/task_summary survive
  const r2 = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws1", status: "running", phase: "Phase 2: Critic Analysis"
  });
  ok("T2: success=true", r2?.success === true);
  const m2 = readManifest(tmpDir, "ws1");
  ok("T2: phase updated",               m2.current_swarm?.phase === "Phase 2: Critic Analysis");
  ok("T2: agent_names survive patch",   Array.isArray(m2.current_swarm?.agent_names) && m2.current_swarm.agent_names.length === 5);
  ok("T2: task_summary survives patch", m2.current_swarm?.task_summary === "F9 review");

  // T3: halted
  const r3 = await callTool(child, id++, "update_swarm_status", { workspace_id: "ws1", status: "halted" });
  ok("T3: success=true",  r3?.success === true);
  ok("T3: status=halted", readManifest(tmpDir, "ws1").current_swarm?.status === "halted");

  // T4: complete — completed_at set
  const r4 = await callTool(child, id++, "update_swarm_status", { workspace_id: "ws1", status: "complete" });
  ok("T4: success=true",        r4?.success === true);
  const m4 = readManifest(tmpDir, "ws1");
  ok("T4: status=complete",     m4.current_swarm?.status === "complete");
  ok("T4: completed_at set",    typeof m4.current_swarm?.completed_at === "string");

  // ── T-RESET: lifecycle timestamps reset on fresh swarm start ─────
  // Workspace ws1 is currently status=complete from T4 with completed_at set.
  // Starting a NEW swarm with status=running should reset both lifecycle fields.
  const m_pre_reset = readManifest(tmpDir, "ws1");
  const oldStartedAt = m_pre_reset.current_swarm?.started_at;
  const oldCompletedAt = m_pre_reset.current_swarm?.completed_at;
  ok("T-RESET pre: completed_at was set (T4 effect)", typeof oldCompletedAt === "string");

  // Sleep 5ms to guarantee a different timestamp than the prior write.
  await new Promise(r => setTimeout(r, 5));

  const rReset = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws1", status: "running", phase: "New Run Phase 1"
  });
  ok("T-RESET: success=true", rReset?.success === true);
  const m_post_reset = readManifest(tmpDir, "ws1");
  ok("T-RESET: completed_at cleared on fresh start", m_post_reset.current_swarm?.completed_at === null);
  ok("T-RESET: started_at reset to a new timestamp", m_post_reset.current_swarm?.started_at !== oldStartedAt);
  ok("T-RESET: started_at is a string", typeof m_post_reset.current_swarm?.started_at === "string");

  // ── T-NOSTATUS: patch with no status arg leaves status + lifecycle untouched ─
  // ws1 is currently status=running from T-RESET.
  const m_pre_nostatus = readManifest(tmpDir, "ws1");
  const expectedStartedAt = m_pre_nostatus.current_swarm?.started_at;

  await new Promise(r => setTimeout(r, 5));

  const rNoStatus = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws1", phase: "Phase 3: Synthesis"
  });
  ok("T-NOSTATUS: success=true", rNoStatus?.success === true);
  const m_post_nostatus = readManifest(tmpDir, "ws1");
  ok("T-NOSTATUS: phase updated", m_post_nostatus.current_swarm?.phase === "Phase 3: Synthesis");
  ok("T-NOSTATUS: status unchanged",    m_post_nostatus.current_swarm?.status === "running");
  ok("T-NOSTATUS: started_at unchanged", m_post_nostatus.current_swarm?.started_at === expectedStartedAt);
  ok("T-NOSTATUS: completed_at still null", m_post_nostatus.current_swarm?.completed_at === null);
  ok("T-NOSTATUS: updated_at refreshed", m_post_nostatus.current_swarm?.updated_at !== m_pre_nostatus.current_swarm?.updated_at);

  // ── T-STARTED-IDEMPOTENT: second running call within a single swarm does NOT update started_at ─
  const m_pre_idem = readManifest(tmpDir, "ws1");
  const startedAtBefore = m_pre_idem.current_swarm?.started_at;

  await new Promise(r => setTimeout(r, 5));

  const rIdem = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws1", status: "running", phase: "Phase 4"
  });
  ok("T-STARTED-IDEMPOTENT: success=true", rIdem?.success === true);
  const m_post_idem = readManifest(tmpDir, "ws1");
  ok("T-STARTED-IDEMPOTENT: started_at preserved across running→running", m_post_idem.current_swarm?.started_at === startedAtBefore);

  // T5: swarm_artifact_id at manifest top-level
  const r5 = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws1", status: "running", swarm_artifact_id: "cowork-artifact-abc123"
  });
  ok("T5: success=true",               r5?.success === true);
  ok("T5: swarm_artifact_id at root",  readManifest(tmpDir, "ws1").swarm_artifact_id === "cowork-artifact-abc123");
  ok("T5: swarm_artifact_id NOT duplicated inside current_swarm",
     readManifest(tmpDir, "ws1").current_swarm?.swarm_artifact_id === undefined);

  // T6: missing workspace_id → error
  const r6 = await callTool(child, id++, "update_swarm_status", { status: "running" });
  ok("T6: missing workspace_id → success=false", r6?.success === false);

  // T7: invalid status → error
  const r7 = await callTool(child, id++, "update_swarm_status", { workspace_id: "ws1", status: "banana" });
  ok("T7: invalid status → success=false", r7?.success === false);

  // T8: new workspace created from scratch if manifest absent
  const r8 = await callTool(child, id++, "update_swarm_status", {
    workspace_id: "ws-new", status: "running", phase: "Phase 0", task_summary: "new ws"
  });
  ok("T8: success=true for new ws",  r8?.success === true);
  ok("T8: manifest file created",    existsSync(join(tmpDir, "workspaces", "ws-new", "workspace.json")));
  ok("T8: status written to new ws", readManifest(tmpDir, "ws-new").current_swarm?.status === "running");

  child.stdin.end();
  rmSync(tmpDir, { recursive: true });
  console.log(`\n${pass + fail} assertions: ${pass} passed, ${fail} failed`);
  process.exit(fail > 0 ? 1 : 0);
}

run().catch(e => { console.error(e); process.exit(1); });
