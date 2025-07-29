"""Type definitions for agent analysis functionality."""

from enum import Enum

from pydantic import BaseModel, Field


class AgentCapability(str, Enum):
    """Enumeration of different agent capabilities."""

    CODING = "coding"
    ANALYSIS = "analysis"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    CODE_REVIEW = "code_review"
    RESEARCH = "research"
    PLANNING = "planning"
    GENERATION = "generation"


class AgentRecommendation(BaseModel):
    """Recommendation for using specific agents."""

    agent_type: AgentCapability = Field(description="Type of agent recommended")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score from 0 to 1"
    )
    reasoning: str = Field(description="Explanation for why this agent is recommended")
    threshold_met: bool = Field(description="Whether the confidence threshold is met")
    priority: int = Field(
        ge=1, le=10, description="Priority ranking (1=highest, 10=lowest)"
    )


class ContextChunk(BaseModel):
    """Represents a chunk of context with metadata."""

    content: str = Field(description="The actual content of the chunk")
    chunk_type: str = Field(description="Type of chunk (start, middle, end)")
    token_count: int = Field(description="Estimated token count for this chunk")
    position: int = Field(description="Position in the original context")


class AgentAnalysisRequest(BaseModel):
    """Request model for agent analysis."""

    prompt: str = Field(description="The user's prompt to analyze")
    context: str | None = Field(
        default=None, description="Additional context if available"
    )
    max_context_tokens: int = Field(
        default=128000, description="Maximum context length in tokens"
    )
    confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class DiscoveredAgentInfo(BaseModel):
    """Information about a discovered agent from the filesystem."""

    name: str = Field(description="Name of the discovered agent")
    path: str = Field(description="File path to the agent")
    description: str = Field(description="Description of what the agent does")
    capabilities: list[str] = Field(description="List of agent capabilities")
    similarity_score: float = Field(
        ge=0.0, le=1.0, description="Similarity score to the prompt"
    )
    usage_pattern: str = Field(description="How to use this agent")


class AgentAnalysisResponse(BaseModel):
    """Response model for agent analysis."""

    recommendations: list[AgentRecommendation] = Field(
        description="List of agent recommendations"
    )
    discovered_agents: list[DiscoveredAgentInfo] = Field(
        default=[], description="Relevant agents found in filesystem"
    )
    context_used: list[ContextChunk] = Field(
        description="Context chunks that were analyzed"
    )
    total_tokens_used: int = Field(description="Total tokens used in the analysis")
    analysis_summary: str = Field(description="Summary of the analysis performed")
    multiple_agents_recommended: bool = Field(
        description="Whether multiple agents are recommended"
    )
    claude_code_prompt_modification: str | None = Field(
        default=None, description="Suggested prompt modification for Claude Code"
    )

    @property
    def top_recommendation(self) -> AgentRecommendation | None:
        """Get the highest priority recommendation that meets the threshold."""
        qualified = [r for r in self.recommendations if r.threshold_met]
        return min(qualified, key=lambda x: x.priority) if qualified else None

    @property
    def qualified_recommendations(self) -> list[AgentRecommendation]:
        """Get all recommendations that meet the confidence threshold."""
        return [r for r in self.recommendations if r.threshold_met]


class TokenUsage(BaseModel):
    """Token usage tracking."""

    input_tokens: int = Field(description="Number of input tokens")
    output_tokens: int = Field(description="Number of output tokens")
    total_tokens: int = Field(description="Total tokens used")

    @property
    def cost_estimate(self) -> float:
        """Rough cost estimate based on typical Groq pricing."""
        # Using rough Groq pricing estimates (adjust as needed)
        input_cost_per_1k = 0.0001  # $0.0001 per 1K input tokens
        output_cost_per_1k = 0.0002  # $0.0002 per 1K output tokens

        input_cost = (self.input_tokens / 1000) * input_cost_per_1k
        output_cost = (self.output_tokens / 1000) * output_cost_per_1k

        return input_cost + output_cost
