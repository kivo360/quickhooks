#!/usr/bin/env python3
"""
QuickHook: Language-Aware Linter
Automatically runs the appropriate linter based on detected programming language.

Supported linters:
- Python: ruff, flake8, pylint
- JavaScript/TypeScript: eslint
- Go: golangci-lint
- Rust: clippy
- Ruby: rubocop
- Java: checkstyle
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class LanguageDetector:
    """Detects programming language from file extensions and config files."""
    
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)
        
    def detect_languages(self) -> List[str]:
        """Detect all programming languages in the current directory."""
        languages = set()
        
        # Check for language-specific config files
        config_mappings = {
            'pyproject.toml': 'python',
            'setup.py': 'python',
            'requirements.txt': 'python',
            'package.json': 'javascript',
            'tsconfig.json': 'typescript',
            'go.mod': 'go',
            'Cargo.toml': 'rust',
            'Gemfile': 'ruby',
            'pom.xml': 'java',
            'build.gradle': 'java',
        }
        
        for config_file, language in config_mappings.items():
            if (self.cwd / config_file).exists():
                languages.add(language)
        
        # Check file extensions in the directory
        extension_mappings = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.java': 'java',
        }
        
        for file in self.cwd.rglob('*'):
            if file.is_file():
                ext = file.suffix.lower()
                if ext in extension_mappings:
                    languages.add(extension_mappings[ext])
        
        return list(languages)
    
    def get_primary_language(self) -> Optional[str]:
        """Get the primary language based on config files and file count."""
        languages = self.detect_languages()
        
        if not languages:
            return None
            
        # Prioritize based on config files
        if 'pyproject.toml' in os.listdir(self.cwd) or 'setup.py' in os.listdir(self.cwd):
            return 'python'
        elif 'package.json' in os.listdir(self.cwd):
            return 'typescript' if 'tsconfig.json' in os.listdir(self.cwd) else 'javascript'
        elif 'go.mod' in os.listdir(self.cwd):
            return 'go'
        elif 'Cargo.toml' in os.listdir(self.cwd):
            return 'rust'
            
        # Return the first detected language
        return languages[0] if languages else None


class LanguageAwareLinter:
    """Transforms generic lint commands to language-specific linters."""
    
    def __init__(self):
        # Map languages to their preferred linters and commands
        self.linter_mappings = {
            'python': {
                'primary': 'ruff',
                'alternatives': ['flake8', 'pylint'],
                'commands': {
                    'ruff': 'ruff check .',
                    'flake8': 'flake8 .',
                    'pylint': 'pylint **/*.py'
                }
            },
            'javascript': {
                'primary': 'eslint',
                'commands': {
                    'eslint': 'npx eslint . --ext .js,.jsx'
                }
            },
            'typescript': {
                'primary': 'eslint',
                'commands': {
                    'eslint': 'npx eslint . --ext .ts,.tsx'
                }
            },
            'go': {
                'primary': 'golangci-lint',
                'commands': {
                    'golangci-lint': 'golangci-lint run ./...'
                }
            },
            'rust': {
                'primary': 'clippy',
                'commands': {
                    'clippy': 'cargo clippy -- -D warnings'
                }
            },
            'ruby': {
                'primary': 'rubocop',
                'commands': {
                    'rubocop': 'rubocop'
                }
            },
            'java': {
                'primary': 'checkstyle',
                'alternatives': ['spotbugs'],
                'commands': {
                    'checkstyle': 'mvn checkstyle:check',
                    'spotbugs': 'mvn spotbugs:check'
                }
            }
        }
    
    def should_intercept(self, command: str) -> bool:
        """Check if this command should be intercepted."""
        lint_keywords = ['lint', 'check', 'analyze', 'validate']
        
        # Check if command contains lint-related keywords
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in lint_keywords)
    
    def transform_command(self, command: str, language: str) -> Optional[str]:
        """Transform a generic lint command to language-specific linter."""
        if language not in self.linter_mappings:
            return None
            
        linter_config = self.linter_mappings[language]
        primary_linter = linter_config['primary']
        
        # If the command already specifies a linter, don't transform
        if any(linter in command for linter in linter_config['commands'].keys()):
            return None
        
        # Return the primary linter command
        return linter_config['commands'][primary_linter]
    
    def get_lint_command_for_file(self, filepath: str) -> Optional[str]:
        """Get appropriate lint command for a specific file."""
        file_ext = Path(filepath).suffix.lower()
        
        ext_to_language = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.java': 'java',
        }
        
        language = ext_to_language.get(file_ext)
        if not language:
            return None
            
        linter_config = self.linter_mappings.get(language)
        if not linter_config:
            return None
            
        # Modify command to target specific file
        primary_linter = linter_config['primary']
        base_command = linter_config['commands'][primary_linter]
        
        # Adjust command for single file
        if language == 'python' and primary_linter == 'ruff':
            return f'ruff check {filepath}'
        elif language in ['javascript', 'typescript'] and primary_linter == 'eslint':
            return f'npx eslint {filepath}'
        elif language == 'go':
            return f'golangci-lint run {filepath}'
        
        return None


def main():
    """Main entry point for the language-aware linter hook."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Extract fields
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        cwd = input_data.get('cwd', '.')
        
        # Only process Bash commands
        if tool_name != 'Bash':
            return
        
        command = tool_input.get('command', '')
        if not command:
            return
        
        # Initialize components
        detector = LanguageDetector(cwd)
        linter = LanguageAwareLinter()
        
        # Check if we should intercept this command
        if not linter.should_intercept(command):
            return
        
        # Detect primary language
        language = detector.get_primary_language()
        if not language:
            print("ℹ️  No programming language detected in current directory", file=sys.stderr)
            return
        
        # Try to transform the command
        new_command = linter.transform_command(command, language)
        
        if new_command and new_command != command:
            # Provide feedback about the transformation
            print(f"🔧 Lint: Using {language} linter → {new_command}", file=sys.stderr)
            
            # Note: We can't modify the command directly in pre-tool-use hooks
            # But we provide feedback that Claude can see
            response = {
                "continue": True,
                "suppressOutput": False,
                "metadata": {
                    "detected_language": language,
                    "suggested_command": new_command
                }
            }
            print(json.dumps(response))
        
    except Exception as e:
        # Fail safely - don't block execution
        print(f"Language-aware linter hook error: {str(e)}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()