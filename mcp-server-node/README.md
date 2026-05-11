# core-mcp (Node.js)

Zero-dependency Node.js implementation of the CORE MCP server. Speaks MCP over stdio (newline-delimited JSON-RPC 2.0) and exposes 8 read-only tools that surface CORE project state to Live Artifact dashboards.

## Why Node.js (and not Python)

- Anthropic's plugin reference uses `npx` examples for plugin-bundled MCP servers — Node is the assumed runtime.
- Zero dependencies = zero install footprint. No pip, no venv, no PEP 668 surprises.
- The community guide for cross-platform Claude Code hooks recommends `node` as the safest default (Claude Code requires Node.js so it's guaranteed available).

## How it's invoked

The plugin's install script (`scripts/mcp_server_install.py`) registers this server in `claude_desktop_config.json` (or platform-equivalent) once per machine. Cowork launches the server at app start; subsequent sessions connect to it automatically.

The registered command is:
```json
{
  "mcpServers": {
    "core": {
      "command": "node",
      "args": ["/absolute/path/to/server.mjs"]
    }
  }
}
```

## Tools

All read-only. All return JSON. All are safe to call at any time without state-change side effects.

| Tool | Reads from | Returns |
|---|---|---|
| `list_workspaces` | `~/.core/index.json` | Workspace registry sorted by last-active |
| `read_dm_profile` | `~/.core/dm-profile.md` | DM emergent name + full profile content |
| `read_project_md` | `<workspace>/PROJECT.md` | Full content + parsed §State/§Moves/§Risks/§People/§Notes |
| `read_persuasion_log` | Session logs at `<workspace>/sessions/YYYY-MM-DD/` | Parsed persuasion entries (Agent / From / To / Trigger) |
| `read_swarm_topology` | Session logs | Agent roster + phase timeline |
| `read_convergence_trajectory` | Session logs | Convergence table + ratio (multi-agent agreement %) |
| `read_vibe_log` | `~/.core/vibes/vibe-log.md` | Parsed vibe entries with date / descriptor / ASCII art |
| `read_workshop_state` | Aggregates the above | Bundle for the DM Workshop Live Artifact |

## Develop / smoke test

```bash
# Smoke test the handshake
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | node server.mjs

# Smoke test a tool call
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_workspaces","arguments":{}}}' \
  | node server.mjs
```

Logs go to stderr with the `[core-mcp]` prefix. Stdout is reserved for JSON-RPC responses.

## Requirements

Node.js >= 18.0.0. No npm install needed — `server.mjs` uses only built-in modules (`fs`, `os`, `path`, `readline`).
