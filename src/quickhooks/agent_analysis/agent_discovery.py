"""Agent discovery system using Chroma vector database."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


@dataclass
class DiscoveredAgent:
    """Represents a discovered agent from the filesystem."""

    name: str
    path: str
    description: str
    capabilities: list[str]
    usage_pattern: str
    content: str
    metadata: dict[str, str]
    similarity_score: float = 0.0


class AgentDiscovery:
    """Discovers and indexes agents from the Claude Code agents directory."""

    def __init__(
        self, agents_dir: Path | None = None, db_path: Path | None = None
    ):
        """
        Initialize the agent discovery system.

        Args:
            agents_dir: Path to the agents directory (defaults to ~/.claude/agents)
            db_path: Path to store the Chroma database (defaults to ~/.quickhooks/agent_db)
        """
        self.agents_dir = agents_dir or Path.home() / ".claude" / "agents"
        self.db_path = db_path or Path.home() / ".quickhooks" / "agent_db"

        # Ensure directories exist
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Initialize sentence transformer for embeddings
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="claude_agents",
            metadata={"description": "Claude Code agents for task matching"},
        )

    def scan_and_index_agents(self, force_reindex: bool = False) -> int:
        """
        Scan the agents directory and index all found agents.

        Args:
            force_reindex: If True, clear existing index and reindex all agents

        Returns:
            Number of agents indexed
        """
        if not self.agents_dir.exists():
            print(f"Agents directory not found: {self.agents_dir}")
            return 0

        if force_reindex:
            # Clear existing collection
            self.client.delete_collection("claude_agents")
            self.collection = self.client.create_collection(
                name="claude_agents",
                metadata={"description": "Claude Code agents for task matching"},
            )

        agents = self._discover_agents()
        indexed_count = 0

        for agent in agents:
            # Check if agent is already indexed (by content hash)
            content_hash = self._get_content_hash(agent.content)

            existing = self.collection.get(
                where={"content_hash": content_hash}, limit=1
            )

            if not existing["ids"] or force_reindex:
                self._index_agent(agent, content_hash)
                indexed_count += 1

        return indexed_count

    def find_relevant_agents(
        self,
        prompt: str,
        context: str = "",
        limit: int = 5,
        min_similarity: float = 0.3,
    ) -> list[DiscoveredAgent]:
        """
        Find agents most relevant to the given prompt and context.

        Args:
            prompt: The user's prompt
            context: Additional context
            limit: Maximum number of agents to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of relevant agents sorted by similarity
        """
        # Combine prompt and context for search
        search_text = f"{prompt}\n\n{context}".strip()

        # Query the collection
        results = self.collection.query(
            query_texts=[search_text],
            n_results=min(limit * 2, 20),  # Get more results to filter
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"][0]:
            return []

        relevant_agents = []

        for i, _agent_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            similarity = 1 - distance  # Convert distance to similarity

            if similarity < min_similarity:
                continue

            metadata = results["metadatas"][0][i]
            document = results["documents"][0][i]

            agent = DiscoveredAgent(
                name=metadata["name"],
                path=metadata["path"],
                description=metadata["description"],
                capabilities=json.loads(metadata["capabilities"]),
                usage_pattern=metadata["usage_pattern"],
                content=document,
                metadata=metadata,
                similarity_score=similarity,
            )

            relevant_agents.append(agent)

        # Sort by similarity and return top results
        relevant_agents.sort(key=lambda x: x.similarity_score, reverse=True)
        return relevant_agents[:limit]

    def _discover_agents(self) -> list[DiscoveredAgent]:
        """Discover all agents in the agents directory."""
        agents = []

        # Look for different agent file patterns
        patterns = ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml"]

        for pattern in patterns:
            for agent_file in self.agents_dir.rglob(pattern):
                if agent_file.is_file():
                    agent = self._parse_agent_file(agent_file)
                    if agent:
                        agents.append(agent)

        return agents

    def _parse_agent_file(self, file_path: Path) -> DiscoveredAgent | None:
        """Parse an agent file and extract metadata."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract basic info
            name = file_path.stem
            description = ""
            capabilities = []
            usage_pattern = ""

            # Parse different file types
            if file_path.suffix == ".py":
                description, capabilities, usage_pattern = self._parse_python_agent(
                    content
                )
            elif file_path.suffix == ".md":
                description, capabilities, usage_pattern = self._parse_markdown_agent(
                    content
                )
            elif file_path.suffix == ".json":
                description, capabilities, usage_pattern = self._parse_json_agent(
                    content
                )
            else:
                # Generic text file
                description = content[:200] + "..." if len(content) > 200 else content
                capabilities = self._extract_capabilities_from_text(content)
                usage_pattern = self._extract_usage_pattern(content)

            return DiscoveredAgent(
                name=name,
                path=str(file_path),
                description=description,
                capabilities=capabilities,
                usage_pattern=usage_pattern,
                content=content,
                metadata={
                    "file_type": file_path.suffix,
                    "file_size": str(file_path.stat().st_size),
                    "last_modified": str(file_path.stat().st_mtime),
                },
            )

        except Exception as e:
            print(f"Error parsing agent file {file_path}: {e}")
            return None

    def _parse_python_agent(self, content: str) -> tuple[str, list[str], str]:
        """Parse Python agent file for metadata."""
        lines = content.split("\n")
        description = ""
        capabilities = []
        usage_pattern = ""

        # Look for docstrings and comments
        in_docstring = False
        docstring_content = []

        for line in lines:
            stripped = line.strip()

            # Extract docstring
            if '"""' in stripped or "'''" in stripped:
                if not in_docstring:
                    in_docstring = True
                    # Check if docstring starts and ends on same line
                    if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                        content_part = (
                            stripped.split('"""')[1]
                            if '"""' in stripped
                            else stripped.split("'''")[1]
                        )
                        docstring_content.append(content_part)
                        in_docstring = False
                else:
                    in_docstring = False
            elif in_docstring:
                docstring_content.append(stripped)

            # Look for capability hints
            if "capability" in stripped.lower() or "can_handle" in stripped.lower():
                capabilities.extend(self._extract_capabilities_from_text(stripped))

            # Look for usage patterns
            if "usage:" in stripped.lower() or "example:" in stripped.lower():
                usage_pattern = stripped

        if docstring_content:
            description = " ".join(docstring_content).strip()

        if not capabilities:
            capabilities = self._extract_capabilities_from_text(content)

        return description, capabilities, usage_pattern

    def _parse_markdown_agent(self, content: str) -> tuple[str, list[str], str]:
        """Parse Markdown agent file for metadata."""
        lines = content.split("\n")
        description = ""
        capabilities = []
        usage_pattern = ""

        # Extract title and description
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                description = stripped[2:].strip()
                break

        # Look for capability sections
        in_capabilities = False
        for line in lines:
            stripped = line.strip()

            if "capabilities" in stripped.lower() or "features" in stripped.lower():
                in_capabilities = True
                continue

            if in_capabilities and stripped.startswith("-"):
                capabilities.append(stripped[1:].strip())
            elif in_capabilities and stripped.startswith("#"):
                in_capabilities = False

            if "usage" in stripped.lower() and ":" in stripped:
                usage_pattern = stripped

        if not capabilities:
            capabilities = self._extract_capabilities_from_text(content)

        return description, capabilities, usage_pattern

    def _parse_json_agent(self, content: str) -> tuple[str, list[str], str]:
        """Parse JSON agent file for metadata."""
        try:
            data = json.loads(content)

            description = data.get("description", "")
            capabilities = data.get("capabilities", [])
            usage_pattern = data.get("usage", "")

            return description, capabilities, usage_pattern

        except json.JSONDecodeError:
            return "", [], ""

    def _extract_capabilities_from_text(self, text: str) -> list[str]:
        """Extract capability keywords from text."""
        capability_keywords = [
            "coding",
            "programming",
            "development",
            "testing",
            "debug",
            "fix",
            "analysis",
            "analyze",
            "review",
            "documentation",
            "document",
            "explain",
            "refactor",
            "optimize",
            "improve",
            "research",
            "investigate",
            "find",
            "planning",
            "design",
            "architecture",
            "generation",
            "create",
            "build",
        ]

        capabilities = []
        text_lower = text.lower()

        for keyword in capability_keywords:
            if keyword in text_lower:
                capabilities.append(keyword)

        return list(set(capabilities))  # Remove duplicates

    def _extract_usage_pattern(self, text: str) -> str:
        """Extract usage pattern from text."""
        lines = text.split("\n")

        for line in lines:
            if "usage:" in line.lower() or "example:" in line.lower():
                return line.strip()

        return ""

    def _index_agent(self, agent: DiscoveredAgent, content_hash: str):
        """Index an agent in the Chroma collection."""
        # Create searchable text combining all agent information
        searchable_text = f"""
        Name: {agent.name}
        Description: {agent.description}
        Capabilities: {", ".join(agent.capabilities)}
        Usage: {agent.usage_pattern}
        Content: {agent.content[:1000]}  # Limit content for indexing
        """.strip()

        # Add to collection
        self.collection.add(
            documents=[searchable_text],
            metadatas=[
                {
                    "name": agent.name,
                    "path": agent.path,
                    "description": agent.description,
                    "capabilities": json.dumps(agent.capabilities),
                    "usage_pattern": agent.usage_pattern,
                    "content_hash": content_hash,
                    **agent.metadata,
                }
            ],
            ids=[f"agent_{content_hash}"],
        )

    def _get_content_hash(self, content: str) -> str:
        """Generate a hash for content to detect changes."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get_collection_stats(self) -> dict[str, int]:
        """Get statistics about the indexed agents."""
        count = self.collection.count()
        return {
            "total_agents": count,
            "agents_directory": str(self.agents_dir),
            "database_path": str(self.db_path),
        }
