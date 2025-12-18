#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
#   "quickhooks>=0.1.0",
# ]
# requires-python = ">=3.12"
# ///

"""Test hook for verification"""

from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput


class TestHook(BaseHook):
    """Test hook for verification"""

    name = "test-hook"
    description = "Test hook for verification"
    version = "1.0.0"

    def process(self, hook_input: HookInput) -> HookOutput:
        """Process the hook input and return output."""
        # TODO: Implement hook logic here
        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Hook processed successfully",
        )
