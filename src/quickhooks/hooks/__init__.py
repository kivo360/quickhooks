"""Hooks module for QuickHooks framework.

This module contains the base hook class and hook implementations,
including parallel processing capabilities.
"""

from .base import BaseHook
from .parallel import DataParallelHook, MultiHookProcessor, ParallelHook, PipelineHook

__all__ = [
    "BaseHook",
    "DataParallelHook",
    "MultiHookProcessor",
    "ParallelHook",
    "PipelineHook",
]
