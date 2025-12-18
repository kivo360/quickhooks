"""CLI commands for agent discovery and management."""

from pathlib import Path
from typing import Annotated, List

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from quickhooks.agent_discovery import (
    AgentDiscovery,
    AgentInfo,
    discover_agents_for_query,
)

agents_app = cyclopts.App(help="Agent discovery and management commands")
console = Console()


@agents_app.command()
async def search(
    query: str,
    codebase_path: Annotated[
        Path,
        Parameter(
            "--path", help="Path to the codebase (defaults to current directory)"
        ),
    ] = Path.cwd(),
    limit: Annotated[
        int, Parameter("--limit", alias="-l", help="Maximum number of results")
    ] = 5,
    min_similarity: Annotated[
        float,
        Parameter("--min-similarity", help="Minimum similarity threshold (0.0-1.0)"),
    ] = 0.5,
):
    """Search for agents that match your query.

    Args:
        query: Description of what you're looking for
        codebase_path: Path to the codebase to search
        limit: Maximum number of results to return
        min_similarity: Minimum similarity threshold
    """
    console.print(f"🔍 Searching for agents matching: '{query}'")
    console.print(f"📂 Searching in: {codebase_path}")

    try:
        agents = await discover_agents_for_query(
            query=query,
            codebase_path=codebase_path,
            limit=limit,
            min_similarity=min_similarity,
        )

        if not agents:
            console.print("❌ No matching agents found.", style="yellow")
            console.print(
                "💡 Try using a more general query or rebuilding the index with:"
            )
            console.print("   quickhooks agents rebuild --path /path/to/codebase")
            return

        _display_agents_table(agents, f"🎯 Found {len(agents)} matching agents")

    except Exception as e:
        console.print(f"❌ Error searching for agents: {e}", style="red")


@agents_app.command()
async def list(
    codebase_path: Annotated[
        Path,
        Parameter(
            "--path", help="Path to the codebase (defaults to current directory)"
        ),
    ] = Path.cwd(),
):
    """List all discovered agents in the codebase.

    Args:
        codebase_path: Path to the codebase
    """
    console.print(f"📋 Listing all agents in: {codebase_path}")

    discovery = AgentDiscovery()
    try:
        await discovery.initialize()

        agents = await discovery.list_all_agents()

        if len(agents) == 0:
            console.print(
                "📭 No agents found. The index might be empty.", style="yellow"
            )
            console.print("💡 Try rebuilding the index with:")
            console.print("   quickhooks agents rebuild --path /path/to/codebase")
            return

        _display_agents_table(agents, f"📋 Found {len(agents)} indexed agents")

    except Exception as e:
        console.print(f"❌ Error listing agents: {e}", style="red")
    finally:
        await discovery.close()


@agents_app.command()
async def rebuild(
    codebase_path: Annotated[
        Path,
        Parameter(
            "--path", help="Path to the codebase (defaults to current directory)"
        ),
    ] = Path.cwd(),
):
    """Rebuild the agent index by scanning the codebase.

    Args:
        codebase_path: Path to the codebase to scan
    """
    console.print(f"🔄 Rebuilding agent index for: {codebase_path}")

    discovery = AgentDiscovery()
    try:
        await discovery.initialize()

        # Scan for agents
        console.print("🔍 Scanning codebase for agents...")
        agents = await discovery.scan_codebase_for_agents(codebase_path)

        if not agents:
            console.print("❌ No agents found in the codebase.", style="yellow")
            return

        console.print(f"✅ Found {len(agents)} agents")

        # Index them
        console.print("📊 Indexing agents...")
        await discovery.index_agents(agents)

        console.print(f"🎉 Successfully indexed {len(agents)} agents!")

        # Show summary
        _display_agents_summary(agents)

    except Exception as e:
        console.print(f"❌ Error rebuilding index: {e}", style="red")
    finally:
        await discovery.close()


@agents_app.command()
async def types(
    codebase_path: Annotated[
        Path,
        Parameter(
            "--path", help="Path to the codebase (defaults to current directory)"
        ),
    ] = Path.cwd(),
):
    """List all available agent types in the codebase.

    Args:
        codebase_path: Path to the codebase
    """
    from quickhooks.agent_discovery import get_available_agent_types

    console.print(f"🏷️  Getting agent types for: {codebase_path}")

    try:
        agent_types = await get_available_agent_types(codebase_path)

        if not agent_types:
            console.print("📭 No agent types found.", style="yellow")
            console.print("💡 Try rebuilding the index with:")
            console.print("   quickhooks agents rebuild --path /path/to/codebase")
            return

        # Create table for agent types
        table = Table(title=f"🏷️  Found {len(agent_types)} agent types")
        table.add_column("Agent Type", style="cyan")
        table.add_column("Description", style="white")

        # Add some basic descriptions for common agent types
        descriptions = {
            "general-purpose": "General purpose agent for various tasks",
            "frontend-developer": "Builds React components and UI",
            "backend-architect": "Designs APIs and backend systems",
            "database-optimizer": "Optimizes database queries and schemas",
            "security-auditor": "Reviews code for security issues",
            "test-automator": "Creates and manages test suites",
            "deployment-engineer": "Handles CI/CD and deployment",
            "documentation-writer": "Creates technical documentation",
            "performance-engineer": "Optimizes application performance",
            "error-detective": "Debugs and troubleshoots issues",
        }

        for agent_type in sorted(agent_types):
            description = descriptions.get(
                agent_type, f"Agent specialized in {agent_type}"
            )
            table.add_row(agent_type, description)

        console.print(table)

    except Exception as e:
        console.print(f"❌ Error getting agent types: {e}", style="red")


@agents_app.command()
async def info(
    name: str,
    codebase_path: Annotated[
        Path,
        Parameter(
            "--path", help="Path to the codebase (defaults to current directory)"
        ),
    ] = Path.cwd(),
):
    """Get detailed information about a specific agent.

    Args:
        name: Name of the agent to look up
        codebase_path: Path to the codebase
    """
    console.print(f"ℹ️  Looking for agent: {name}")

    discovery = AgentDiscovery()
    try:
        await discovery.initialize()

        agent = await discovery.get_agent_by_name(name)

        if not agent:
            console.print(f"❌ Agent '{name}' not found.", style="red")
            console.print("💡 Use 'quickhooks agents list' to see available agents")
            return

        # Display detailed information
        _display_agent_details(agent)

    except Exception as e:
        console.print(f"❌ Error getting agent info: {e}", style="red")
    finally:
        await discovery.close()


def _display_agents_table(agents: List[AgentInfo], title: str) -> None:
    """Display agents in a formatted table.

    Args:
        agents: List of agents to display
        title: Table title
    """
    table = Table(title=title)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("File", style="blue")

    for agent in agents:
        # Truncate long descriptions
        description = agent.description
        if len(description) > 60:
            description = description[:57] + "..."

        # Shorten file paths
        file_path = Path(agent.file_path).name
        if file_path == agent.file_path:  # No directory components
            file_path = agent.file_path
        else:
            file_path = f".../{file_path}"

        table.add_row(agent.name, agent.subagent_type or "N/A", description, file_path)

    console.print(table)


def _display_agents_summary(agents: List[AgentInfo]) -> None:
    """Display a summary of indexed agents.

    Args:
        agents: List of agents
    """
    # Count agent types
    type_counts = {}
    for agent in agents:
        agent_type = agent.subagent_type or "unknown"
        type_counts[agent_type] = type_counts.get(agent_type, 0) + 1

    # Create summary table
    table = Table(title="📊 Agent Index Summary")
    table.add_column("Agent Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    for agent_type, count in sorted(type_counts.items()):
        table.add_row(agent_type, str(count))

    console.print(table)

    # Show database location
    console.print(f"\n💾 Database location: {Path.cwd() / '.quickhooks' / 'agents.db'}")


def _display_agent_details(agent: AgentInfo) -> None:
    """Display detailed information about a single agent.

    Args:
        agent: Agent to display
    """
    content = f"""
**Name:** {agent.name}
**Type:** {agent.subagent_type or "N/A"}

**Description:**
{agent.description}

**File Location:**
{agent.file_path}

**Capabilities:**
{chr(10).join(f"• {cap}" for cap in agent.capabilities) if agent.capabilities else "None specified"}
"""

    panel = Panel(content, title=f"ℹ️  Agent Details: {agent.name}", border_style="cyan")
    console.print(panel)
