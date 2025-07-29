"""
Tests for the grep-to-ripgrep hook implementation.

This test suite validates the GrepToRipgrepTransformer class and the complete
hook functionality including command parsing, transformation, and JSON I/O.
"""

import importlib.util
import json
import subprocess

# Import the hook's transformer class
from pathlib import Path
from typing import Any

import pytest

hook_path = Path(__file__).parent.parent / "hooks" / "grep_to_ripgrep.py"
spec = importlib.util.spec_from_file_location("grep_to_ripgrep", hook_path)
grep_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grep_module)
GrepToRipgrepTransformer = grep_module.GrepToRipgrepTransformer


class TestGrepToRipgrepTransformer:
    """Test cases for the GrepToRipgrepTransformer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = GrepToRipgrepTransformer()

    def test_parse_simple_grep_command(self):
        """Test parsing a simple grep command."""
        command = 'grep "pattern" file.txt'
        result = self.transformer.parse_grep_command(command)

        assert result is not None
        assert result["prefix"] == []
        assert result["grep_cmd"] == "grep"
        assert result["args"] == ['"pattern"', "file.txt"]

    def test_parse_grep_with_prefix(self):
        """Test parsing grep command with prefix commands."""
        command = 'sudo env VAR=value grep "pattern" file.txt'
        result = self.transformer.parse_grep_command(command)

        assert result is not None
        assert result["prefix"] == ["sudo", "env", "VAR=value"]
        assert result["grep_cmd"] == "grep"
        assert result["args"] == ['"pattern"', "file.txt"]

    def test_parse_non_grep_command(self):
        """Test parsing a non-grep command."""
        command = "ls -la"
        result = self.transformer.parse_grep_command(command)

        assert result is None

    def test_parse_command_with_grep_in_path(self):
        """Test parsing command with grep in the path."""
        command = '/usr/bin/grep "pattern" file.txt'
        result = self.transformer.parse_grep_command(command)

        assert result is not None
        assert result["grep_cmd"] == "/usr/bin/grep"

    def test_transform_basic_grep(self):
        """Test basic grep to rg transformation."""
        command = 'grep "hello" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg "hello" file.txt'

    def test_transform_recursive_grep(self):
        """Test recursive grep transformation."""
        command = 'grep -r "pattern" /path/to/dir'
        result = self.transformer.transform_command(command)

        # -r is default in rg, so it should be omitted
        assert result == 'rg "pattern" /path/to/dir'

    def test_transform_case_insensitive(self):
        """Test case insensitive grep transformation."""
        command = 'grep -i "Pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -i "Pattern" file.txt'

    def test_transform_line_numbers(self):
        """Test line numbers flag transformation."""
        command = 'grep -n "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -n "pattern" file.txt'

    def test_transform_invert_match(self):
        """Test invert match transformation."""
        command = 'grep -v "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -v "pattern" file.txt'

    def test_transform_combined_flags(self):
        """Test combined short flags transformation."""
        command = 'grep -rni "pattern" /path'
        result = self.transformer.transform_command(command)

        # -r is omitted (default in rg), -n and -i are kept
        assert result == 'rg -n -i "pattern" /path'

    def test_transform_files_with_matches(self):
        """Test files with matches flag."""
        command = 'grep -l "pattern" *.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -l "pattern" *.txt'

    def test_transform_count_matches(self):
        """Test count matches flag."""
        command = 'grep -c "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -c "pattern" file.txt'

    def test_transform_context_flags(self):
        """Test context flags transformation."""
        command = 'grep -A 3 -B 2 "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -A 3 -B 2 "pattern" file.txt'

    def test_transform_context_combined(self):
        """Test combined context flag."""
        command = 'grep -C 5 "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -C 5 "pattern" file.txt'

    def test_transform_fixed_strings(self):
        """Test fixed strings flag transformation."""
        command = 'grep -F "literal.string" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg --fixed-strings "literal.string" file.txt'

    def test_transform_perl_regex(self):
        """Test Perl regex flag transformation."""
        command = 'grep -P "(?<=word)pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg --pcre2 "(?<=word)pattern" file.txt'

    def test_transform_include_pattern(self):
        """Test include pattern transformation."""
        command = 'grep --include="*.py" "pattern" /path'
        result = self.transformer.transform_command(command)

        assert result == 'rg --glob "*.py" "pattern" /path'

    def test_transform_exclude_pattern(self):
        """Test exclude pattern transformation."""
        command = 'grep --exclude="*.log" "pattern" /path'
        result = self.transformer.transform_command(command)

        assert result == 'rg --glob "!*.log" "pattern" /path'

    def test_transform_exclude_dir(self):
        """Test exclude directory transformation."""
        command = 'grep --exclude-dir="node_modules" "pattern" /path'
        result = self.transformer.transform_command(command)

        assert result == 'rg --glob "!node_modules/" "pattern" /path'

    def test_transform_word_boundaries(self):
        """Test word boundaries flag."""
        command = 'grep -w "word" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -w "word" file.txt'

    def test_transform_whole_line(self):
        """Test whole line match flag."""
        command = 'grep -x "exact line" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -x "exact line" file.txt'

    def test_transform_with_prefix(self):
        """Test transformation preserves command prefix."""
        command = 'sudo grep -i "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'sudo rg -i "pattern" file.txt'

    def test_transform_complex_command(self):
        """Test complex command transformation."""
        command = 'env DEBUG=1 sudo grep -rni --include="*.py" --exclude-dir="__pycache__" "TODO" /src'
        result = self.transformer.transform_command(command)

        expected = (
            'env DEBUG=1 sudo rg -n -i --glob "*.py" --glob "!__pycache__/" "TODO" /src'
        )
        assert result == expected

    def test_no_transformation_for_non_grep(self):
        """Test that non-grep commands are not transformed."""
        command = "ls -la | head -10"
        result = self.transformer.transform_command(command)

        assert result is None


class TestHookIntegration:
    """Integration tests for the complete hook functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hook_path = Path(__file__).parent.parent / "hooks" / "grep_to_ripgrep.py"
        assert self.hook_path.exists(), f"Hook script not found: {self.hook_path}"

    def run_hook(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run the hook script with given input data.

        Args:
            input_data: Input data to pass to the hook

        Returns:
            Parsed JSON output from the hook
        """
        process = subprocess.run(
            ["python", str(self.hook_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert process.returncode == 0, f"Hook failed: {process.stderr}"
        return json.loads(process.stdout.strip())

    def test_hook_non_bash_tool(self):
        """Test hook behavior with non-Bash tools."""
        input_data = {
            "tool_name": "NotBash",
            "tool_input": {"command": 'grep "pattern" file.txt'},
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is False
        assert result["tool_name"] == "NotBash"

    def test_hook_bash_non_grep(self):
        """Test hook behavior with Bash commands that don't contain grep."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la | head -10"},
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is False
        assert result["tool_input"]["command"] == "ls -la | head -10"

    def test_hook_simple_grep_transformation(self):
        """Test hook transforms simple grep command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": 'grep "hello" file.txt'},
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is True
        assert result["tool_input"]["command"] == 'rg "hello" file.txt'
        assert "Transformed grep to ripgrep" in result["message"]

    def test_hook_complex_grep_transformation(self):
        """Test hook transforms complex grep command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'grep -rni --include="*.py" "TODO" /src',
                "description": "Search for TODO comments",
            },
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is True
        expected_cmd = 'rg -n -i --glob "*.py" "TODO" /src'
        assert result["tool_input"]["command"] == expected_cmd
        assert (
            result["tool_input"]["description"] == "Search for TODO comments"
        )  # Preserved

    def test_hook_preserves_other_tool_input(self):
        """Test hook preserves other tool input fields."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'grep -i "pattern" file.txt',
                "timeout": 30,
                "description": "Search for pattern",
            },
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is True
        assert result["tool_input"]["command"] == 'rg -i "pattern" file.txt'
        assert result["tool_input"]["timeout"] == 30
        assert result["tool_input"]["description"] == "Search for pattern"

    def test_hook_handles_empty_command(self):
        """Test hook handles empty command gracefully."""
        input_data = {"tool_name": "Bash", "tool_input": {"command": ""}}

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is False

    def test_hook_handles_invalid_json_gracefully(self):
        """Test hook handles errors gracefully and allows original command."""
        # Test with malformed input by running the hook directly
        process = subprocess.run(
            ["python", str(self.hook_path)],
            input='{"invalid": json',  # Malformed JSON
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should exit successfully but allow original command
        assert process.returncode == 0
        result = json.loads(process.stdout.strip())
        assert result["allowed"] is True
        assert result["modified"] is False
        assert "Hook error" in result["message"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = GrepToRipgrepTransformer()

    def test_quoted_patterns_with_spaces(self):
        """Test handling of quoted patterns with spaces."""
        command = 'grep "hello world" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg "hello world" file.txt'

    def test_single_quoted_patterns(self):
        """Test handling of single-quoted patterns."""
        command = "grep 'hello world' file.txt"
        result = self.transformer.transform_command(command)

        assert result == "rg 'hello world' file.txt"

    def test_patterns_with_special_chars(self):
        """Test patterns with special shell characters."""
        command = 'grep "hello|world.*test" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg "hello|world.*test" file.txt'

    def test_multiple_files(self):
        """Test grep with multiple files."""
        command = 'grep -i "pattern" file1.txt file2.txt dir/*.log'
        result = self.transformer.transform_command(command)

        assert result == 'rg -i "pattern" file1.txt file2.txt dir/*.log'

    def test_pipes_and_redirects(self):
        """Test commands with pipes and redirects."""
        command = 'grep "pattern" file.txt | head -10'
        result = self.transformer.transform_command(command)

        # Should only transform the grep part
        assert result == 'rg "pattern" file.txt | head -10'

    def test_command_substitution(self):
        """Test commands with command substitution."""
        command = 'grep "pattern" $(find . -name "*.txt")'
        result = self.transformer.transform_command(command)

        assert result == 'rg "pattern" $(find . -name "*.txt")'

    def test_escaped_quotes(self):
        """Test patterns with escaped quotes."""
        command = r'grep "say \"hello\"" file.txt'
        result = self.transformer.transform_command(command)

        assert result == r'rg "say \"hello\"" file.txt'

    def test_long_flag_forms(self):
        """Test long form flags."""
        command = 'grep --ignore-case --line-number --invert-match "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg -i -n -v "pattern" file.txt'

    def test_unknown_flags_passthrough(self):
        """Test that unknown flags are passed through."""
        command = 'grep --some-unknown-flag "pattern" file.txt'
        result = self.transformer.transform_command(command)

        assert result == 'rg --some-unknown-flag "pattern" file.txt'


@pytest.mark.parametrize(
    "command,expected",
    [
        # Basic transformations
        ('grep "test" file.txt', 'rg "test" file.txt'),
        ('grep -i "Test" file.txt', 'rg -i "Test" file.txt'),
        ('grep -n "pattern" file.txt', 'rg -n "pattern" file.txt'),
        ('grep -v "exclude" file.txt', 'rg -v "exclude" file.txt'),
        # Recursive (should omit -r)
        ('grep -r "pattern" dir/', 'rg "pattern" dir/'),
        ('grep --recursive "pattern" dir/', 'rg "pattern" dir/'),
        # Combined flags
        ('grep -rni "pattern" dir/', 'rg -n -i "pattern" dir/'),
        ('grep -rnv "pattern" dir/', 'rg -n -v "pattern" dir/'),
        # Context
        ('grep -A 3 "pattern" file.txt', 'rg -A 3 "pattern" file.txt'),
        ('grep -B 2 "pattern" file.txt', 'rg -B 2 "pattern" file.txt'),
        ('grep -C 5 "pattern" file.txt', 'rg -C 5 "pattern" file.txt'),
        # Fixed strings and regex
        ('grep -F "literal" file.txt', 'rg --fixed-strings "literal" file.txt'),
        ('grep -P "(?<=word)" file.txt', 'rg --pcre2 "(?<=word)" file.txt'),
        # File patterns
        ('grep --include="*.py" "pattern" dir/', 'rg --glob "*.py" "pattern" dir/'),
        ('grep --exclude="*.log" "pattern" dir/', 'rg --glob "!*.log" "pattern" dir/'),
        # With prefixes
        ('sudo grep -i "pattern" file.txt', 'sudo rg -i "pattern" file.txt'),
        ('env VAR=1 grep "pattern" file.txt', 'env VAR=1 rg "pattern" file.txt'),
    ],
)
def test_parametrized_transformations(command, expected):
    """Parametrized test for various command transformations."""
    transformer = GrepToRipgrepTransformer()
    result = transformer.transform_command(command)
    assert result == expected
