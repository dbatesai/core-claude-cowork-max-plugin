# core-mcp

FastMCP-based MCP server for the CORE Cowork Max plugin. Exposes 8 read-only tools so Live Artifact dashboards can render real-time project state.

## Tools

| Tool | Reads | Returns |
|---|---|---|
| `list_workspaces` | `~/.core/index.json` | Workspace registry |
| `read_dm_profile` | `~/.core/dm-profile.md` | DM identity + profile content |
| `read_project_md` | `<workspace>/PROJECT.md` | Full content + section extracts |
| `read_persuasion_log` | Session logs | Parsed persuasion entries |
| `read_swarm_topology` | Session logs | Agent roster + phases |
| `read_convergence_trajectory` | Session logs | Convergence table + ratio |
| `read_vibe_log` | `~/.core/vibes/vibe-log.md` | Structured vibe entries |
| `read_workshop_state` | Aggregates the above | DM Workshop state bundle |

All tools are **read-only** — the server never writes.

## Install

The plugin's `scripts/mcp-server-install.sh` handles install automatically:
1. Creates `~/.core/mcp-venv/`
2. Installs `fastmcp>=2.0,<3` and this package
3. Registers `~/.core/mcp-venv/bin/python -m core_mcp.server` in `~/Library/Application Support/Claude/claude_desktop_config.json`

After the registration, quit Cowork (Cmd+Q) and reopen — the MCP server loads at app start.

## Develop

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m core_mcp.server  # smoke run; Ctrl+C to stop
pytest tests/              # if tests/ exists
```
