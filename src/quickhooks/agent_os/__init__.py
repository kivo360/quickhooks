"""Agent OS integration for QuickHooks.

This module provides seamless integration between QuickHooks and Agent OS,
enabling spec-driven agentic development workflows within the QuickHooks
framework.
"""

from .executor import AgentOSExecutor
from .hooks import AgentOSHook
from .instruction_parser import InstructionParser
from .workflow_manager import WorkflowManager

__all__ = [
    "AgentOSExecutor",
    "AgentOSHook",
    "InstructionParser",
    "WorkflowManager",
]
