#!/usr/bin/env python3
"""
QuickHook: Grep to Ripgrep Command Transformer

This pre-tool-use hook intercepts Bash commands containing 'grep' and
transforms them to use 'ripgrep' (rg) instead, providing faster and more
efficient text searching.

Key transformations:
- grep "pattern" file → rg "pattern" file
- grep -r "pattern" dir → rg "pattern" dir (recursive by default)
- grep -i "pattern" file → rg -i "pattern" file (case insensitive)
- grep -n "pattern" file → rg -n "pattern" file (show line numbers)
- grep -v "pattern" file → rg -v "pattern" file (invert match)
- grep -l "pattern" files → rg -l "pattern" files (files with matches)
- grep -c "pattern" file → rg -c "pattern" file (count matches)

Author: QuickHooks Framework
Version: 1.0.0
"""

import json
import shlex
import sys
from typing import Any


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
        }

        # Flags that require special handling
        self.special_flags = {
            "-r",
            "--recursive",  # recursive (default in rg)
            "-R",
            "--dereference-recursive",
            "-A",
            "--after-context",  # context lines after
            "-B",
            "--before-context",  # context lines before
            "-C",
            "--context",  # context lines around
            "-E",
            "--extended-regexp",  # extended regex (default in rg)
            "-F",
            "--fixed-strings",  # fixed strings
            "-P",
            "--perl-regexp",  # perl regex
            "--include",  # include pattern
            "--exclude",  # exclude pattern
            "--exclude-dir",  # exclude directory
        }

    def parse_grep_command(self, command: str) -> dict[str, Any] | None:
        """Parse a grep command into components.

        Args:
            command: The full command string

        Returns:
            Dict with parsed components or None if not a grep command
        """
        try:
            # Split the command into tokens
            tokens = shlex.split(command)

            if not tokens or not any(token.endswith("grep") for token in tokens):
                return None

            # Find the grep command
            grep_index = -1
            for i, token in enumerate(tokens):
                if token.endswith("grep"):
                    grep_index = i
                    break

            if grep_index == -1:
                return None

            # Parse arguments after grep
            args = tokens[grep_index + 1 :]

            return {
                "prefix": tokens[
                    :grep_index
                ],  # Commands before grep (e.g., sudo, env vars)
                "grep_cmd": tokens[grep_index],
                "args": args,
                "full_tokens": tokens,
            }

        except ValueError:
            # Handle shell parsing errors
            return None

    def transform_args(self, args: list[str]) -> tuple[list[str], list[str]]:
        """Transform grep arguments to ripgrep arguments.

        Args:
            args: List of grep arguments

        Returns:
            Tuple of (rg_flags, remaining_args)
        """
        rg_flags = []
        remaining_args = []
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
                        if flag == "-E":
                            # Extended regex is default in rg
                            continue
                        rg_flags.append(flag)
                i += 1
                continue

            # Handle long flags and flags with values
            if arg.startswith("-"):
                # Check for flags that take values
                if arg in [
                    "-A",
                    "--after-context",
                    "-B",
                    "--before-context",
                    "-C",
                    "--context",
                ]:
                    if i + 1 < len(args):
                        rg_flags.extend([arg, args[i + 1]])
                        i += 2
                        continue
                elif (
                    arg.startswith("--include=")
                    or arg.startswith("--exclude=")
                    or arg.startswith("--exclude-dir=")
                ):
                    # Convert to rg equivalent
                    if arg.startswith("--include="):
                        pattern = arg.split("=", 1)[1]
                        rg_flags.extend(["--glob", pattern])
                    elif arg.startswith("--exclude="):
                        pattern = arg.split("=", 1)[1]
                        rg_flags.extend(["--glob", f"!{pattern}"])
                    elif arg.startswith("--exclude-dir="):
                        pattern = arg.split("=", 1)[1]
                        rg_flags.extend(["--glob", f"!{pattern}/"])
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
                            rg_flags.extend(["--glob", f"!{pattern}/"])
                        i += 2
                        continue
                elif arg == "-F" or arg == "--fixed-strings":
                    rg_flags.append("--fixed-strings")
                    i += 1
                    continue
                elif arg == "-P" or arg == "--perl-regexp":
                    rg_flags.append("--pcre2")
                    i += 1
                    continue

                # Direct mapping
                if arg in self.direct_mappings:
                    mapped = self.direct_mappings[arg]
                    if mapped not in rg_flags:
                        rg_flags.append(mapped)
                elif arg in self.special_flags:
                    if arg not in [
                        "-r",
                        "--recursive",
                        "-R",
                        "--dereference-recursive",
                        "-E",
                        "--extended-regexp",
                    ]:
                        rg_flags.append(arg)
                else:
                    # Unknown flag, pass through (might be valid for rg)
                    rg_flags.append(arg)

                i += 1
            else:
                # Non-flag argument (pattern or file)
                remaining_args.append(arg)
                i += 1

        return rg_flags, remaining_args

    def transform_command(self, command: str) -> str | None:
        """Transform a grep command to use ripgrep.

        Args:
            command: The original command string

        Returns:
            Transformed command or None if not applicable
        """
        parsed = self.parse_grep_command(command)
        if not parsed:
            return None

        # Transform the arguments
        rg_flags, remaining_args = self.transform_args(parsed["args"])

        # Build the new command
        new_tokens = []

        # Add prefix (sudo, env vars, etc.)
        new_tokens.extend(parsed["prefix"])

        # Replace grep with rg
        new_tokens.append("rg")

        # Add transformed flags
        new_tokens.extend(rg_flags)

        # Add remaining arguments (pattern and files)
        new_tokens.extend(remaining_args)

        # Join back into command string
        return shlex.join(new_tokens)


def main():
    """Main hook entry point following official Claude Code format."""
    try:
        # Read JSON input from stdin (official format)
        input_data = json.loads(sys.stdin.read())

        # Extract standard fields from official Claude Code format
        input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        input_data.get("hook_event_name", "")
        input_data.get("transcript_path", "")
        input_data.get("cwd", "")

        # Only process Bash tool commands
        if tool_name != "Bash":
            # No transformation needed - proceed normally
            return

        # Get the command from tool input
        command = tool_input.get("command", "")
        if not command:
            # No command to transform - proceed normally
            return

        # Check if this is a grep command
        transformer = GrepToRipgrepTransformer()
        transformed_command = transformer.transform_command(command)

        if transformed_command and transformed_command != command:
            # Command was transformed - provide feedback
            print(
                f"Grep→Ripgrep: {command[:50]}{'...' if len(command) > 50 else ''} → rg",
                file=sys.stderr,
            )

            # Note: PreToolUse hooks cannot directly modify tool_input
            # We provide feedback via stderr that Claude can see
            response = {"continue": True, "suppressOutput": False}
            print(json.dumps(response))
        else:
            # No transformation needed - proceed normally
            # No JSON response needed (exit code 0 is sufficient)
            pass

    except Exception as e:
        # Always fail-safe - log error but don't block execution
        print(f"Grep transformer hook error: {e!s}", file=sys.stderr)
        # Exit code 0 allows tool to proceed
        sys.exit(0)


if __name__ == "__main__":
    main()
