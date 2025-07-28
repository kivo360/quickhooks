"""Base hook class for the QuickHooks framework.

This module defines the abstract base class that all hooks must inherit from.
It provides the core functionality for hook execution, validation, and lifecycle management.
"""

import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from quickhooks.models import (
    HookInput,
    HookOutput, 
    HookStatus,
    ExecutionContext,
    HookResult,
    HookError,
)


class BaseHook(ABC):
    """Abstract base class for all hooks in the QuickHooks framework.
    
    This class provides the fundamental structure and lifecycle management
    for hooks. All concrete hook implementations must inherit from this class
    and implement the abstract execute method.
    
    Attributes:
        name: The name of the hook (defaults to class name)
        description: Description of what the hook does (defaults to class docstring)
        version: Version of the hook (defaults to "1.0.0")
        enabled: Whether the hook is enabled for execution (defaults to True)
    """
    
    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        enabled: bool = True
    ) -> None:
        """Initialize the base hook.
        
        Args:
            name: Custom name for the hook (defaults to class name)
            description: Custom description (defaults to class docstring)
            version: Version string for the hook
            enabled: Whether the hook is enabled for execution
        """
        self._name = name or self.__class__.__name__
        self._description = description or (self.__class__.__doc__ or "").strip().split('\n')[0]
        self._version = version
        self._enabled = enabled
    
    @property
    def name(self) -> str:
        """Get the hook name."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the hook description."""
        return self._description
    
    @property
    def version(self) -> str:
        """Get the hook version."""
        return self._version
    
    @property
    def enabled(self) -> bool:
        """Get whether the hook is enabled."""
        return self._enabled
    
    def __str__(self) -> str:
        """String representation of the hook."""
        return f"{self.name} v{self.version}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the hook."""
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}', enabled={self.enabled})"
    
    @abstractmethod
    async def execute(self, input_data: HookInput, context: ExecutionContext) -> HookOutput:
        """Execute the hook with the given input data and context.
        
        This is the main method that subclasses must implement to define
        their specific behavior.
        
        Args:
            input_data: The input data for the hook execution
            context: The execution context containing environment and metadata
            
        Returns:
            HookOutput: The result of the hook execution
            
        Raises:
            Any exception that occurs during execution will be caught
            and converted to a failed HookOutput by the run method.
        """
        pass
    
    async def validate_input(self, input_data: HookInput) -> bool:
        """Validate the input data before execution.
        
        Subclasses can override this method to implement custom validation logic.
        
        Args:
            input_data: The input data to validate
            
        Returns:
            bool: True if the input is valid, False otherwise
        """
        return True
    
    async def before_execute(self, input_data: HookInput, context: ExecutionContext) -> None:
        """Hook called before execute() is invoked.
        
        Subclasses can override this method to perform setup operations
        before the main execution.
        
        Args:
            input_data: The input data for the hook execution
            context: The execution context
        """
        pass
    
    async def after_execute(
        self, 
        input_data: HookInput, 
        context: ExecutionContext, 
        result: HookOutput
    ) -> None:
        """Hook called after execute() completes successfully.
        
        Subclasses can override this method to perform cleanup operations
        after the main execution.
        
        Args:
            input_data: The input data for the hook execution
            context: The execution context
            result: The result from the execute method
        """
        pass
    
    async def run(self, input_data: HookInput, context: ExecutionContext) -> HookResult:
        """Run the hook with full lifecycle management.
        
        This method orchestrates the complete hook execution lifecycle:
        1. Check if hook is enabled
        2. Validate input data
        3. Call before_execute hook
        4. Execute the main hook logic
        5. Call after_execute hook
        6. Handle any exceptions and create appropriate results
        
        Args:
            input_data: The input data for the hook execution
            context: The execution context
            
        Returns:
            HookResult: Complete result of the hook execution including timing
        """
        # Create initial result object
        result = HookResult(
            hook_id=context.hook_id,
            status=HookStatus.PENDING,
            input_data=input_data,
            output_data=None,
            execution_context=context
        )
        
        try:
            # Check if hook is enabled
            if not self.enabled:
                output = HookOutput(
                    status=HookStatus.CANCELLED,
                    data={},
                    message="Hook is disabled and will not execute"
                )
                result.status = HookStatus.CANCELLED
                result.output_data = output
                return result
            
            # Validate input data
            if not await self.validate_input(input_data):
                error = HookError(
                    code="VALIDATION_ERROR",
                    message="Input validation failed",
                    details={"input_data": input_data.model_dump()}
                )
                output = HookOutput(
                    status=HookStatus.FAILED,
                    data={},
                    error=error,
                    message="Input validation failed"
                )
                result.status = HookStatus.FAILED
                result.output_data = output
                return result
            
            # Update status to running
            result.status = HookStatus.RUNNING
            
            # Record start time
            start_time = time.perf_counter()
            
            try:
                # Call before_execute hook
                await self.before_execute(input_data, context)
                
                # Execute the main hook logic
                output = await self.execute(input_data, context)
                
                # Calculate execution time
                execution_time = time.perf_counter() - start_time
                output.execution_time = execution_time
                
                # Call after_execute hook
                await self.after_execute(input_data, context, output)
                
                # Update result with successful output
                result.status = output.status
                result.output_data = output
                
            except Exception as e:
                # Calculate execution time even for failed executions
                execution_time = time.perf_counter() - start_time
                
                # Create error information
                error = HookError(
                    code="EXECUTION_ERROR",
                    message=f"Hook execution failed: {str(e)}",
                    details={
                        "exception_type": type(e).__name__,
                        "exception_args": e.args,
                        "traceback": traceback.format_exc()
                    }
                )
                
                # Create failed output
                output = HookOutput(
                    status=HookStatus.FAILED,
                    data={},
                    error=error,
                    message=f"Hook execution failed: {str(e)}",
                    execution_time=execution_time
                )
                
                # Update result with failed output
                result.status = HookStatus.FAILED
                result.output_data = output
                
        except Exception as e:
            # Handle any unexpected exceptions in the lifecycle itself
            error = HookError(
                code="LIFECYCLE_ERROR",
                message=f"Hook lifecycle error: {str(e)}",
                details={
                    "exception_type": type(e).__name__,
                    "exception_args": e.args,
                    "traceback": traceback.format_exc()
                }
            )
            
            output = HookOutput(
                status=HookStatus.FAILED,
                data={},
                error=error,
                message=f"Hook lifecycle error: {str(e)}"
            )
            
            result.status = HookStatus.FAILED
            result.output_data = output
        
        return result
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about this hook.
        
        Returns:
            Dict containing hook metadata including name, description,
            version, enabled status, and class information.
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "class_name": self.__class__.__name__,
            "module": self.__class__.__module__
        }