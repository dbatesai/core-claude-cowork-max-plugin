"""
CORE MCP server — FastMCP-based read-only tools for the CORE Cowork max plugin.
All tools read from ~/.core/ and project-level files. No writes.
Registered in ~/Library/Application Support/Claude/claude_desktop_config.json
by scripts/mcp-server-install.sh on first session.
"""

from fastmcp import FastMCP

from core_mcp.tools.list_workspaces import list_workspaces_impl
from core_mcp.tools.read_dm_profile import read_dm_profile_impl
from core_mcp.tools.read_project_md import read_project_md_impl
from core_mcp.tools.read_persuasion_log import read_persuasion_log_impl
from core_mcp.tools.read_swarm_topology import read_swarm_topology_impl
from core_mcp.tools.read_convergence_trajectory import read_convergence_trajectory_impl
from core_mcp.tools.read_vibe_log import read_vibe_log_impl
from core_mcp.tools.read_workshop_state import read_workshop_state_impl

mcp = FastMCP("CORE")


@mcp.tool()
def list_workspaces() -> dict:
    """List all CORE workspaces from ~/.core/index.json with last-active timestamps."""
    return list_workspaces_impl()


@mcp.tool()
def read_dm_profile() -> dict:
    """Read the DM's persistent profile from ~/.core/dm-profile.md."""
    return read_dm_profile_impl()


@mcp.tool()
def read_project_md(workspace_id: str = "") -> dict:
    """
    Read PROJECT.md for the given workspace ID (or the most-recently-active workspace).
    Returns the raw content plus structured extracts of §State and §Moves.
    """
    return read_project_md_impl(workspace_id)


@mcp.tool()
def read_persuasion_log(workspace_id: str = "", session_date: str = "") -> dict:
    """
    Read the most recent persuasion log from a swarm session.
    workspace_id: optional; defaults to most-recently-active workspace.
    session_date: optional YYYY-MM-DD filter; defaults to most recent session.
    """
    return read_persuasion_log_impl(workspace_id, session_date)


@mcp.tool()
def read_swarm_topology(workspace_id: str = "", session_date: str = "") -> dict:
    """
    Read swarm topology (agent roster + phase timeline) from a session.
    workspace_id: optional; defaults to most-recently-active workspace.
    session_date: optional YYYY-MM-DD filter; defaults to most recent session.
    """
    return read_swarm_topology_impl(workspace_id, session_date)


@mcp.tool()
def read_convergence_trajectory(workspace_id: str = "", session_date: str = "") -> dict:
    """
    Read convergence trajectory data (agreement/disagreement delta per phase) from a session.
    workspace_id: optional; defaults to most-recently-active workspace.
    session_date: optional YYYY-MM-DD filter; defaults to most recent session.
    """
    return read_convergence_trajectory_impl(workspace_id, session_date)


@mcp.tool()
def read_vibe_log(limit: int = 10) -> dict:
    """
    Read the most recent vibe-log entries from ~/.core/vibes/vibe-log.md.
    Returns structured JSON with session dates, vibe labels, and ASCII art entries.
    limit: max number of entries to return (default 10, max 50).
    """
    return read_vibe_log_impl(min(limit, 50))


@mcp.tool()
def read_workshop_state(workspace_id: str = "") -> dict:
    """
    Aggregate state for the DM Workshop Live Artifact.
    Returns: dm_name, project_name, project_state_summary, active_risk_count,
    session_age_days, last_swarm_date, vibe_label, workspace_count.
    workspace_id: optional; defaults to most-recently-active workspace.
    """
    return read_workshop_state_impl(workspace_id)


if __name__ == "__main__":
    mcp.run()
