#!/usr/bin/env python3
"""
QuickHook: Language-Aware Build Checker
Automatically runs the appropriate build/test commands based on detected programming language.

Supported build systems:
- Python: pytest, unittest, tox, nox
- JavaScript/TypeScript: npm test, yarn test, jest
- Go: go test, go build
- Rust: cargo test, cargo build
- Ruby: rspec, rake test
- Java: mvn test, gradle test
- C/C++: make, cmake, bazel
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
            "tox.ini": "python",
            "noxfile.py": "python",
            "package.json": "javascript",
            "tsconfig.json": "typescript",
            "go.mod": "go",
            "Cargo.toml": "rust",
            "Gemfile": "ruby",
            "Rakefile": "ruby",
            "pom.xml": "java",
            "build.gradle": "java",
            "CMakeLists.txt": "cpp",
            "Makefile": "make",
            "BUILD": "bazel",
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

    def detect_build_system(self) -> str | None:
        """Detect the build system being used."""
        # Check for build system files
        if (self.cwd / "Makefile").exists():
            return "make"
        if (self.cwd / "CMakeLists.txt").exists():
            return "cmake"
        if (self.cwd / "BUILD").exists() or (self.cwd / "BUILD.bazel").exists():
            return "bazel"
        if (self.cwd / "pom.xml").exists():
            return "maven"
        if (self.cwd / "build.gradle").exists() or (
            self.cwd / "build.gradle.kts"
        ).exists():
            return "gradle"
        if (self.cwd / "package.json").exists():
            # Check if using npm or yarn
            if (self.cwd / "yarn.lock").exists():
                return "yarn"
            return "npm"
        if (self.cwd / "Cargo.toml").exists():
            return "cargo"
        if (self.cwd / "go.mod").exists():
            return "go"
        if (self.cwd / "pyproject.toml").exists():
            # Check for specific Python build tools
            try:
                with open(self.cwd / "pyproject.toml") as f:
                    content = f.read()
                    if "tool.poetry" in content:
                        return "poetry"
                    if "tool.hatch" in content:
                        return "hatch"
                    if "tool.setuptools" in content:
                        return "setuptools"
            except:
                pass

        return None


class LanguageAwareBuildChecker:
    """Transforms generic build/test commands to language-specific ones."""

    def __init__(self):
        # Map languages to their build and test commands
        self.build_mappings = {
            "python": {
                "test_commands": {
                    "pytest": "pytest",
                    "unittest": "python -m unittest discover",
                    "tox": "tox",
                    "nox": "nox",
                },
                "build_commands": {
                    "setuptools": "python setup.py build",
                    "poetry": "poetry build",
                    "hatch": "hatch build",
                    "pip": "pip install -e .",
                },
            },
            "javascript": {
                "test_commands": {
                    "npm": "npm test",
                    "yarn": "yarn test",
                    "jest": "npx jest",
                },
                "build_commands": {
                    "npm": "npm run build",
                    "yarn": "yarn build",
                },
            },
            "typescript": {
                "test_commands": {
                    "npm": "npm test",
                    "yarn": "yarn test",
                    "jest": "npx jest",
                },
                "build_commands": {
                    "npm": "npm run build",
                    "yarn": "yarn build",
                    "tsc": "npx tsc",
                },
            },
            "go": {
                "test_commands": {
                    "go": "go test ./...",
                },
                "build_commands": {
                    "go": "go build ./...",
                },
            },
            "rust": {
                "test_commands": {
                    "cargo": "cargo test",
                },
                "build_commands": {
                    "cargo": "cargo build",
                },
            },
            "ruby": {
                "test_commands": {
                    "rspec": "rspec",
                    "rake": "rake test",
                    "minitest": "ruby -Itest test/*_test.rb",
                },
                "build_commands": {
                    "bundler": "bundle install",
                    "rake": "rake build",
                },
            },
            "java": {
                "test_commands": {
                    "maven": "mvn test",
                    "gradle": "gradle test",
                },
                "build_commands": {
                    "maven": "mvn compile",
                    "gradle": "gradle build",
                },
            },
            "c": {
                "test_commands": {
                    "make": "make test",
                    "cmake": "cmake --build . && ctest",
                },
                "build_commands": {
                    "make": "make",
                    "cmake": "cmake --build .",
                    "gcc": "gcc -o app *.c",
                },
            },
            "cpp": {
                "test_commands": {
                    "make": "make test",
                    "cmake": "cmake --build . && ctest",
                    "bazel": "bazel test //...",
                },
                "build_commands": {
                    "make": "make",
                    "cmake": "cmake --build .",
                    "bazel": "bazel build //...",
                    "g++": "g++ -o app *.cpp",
                },
            },
        }

    def should_intercept(self, command: str) -> bool:
        """Check if this command should be intercepted."""
        build_keywords = [
            "build",
            "compile",
            "make",
            "test",
            "check",
            "verify",
            "validate",
        ]

        # Check if command contains build-related keywords
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in build_keywords)

    def is_test_command(self, command: str) -> bool:
        """Check if this is a test command."""
        test_keywords = ["test", "spec", "check", "verify"]
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in test_keywords)

    def transform_command(
        self, command: str, language: str, build_system: str | None = None
    ) -> str | None:
        """Transform a generic build/test command to language-specific one."""
        if language not in self.build_mappings:
            return None

        build_config = self.build_mappings[language]

        # Determine if this is a test or build command
        is_test = self.is_test_command(command)

        if is_test:
            commands = build_config.get("test_commands", {})
        else:
            commands = build_config.get("build_commands", {})

        # If build system is detected, prefer that
        if build_system and build_system in commands:
            return commands[build_system]

        # Otherwise, return the first available command
        if commands:
            return list(commands.values())[0]

        return None

    def get_available_commands(self, language: str) -> dict[str, list[str]]:
        """Get all available build and test commands for a language."""
        if language not in self.build_mappings:
            return {}

        build_config = self.build_mappings[language]
        return {
            "test": list(build_config.get("test_commands", {}).values()),
            "build": list(build_config.get("build_commands", {}).values()),
        }


def main():
    """Main entry point for the language-aware build checker hook."""
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
        build_checker = LanguageAwareBuildChecker()

        # Check if we should intercept this command
        if not build_checker.should_intercept(command):
            return

        # Detect primary language and build system
        language = detector.get_primary_language()
        build_system = detector.detect_build_system()

        if not language:
            print(
                "ℹ️  No programming language detected in current directory",
                file=sys.stderr,
            )
            return

        # Try to transform the command
        new_command = build_checker.transform_command(command, language, build_system)

        if new_command and new_command != command:
            # Provide feedback about the transformation
            action = "Testing" if build_checker.is_test_command(command) else "Building"
            print(f"🔨 {action}: Using {language} → {new_command}", file=sys.stderr)

            # Get all available commands
            available = build_checker.get_available_commands(language)
            if available:
                if available.get("test"):
                    print(
                        f"   Available test commands: {', '.join(available['test'])}",
                        file=sys.stderr,
                    )
                if available.get("build"):
                    print(
                        f"   Available build commands: {', '.join(available['build'])}",
                        file=sys.stderr,
                    )

            # Note: We can't modify the command directly in pre-tool-use hooks
            # But we provide feedback that Claude can see
            response = {
                "continue": True,
                "suppressOutput": False,
                "metadata": {
                    "detected_language": language,
                    "detected_build_system": build_system,
                    "suggested_command": new_command,
                    "available_commands": available,
                },
            }
            print(json.dumps(response))

    except Exception as e:
        # Fail safely - don't block execution
        print(f"Language-aware build checker hook error: {e!s}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
