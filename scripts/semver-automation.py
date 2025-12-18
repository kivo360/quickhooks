#!/usr/bin/env python3
"""
Automated SemVer versioning using Groq API to analyze git changes.

This script analyzes git commits and determines the appropriate semantic version bump
based on the complexity and nature of changes using AI analysis.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum

import toml
from groq import Groq
from pydantic import BaseModel, Field

# Add path to access quickhooks utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from quickhooks.utils.jinja_utils import TemplateRenderer


class VersionBumpType(str, Enum):
    """Types of version bumps in semantic versioning."""

    MAJOR = "major"  # Breaking changes
    MINOR = "minor"  # New features, backwards compatible
    PATCH = "patch"  # Bug fixes, backwards compatible
    NONE = "none"  # No version change needed


class CommitAnalysis(BaseModel):
    """Analysis of commit changes."""

    breaking_changes: bool = Field(description="Whether changes are breaking")
    new_features: bool = Field(description="Whether new features were added")
    bug_fixes: bool = Field(description="Whether bugs were fixed")
    documentation_only: bool = Field(
        description="Whether changes are documentation only"
    )
    test_only: bool = Field(description="Whether changes are test-only")
    refactor_only: bool = Field(description="Whether changes are refactoring only")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in analysis")
    reasoning: str = Field(description="Detailed reasoning for the analysis")
    suggested_bump: VersionBumpType = Field(description="Suggested version bump type")


@dataclass
class GitChange:
    """Represents a git change."""

    commit_hash: str
    message: str
    diff: str
    files_changed: list[str]
    insertions: int
    deletions: int


class SemVerAnalyzer:
    """Analyzes git changes and determines semantic version bumps."""

    def __init__(self, groq_api_key: str | None = None, conservative_mode: bool = True):
        """Initialize the analyzer."""
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY must be provided or set as environment variable"
            )

        self.client = Groq(api_key=self.groq_api_key)
        self.reasoning_model = "qwen/qwen-2.5-72b-instruct"  # Primary reasoning model with reasoning capability
        self.verification_model = (
            "llama-3.1-8b-instant"  # Fast verification/evaluation model
        )
        self.conservative_mode = conservative_mode

        # Conservative thresholds
        self.confidence_thresholds = {
            VersionBumpType.MAJOR: 0.95,  # Very high confidence required for breaking changes
            VersionBumpType.MINOR: 0.80,  # High confidence for features
            VersionBumpType.PATCH: 0.60,  # Moderate confidence for fixes
            VersionBumpType.NONE: 0.40,  # Low threshold for no change
        }

        # Initialize QuickHooks template renderer
        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.template_renderer = TemplateRenderer(template_dir=template_dir)

        # Get project info for templates
        self.project_name = self._get_project_name()
        self.current_version = self._get_current_version()

    def get_git_changes(
        self, from_ref: str = "HEAD~1", to_ref: str = "HEAD"
    ) -> list[GitChange]:
        """Get git changes between two references."""
        try:
            # Get commit information
            cmd = [
                "git",
                "log",
                f"{from_ref}..{to_ref}",
                "--pretty=format:%H|%s",
                "--name-only",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if not result.stdout.strip():
                return []

            changes = []
            lines = result.stdout.strip().split("\n")

            i = 0
            while i < len(lines):
                if "|" in lines[i]:
                    hash_msg = lines[i].split("|", 1)
                    commit_hash = hash_msg[0]
                    message = hash_msg[1] if len(hash_msg) > 1 else ""

                    # Collect file names until next commit or end
                    files = []
                    i += 1
                    while i < len(lines) and "|" not in lines[i] and lines[i].strip():
                        files.append(lines[i].strip())
                        i += 1

                    # Get diff for this commit
                    diff_cmd = [
                        "git",
                        "show",
                        commit_hash,
                        "--pretty=format:",
                        "--name-only",
                    ]
                    subprocess.run(
                        diff_cmd, capture_output=True, text=True, check=False
                    )

                    # Get detailed diff
                    full_diff_cmd = ["git", "show", commit_hash]
                    full_diff_result = subprocess.run(
                        full_diff_cmd, capture_output=True, text=True, check=False
                    )

                    # Get stats
                    stats_cmd = ["git", "show", "--stat", commit_hash]
                    stats_result = subprocess.run(
                        stats_cmd, capture_output=True, text=True, check=False
                    )

                    # Parse insertions/deletions from stats
                    insertions, deletions = self._parse_git_stats(stats_result.stdout)

                    changes.append(
                        GitChange(
                            commit_hash=commit_hash,
                            message=message,
                            diff=full_diff_result.stdout,
                            files_changed=files,
                            insertions=insertions,
                            deletions=deletions,
                        )
                    )
                else:
                    i += 1

            return changes

        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            return []

    def _parse_git_stats(self, stats_output: str) -> tuple[int, int]:
        """Parse insertions and deletions from git stats output."""
        insertions = 0
        deletions = 0

        # Look for patterns like "5 files changed, 123 insertions(+), 45 deletions(-)"
        stats_pattern = r"(\d+) insertion[s]?\(\+\)|(\d+) deletion[s]?\(\-\)"
        matches = re.findall(stats_pattern, stats_output)

        for match in matches:
            if match[0]:  # insertions
                insertions += int(match[0])
            if match[1]:  # deletions
                deletions += int(match[1])

        return insertions, deletions

    def analyze_changes(self, changes: list[GitChange]) -> CommitAnalysis:
        """Analyze git changes using dual-model critique system."""
        if not changes:
            return CommitAnalysis(
                breaking_changes=False,
                new_features=False,
                bug_fixes=False,
                documentation_only=False,
                test_only=False,
                refactor_only=False,
                confidence=1.0,
                reasoning="No changes to analyze",
                suggested_bump=VersionBumpType.NONE,
            )

        try:
            # Step 1: Reasoning phase - Use qwen to create step-by-step reasoning
            reasoning_output = self._perform_reasoning_analysis(changes)

            # Step 2: Verification phase - Use llama to verify and evaluate the reasoning
            final_analysis = self._perform_verification_analysis(
                changes, reasoning_output
            )

            # Step 3: Apply conservative bias if enabled
            final_analysis = self._apply_conservative_bias(final_analysis)

            return final_analysis

        except Exception as e:
            print(f"Error analyzing changes with Groq: {e}")
            # Fallback to conservative heuristic analysis
            return self._heuristic_analysis(changes)

    def _perform_reasoning_analysis(self, changes: list[GitChange]) -> str:
        """Step 1: Use qwen to create detailed step-by-step reasoning."""
        reasoning_prompt = self._build_reasoning_prompt(changes)

        response = self.client.chat.completions.create(
            model=self.reasoning_model,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert software engineering analyst specializing in semantic versioning. 
                    
                    Your task is to create a DETAILED, STEP-BY-STEP reasoning process for analyzing git commits 
                    to determine the appropriate semantic version bump.
                    
                    Break down your analysis into clear steps:
                    1. Change categorization
                    2. Impact assessment  
                    3. API analysis
                    4. Breaking change evaluation
                    5. Feature vs fix determination
                    6. Confidence assessment
                    7. Final recommendation with reasoning
                    
                    Be thorough and methodical. Explain your reasoning at each step.""",
                },
                {"role": "user", "content": reasoning_prompt},
            ],
            temperature=0.2,  # Allow some creativity in reasoning
            max_tokens=2000,  # More space for detailed reasoning
            extra_body={
                "reasoning_effort": "default"  # Enable reasoning mode for qwen
            },
        )

        return response.choices[0].message.content

    def _perform_verification_analysis(
        self, changes: list[GitChange], reasoning_output: str
    ) -> CommitAnalysis:
        """Step 2: Use llama to verify and evaluate the reasoning, producing final analysis."""
        verification_prompt = self._build_verification_prompt(changes, reasoning_output)

        response = self.client.chat.completions.create(
            model=self.verification_model,
            messages=[
                {
                    "role": "system",
                    "content": """You are a verification specialist reviewing semantic versioning analysis.
                    
                    Your job is to:
                    1. Evaluate the provided reasoning for accuracy and completeness
                    2. Identify any logical errors or oversights  
                    3. Apply conservative principles to reduce version bumps when appropriate
                    4. Provide a final, verified analysis
                    
                    Conservative verification principles:
                    - MAJOR: Only for clear, documented breaking API changes
                    - MINOR: Only for substantial new user-facing functionality
                    - PATCH: For bug fixes and small improvements
                    - NONE: For docs, tests, internal refactoring
                    
                    Respond ONLY with valid JSON matching the CommitAnalysis schema.""",
                },
                {"role": "user", "content": verification_prompt},
            ],
            temperature=0.05,  # Very low temperature for verification
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        analysis_json = json.loads(response.choices[0].message.content)
        return CommitAnalysis(**analysis_json)

    def _apply_conservative_bias(self, analysis: CommitAnalysis) -> CommitAnalysis:
        """Apply additional conservative bias to the analysis."""
        if not self.conservative_mode:
            return analysis

        # Check if confidence meets threshold for suggested bump
        required_confidence = self.confidence_thresholds.get(
            analysis.suggested_bump, 0.5
        )

        if analysis.confidence < required_confidence:
            # Downgrade to lower bump type
            if analysis.suggested_bump == VersionBumpType.MAJOR:
                downgraded_bump = VersionBumpType.MINOR
                reasoning_addendum = " [CONSERVATIVE: Downgraded from MAJOR to MINOR due to insufficient confidence]"
            elif analysis.suggested_bump == VersionBumpType.MINOR:
                downgraded_bump = VersionBumpType.PATCH
                reasoning_addendum = " [CONSERVATIVE: Downgraded from MINOR to PATCH due to insufficient confidence]"
            elif analysis.suggested_bump == VersionBumpType.PATCH:
                downgraded_bump = VersionBumpType.NONE
                reasoning_addendum = " [CONSERVATIVE: Downgraded from PATCH to NONE due to insufficient confidence]"
            else:
                downgraded_bump = analysis.suggested_bump
                reasoning_addendum = ""

            return CommitAnalysis(
                breaking_changes=analysis.breaking_changes,
                new_features=analysis.new_features,
                bug_fixes=analysis.bug_fixes,
                documentation_only=analysis.documentation_only,
                test_only=analysis.test_only,
                refactor_only=analysis.refactor_only,
                confidence=analysis.confidence,
                reasoning=analysis.reasoning + reasoning_addendum,
                suggested_bump=downgraded_bump,
            )

        return analysis

    def _get_project_name(self) -> str:
        """Get project name from pyproject.toml."""
        try:
            pyproject_path = os.path.join(
                os.path.dirname(__file__), "..", "pyproject.toml"
            )
            with open(pyproject_path) as f:
                pyproject = toml.load(f)
                return pyproject.get("project", {}).get("name", "Python Package")
        except Exception:
            return "Python Package"

    def _get_current_version(self) -> str:
        """Get current version from pyproject.toml."""
        try:
            pyproject_path = os.path.join(
                os.path.dirname(__file__), "..", "pyproject.toml"
            )
            with open(pyproject_path) as f:
                pyproject = toml.load(f)
                return pyproject.get("project", {}).get("version", "0.0.0")
        except Exception:
            return "0.0.0"

    def _build_reasoning_prompt(self, changes: list[GitChange]) -> str:
        """Build reasoning prompt using Jinja2 template."""
        # Prepare changes with diff samples
        template_changes = []
        for change in changes:
            diff_sample = None
            if change.diff:
                diff_sample = (
                    change.diff[:1500] + "...[truncated]"
                    if len(change.diff) > 1500
                    else change.diff
                )

            template_changes.append(
                {
                    "commit_hash": change.commit_hash,
                    "message": change.message,
                    "files_changed": change.files_changed,
                    "insertions": change.insertions,
                    "deletions": change.deletions,
                    "diff_sample": diff_sample,
                }
            )

        return self.template_renderer.render(
            "prompts/semver_reasoning.j2",
            project_name=self.project_name,
            current_version=self.current_version,
            changes=template_changes,
        )

    def _build_verification_prompt(
        self, changes: list[GitChange], reasoning_output: str
    ) -> str:
        """Build verification prompt using Jinja2 template."""
        # Prepare changes for template
        template_changes = []
        for change in changes:
            template_changes.append(
                {
                    "commit_hash": change.commit_hash,
                    "message": change.message,
                    "files_changed": change.files_changed,
                    "insertions": change.insertions,
                    "deletions": change.deletions,
                }
            )

        return self.template_renderer.render(
            "prompts/semver_verification.j2",
            reasoning_output=reasoning_output,
            changes=template_changes,
        )

    def _heuristic_analysis(self, changes: list[GitChange]) -> CommitAnalysis:
        """Fallback heuristic analysis when API fails."""
        breaking_changes = False
        new_features = False
        bug_fixes = False
        documentation_only = True
        test_only = True
        refactor_only = True

        for change in changes:
            message = change.message.lower()

            # Check commit message patterns
            if any(
                pattern in message for pattern in ["breaking change", "major:", "!:"]
            ):
                breaking_changes = True
                documentation_only = False
                test_only = False
                refactor_only = False

            if any(
                pattern in message for pattern in ["feat:", "feature:", "add:", "new:"]
            ):
                new_features = True
                documentation_only = False
                test_only = False

            if any(
                pattern in message for pattern in ["fix:", "bug:", "patch:", "hotfix:"]
            ):
                bug_fixes = True
                documentation_only = False
                test_only = False

            # Check file patterns
            for file_path in change.files_changed:
                if not any(
                    pattern in file_path
                    for pattern in ["README", "docs/", ".md", "LICENSE"]
                ):
                    documentation_only = False

                if not file_path.startswith("test") and "test" not in file_path:
                    test_only = False

                if file_path.startswith("src/") or file_path.endswith(".py"):
                    if (
                        change.insertions > change.deletions * 2
                    ):  # Significant additions
                        new_features = True
                        refactor_only = False

        # Determine suggested bump
        if breaking_changes:
            suggested_bump = VersionBumpType.MAJOR
        elif new_features:
            suggested_bump = VersionBumpType.MINOR
        elif bug_fixes:
            suggested_bump = VersionBumpType.PATCH
        elif documentation_only or test_only:
            suggested_bump = VersionBumpType.NONE
        else:
            suggested_bump = VersionBumpType.PATCH  # Default safe choice

        return CommitAnalysis(
            breaking_changes=breaking_changes,
            new_features=new_features,
            bug_fixes=bug_fixes,
            documentation_only=documentation_only,
            test_only=test_only,
            refactor_only=refactor_only,
            confidence=0.7,  # Lower confidence for heuristic
            reasoning="Heuristic analysis based on commit messages and file patterns",
            suggested_bump=suggested_bump,
        )

    def get_current_version(self, pyproject_path: str = "pyproject.toml") -> str:
        """Get current version from pyproject.toml."""
        try:
            with open(pyproject_path) as f:
                data = toml.load(f)
            return data["project"]["version"]
        except Exception as e:
            print(f"Error reading version from {pyproject_path}: {e}")
            return "0.0.0"

    def bump_version(self, current_version: str, bump_type: VersionBumpType) -> str:
        """Bump version according to semantic versioning."""
        if bump_type == VersionBumpType.NONE:
            return current_version

        try:
            major, minor, patch = map(int, current_version.split("."))
        except ValueError:
            print(f"Invalid version format: {current_version}")
            return current_version

        if bump_type == VersionBumpType.MAJOR:
            return f"{major + 1}.0.0"
        if bump_type == VersionBumpType.MINOR:
            return f"{major}.{minor + 1}.0"
        if bump_type == VersionBumpType.PATCH:
            return f"{major}.{minor}.{patch + 1}"

        return current_version

    def update_pyproject_version(
        self, new_version: str, pyproject_path: str = "pyproject.toml"
    ) -> bool:
        """Update version in pyproject.toml."""
        try:
            with open(pyproject_path) as f:
                data = toml.load(f)

            data["project"]["version"] = new_version

            with open(pyproject_path, "w") as f:
                toml.dump(data, f)

            print(f"Updated version to {new_version} in {pyproject_path}")
            return True

        except Exception as e:
            print(f"Error updating version in {pyproject_path}: {e}")
            return False


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated SemVer versioning using AI analysis"
    )
    parser.add_argument(
        "--from-ref", default="HEAD~1", help="Git reference to compare from"
    )
    parser.add_argument("--to-ref", default="HEAD", help="Git reference to compare to")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show analysis without updating version"
    )
    parser.add_argument(
        "--pyproject", default="pyproject.toml", help="Path to pyproject.toml file"
    )
    parser.add_argument(
        "--groq-api-key", help="Groq API key (or set GROQ_API_KEY env var)"
    )
    parser.add_argument(
        "--conservative",
        action="store_true",
        default=True,
        help="Use conservative mode (default: True)",
    )
    parser.add_argument(
        "--aggressive", action="store_true", help="Disable conservative mode"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Determine conservative mode
    conservative_mode = args.conservative and not args.aggressive

    try:
        analyzer = SemVerAnalyzer(
            groq_api_key=args.groq_api_key, conservative_mode=conservative_mode
        )

        if args.verbose:
            print(f"Analyzing changes from {args.from_ref} to {args.to_ref}")
            print(f"Conservative mode: {'ON' if conservative_mode else 'OFF'}")
            print(f"Reasoning model: {analyzer.reasoning_model}")
            print(f"Verification model: {analyzer.verification_model}")

        # Get git changes
        changes = analyzer.get_git_changes(args.from_ref, args.to_ref)

        if not changes:
            print("No changes found.")
            return 0

        if args.verbose:
            print(f"Found {len(changes)} commits to analyze")
            for change in changes:
                print(f"  {change.commit_hash[:8]}: {change.message}")

        # Analyze changes
        analysis = analyzer.analyze_changes(changes)

        # Get current version
        current_version = analyzer.get_current_version(args.pyproject)
        new_version = analyzer.bump_version(current_version, analysis.suggested_bump)

        # Output results
        print("\n=== SEMVER ANALYSIS ===")
        print(f"Current version: {current_version}")
        print(f"Suggested bump: {analysis.suggested_bump.value}")
        print(f"New version: {new_version}")
        print(f"Confidence: {analysis.confidence:.2f}")
        print(f"\nReasoning: {analysis.reasoning}")

        print("\nChange Analysis:")
        print(f"  Breaking changes: {analysis.breaking_changes}")
        print(f"  New features: {analysis.new_features}")
        print(f"  Bug fixes: {analysis.bug_fixes}")
        print(f"  Documentation only: {analysis.documentation_only}")
        print(f"  Test only: {analysis.test_only}")
        print(f"  Refactor only: {analysis.refactor_only}")

        if analysis.suggested_bump == VersionBumpType.NONE:
            print("\nNo version bump needed.")
            return 0

        if args.dry_run:
            print(
                f"\n[DRY RUN] Would update version from {current_version} to {new_version}"
            )
            return 0

        # Update version
        if analyzer.update_pyproject_version(new_version, args.pyproject):
            print(f"\n✅ Successfully updated version to {new_version}")

            # Output JSON for CI/CD integration
            output = {
                "old_version": current_version,
                "new_version": new_version,
                "bump_type": analysis.suggested_bump.value,
                "confidence": analysis.confidence,
                "reasoning": analysis.reasoning,
            }

            with open("semver-output.json", "w") as f:
                json.dump(output, f, indent=2)

            print("Wrote analysis to semver-output.json")
            return 0
        print("❌ Failed to update version")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
