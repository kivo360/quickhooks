#!/usr/bin/env python3
"""
QuickHook: Enhanced Grep to Ripgrep Transformer
This hook intercepts grep commands and executes ripgrep instead.

This is an enhanced version that actually executes ripgrep and returns
the results, effectively replacing grep with ripgrep transparently.
"""

import json
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


class GrepToRipgrepTransformer:
    """Transforms grep commands to equivalent ripgrep commands."""
    
    def __init__(self):
        """Initialize the transformer with flag mappings."""
        # Direct flag mappings (grep flag -> rg flag)
        self.direct_mappings = {
            "-i": "-i",  # case insensitive
            "--ignore-case": "-i",
            "-n": "-n",  # show line numbers
            "--line-number": "-n",
            "-v": "-v",  # invert match
            "--invert-match": "-v",
            "-l": "-l",  # files with matches
            "--files-with-matches": "-l",
            "-c": "-c",  # count matches
            "--count": "-c",
            "-w": "-w",  # word boundaries
            "--word-regexp": "-w",
            "-x": "-x",  # whole line match
            "--line-regexp": "-x",
            "-H": "-H",  # print filename
            "--with-filename": "-H",
            "-h": "--no-filename",  # suppress filename
            "--no-filename": "--no-filename",
            "-o": "-o",  # only matching
            "--only-matching": "-o",
            "-q": "-q",  # quiet mode
            "--quiet": "-q",
            "--silent": "-q",
        }
        
        # Flags that require special handling
        self.special_flags = {
            "-r", "--recursive",  # recursive (default in rg)
            "-R", "--dereference-recursive",
            "-A", "--after-context",  # context lines after
            "-B", "--before-context",  # context lines before
            "-C", "--context",  # context lines around
            "-E", "--extended-regexp",  # extended regex (default in rg)
            "-F", "--fixed-strings",  # fixed strings
            "-P", "--perl-regexp",  # perl regex
            "--include",  # include pattern
            "--exclude",  # exclude pattern
            "--exclude-dir",  # exclude directory
            "-e",  # pattern (can be multiple)
            "-f", "--file",  # read patterns from file
            "-m", "--max-count",  # max matches per file
        }
    
    def parse_grep_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Parse a grep command into components."""
        try:
            # Split the command into tokens
            tokens = shlex.split(command)
            
            if not tokens:
                return None
            
            # Find grep command (could be grep, egrep, fgrep, etc.)
            grep_index = -1
            for i, token in enumerate(tokens):
                if token in ["grep", "egrep", "fgrep"] or token.endswith("grep"):
                    grep_index = i
                    break
            
            if grep_index == -1:
                return None
            
            # Parse arguments after grep
            args = tokens[grep_index + 1:]
            
            return {
                "prefix": tokens[:grep_index],  # Commands before grep
                "grep_cmd": tokens[grep_index],
                "args": args,
                "full_tokens": tokens,
            }
            
        except ValueError:
            # Handle shell parsing errors
            return None
    
    def transform_args(self, args: List[str]) -> Tuple[List[str], List[str]]:
        """Transform grep arguments to ripgrep arguments."""
        rg_flags = []
        remaining_args = []
        patterns = []
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            # Handle combined short flags (e.g., -rni)
            if arg.startswith("-") and len(arg) > 2 and not arg.startswith("--"):
                # Split combined flags
                for char in arg[1:]:
                    flag = f"-{char}"
                    if flag in self.direct_mappings:
                        mapped = self.direct_mappings[flag]
                        if mapped not in rg_flags:
                            rg_flags.append(mapped)
                    elif flag in self.special_flags:
                        # Handle special cases
                        if flag in ["-r", "-R"]:
                            # Recursive is default in rg, skip
                            continue
                        elif flag == "-E":
                            # Extended regex is default in rg
                            continue
                        elif flag == "-e":
                            # Pattern follows
                            if i + 1 < len(args):
                                patterns.append(args[i + 1])
                                i += 1
                        else:
                            rg_flags.append(flag)
                i += 1
                continue
            
            # Handle long flags and flags with values
            if arg.startswith("-"):
                # Pattern flag
                if arg == "-e":
                    if i + 1 < len(args):
                        patterns.append(args[i + 1])
                        i += 2
                        continue
                
                # File input flag
                elif arg in ["-f", "--file"]:
                    if i + 1 < len(args):
                        rg_flags.extend(["-f", args[i + 1]])
                        i += 2
                        continue
                
                # Max count flag
                elif arg in ["-m", "--max-count"]:
                    if i + 1 < len(args):
                        rg_flags.extend(["-m", args[i + 1]])
                        i += 2
                        continue
                
                # Context flags
                elif arg in ["-A", "--after-context", "-B", "--before-context", "-C", "--context"]:
                    if i + 1 < len(args):
                        rg_flags.extend([arg, args[i + 1]])
                        i += 2
                        continue
                
                # Include/exclude patterns
                elif arg.startswith("--include=") or arg.startswith("--exclude=") or arg.startswith("--exclude-dir="):
                    # Convert to rg equivalent
                    if arg.startswith("--include="):
                        pattern = arg.split("=", 1)[1]
                        rg_flags.extend(["--glob", pattern])
                    elif arg.startswith("--exclude="):
                        pattern = arg.split("=", 1)[1]
                        rg_flags.extend(["--glob", f"!{pattern}"])
                    elif arg.startswith("--exclude-dir="):
                        pattern = arg.split("=", 1)[1]
                        rg_flags.extend(["--glob", f"!{pattern}/**"])
                    i += 1
                    continue
                    
                elif arg in ["--include", "--exclude", "--exclude-dir"]:
                    if i + 1 < len(args):
                        pattern = args[i + 1]
                        if arg == "--include":
                            rg_flags.extend(["--glob", pattern])
                        elif arg == "--exclude":
                            rg_flags.extend(["--glob", f"!{pattern}"])
                        elif arg == "--exclude-dir":
                            rg_flags.extend(["--glob", f"!{pattern}/**"])
                        i += 2
                        continue
                
                # Fixed strings
                elif arg in ["-F", "--fixed-strings"]:
                    rg_flags.append("--fixed-strings")
                    i += 1
                    continue
                
                # Perl regex
                elif arg in ["-P", "--perl-regexp"]:
                    rg_flags.append("--pcre2")
                    i += 1
                    continue
                
                # Direct mapping
                if arg in self.direct_mappings:
                    mapped = self.direct_mappings[arg]
                    if mapped not in rg_flags:
                        rg_flags.append(mapped)
                elif arg in self.special_flags:
                    if arg not in ["-r", "--recursive", "-R", "--dereference-recursive", "-E", "--extended-regexp"]:
                        rg_flags.append(arg)
                else:
                    # Unknown flag, pass through
                    rg_flags.append(arg)
                
                i += 1
            else:
                # Non-flag argument (pattern or file)
                remaining_args.append(arg)
                i += 1
        
        # If we collected patterns with -e, add them at the end
        if patterns:
            # Use the last pattern as the main pattern
            if remaining_args and not remaining_args[0].startswith("/") and not remaining_args[0].startswith("."):
                # First remaining arg might be a pattern
                patterns.append(remaining_args.pop(0))
            
            # Add all patterns with -e flag
            for pattern in patterns[:-1]:
                rg_flags.extend(["-e", pattern])
            
            # Last pattern goes as positional argument
            remaining_args.insert(0, patterns[-1])
        
        return rg_flags, remaining_args
    
    def build_ripgrep_command(self, parsed: Dict[str, Any]) -> List[str]:
        """Build the ripgrep command from parsed components."""
        # Transform the arguments
        rg_flags, remaining_args = self.transform_args(parsed["args"])
        
        # Build the new command
        new_command = []
        
        # Add prefix (sudo, env vars, etc.)
        new_command.extend(parsed["prefix"])
        
        # Use rg instead of grep
        new_command.append("rg")
        
        # Add color option for terminal output
        new_command.append("--color=auto")
        
        # Add transformed flags
        new_command.extend(rg_flags)
        
        # Add remaining arguments (pattern and files)
        new_command.extend(remaining_args)
        
        return new_command


def execute_ripgrep(command_parts: List[str], cwd: str) -> Dict[str, Any]:
    """Execute ripgrep command and capture output."""
    try:
        # Run the command
        result = subprocess.run(
            command_parts,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Main hook entry point."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Extract fields
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", ".")
        
        # Only process Bash tool commands
        if tool_name != "Bash":
            return
        
        command = tool_input.get("command", "")
        if not command:
            return
        
        # Initialize transformer
        transformer = GrepToRipgrepTransformer()
        
        # Parse the command
        parsed = transformer.parse_grep_command(command)
        if not parsed:
            return
        
        # Build ripgrep command
        rg_command = transformer.build_ripgrep_command(parsed)
        
        # Execute ripgrep
        result = execute_ripgrep(rg_command, cwd)
        
        if result.get("success"):
            # Print the ripgrep output
            if result["stdout"]:
                print(result["stdout"], end="")
            if result["stderr"]:
                print(result["stderr"], end="", file=sys.stderr)
            
            # Provide feedback about the transformation
            print(f"\n🔍 Grep→Ripgrep: Executed '{' '.join(rg_command)}'", file=sys.stderr)
            
            # Return a response that prevents the original grep from running
            response = {
                "continue": False,  # Don't run the original grep
                "suppressOutput": False,
                "exitCode": result["returncode"]
            }
            print(json.dumps(response))
            
            # Exit with the same code as ripgrep
            sys.exit(result["returncode"])
        else:
            # If ripgrep execution failed, fall back to grep
            print(f"⚠️  Ripgrep execution failed: {result.get('error', 'Unknown error')}", file=sys.stderr)
            print("ℹ️  Falling back to standard grep", file=sys.stderr)
            
            # Let the original grep command run
            return
            
    except Exception as e:
        # Always fail-safe - log error but don't block execution
        print(f"Grep transformer hook error: {str(e)}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()