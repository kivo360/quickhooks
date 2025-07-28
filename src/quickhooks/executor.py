"""Hook execution engine for the QuickHooks framework.

This module provides the core HookExecutor class responsible for executing
external hook scripts with timeout handling, JSON communication, and comprehensive
error management.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class ExecutionError(Exception):
    """Exception raised when hook execution fails.
    
    This includes timeouts, process failures, JSON parsing errors,
    and any other execution-related issues.
    """
    pass


class PreToolUseInput(BaseModel):
    """Input data structure for pre-tool-use hooks.
    
    This represents the data passed to hooks before tool execution,
    containing the tool name and its input parameters.
    """
    
    tool_name: str = Field(..., description="Name of the tool about to be executed")
    tool_input: Dict[str, Any] = Field(..., description="Input parameters for the tool")


@dataclass
class ExecutionResult:
    """Result of hook script execution.
    
    Captures all relevant information about the execution including
    exit code, parsed output, raw streams, and timing data.
    """
    
    exit_code: int
    output: Dict[str, Any]
    stdout: str
    stderr: str
    duration: float


class HookExecutor:
    """Executes hook scripts with timeout and error handling.
    
    The HookExecutor manages the execution of external Python scripts that act
    as hooks in the QuickHooks framework. It handles:
    
    - Async subprocess execution
    - JSON input/output communication
    - Timeout management with cleanup
    - Error handling and reporting
    - Performance measurement
    
    Example:
        executor = HookExecutor()
        input_data = PreToolUseInput(tool_name="Bash", tool_input={"command": "ls"})
        result = await executor.execute("/path/to/hook.py", input_data.model_dump())
    """
    
    def __init__(self, default_timeout: float = 30.0):
        """Initialize the hook executor.
        
        Args:
            default_timeout: Default timeout in seconds for hook execution
        """
        self.default_timeout = default_timeout
    
    async def execute(
        self,
        hook_script: Union[str, Path],
        input_data: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """Execute a hook script with the given input data.
        
        Args:
            hook_script: Path to the Python script to execute
            input_data: Dictionary of input data to pass to the hook via stdin
            timeout: Optional timeout in seconds (uses default if not provided)
            
        Returns:
            ExecutionResult: Complete execution result with output and metadata
            
        Raises:
            ExecutionError: If execution fails, times out, or output is invalid
            FileNotFoundError: If the hook script doesn't exist
        """
        hook_path = Path(hook_script)
        if not hook_path.exists():
            raise FileNotFoundError(f"Hook script not found: {hook_path}")
        
        if not hook_path.is_file():
            raise ExecutionError(f"Hook path is not a file: {hook_path}")
            
        execution_timeout = timeout or self.default_timeout
        start_time = time.perf_counter()
        
        try:
            # Prepare JSON input
            json_input = json.dumps(input_data).encode('utf-8')
            
            # Start the subprocess
            process = await asyncio.create_subprocess_exec(
                'python',
                str(hook_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Communicate with timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=json_input),
                    timeout=execution_timeout
                )
                
                # Calculate duration
                duration = time.perf_counter() - start_time
                
                # Decode output streams
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                
                # Parse JSON output from stdout
                parsed_output = self._parse_json_output(stdout)
                
                return ExecutionResult(
                    exit_code=process.returncode or 0,
                    output=parsed_output,
                    stdout=stdout,
                    stderr=stderr,
                    duration=duration
                )
                
            except asyncio.TimeoutError:
                # Kill the process on timeout
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass  # Process already terminated
                
                duration = time.perf_counter() - start_time
                raise ExecutionError(
                    f"Hook execution timed out after {execution_timeout:.1f} seconds"
                )
                
        except ExecutionError:
            # Re-raise execution errors as-is
            raise
        except Exception as e:
            duration = time.perf_counter() - start_time
            raise ExecutionError(f"Hook execution failed: {str(e)}") from e
    
    def _parse_json_output(self, stdout: str) -> Dict[str, Any]:
        """Parse JSON output from hook stdout.
        
        Args:
            stdout: Raw stdout string from the hook process
            
        Returns:
            Dict containing the parsed JSON output
            
        Raises:
            ExecutionError: If JSON parsing fails or output is invalid
        """
        if not stdout.strip():
            # Empty output - return default structure
            return {"allowed": True}
        
        try:
            # Try to parse the entire stdout as JSON
            return json.loads(stdout.strip())
        except json.JSONDecodeError as e:
            # Try to find JSON in the output (hooks might print debug info)
            lines = stdout.strip().split('\n')
            
            # Look for lines that might be JSON
            for line in lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
            # If no valid JSON found, treat as error
            raise ExecutionError(
                f"Invalid JSON output from hook: {str(e)}\n"
                f"Raw output: {stdout[:200]}..."
            ) from e
    
    async def execute_with_context(
        self,
        hook_script: Union[str, Path],
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """Execute a hook script with additional context data.
        
        This method extends the basic execute method to include context
        information that might be useful for hook execution.
        
        Args:
            hook_script: Path to the Python script to execute
            input_data: Dictionary of input data to pass to the hook
            context: Optional context data to include in the input
            timeout: Optional timeout in seconds
            
        Returns:
            ExecutionResult: Complete execution result
            
        Raises:
            ExecutionError: If execution fails
        """
        # Merge context into input data
        full_input = dict(input_data)
        if context:
            full_input['context'] = context
            
        return await self.execute(hook_script, full_input, timeout)
    
    def validate_hook_script(self, hook_script: Union[str, Path]) -> bool:
        """Validate that a hook script is executable.
        
        Args:
            hook_script: Path to the hook script to validate
            
        Returns:
            bool: True if the script exists and appears to be a valid Python file
        """
        hook_path = Path(hook_script)
        
        # Check if file exists
        if not hook_path.exists():
            return False
            
        # Check if it's a file (not directory)
        if not hook_path.is_file():
            return False
            
        # Check if it's a Python file
        if hook_path.suffix != '.py':
            return False
            
        # Basic validation - try to read first few lines
        try:
            with open(hook_path, 'r', encoding='utf-8') as f:
                # Read first 10 lines to check for basic Python syntax
                lines = [f.readline() for _ in range(10)]
                content = ''.join(lines)
                
                # Very basic checks - should contain typical Python patterns
                if not content.strip():
                    return False
                    
                # Check for common Python imports or structures
                python_indicators = [
                    'import ', 'from ', 'def ', 'class ', 'if __name__',
                    '#!/usr/bin/env python', '# -*- coding:'
                ]
                
                return any(indicator in content for indicator in python_indicators)
                
        except (IOError, UnicodeDecodeError):
            return False