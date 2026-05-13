#!/usr/bin/env node
// F8 unit test — vibe-log ordering. Verifies the fix for the iteration-3 finding
// that read_vibe_log.most_recent_vibe returned a stale entry when multiple entries
// shared the same date string. Exercises the MCP server over JSON-RPC on a fresh
// CORE_DATA_DIR so the live ~/.core/vibes/vibe-log.md is never touched.
//
// Run: node test-vibe-log.mjs   (or: npm test, from this directory)

import { mkdtempSync, rmSync, readFileSync } from "node:fs";
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

async function main() {
  const tmpDir = mkdtempSync(join(tmpdir(), "core-vibe-test-"));
  const child = spawn("node", [SERVER], {
    env: { ...process.env, CORE_DATA_DIR: tmpDir },
    stdio: ["pipe", "pipe", "inherit"],
  });

  let assertions = 0;
  try {
    await rpc(child, 1, "initialize", {});

    // Case 1: two entries with the same date — second one must be most_recent_vibe.
    const r1 = await callTool(child, 2, "append_vibe_log", {
      date: "2026-05-12",
      label: "test-workspace [first]",
      vibe: "First vibe on 2026-05-12.",
    });
    assert.equal(r1.success, true, "first append succeeded");
    assertions++;

    const r2 = await callTool(child, 3, "append_vibe_log", {
      date: "2026-05-12",
      label: "test-workspace [second]",
      vibe: "Second vibe on 2026-05-12 — must be most recent.",
    });
    assert.equal(r2.success, true, "second append succeeded");
    assertions++;

    const r3 = await callTool(child, 4, "read_vibe_log", { limit: 10 });
    assert.equal(r3.found, true, "log is readable");
    assert.equal(r3.total_entries, 2, "2 entries parsed");
    assert.equal(
      r3.most_recent_vibe,
      "Second vibe on 2026-05-12 — must be most recent.",
      "F8: same-date second append must be most_recent_vibe",
    );
    assertions += 3;

    // Case 2: backfill with an older date string — newest-by-insertion wins,
    // not newest-by-date-string. Confirms the fix doesn't reintroduce sort dependency.
    const r4 = await callTool(child, 5, "append_vibe_log", {
      date: "2026-01-01",
      label: "backfill [old date]",
      vibe: "Old-dated vibe added last — most recent by insertion.",
    });
    assert.equal(r4.success, true, "backfill append succeeded");
    assertions++;

    const r5 = await callTool(child, 6, "read_vibe_log", { limit: 10 });
    assert.equal(
      r5.most_recent_vibe,
      "Old-dated vibe added last — most recent by insertion.",
      "F8: backfilled older-dated entry lands at top of read order",
    );
    assert.equal(r5.entries[0].date, "2026-01-01", "entries[0] is the most recently appended");
    assert.equal(r5.entries[1].date, "2026-05-12", "entries[1] is the second-written");
    assert.equal(r5.entries[2].date, "2026-05-12", "entries[2] is the first-written");
    assertions += 4;

    // Case 3: file is physically newest-first on disk (not just in the read tool).
    const fileContent = readFileSync(join(tmpDir, "vibes", "vibe-log.md"), "utf-8");
    const firstHeader = fileContent.match(/^## (\d{4}-\d{2}-\d{2})/);
    assert.equal(firstHeader[1], "2026-01-01", "file's first header is the most recent insertion");
    assertions++;

    console.log(`✓ F8 test passed (${assertions} assertions)`);
  } finally {
    child.kill();
    rmSync(tmpDir, { recursive: true, force: true });
  }
}

main().catch((e) => {
  console.error("✗ F8 test failed:", e.message);
  process.exit(1);
});
