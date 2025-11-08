"""Agent analysis using Pydantic AI and Fireworks AI."""

import os

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.fireworks import FireworksProvider

from ..config import get_config
from .agent_discovery import AgentDiscovery
from .context_manager import ContextManager
from .types import (
    AgentAnalysisRequest,
    AgentAnalysisResponse,
    AgentCapability,
    DiscoveredAgentInfo,
)


class AgentAnalyzer:
    """Analyzes prompts to determine appropriate agent usage with Pydantic AI and Fireworks AI."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        enable_agent_discovery: bool = True,
    ):
        """
        Initialize the agent analyzer.

        Args:
            api_key: Fireworks API key (uses FIREWORKS_API_KEY env var if not provided)
            model_name: Fireworks model to use for analysis (uses FIREWORKS_LLM env var if not provided)
            base_url: Fireworks API base URL (uses config default if not provided)
            enable_agent_discovery: Whether to enable discovery of local agents
        """
        # Get configuration
        config = get_config()

        # Use provided values or fall back to config/env
        api_key = api_key or config.ai.api_key or os.getenv("FIREWORKS_API_KEY")
        if not api_key:
            raise ValueError(
                "FIREWORKS_API_KEY environment variable must be set or api_key must be provided"
            )

        model_name = model_name or config.ai.llm

        # Create Fireworks provider with the API key
        # pydantic-ai has built-in Fireworks support via FireworksProvider
        fireworks_provider = FireworksProvider(api_key=api_key)

        # Create OpenAI-compatible model with the Fireworks provider
        self.model = OpenAIModel(
            model_name,
            provider=fireworks_provider,
        )
        self.context_manager = ContextManager()

        # Initialize agent discovery if enabled
        self.agent_discovery = AgentDiscovery() if enable_agent_discovery else None

        # Create the Pydantic AI agent for analysis with tool calls enabled
        self.agent = Agent(
            self.model,
            output_type=AgentAnalysisResponse,
            system_prompt=self._get_system_prompt(),
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for agent analysis."""
        return """You are an expert AI agent classifier and analyzer. Your job is to analyze user prompts and determine which types of AI agents would be most effective for handling the request.

AGENT CAPABILITIES:
- CODING: Writing, modifying, or generating code
- ANALYSIS: Analyzing existing code, data, or systems
- TESTING: Creating tests, debugging, or quality assurance
- DOCUMENTATION: Writing docs, comments, or explanations
- DEBUGGING: Finding and fixing bugs or issues
- REFACTORING: Improving code structure and quality
- CODE_REVIEW: Reviewing code for best practices and issues
- RESEARCH: Gathering information or investigating topics
- PLANNING: Strategic planning, architecture, or design
- GENERATION: Creating content, templates, or boilerplate

DISCOVERED LOCAL AGENTS:
When specific agents are discovered in the user's ~/.claude/agents directory, they will be listed with their descriptions and capabilities. Consider these agents as highly relevant options if they match the user's request.

ANALYSIS CRITERIA:
1. Analyze the prompt for keywords, intent, and complexity
2. If local agents are discovered, evaluate their relevance first
3. Consider if multiple agents working together would be beneficial
4. Assign confidence scores (0.0 to 1.0) based on how well each agent matches
5. Only recommend agents with confidence >= threshold
6. Rank by priority (1=highest priority, 10=lowest)
7. Provide clear reasoning for each recommendation

CLAUDE CODE INTEGRATION:
Generate a claude_code_prompt_modification that includes:
1. A revised version of the original prompt that mentions specific agents
2. Clear instructions to use the recommended agents
3. Format: "Use the [agent_name] agent to [original_prompt]. The agent is specifically designed for [agent_description]."

RESPONSE FORMAT:
- Always return valid AgentAnalysisResponse with all required fields
- Include discovered_agents list with relevant local agents
- Include detailed reasoning for each recommendation
- Set threshold_met=True only if confidence >= user's threshold
- Provide a comprehensive analysis_summary
- Set multiple_agents_recommended=True if 2+ agents are beneficial
- Generate claude_code_prompt_modification to guide Claude Code to use specific agents

Focus on practical, actionable recommendations that would genuinely help with the user's request."""

    async def analyze_prompt(
        self, request: AgentAnalysisRequest
    ) -> AgentAnalysisResponse:
        """
        Analyze a prompt to determine appropriate agent usage.

        Args:
            request: The analysis request containing prompt and parameters

        Returns:
            Analysis response with agent recommendations
        """
        # Discover relevant local agents
        discovered_agents = []
        if self.agent_discovery:
            try:
                # First ensure agents are indexed
                self.agent_discovery.scan_and_index_agents()

                # Find relevant agents
                relevant_agents = self.agent_discovery.find_relevant_agents(
                    prompt=request.prompt,
                    context=request.context or "",
                    limit=5,
                    min_similarity=0.3,
                )

                # Convert to response format
                discovered_agents = [
                    DiscoveredAgentInfo(
                        name=agent.name,
                        path=agent.path,
                        description=agent.description,
                        capabilities=agent.capabilities,
                        similarity_score=agent.similarity_score,
                        usage_pattern=agent.usage_pattern,
                    )
                    for agent in relevant_agents
                ]
            except Exception as e:
                print(f"Warning: Agent discovery failed: {e}")

        # Manage context chunking
        context_chunks = self.context_manager.chunk_context(
            context=request.context or "", prompt=request.prompt
        )

        # Build the analysis prompt
        analysis_prompt = self._build_analysis_prompt(
            request, context_chunks, discovered_agents
        )

        # Run the agent analysis
        result = await self.agent.run(analysis_prompt)

        # Update the response with context information
        response = result.output
        response.context_used = context_chunks
        response.discovered_agents = discovered_agents
        response.total_tokens_used = self.context_manager.calculate_total_tokens(
            context_chunks, request.prompt
        )

        return response

    def analyze_prompt_sync(
        self, request: AgentAnalysisRequest
    ) -> AgentAnalysisResponse:
        """
        Synchronous version of analyze_prompt.

        Args:
            request: The analysis request containing prompt and parameters

        Returns:
            Analysis response with agent recommendations
        """
        # Discover relevant local agents
        discovered_agents = []
        if self.agent_discovery:
            try:
                # First ensure agents are indexed
                self.agent_discovery.scan_and_index_agents()

                # Find relevant agents
                relevant_agents = self.agent_discovery.find_relevant_agents(
                    prompt=request.prompt,
                    context=request.context or "",
                    limit=5,
                    min_similarity=0.3,
                )

                # Convert to response format
                discovered_agents = [
                    DiscoveredAgentInfo(
                        name=agent.name,
                        path=agent.path,
                        description=agent.description,
                        capabilities=agent.capabilities,
                        similarity_score=agent.similarity_score,
                        usage_pattern=agent.usage_pattern,
                    )
                    for agent in relevant_agents
                ]
            except Exception as e:
                print(f"Warning: Agent discovery failed: {e}")

        # Manage context chunking
        context_chunks = self.context_manager.chunk_context(
            context=request.context or "", prompt=request.prompt
        )

        # Build the analysis prompt
        analysis_prompt = self._build_analysis_prompt(
            request, context_chunks, discovered_agents
        )

        # Run the agent analysis
        result = self.agent.run_sync(analysis_prompt)

        # Update the response with context information
        response = result.output
        response.context_used = context_chunks
        response.discovered_agents = discovered_agents
        response.total_tokens_used = self.context_manager.calculate_total_tokens(
            context_chunks, request.prompt
        )

        return response

    def _build_analysis_prompt(
        self,
        request: AgentAnalysisRequest,
        context_chunks: list,
        discovered_agents: list[DiscoveredAgentInfo] = None,
    ) -> str:
        """Build the analysis prompt from request and context chunks."""
        prompt_parts = [
            "ANALYZE THIS PROMPT FOR AGENT RECOMMENDATIONS:",
            f"User Prompt: {request.prompt}",
            f"Confidence Threshold: {request.confidence_threshold}",
            "",
        ]

        # Add discovered agents information
        if discovered_agents:
            prompt_parts.append("DISCOVERED LOCAL AGENTS (High Priority):")
            for agent in discovered_agents:
                prompt_parts.append(f"Agent: {agent.name}")
                prompt_parts.append(f"  Description: {agent.description}")
                prompt_parts.append(f"  Capabilities: {', '.join(agent.capabilities)}")
                prompt_parts.append(f"  Similarity Score: {agent.similarity_score:.2f}")
                prompt_parts.append(f"  Usage: {agent.usage_pattern}")
                prompt_parts.append(f"  Path: {agent.path}")
                prompt_parts.append("")

        if context_chunks:
            prompt_parts.append("CONTEXT INFORMATION:")
            for i, chunk in enumerate(context_chunks):
                prompt_parts.append(f"Context Chunk {i + 1} ({chunk.chunk_type}):")
                prompt_parts.append(chunk.content)
                prompt_parts.append("")

        prompt_parts.extend(
            [
                "Please analyze this prompt and provide agent recommendations with:",
                "1. Prioritize discovered local agents if they match the task",
                "2. Appropriate agent types and confidence scores",
                "3. Clear reasoning for each recommendation",
                "4. Priority rankings (local agents should get higher priority)",
                "5. Whether multiple agents would be beneficial",
                "6. Generate a claude_code_prompt_modification for guaranteed agent usage",
                "7. Comprehensive analysis summary",
            ]
        )

        return "\n".join(prompt_parts)

    @property
    def available_capabilities(self) -> list[str]:
        """Get list of available agent capabilities."""
        return [capability.value for capability in AgentCapability]
