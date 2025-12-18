#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
#   "quickhooks>=0.1.0",
#   "groq>=0.13.0",
#   "pydantic-ai-slim[groq]>=0.0.49",
#   "chromadb>=0.4.0",
#   "sentence-transformers>=2.2.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Agent Analysis hook for Claude Code using PEP 723 inline dependencies.

This hook automatically:
1. Analyzes user prompts for optimal agent usage
2. Discovers relevant agents in ~/.claude/agents
3. Modifies prompts to ensure agent usage
4. Configures Claude Code to use specific agents

Configuration via environment variables:
- GROQ_API_KEY (required): Your Groq API key
- QUICKHOOKS_AGENT_ANALYSIS_ENABLED (default: "true"): Enable/disable hook
- QUICKHOOKS_AGENT_MODEL (default: "qwen/qwen3-32b"): Groq model to use
- QUICKHOOKS_CONFIDENCE_THRESHOLD (default: "0.7"): Confidence threshold
- QUICKHOOKS_MIN_SIMILARITY (default: "0.3"): Minimum similarity score
- QUICKHOOKS_VERBOSE (default: "false"): Verbose logging

Usage in Claude Code settings.json:
{
  "hooks": {
    "user-prompt-submit": {
      "command": "uv run -s /path/to/.claude/hooks/agent_analysis_hook_pep723.py",
      "enabled": true
    }
  },
  "environment": {
    "GROQ_API_KEY": "your_api_key_here",
    "QUICKHOOKS_AGENT_ANALYSIS_ENABLED": "true",
    "QUICKHOOKS_VERBOSE": "false"
  }
}
"""

import json
import os
import sys
from typing import Any


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
        self.verbose = os.getenv("QUICKHOOKS_VERBOSE", "false").lower() == "true"

        if not self.enabled:
            return

        # Check for required API key
        if not os.getenv("GROQ_API_KEY"):
            print(
                "[QuickHooks] Warning: GROQ_API_KEY not set. Agent analysis disabled.",
                file=sys.stderr,
            )
            self.enabled = False
            return

        try:
            from quickhooks.agent_analysis import AgentAnalyzer

            self.analyzer = AgentAnalyzer(
                model_name=self.model, enable_agent_discovery=True
            )
        except Exception as e:
            print(
                f"[QuickHooks] Warning: Failed to initialize analyzer: {e}",
                file=sys.stderr,
            )
            self.enabled = False

    def should_analyze(self, user_input: str) -> bool:
        """
        Determine if the user input should be analyzed.

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
        lower_input = user_input.lower()
        return not (
            "agent" in lower_input and ("use" in lower_input or "with" in lower_input)
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
                "reason": "Analysis skipped",
            }

        try:
            from quickhooks.agent_analysis import AgentAnalysisRequest

            # Create analysis request
            request = AgentAnalysisRequest(
                prompt=user_input,
                context=context,
                confidence_threshold=self.confidence_threshold,
            )

            # Perform analysis
            response = self.analyzer.analyze_prompt_sync(request)

            # Use modified prompt if available
            modified_prompt = user_input
            if response.claude_code_prompt_modification and response.discovered_agents:
                modified_prompt = response.claude_code_prompt_modification
            elif response.discovered_agents:
                top_agent = response.discovered_agents[0]
                modified_prompt = (
                    f"Use the '{top_agent.name}' agent to {user_input.lower()}"
                )

            return {
                "modified": modified_prompt != user_input,
                "original_prompt": user_input,
                "modified_prompt": modified_prompt,
                "analysis": {
                    "discovered_agents": len(response.discovered_agents),
                    "recommendations": len(response.recommendations),
                    "tokens_used": response.total_tokens_used,
                },
                "reason": "Analysis completed",
            }

        except Exception as e:
            print(f"[QuickHooks] Error during analysis: {e}", file=sys.stderr)
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


def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process user prompt submit event.

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

    # Log analysis results if verbose
    if hook.verbose:
        print(
            f"[QuickHooks Agent Analysis] Modified: {result['modified']}",
            file=sys.stderr,
        )
        print(
            f"[QuickHooks Agent Analysis] Reason: {result['reason']}", file=sys.stderr
        )
        if result["analysis"]:
            print(
                f"[QuickHooks Agent Analysis] Discovered: {result['analysis']['discovered_agents']} agents",
                file=sys.stderr,
            )
            print(
                f"[QuickHooks Agent Analysis] Tokens: {result['analysis']['tokens_used']}",
                file=sys.stderr,
            )

    # Return response
    response = {
        "continue": True,
        "suppressOutput": False,
    }

    if result["modified"]:
        response["message"] = (
            f"Prompt modified to use {result['analysis']['discovered_agents']} discovered agent(s)"
        )

    return response


def main() -> None:
    """Main entry point for the hook."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Process the event
        response = process_hook_event(input_data)

        # Output JSON response
        print(json.dumps(response))

        sys.exit(0)

    except Exception as e:
        print(f"[QuickHooks Agent Analysis] Error: {e}", file=sys.stderr)
        # Fail-safe: allow execution to continue
        print(json.dumps({"continue": True, "suppressOutput": False}))
        sys.exit(0)


if __name__ == "__main__":
    main()
