#!/usr/bin/env python3
"""
QuickHook: Intelligent Tool Selector with AI-Powered Caching
Uses st (directory indexing) and AI to analyze codebases and select optimal tools.

This hook maintains a cache of tool decisions and uses AI to analyze new projects.
"""

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from groq import Groq
except ImportError:
    Groq = None


class ToolCategory(str, Enum):
    """Categories of development tools."""

    LINTER = "linter"
    FORMATTER = "formatter"
    TEST_RUNNER = "test_runner"
    BUILD_TOOL = "build_tool"
    TYPE_CHECKER = "type_checker"
    AUTO_FIXER = "auto_fixer"


@dataclass
class ToolDecision:
    """Represents a tool selection decision."""

    project_hash: str
    language: str
    category: ToolCategory
    selected_tool: str
    command: str
    confidence: float
    reasons: list[str]
    detected_configs: list[str]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)


@dataclass
class ProjectAnalysis:
    """Results of project analysis."""

    primary_language: str
    languages: list[str]
    structure_hash: str
    config_files: list[str]
    dependencies: dict[str, list[str]]
    project_type: str  # web, cli, library, etc.
    framework: str | None
    test_framework: str | None
    build_system: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CodebaseAnalyzer:
    """Analyzes codebases using st tool and file inspection."""

    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def run_st_analysis(self) -> dict[str, Any]:
        """Run st tool to get project structure and statistics."""
        analyses = {}

        # Run different st commands for comprehensive analysis
        st_commands = [
            ("project_overview", ["st", "project-overview", str(self.cwd)]),
            ("statistics", ["st", "get-statistics", str(self.cwd)]),
            (
                "code_files",
                ["st", "find-code-files", "--languages", "all", str(self.cwd)],
            ),
            ("config_files", ["st", "find-config-files", str(self.cwd)]),
            ("build_files", ["st", "find-build-files", str(self.cwd)]),
            ("test_files", ["st", "find-tests", str(self.cwd)]),
            ("semantic", ["st", "semantic-analysis", str(self.cwd)]),
        ]

        for name, cmd in st_commands:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=10, check=False
                )
                if result.returncode == 0:
                    try:
                        analyses[name] = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        analyses[name] = {"raw": result.stdout}
                else:
                    analyses[name] = {"error": result.stderr}
            except Exception as e:
                analyses[name] = {"error": str(e)}

        return analyses

    def analyze_package_files(self) -> dict[str, list[str]]:
        """Analyze package files to detect dependencies."""
        dependencies = {}

        # Python dependencies
        if (self.cwd / "requirements.txt").exists():
            with open(self.cwd / "requirements.txt") as f:
                deps = [
                    line.strip().split("==")[0]
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
                dependencies["python"] = deps

        if (self.cwd / "pyproject.toml").exists():
            try:
                import tomllib

                with open(self.cwd / "pyproject.toml", "rb") as f:
                    data = tomllib.load(f)
                    deps = []
                    if "project" in data and "dependencies" in data["project"]:
                        deps.extend(data["project"]["dependencies"])
                    if (
                        "tool" in data
                        and "poetry" in data["tool"]
                        and "dependencies" in data["tool"]["poetry"]
                    ):
                        deps.extend(data["tool"]["poetry"]["dependencies"].keys())
                    dependencies["python"] = deps
            except:
                pass

        # JavaScript/TypeScript dependencies
        if (self.cwd / "package.json").exists():
            try:
                with open(self.cwd / "package.json") as f:
                    data = json.load(f)
                    deps = []
                    if "dependencies" in data:
                        deps.extend(data["dependencies"].keys())
                    if "devDependencies" in data:
                        deps.extend(data["devDependencies"].keys())
                    dependencies["javascript"] = deps
            except:
                pass

        # Go dependencies
        if (self.cwd / "go.mod").exists():
            try:
                with open(self.cwd / "go.mod") as f:
                    deps = []
                    for line in f:
                        if line.strip().startswith("require"):
                            # Parse require block
                            continue
                        if "\t" in line and "/" in line:
                            dep = line.split()[0]
                            deps.append(dep)
                    dependencies["go"] = deps
            except:
                pass

        # Rust dependencies
        if (self.cwd / "Cargo.toml").exists():
            try:
                import tomllib

                with open(self.cwd / "Cargo.toml", "rb") as f:
                    data = tomllib.load(f)
                    deps = []
                    if "dependencies" in data:
                        deps.extend(data["dependencies"].keys())
                    if "dev-dependencies" in data:
                        deps.extend(data["dev-dependencies"].keys())
                    dependencies["rust"] = deps
            except:
                pass

        return dependencies

    def detect_framework(self, language: str, dependencies: list[str]) -> str | None:
        """Detect the framework being used based on dependencies."""
        frameworks = {
            "python": {
                "django": ["django"],
                "flask": ["flask"],
                "fastapi": ["fastapi"],
                "pytest": ["pytest"],
                "unittest": [],  # Built-in
            },
            "javascript": {
                "react": ["react", "react-dom"],
                "vue": ["vue"],
                "angular": ["@angular/core"],
                "express": ["express"],
                "nextjs": ["next"],
                "jest": ["jest"],
                "mocha": ["mocha"],
            },
            "go": {
                "gin": ["github.com/gin-gonic/gin"],
                "echo": ["github.com/labstack/echo"],
                "fiber": ["github.com/gofiber/fiber"],
            },
            "rust": {
                "actix": ["actix-web"],
                "rocket": ["rocket"],
                "tokio": ["tokio"],
            },
        }

        if language not in frameworks:
            return None

        for framework, markers in frameworks[language].items():
            if not markers:  # Built-in framework
                continue
            if any(marker in dep.lower() for dep in dependencies for marker in markers):
                return framework

        return None

    def calculate_structure_hash(self, st_analysis: dict[str, Any]) -> str:
        """Calculate a hash of the project structure for caching."""
        # Create a stable representation of project structure
        structure_data = {
            "files": st_analysis.get("statistics", {}).get("total_files", 0),
            "languages": st_analysis.get("statistics", {}).get("languages", {}),
            "config_files": sorted(
                st_analysis.get("config_files", {}).get("files", [])
            ),
            "build_files": sorted(st_analysis.get("build_files", {}).get("files", [])),
        }

        structure_str = json.dumps(structure_data, sort_keys=True)
        return hashlib.sha256(structure_str.encode()).hexdigest()[:16]

    def analyze(self) -> ProjectAnalysis:
        """Perform comprehensive project analysis."""
        # Run st analysis
        st_analysis = self.run_st_analysis()

        # Analyze dependencies
        dependencies = self.analyze_package_files()

        # Determine primary language
        stats = st_analysis.get("statistics", {})
        language_stats = stats.get("languages", {})
        primary_language = (
            max(language_stats.items(), key=lambda x: x[1])[0]
            if language_stats
            else "unknown"
        )

        # Get all languages
        languages = list(language_stats.keys())

        # Calculate structure hash
        structure_hash = self.calculate_structure_hash(st_analysis)

        # Get config files
        config_files = [
            f["path"] for f in st_analysis.get("config_files", {}).get("files", [])
        ]

        # Detect framework
        primary_deps = dependencies.get(primary_language, [])
        framework = self.detect_framework(primary_language, primary_deps)

        # Detect test framework
        test_framework = None
        if framework in ["pytest", "jest", "mocha"]:
            test_framework = framework

        # Detect build system
        build_files = st_analysis.get("build_files", {}).get("files", [])
        build_system = None
        for bf in build_files:
            name = Path(bf["path"]).name
            if name == "Makefile":
                build_system = "make"
                break
            if name == "CMakeLists.txt":
                build_system = "cmake"
                break
            if name in ["pom.xml"]:
                build_system = "maven"
                break
            if name in ["build.gradle", "build.gradle.kts"]:
                build_system = "gradle"
                break

        # Determine project type
        project_type = "library"  # default
        if framework in [
            "django",
            "flask",
            "fastapi",
            "express",
            "nextjs",
            "gin",
            "echo",
            "actix",
        ]:
            project_type = "web"
        elif any(
            "cli" in dep.lower() or "click" in dep.lower()
            for deps in dependencies.values()
            for dep in deps
        ):
            project_type = "cli"

        return ProjectAnalysis(
            primary_language=primary_language,
            languages=languages,
            structure_hash=structure_hash,
            config_files=config_files,
            dependencies=dependencies,
            project_type=project_type,
            framework=framework,
            test_framework=test_framework,
            build_system=build_system,
        )
