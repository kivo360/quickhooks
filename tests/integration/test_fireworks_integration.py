"""Test script to verify Fireworks AI integration with pydantic-ai."""

import asyncio
import os

from quickhooks.agent_analysis.analyzer import AgentAnalyzer
from quickhooks.agent_analysis.types import AgentAnalysisRequest
from quickhooks.config import get_config


async def test_fireworks_integration() -> None:
    """Test the Fireworks AI integration."""
    print("=" * 60)
    print("Testing Fireworks AI Integration with pydantic-ai")
    print("=" * 60)

    # Check configuration
    config = get_config()
    print("\nConfiguration loaded:")
    print("  AI Provider: Fireworks AI")
    print(f"  LLM Model: {config.ai.llm}")
    print(f"  VLM Model: {config.ai.vlm}")
    print(f"  Base URL: {config.ai.base_url}")
    print(f"  Tool Calls Enabled: {config.ai.enable_tool_calls}")
    print(f"  Temperature: {config.ai.temperature}")

    # Check API key
    api_key = os.getenv("FIREWORKS_API_KEY")
    if api_key:
        print(f"  API Key: {'*' * 8}{api_key[-4:]}")
    else:
        print("  WARNING: FIREWORKS_API_KEY not set!")
        return

    # Initialize analyzer
    print("\nInitializing AgentAnalyzer with Fireworks AI...")
    try:
        analyzer = AgentAnalyzer()
        print("  ✓ AgentAnalyzer initialized successfully")
    except Exception as e:
        print(f"  ✗ Failed to initialize AgentAnalyzer: {e}")
        return

    # Create test request
    print("\nCreating test analysis request...")
    request = AgentAnalysisRequest(
        prompt="Help me write a Python function to calculate fibonacci numbers",
        context="I need a fast and efficient implementation",
        confidence_threshold=0.7,
    )

    # Run analysis
    print("\nRunning agent analysis with Fireworks AI...")
    try:
        response = await analyzer.analyze_prompt(request)
        print("  ✓ Analysis completed successfully")

        print("\n" + "=" * 60)
        print("Analysis Results:")
        print("=" * 60)
        print(f"\nRecommendations: {len(response.recommended_agents)} agent(s)")
        for i, agent in enumerate(response.recommended_agents, 1):
            print(f"\n{i}. {agent.agent_type.value.upper()}")
            print(f"   Confidence: {agent.confidence:.2%}")
            print(f"   Priority: {agent.priority}")
            print(f"   Reasoning: {agent.reasoning}")

        print(f"\nMultiple Agents Recommended: {response.multiple_agents_recommended}")
        print(f"Threshold Met: {response.threshold_met}")

        if response.claude_code_prompt_modification:
            print("\nClaude Code Prompt Modification:")
            print(f"  {response.claude_code_prompt_modification[:200]}...")

        print(f"\nTotal Tokens Used: {response.total_tokens_used}")

        print("\n" + "=" * 60)
        print("✓ Fireworks AI integration test PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"  ✗ Analysis failed: {e}")
        print("\n" + "=" * 60)
        print("✗ Fireworks AI integration test FAILED")
        print("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(test_fireworks_integration())
