"""Agent discovery system using semantic embeddings.

This module provides functionality to discover and match agents in a codebase
using FastEmbed for embeddings and LanceDB for vector storage and similarity search.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import lancedb
from fastembed import TextEmbedding
from pydantic import BaseModel, Field

from quickhooks.config import get_config


class AgentInfo(BaseModel):
    """Information about a discovered agent."""

    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of what the agent does")
    file_path: str = Field(..., description="Path to the agent file")
    subagent_type: Optional[str] = Field(None, description="Type of subagent if applicable")
    capabilities: List[str] = Field(default_factory=list, description="List of agent capabilities")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector for semantic search")


class AgentDiscovery:
    """Agent discovery system using semantic embeddings.

    This class provides functionality to:
    1. Scan the codebase for agents
    2. Generate embeddings for agent descriptions
    3. Store embeddings in LanceDB for fast similarity search
    4. Find the best matching agents for a given query
    """

    def __init__(self, db_path: Optional[Path] = None, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the agent discovery system.

        Args:
            db_path: Path to the LanceDB database (defaults to .quickhooks/agents.db)
            embedding_model: FastEmbed model to use for embeddings
        """
        self.db_path = db_path or Path.cwd() / ".quickhooks" / "agents.db"
        self.embedding_model = embedding_model
        self.embedding_client: Optional[TextEmbedding] = None
        self.db: Optional[lancedb.DBConnection] = None
        self.table: Optional[lancedb.Table] = None

    async def initialize(self) -> None:
        """Initialize the embedding client and database connection."""
        # Initialize FastEmbed client
        self.embedding_client = TextEmbedding(self.embedding_model)

        # Initialize LanceDB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await lancedb.connect(str(self.db_path))

        # Get or create the agents table
        try:
            self.table = await self.db.open_table("agents")
        except lancedb.TableNotFoundException:
            # Create table with schema
            schema = {
                "name": str,
                "description": str,
                "file_path": str,
                "subagent_type": str,
                "capabilities": list,
                "embedding": list,
            }
            self.table = await self.db.create_table("agents", schema=schema)

    async def close(self) -> None:
        """Close the database connection."""
        if self.db:
            await self.db.close()

    async def scan_codebase_for_agents(self, codebase_path: Path) -> List[AgentInfo]:
        """Scan the codebase for agent definitions.

        Args:
            codebase_path: Path to the codebase to scan

        Returns:
            List of discovered agents
        """
        agents = []

        # Look for Python files that might contain agents
        for py_file in codebase_path.rglob("*.py"):
            # Skip __pycache__ and test directories
            if any(skip in str(py_file) for skip in ["__pycache__", "tests", ".pytest_cache"]):
                continue

            try:
                file_agents = await self._extract_agents_from_file(py_file)
                agents.extend(file_agents)
            except Exception as e:
                # Skip files that can't be parsed
                continue

        return agents

    async def _extract_agents_from_file(self, file_path: Path) -> List[AgentInfo]:
        """Extract agent information from a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of agents found in the file
        """
        agents = []

        try:
            content = file_path.read_text(encoding="utf-8")

            # Look for Task tool usage with subagent_type parameter
            import re

            # Pattern to find Task tool calls with subagent_type
            task_pattern = r'Task\(\s*.*?subagent_type\s*=\s*["\']([^"\']+)["\']'
            task_matches = re.findall(task_pattern, content, re.DOTALL)

            if task_matches:
                # Extract context around each Task call
                for i, match in enumerate(task_matches):
                    # Get surrounding context for description
                    lines = content.split('\n')
                    context_start = max(0, content.find(match) - 200)
                    context_end = min(len(content), content.find(match) + 500)
                    context = content[context_start:context_end]

                    # Try to extract a description from comments or nearby strings
                    description = await self._extract_description_from_context(context)

                    agents.append(AgentInfo(
                        name=f"Agent_{match}_{i}",
                        description=description or f"Agent of type {match}",
                        file_path=str(file_path),
                        subagent_type=match,
                        capabilities=[match]
                    ))

            # Also look for class definitions that might be agents
            class_pattern = r'class\s+(\w+Agent)\s*\([^)]*\):\s*"""([^"]+)"""'
            class_matches = re.findall(class_pattern, content, re.MULTILINE | re.DOTALL)

            for class_name, class_desc in class_matches:
                agents.append(AgentInfo(
                    name=class_name,
                    description=class_desc.strip(),
                    file_path=str(file_path),
                    capabilities=[class_name.lower().replace("agent", "")]
                ))

        except Exception:
            # Skip files that can't be read or parsed
            pass

        return agents

    async def _extract_description_from_context(self, context: str) -> Optional[str]:
        """Extract a meaningful description from code context.

        Args:
            context: Code context around a Task call

        Returns:
            Extracted description or None
        """
        # Look for comments or docstrings in the context
        lines = context.split('\n')

        # Look for comment lines before the Task call
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('#'):
                return line[1:].strip()
            elif line.startswith('"""') and line.endswith('"""'):
                return line[3:-3].strip()
            elif '"""' in line:
                # Start of a multiline docstring
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    desc_line = lines[idx + 1].strip()
                    if desc_line and not desc_line.startswith('"""'):
                        return desc_line

        return None

    async def index_agents(self, agents: List[AgentInfo]) -> None:
        """Index agents in the vector database.

        Args:
            agents: List of agents to index
        """
        if not self.embedding_client or not self.table:
            await self.initialize()

        # Generate embeddings for all agents
        descriptions = [agent.description for agent in agents]
        embeddings = list(self.embedding_client.embed(descriptions))

        # Update agents with embeddings
        for i, agent in enumerate(agents):
            agent.embedding = embeddings[i].tolist()

        # Convert to data for LanceDB
        data = []
        for agent in agents:
            data.append({
                "name": agent.name,
                "description": agent.description,
                "file_path": agent.file_path,
                "subagent_type": agent.subagent_type,
                "capabilities": agent.capabilities,
                "embedding": agent.embedding,
            })

        # Add to database in batches
        if data:
            await self.table.add(data)

    async def find_similar_agents(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5
    ) -> List[AgentInfo]:
        """Find agents similar to the given query.

        Args:
            query: Query string to search for
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of similar agents ranked by similarity
        """
        if not self.embedding_client or not self.table:
            await self.initialize()

        # Generate embedding for the query
        query_embedding = list(self.embedding_client.embed([query]))[0].tolist()

        # Search for similar agents
        results = await self.table.vector_search(
            query_embedding,
            vector_column_name="embedding",
            limit=limit
        ).to_pandas()

        # Filter by similarity and convert to AgentInfo objects
        similar_agents = []
        for _, row in results.iterrows():
            # LanceDB provides a _distance column (lower is more similar)
            # Convert distance to similarity score
            distance = row.get('_distance', 1.0)
            similarity = max(0.0, 1.0 - distance)  # Simple conversion, may need tuning

            if similarity >= min_similarity:
                agent = AgentInfo(
                    name=row['name'],
                    description=row['description'],
                    file_path=row['file_path'],
                    subagent_type=row.get('subagent_type'),
                    capabilities=row['capabilities'],
                    embedding=row.get('embedding')
                )
                similar_agents.append((agent, similarity))

        # Sort by similarity (descending)
        similar_agents.sort(key=lambda x: x[1], reverse=True)

        # Return just the agents (without similarity scores)
        return [agent for agent, _ in similar_agents]

    async def get_agent_by_name(self, name: str) -> Optional[AgentInfo]:
        """Get an agent by its exact name.

        Args:
            name: Name of the agent to find

        Returns:
            AgentInfo if found, None otherwise
        """
        if not self.table:
            await self.initialize()

        # Search by name
        results = await self.table.search().where(f"name = '{name}'").limit(1).to_pandas()

        if len(results) == 0:
            return None

        row = results.iloc[0]
        return AgentInfo(
            name=row['name'],
            description=row['description'],
            file_path=row['file_path'],
            subagent_type=row.get('subagent_type'),
            capabilities=row['capabilities'],
            embedding=row.get('embedding')
        )

    async def list_all_agents(self) -> List[AgentInfo]:
        """List all indexed agents.

        Returns:
            List of all agents in the database
        """
        if not self.table:
            await self.initialize()

        results = await self.table.search().limit(None).to_pandas()

        agents = []
        for _, row in results.iterrows():
            agent = AgentInfo(
                name=row['name'],
                description=row['description'],
                file_path=row['file_path'],
                subagent_type=row.get('subagent_type'),
                capabilities=row['capabilities'],
                embedding=row.get('embedding')
            )
            agents.append(agent)

        return agents

    async def rebuild_index(self, codebase_path: Path) -> None:
        """Rebuild the entire agent index from the codebase.

        Args:
            codebase_path: Path to the codebase to scan
        """
        if not self.table:
            await self.initialize()

        # Clear existing data
        await self.table.delete()

        # Scan for agents
        agents = await self.scan_codebase_for_agents(codebase_path)

        if agents:
            # Index the discovered agents
            await self.index_agents(agents)


# Convenience functions for common operations

async def discover_agents_for_query(
    query: str,
    codebase_path: Path,
    limit: int = 5,
    min_similarity: float = 0.5
) -> List[AgentInfo]:
    """Discover agents for a specific query.

    Args:
        query: Query describing what you need
        codebase_path: Path to the codebase to search
        limit: Maximum number of results
        min_similarity: Minimum similarity threshold

    Returns:
        List of matching agents
    """
    discovery = AgentDiscovery()
    try:
        await discovery.initialize()

        # Check if we need to rebuild the index (simplified heuristic)
        agents = await discovery.list_all_agents()
        if len(agents) == 0:
            # No agents indexed, scan and index the codebase
            await discovery.rebuild_index(codebase_path)

        # Find similar agents
        return await discovery.find_similar_agents(query, limit, min_similarity)
    finally:
        await discovery.close()


async def get_available_agent_types(codebase_path: Path) -> List[str]:
    """Get a list of all available agent types in the codebase.

    Args:
        codebase_path: Path to the codebase to scan

    Returns:
        List of unique agent types
    """
    discovery = AgentDiscovery()
    try:
        await discovery.initialize()

        agents = await discovery.list_all_agents()
        if len(agents) == 0:
            await discovery.rebuild_index(codebase_path)
            agents = await discovery.list_all_agents()

        # Extract unique subagent types
        agent_types = set()
        for agent in agents:
            if agent.subagent_type:
                agent_types.add(agent.subagent_type)

        return sorted(list(agent_types))
    finally:
        await discovery.close()