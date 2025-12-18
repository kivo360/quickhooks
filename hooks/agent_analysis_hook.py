#!/usr/bin/env python3
"""
Claude Code hook for automatic agent analysis and prompt modification.

This hook integrates with QuickHooks agent analysis to automatically:
1. Analyze user prompts for optimal agent usage
2. Discover relevant agents in ~/.claude/agents
3. Modify prompts to ensure agent usage
4. Configure Claude Code to use specific agents

Installation:
1. Add this hook to your Claude Code settings.json
2. Set GROQ_API_KEY environment variable
3. Ensure QuickHooks is installed with agent analysis dependencies

Usage:
This hook runs automatically on user prompt submission.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add QuickHooks to path if needed
try:
    from quickhooks.agent_analysis import AgentAnalysisRequest, AgentAnalyzer
except ImportError:
    # Try to add QuickHooks to path
    quickhooks_path = Path.home() / ".quickhooks" / "src"
    if quickhooks_path.exists():
        sys.path.insert(0, str(quickhooks_path))
        from quickhooks.agent_analysis import AgentAnalysisRequest, AgentAnalyzer
    else:
        print(
            "QuickHooks not found. Please install QuickHooks with agent analysis dependencies."
        )
        sys.exit(1)


class AgentAnalysisHook:
    """Hook that analyzes prompts and modifies them for optimal agent usage."""

    def __init__(self):
        """Initialize the agent analysis hook."""
        self.enabled = (
            os.getenv("QUICKHOOKS_AGENT_ANALYSIS_ENABLED", "true").lower() == "true"
        )
        self.model = os.getenv("QUICKHOOKS_AGENT_MODEL", "qwen/qwen3-32b")
        self.confidence_threshold = float(
            os.getenv("QUICKHOOKS_CONFIDENCE_THRESHOLD", "0.7")
        )
        self.min_similarity = float(os.getenv("QUICKHOOKS_MIN_SIMILARITY", "0.3"))

        if not self.enabled:
            return

        # Check for required API key
        if not os.getenv("GROQ_API_KEY"):
            print("Warning: GROQ_API_KEY not set. Agent analysis hook disabled.")
            self.enabled = False
            return

        try:
            self.analyzer = AgentAnalyzer(
                model_name=self.model, enable_agent_discovery=True
            )
        except Exception as e:
            print(f"Warning: Failed to initialize agent analyzer: {e}")
            self.enabled = False

    def should_analyze(self, user_input: str) -> bool:
        """
        Determine if the user input should be analyzed for agent usage.

        Args:
            user_input: The user's input

        Returns:
            True if analysis should be performed
        """
        if not self.enabled:
            return False

        # Skip very short inputs
        if len(user_input.strip()) < 10:
            return False

        # Skip if input already mentions agents explicitly
        return not (
            "agent" in user_input.lower()
            and ("use" in user_input.lower() or "with" in user_input.lower())
        )

    def analyze_and_modify_prompt(
        self, user_input: str, context: str = ""
    ) -> dict[str, Any]:
        """
        Analyze the user input and modify it for optimal agent usage.

        Args:
            user_input: The original user input
            context: Additional context if available

        Returns:
            Dictionary with analysis results and modified prompt
        """
        if not self.should_analyze(user_input):
            return {
                "modified": False,
                "original_prompt": user_input,
                "modified_prompt": user_input,
                "analysis": None,
                "reason": "Analysis skipped (disabled, too short, or already mentions agents)",
            }

        try:
            # Create analysis request
            request = AgentAnalysisRequest(
                prompt=user_input,
                context=context,
                confidence_threshold=self.confidence_threshold,
            )

            # Perform analysis
            response = self.analyzer.analyze_prompt_sync(request)

            # Use modified prompt if available and agents were discovered
            modified_prompt = user_input
            if response.claude_code_prompt_modification and response.discovered_agents:
                modified_prompt = response.claude_code_prompt_modification
            elif response.discovered_agents:
                # Create a basic modification if no specific one was generated
                top_agent = response.discovered_agents[0]
                modified_prompt = f"Use the '{top_agent.name}' agent to {user_input.lower()}. The agent is located at {top_agent.path} and specializes in: {', '.join(top_agent.capabilities)}."

            return {
                "modified": modified_prompt != user_input,
                "original_prompt": user_input,
                "modified_prompt": modified_prompt,
                "analysis": {
                    "recommendations": [
                        {
                            "agent_type": rec.agent_type.value,
                            "confidence": rec.confidence,
                            "reasoning": rec.reasoning,
                            "threshold_met": rec.threshold_met,
                            "priority": rec.priority,
                        }
                        for rec in response.recommendations
                    ],
                    "discovered_agents": [
                        {
                            "name": agent.name,
                            "path": agent.path,
                            "description": agent.description,
                            "capabilities": agent.capabilities,
                            "similarity_score": agent.similarity_score,
                        }
                        for agent in response.discovered_agents
                    ],
                    "analysis_summary": response.analysis_summary,
                    "multiple_agents_recommended": response.multiple_agents_recommended,
                    "total_tokens_used": response.total_tokens_used,
                },
                "reason": "Analysis completed successfully",
            }

        except Exception as e:
            print(f"Error during agent analysis: {e}")
            return {
                "modified": False,
                "original_prompt": user_input,
                "modified_prompt": user_input,
                "analysis": None,
                "reason": f"Analysis failed: {e!s}",
            }


# Global hook instance
_hook_instance = None


def get_hook_instance() -> AgentAnalysisHook:
    """Get or create the global hook instance."""
    global _hook_instance
    if _hook_instance is None:
        _hook_instance = AgentAnalysisHook()
    return _hook_instance


def on_user_prompt_submit(event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Hook function called when user submits a prompt.

    This is the main entry point for Claude Code integration.

    Args:
        event_data: Event data from Claude Code

    Returns:
        Modified event data with potentially updated prompt
    """
    hook = get_hook_instance()

    # Extract user input and context
    user_input = event_data.get("prompt", "")
    context = event_data.get("context", "")

    # Analyze and potentially modify the prompt
    result = hook.analyze_and_modify_prompt(user_input, context)

    # Log analysis results if requested
    if os.getenv("QUICKHOOKS_VERBOSE", "false").lower() == "true":
        print("[QuickHooks Agent Analysis]")
        print(f"  Modified: {result['modified']}")
        print(f"  Reason: {result['reason']}")
        if result["analysis"]:
            discovered = len(result["analysis"]["discovered_agents"])
            recommendations = len(result["analysis"]["recommendations"])
            print(f"  Discovered agents: {discovered}")
            print(f"  Recommendations: {recommendations}")
            print(f"  Tokens used: {result['analysis']['total_tokens_used']}")

    # Update the prompt if modified
    if result["modified"]:
        event_data["prompt"] = result["modified_prompt"]

        # Add metadata about the analysis
        if "metadata" not in event_data:
            event_data["metadata"] = {}

        event_data["metadata"]["quickhooks_agent_analysis"] = {
            "original_prompt": result["original_prompt"],
            "modified": True,
            "analysis_summary": result["analysis"]["analysis_summary"]
            if result["analysis"]
            else None,
            "discovered_agents": result["analysis"]["discovered_agents"]
            if result["analysis"]
            else [],
            "recommendations": result["analysis"]["recommendations"]
            if result["analysis"]
            else [],
        }

    return event_data


def main():
    """Main function for testing the hook."""

    print("QuickHooks Agent Analysis Hook Test")
    print("=" * 50)

    # Test the hook
    test_prompts = [
        "Write a Python function that sorts a list",
        "Help me debug this authentication error",
        "Create documentation for my API endpoints",
        "Use the coding expert agent to write Python code",  # Should skip
        "hi",  # Should skip (too short)
    ]

    hook = get_hook_instance()

    for prompt in test_prompts:
        print(f"\nTesting: {prompt}")
        result = hook.analyze_and_modify_prompt(prompt)

        print(f"  Modified: {result['modified']}")
        print(f"  Reason: {result['reason']}")

        if result["modified"]:
            print(f"  Original: {result['original_prompt']}")
            print(f"  Modified: {result['modified_prompt']}")

        if result["analysis"] and result["analysis"]["discovered_agents"]:
            print(
                f"  Discovered {len(result['analysis']['discovered_agents'])} agents:"
            )
            for agent in result["analysis"]["discovered_agents"][:2]:  # Show first 2
                print(f"    - {agent['name']}: {agent['description'][:50]}...")


if __name__ == "__main__":
    main()
