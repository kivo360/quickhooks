from quickhooks.hooks.base import BaseHook
from quickhooks.models import ExecutionContext, HookInput, HookOutput, HookStatus


class TestHook(BaseHook):
    """A test hook for validation"""

    name = "test_hook"
    description = "A test hook for validation"
    version = "1.0.0"

    async def execute(
        self, input_data: HookInput, context: ExecutionContext
    ) -> HookOutput:
        """Process the hook input and return output."""
        # TODO: Implement hook logic here
        return HookOutput(
            status=HookStatus.SUCCESS, data={}, message="Hook processed successfully"
        )
