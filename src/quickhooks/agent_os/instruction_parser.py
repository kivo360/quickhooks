"""Agent OS instruction parser for QuickHooks.

This module parses and processes Agent OS instruction files,
converting them into executable workflows within QuickHooks.
"""

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ProcessFlow(BaseModel):
    """Represents a process flow from Agent OS instructions."""

    steps: list[dict[str, Any]] = Field(default_factory=list)
    pre_flight_check: str | None = None
    post_flight_check: str | None = None


class AgentOSInstruction(BaseModel):
    """Represents a parsed Agent OS instruction."""

    description: str
    globs: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0"
    encoding: str = "UTF-8"
    process_flow: ProcessFlow = Field(default_factory=ProcessFlow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_content: str = ""


class InstructionParser:
    """Parses Agent OS instruction files into executable workflows."""

    def __init__(self, agent_os_path: Path | None = None):
        """
        Initialize the instruction parser.

        Args:
            agent_os_path: Path to Agent OS installation (defaults to ~/.agent-os)
        """
        self.agent_os_path = agent_os_path or Path.home() / ".agent-os"
        self.instructions_path = self.agent_os_path / "commands"
        self.commands_path = self.agent_os_path / "commands"
        self.agents_path = self.agent_os_path / "agents"

    def parse_instruction_file(self, file_path: Path) -> AgentOSInstruction:
        """
        Parse an Agent OS instruction file.

        Args:
            file_path: Path to the instruction file

        Returns:
            Parsed instruction object
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_instruction_content(content, file_path)

    def parse_instruction_content(
        self, content: str, source_path: Path | None = None
    ) -> AgentOSInstruction:
        """
        Parse Agent OS instruction content.

        Args:
            content: Raw instruction content
            source_path: Optional source file path for context

        Returns:
            Parsed instruction object
        """
        # Extract description from first non-empty line
        lines = content.strip().split("\n")
        description = lines[0] if lines else "No description available"

        # Extract sub-instructions (references to other files)
        sub_instructions = []
        step_matches = re.finditer(r"{{[^}]*\.md}}", content)
        for match in step_matches:
            sub_instructions.append(match.group(0))

        # Create a simple process flow with sub-instructions as steps
        steps = []
        for i, instruction_ref in enumerate(sub_instructions):
            # Clean up the reference (remove {{ }} and @ references)
            clean_ref = instruction_ref.replace("{{", "").replace("}}", "").strip()

            steps.append(
                {
                    "number": i + 1,
                    "subagent": "agent",
                    "name": f"step_{i + 1}",
                    "title": f"Step {i + 1}",
                    "content": clean_ref,
                    "data_sources": {},
                    "error_template": None,
                }
            )

        # Sort steps by number
        steps.sort(key=lambda x: x["number"])

        return AgentOSInstruction(
            description=description,
            globs={},
            version="1.0",
            encoding="UTF-8",
            process_flow=ProcessFlow(
                steps=steps, pre_flight_check=None, post_flight_check=None
            ),
            metadata={
                "source_path": str(source_path) if source_path else None,
                "sub_instructions": sub_instructions,
            },
            raw_content=content,
        )

    def _parse_globs(self, globs_str: str) -> dict[str, Any]:
        """Parse the globs configuration from frontmatter."""
        try:
            import json

            return json.loads(globs_str)
        except json.JSONDecodeError:
            return {}

    def _extract_process_flow(self, content: str) -> ProcessFlow:
        """Extract process flow from instruction content."""
        process_flow_match = re.search(
            r"<process_flow>(.*?)</process_flow>", content, re.DOTALL
        )
        if not process_flow_match:
            return ProcessFlow()

        flow_content = process_flow_match.group(1)

        # Extract pre-flight check
        pre_flight_match = re.search(
            r"<pre_flight_check>(.*?)</pre_flight_check>", flow_content, re.DOTALL
        )
        pre_flight_check = (
            pre_flight_match.group(1).strip() if pre_flight_match else None
        )

        # Extract post-flight check
        post_flight_match = re.search(
            r"<post_flight_check>(.*?)</post_flight_check>", flow_content, re.DOTALL
        )
        post_flight_check = (
            post_flight_match.group(1).strip() if post_flight_match else None
        )

        # Extract steps
        steps = []
        step_matches = re.finditer(
            r'<step[^>]*number="(\d+)"[^>]*subagent="([^"]*)"[^>]*name="([^"]*)"[^>]*>(.*?)</step>',
            flow_content,
            re.DOTALL,
        )

        for match in step_matches:
            step_number = int(match.group(1))
            subagent = match.group(2)
            name = match.group(3)
            step_content = match.group(4)

            # Extract title
            title_match = re.search(r"### Step \d+: (.+)", step_content)
            title = title_match.group(1) if title_match else name

            # Extract data sources
            data_sources = self._extract_data_sources(step_content)

            # Extract error template
            error_template = self._extract_error_template(step_content)

            steps.append(
                {
                    "number": step_number,
                    "subagent": subagent,
                    "name": name,
                    "title": title,
                    "content": step_content.strip(),
                    "data_sources": data_sources,
                    "error_template": error_template,
                }
            )

        # Sort steps by number
        steps.sort(key=lambda x: x["number"])

        return ProcessFlow(
            steps=steps,
            pre_flight_check=pre_flight_check,
            post_flight_check=post_flight_check,
        )

    def _extract_data_sources(self, step_content: str) -> dict[str, Any]:
        """Extract data sources from step content."""
        data_sources_match = re.search(
            r"<data_sources>(.*?)</data_sources>", step_content, re.DOTALL
        )
        if not data_sources_match:
            return {}

        sources_content = data_sources_match.group(1)

        # Extract primary source
        primary_match = re.search(r"<primary>(.*?)</primary>", sources_content)
        primary = primary_match.group(1).strip() if primary_match else None

        # Extract fallback sequence
        fallback_sequence = []
        fallback_matches = re.finditer(r"\d+\.\s*(.+)", sources_content)
        for match in fallback_matches:
            fallback_sequence.append(match.group(1).strip())

        return {"primary": primary, "fallback_sequence": fallback_sequence}

    def _extract_error_template(self, step_content: str) -> str | None:
        """Extract error template from step content."""
        error_template_match = re.search(
            r"<error_template>(.*?)</error_template>", step_content, re.DOTALL
        )
        return error_template_match.group(1).strip() if error_template_match else None

    def list_available_instructions(self, category: str | None = None) -> list[Path]:
        """
        List available Agent OS instruction files.

        Args:
            category: Optional category filter ('core', 'meta', 'single-agent', 'multi-agent')

        Returns:
            List of instruction file paths
        """
        instructions_dir = self.instructions_path
        if category:
            # Look for category in commands
            category_dir = instructions_dir / category
            if category_dir.exists():
                return list(category_dir.rglob("*.md"))
            return []

        if not instructions_dir.exists():
            return []

        # Search all command directories for .md files
        return list(instructions_dir.rglob("*.md"))

    def load_instruction(
        self, name: str, category: str | None = None
    ) -> AgentOSInstruction | None:
        """
        Load an Agent OS instruction by name.

        Args:
            name: Name of the instruction (without .md extension)
            category: Optional category ('core', 'meta', 'single-agent', 'multi-agent')

        Returns:
            Parsed instruction or None if not found
        """
        instructions_dir = self.instructions_path

        # Try to find the instruction file
        if category:
            # Look in specific category directory
            instruction_file = instructions_dir / category / f"{name}.md"
            if instruction_file.exists():
                return self.parse_instruction_file(instruction_file)
        else:
            # Search recursively for the instruction
            for instruction_file in instructions_dir.rglob(f"{name}.md"):
                return self.parse_instruction_file(instruction_file)

        return None

    def resolve_agent_reference(self, reference: str) -> Path | None:
        """
        Resolve an agent reference to a file path.

        Args:
            reference: Agent reference (e.g., @~/.agent-os/agents/file-creator.md)

        Returns:
            Path to the agent file or None if not found
        """
        # Handle Agent OS agent references
        if reference.startswith("@~/.agent-os/agents/"):
            agent_name = reference.replace("@~/.agent-os/agents/", "").replace(
                ".md", ""
            )
            agent_path = self.agents_path / f"{agent_name}.md"
            return agent_path if agent_path.exists() else None

        # Handle instruction references
        if reference.startswith("@~/.agent-os/instructions/"):
            instruction_path = self.agent_os_path / reference[1:]  # Remove @
            return instruction_path if instruction_path.exists() else None

        return None
