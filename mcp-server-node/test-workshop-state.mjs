#!/usr/bin/env node
// F6b unit test — read_dashboard_state regex realignment.
// Verifies the fix for the iteration-4 finding that read_dashboard_state's
// inline regexes (separate from extractSection) over-matched project_name
// against §What & Why prose and under-matched project_state_summary by
// requiring `- **bold**` first bullet. Exercises three PROJECT.md shapes
// over JSON-RPC against a fresh CORE_DATA_DIR.
//
// Run: node test-workshop-state.mjs   (or: npm run test:workshop-state)

import { mkdtempSync, rmSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import assert from "node:assert/strict";

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
      try {
        resolve(JSON.parse(buffer.slice(0, nl)));
      } catch (e) {
        reject(e);
      }
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

function makeProject(rootDir, { name, wsId = "test-ws", projectMd }) {
  const projectDir = join(rootDir, "project");
  mkdirSync(projectDir, { recursive: true });
  if (name !== null) {
    writeFileSync(
      join(projectDir, "workspace.json"),
      JSON.stringify({ workspace_id: wsId, name, created: new Date().toISOString() }, null, 2),
      "utf-8",
    );
  }
  writeFileSync(join(projectDir, "PROJECT.md"), projectMd, "utf-8");
  return projectDir;
}

async function main() {
  const tmpRoot = mkdtempSync(join(tmpdir(), "core-workshop-test-"));
  const coreDir = join(tmpRoot, "core");
  mkdirSync(coreDir, { recursive: true });

  const child = spawn("node", [SERVER], {
    env: { ...process.env, CORE_DATA_DIR: coreDir },
    stdio: ["pipe", "pipe", "inherit"],
  });

  let assertions = 0;
  try {
    await rpc(child, 1, "initialize", {});

    // Case 1: §-prefixed PROJECT.md WITHOUT leading `**bold**` State bullet.
    // This is the iter-4 failure case (test-core-plugin's actual PROJECT.md shape).
    const project1 = makeProject(tmpRoot, {
      name: "Test Core Plugin",
      projectMd: `# Test Core Plugin — Cowork User Experience Validation

## §What & Why

Test the installation process for the CORE plugin from a non-technical user perspective.

## §State

- Currently in iteration 4 of validation testing.
- v1.1.1 plugin installed; six checks ran in this session.

## §Moves

- [ ] Next iteration is iteration 5.
`,
    });

    const r1 = await callTool(child, 2, "read_dashboard_state", { project_path: project1 });
    assert.equal(
      r1.project_name,
      "Test Core Plugin",
      "F6b: project_name resolves from workspace.json.name, not §What & Why prose",
    );
    assert.equal(
      r1.project_state_summary,
      "Currently in iteration 4 of validation testing",
      "F6b: project_state_summary returns first bullet (no **bold** wrapper required)",
    );
    assertions += 2;

    // Case 2: §-prefixed PROJECT.md WITH leading `**bold**` State bullet
    // (CORE-project convention). Backwards-compat verification — old behavior
    // (extract bold content) should still hold.
    const project2 = makeProject(tmpRoot.replace("/project", "/project2") + "-bold", {
      name: "CORE Framework Development",
      wsId: "core-framework",
      projectMd: `# CORE — Project Synthesis

## §What & Why

CORE is a multi-agent adversarial reasoning skill.

## §State

- **DC-42 candidate awaits review.** Verdict: A-SHARPENED + cap=5.
- Second bullet.

## §Moves

- [ ] Move 1.
`,
    });

    const r2 = await callTool(child, 3, "read_dashboard_state", { project_path: project2 });
    assert.equal(
      r2.project_name,
      "CORE Framework Development",
      "F6b: project_name from pointer.name preserved when workspace.json present",
    );
    assert.equal(
      r2.project_state_summary,
      "DC-42 candidate awaits review.",
      "F6b: leading **bold** content still extracts including punctuation inside the markers (backwards-compat with CORE convention)",
    );
    assertions += 2;

    // Case 3: PROJECT.md present but NO workspace.json (pointer missing) —
    // project_name should fall back to PROJECT.md H1 title.
    const project3 = makeProject(tmpRoot + "-no-pointer", {
      name: null,
      projectMd: `# Untracked Workspace

## §State

- Plain prose line, no leading bullet bold.
`,
    });

    const r3 = await callTool(child, 4, "read_dashboard_state", { project_path: project3 });
    assert.equal(
      r3.project_name,
      "Untracked Workspace",
      "F6b: no workspace.json — project_name falls back to PROJECT.md H1 title",
    );
    assert.equal(
      r3.project_state_summary,
      "Plain prose line, no leading bullet bold",
      "F6b: plain prose State bullet returns first sentence (no **bold** required)",
    );
    assertions += 2;

    console.log(`✓ F6b test passed (${assertions} assertions across 3 PROJECT.md shapes)`);

    // ── T-WS: workspaces_with_swarm sort order and field shape ───────────────
    // Seed four workspaces with different swarm states; verify the returned
    // array is sorted halted → running → complete → idle and that each entry
    // carries the expected fields. The `complete` workspace is essential: it
    // distinguishes the four-way contract from a three-way one (without it,
    // the SWARM_SORT_ORDER constant could silently swap complete/idle).
    //
    // NOTE: index.json and workspace manifests go in `coreDir` (= CORE_DATA_DIR),
    // not `tmpRoot`. The server reads from CORE_DATA_DIR.

    writeFileSync(join(coreDir, "index.json"), JSON.stringify([
      { workspace_id: "ws-run",  name: "Running WS",  project_path: join(coreDir, "project"), last_active: "2026-05-12T10:00:00Z" },
      { workspace_id: "ws-halt", name: "Halted WS",   project_path: join(coreDir, "project"), last_active: "2026-05-12T09:00:00Z" },
      { workspace_id: "ws-idle", name: "Idle WS",     project_path: join(coreDir, "project"), last_active: "2026-05-12T08:00:00Z" },
      { workspace_id: "ws-comp", name: "Complete WS", project_path: join(coreDir, "project"), last_active: "2026-05-12T07:00:00Z" }
    ], null, 2));

    mkdirSync(join(coreDir, "workspaces", "ws-run"),  { recursive: true });
    writeFileSync(join(coreDir, "workspaces", "ws-run", "workspace.json"), JSON.stringify({
      workspace_id: "ws-run",
      current_swarm: {
        status: "running",
        phase: "Phase 2",
        agent_count: 3,
        task_summary: "running task",
        updated_at: new Date().toISOString()
      }
    }, null, 2));

    mkdirSync(join(coreDir, "workspaces", "ws-halt"), { recursive: true });
    writeFileSync(join(coreDir, "workspaces", "ws-halt", "workspace.json"), JSON.stringify({
      workspace_id: "ws-halt",
      current_swarm: { status: "halted", updated_at: new Date().toISOString() }
    }, null, 2));

    mkdirSync(join(coreDir, "workspaces", "ws-idle"), { recursive: true });
    writeFileSync(join(coreDir, "workspaces", "ws-idle", "workspace.json"), JSON.stringify({
      workspace_id: "ws-idle"
      // no current_swarm — treated as "idle"
    }, null, 2));

    mkdirSync(join(coreDir, "workspaces", "ws-comp"), { recursive: true });
    writeFileSync(join(coreDir, "workspaces", "ws-comp", "workspace.json"), JSON.stringify({
      workspace_id: "ws-comp",
      current_swarm: { status: "complete", completed_at: new Date().toISOString(), updated_at: new Date().toISOString() }
    }, null, 2));

    const rWS = await callTool(child, 5, "read_dashboard_state", {});
    const wws = rWS?.workspaces_with_swarm;
    assert.ok(Array.isArray(wws),                                   "T-WS: workspaces_with_swarm field present and is array");
    assert.equal(wws?.length, 4,                                    "T-WS: 4 entries");
    assert.equal(wws?.[0]?.swarm_status, "halted",                  "T-WS: halted sorts first");
    assert.equal(wws?.[1]?.swarm_status, "running",                 "T-WS: running sorts second");
    assert.equal(wws?.[2]?.swarm_status, "complete",                "T-WS: complete sorts third (between running and idle)");
    assert.equal(wws?.[3]?.swarm_status, "idle",                    "T-WS: idle sorts last");
    assert.ok(
      wws.findIndex(w => w.swarm_status === "running") < wws.findIndex(w => w.swarm_status === "complete"),
      "T-WS: running before complete"
    );
    assert.ok(
      wws.findIndex(w => w.swarm_status === "complete") < wws.findIndex(w => w.swarm_status === "idle"),
      "T-WS: complete before idle"
    );
    assert.equal(wws?.find(w => w.swarm_status === "running")?.swarm_phase,        "Phase 2",       "T-WS: running has phase");
    assert.equal(wws?.find(w => w.swarm_status === "running")?.swarm_agent_count,  3,               "T-WS: running has count");
    assert.equal(wws?.find(w => w.swarm_status === "running")?.swarm_task_summary, "running task",  "T-WS: running has summary");
    assert.equal(wws?.find(w => w.swarm_status === "idle")?.workspace_id,          "ws-idle",       "T-WS: idle has workspace_id");
    assert.equal(wws?.find(w => w.swarm_status === "idle")?.swarm_phase,           null,            "T-WS: idle swarm_phase is null");
    assert.equal(wws?.find(w => w.swarm_status === "complete")?.workspace_id,      "ws-comp",       "T-WS: complete has workspace_id");
    assert.ok("dm_name" in (rWS || {}),                             "T-WS: backwards-compat dm_name field still present");
    assert.ok("workspace_count" in (rWS || {}),                     "T-WS: backwards-compat workspace_count field still present");
    assertions += 16;

    console.log(`✓ T-WS test passed (${assertions} total assertions)`);
  } finally {
    child.kill();
    rmSync(tmpRoot, { recursive: true, force: true });
    rmSync(tmpRoot + "-no-pointer", { recursive: true, force: true });
    rmSync(tmpRoot.replace("/project", "/project2") + "-bold", { recursive: true, force: true });
  }
}

main().catch((e) => {
  console.error("✗ F6b test failed:", e.message);
  process.exit(1);
});
