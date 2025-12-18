#!/usr/bin/env python3
"""
QuickHook: Language-Aware Code Formatter
Automatically runs the appropriate formatter based on detected programming language.

Supported formatters:
- Python: black, ruff format, autopep8, yapf
- JavaScript/TypeScript: prettier, standard
- Go: gofmt, goimports
- Rust: rustfmt
- Ruby: rubocop (with --auto-correct)
- Java: google-java-format
- C/C++: clang-format
"""

import json
import os
import sys
from pathlib import Path


class LanguageDetector:
    """Detects programming language from file extensions and config files."""

    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def detect_languages(self) -> list[str]:
        """Detect all programming languages in the current directory."""
        languages = set()

        # Check for language-specific config files
        config_mappings = {
            "pyproject.toml": "python",
            "setup.py": "python",
            "requirements.txt": "python",
            "package.json": "javascript",
            "tsconfig.json": "typescript",
            "go.mod": "go",
            "Cargo.toml": "rust",
            "Gemfile": "ruby",
            "pom.xml": "java",
            "build.gradle": "java",
            ".clang-format": "cpp",
        }

        for config_file, language in config_mappings.items():
            if (self.cwd / config_file).exists():
                languages.add(language)

        # Check file extensions in the directory
        extension_mappings = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
        }

        for file in self.cwd.rglob("*"):
            if file.is_file():
                ext = file.suffix.lower()
                if ext in extension_mappings:
                    languages.add(extension_mappings[ext])

        return list(languages)

    def get_primary_language(self) -> str | None:
        """Get the primary language based on config files and file count."""
        languages = self.detect_languages()

        if not languages:
            return None

        # Prioritize based on config files
        if "pyproject.toml" in os.listdir(self.cwd) or "setup.py" in os.listdir(
            self.cwd
        ):
            return "python"
        if "package.json" in os.listdir(self.cwd):
            return (
                "typescript"
                if "tsconfig.json" in os.listdir(self.cwd)
                else "javascript"
            )
        if "go.mod" in os.listdir(self.cwd):
            return "go"
        if "Cargo.toml" in os.listdir(self.cwd):
            return "rust"

        # Return the first detected language
        return languages[0] if languages else None


class LanguageAwareFormatter:
    """Transforms generic format commands to language-specific formatters."""

    def __init__(self):
        # Map languages to their preferred formatters and commands
        self.formatter_mappings = {
            "python": {
                "primary": "ruff",
                "alternatives": ["black", "autopep8", "yapf"],
                "commands": {
                    "ruff": "ruff format .",
                    "black": "black .",
                    "autopep8": "autopep8 --in-place --recursive .",
                    "yapf": "yapf -i -r .",
                },
                "file_commands": {
                    "ruff": "ruff format {}",
                    "black": "black {}",
                    "autopep8": "autopep8 --in-place {}",
                    "yapf": "yapf -i {}",
                },
            },
            "javascript": {
                "primary": "prettier",
                "alternatives": ["standard"],
                "commands": {
                    "prettier": 'npx prettier --write "**/*.{js,jsx}"',
                    "standard": "npx standard --fix",
                },
                "file_commands": {
                    "prettier": "npx prettier --write {}",
                    "standard": "npx standard --fix {}",
                },
            },
            "typescript": {
                "primary": "prettier",
                "commands": {"prettier": 'npx prettier --write "**/*.{ts,tsx}"'},
                "file_commands": {"prettier": "npx prettier --write {}"},
            },
            "go": {
                "primary": "gofmt",
                "alternatives": ["goimports"],
                "commands": {"gofmt": "gofmt -w .", "goimports": "goimports -w ."},
                "file_commands": {
                    "gofmt": "gofmt -w {}",
                    "goimports": "goimports -w {}",
                },
            },
            "rust": {
                "primary": "rustfmt",
                "commands": {"rustfmt": "cargo fmt"},
                "file_commands": {"rustfmt": "rustfmt {}"},
            },
            "ruby": {
                "primary": "rubocop",
                "commands": {"rubocop": "rubocop --auto-correct-all"},
                "file_commands": {"rubocop": "rubocop --auto-correct-all {}"},
            },
            "java": {
                "primary": "google-java-format",
                "commands": {
                    "google-java-format": "java -jar google-java-format.jar --replace **/*.java"
                },
                "file_commands": {
                    "google-java-format": "java -jar google-java-format.jar --replace {}"
                },
            },
            "c": {
                "primary": "clang-format",
                "commands": {
                    "clang-format": 'find . -name "*.c" -o -name "*.h" | xargs clang-format -i'
                },
                "file_commands": {"clang-format": "clang-format -i {}"},
            },
            "cpp": {
                "primary": "clang-format",
                "commands": {
                    "clang-format": 'find . -name "*.cpp" -o -name "*.cc" -o -name "*.cxx" -o -name "*.hpp" -o -name "*.h" | xargs clang-format -i'
                },
                "file_commands": {"clang-format": "clang-format -i {}"},
            },
        }

    def should_intercept(self, command: str) -> bool:
        """Check if this command should be intercepted."""
        format_keywords = [
            "format",
            "fmt",
            "prettier",
            "black",
            "autopep8",
            "gofmt",
            "rustfmt",
            "beautify",
            "style",
        ]

        # Check if command contains format-related keywords
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in format_keywords)

    def transform_command(self, command: str, language: str) -> str | None:
        """Transform a generic format command to language-specific formatter."""
        if language not in self.formatter_mappings:
            return None

        formatter_config = self.formatter_mappings[language]
        primary_formatter = formatter_config["primary"]

        # If the command already specifies a formatter, don't transform
        all_formatters = [primary_formatter] + formatter_config.get("alternatives", [])
        if any(formatter in command for formatter in all_formatters):
            return None

        # Check if formatting a specific file
        parts = command.split()
        if len(parts) > 1 and os.path.exists(parts[-1]):
            # Format specific file
            file_commands = formatter_config.get("file_commands", {})
            if primary_formatter in file_commands:
                return file_commands[primary_formatter].format(parts[-1])

        # Return the primary formatter command for all files
        return formatter_config["commands"][primary_formatter]

    def get_format_command_for_file(self, filepath: str) -> str | None:
        """Get appropriate format command for a specific file."""
        file_ext = Path(filepath).suffix.lower()

        ext_to_language = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
        }

        language = ext_to_language.get(file_ext)
        if not language:
            return None

        formatter_config = self.formatter_mappings.get(language)
        if not formatter_config:
            return None

        # Get file-specific command
        primary_formatter = formatter_config["primary"]
        file_commands = formatter_config.get("file_commands", {})

        if primary_formatter in file_commands:
            return file_commands[primary_formatter].format(filepath)

        return None


def main():
    """Main entry point for the language-aware formatter hook."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract fields
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", ".")

        # Only process Bash commands
        if tool_name != "Bash":
            return

        command = tool_input.get("command", "")
        if not command:
            return

        # Initialize components
        detector = LanguageDetector(cwd)
        formatter = LanguageAwareFormatter()

        # Check if we should intercept this command
        if not formatter.should_intercept(command):
            return

        # Detect primary language
        language = detector.get_primary_language()
        if not language:
            print(
                "ℹ️  No programming language detected in current directory",
                file=sys.stderr,
            )
            return

        # Try to transform the command
        new_command = formatter.transform_command(command, language)

        if new_command and new_command != command:
            # Provide feedback about the transformation
            print(
                f"✨ Format: Using {language} formatter → {new_command}",
                file=sys.stderr,
            )

            # Note: We can't modify the command directly in pre-tool-use hooks
            # But we provide feedback that Claude can see
            response = {
                "continue": True,
                "suppressOutput": False,
                "metadata": {
                    "detected_language": language,
                    "suggested_command": new_command,
                },
            }
            print(json.dumps(response))

    except Exception as e:
        # Fail safely - don't block execution
        print(f"Language-aware formatter hook error: {e!s}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
