"""Agent OS integration for QuickHooks.

This module provides seamless integration between QuickHooks and Agent OS,
enabling spec-driven agentic development workflows within the QuickHooks
framework.
"""

from .executor import AgentOSExecutor
from .instruction_parser import InstructionParser
from .workflow_manager import WorkflowManager
from .hooks import AgentOSHook

__all__ = [
    "AgentOSExecutor",
    "InstructionParser",
    "WorkflowManager",
    "AgentOSHook",
]