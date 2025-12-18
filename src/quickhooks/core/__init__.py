"""Core processing components for QuickHooks framework.

This package provides the core parallel processing engine and related
utilities for executing hooks efficiently and at scale.
"""

from .processor import (
    ParallelProcessor,
    ProcessingMode,
    ProcessingPriority,
    ProcessingResult,
    ProcessingStats,
    ProcessingTask,
)

__all__ = [
    "ParallelProcessor",
    "ProcessingMode",
    "ProcessingPriority",
    "ProcessingResult",
    "ProcessingStats",
    "ProcessingTask",
]
