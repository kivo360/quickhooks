#!/usr/bin/env python3
"""
QuickHook: Intelligent Tool Selector with AI-Powered Caching
Uses st (directory indexing) and AI to analyze codebases and select optimal tools.

This hook maintains a cache of tool decisions and uses AI to analyze new projects.
"""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
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


class ToolDiscoveryEngine:
    """Discovers and evaluates available tools using AI."""

    # Comprehensive tool database
    TOOL_DATABASE = {
        "python": {
            ToolCategory.LINTER: [
                {
                    "name": "ruff",
                    "command": "ruff check {}",
                    "features": [
                        "fast",
                        "rust-based",
                        "pyflakes",
                        "pycodestyle",
                        "isort",
                    ],
                    "config_files": ["pyproject.toml", "ruff.toml"],
                },
                {
                    "name": "flake8",
                    "command": "flake8 {}",
                    "features": ["traditional", "plugin-ecosystem"],
                    "config_files": [".flake8", "setup.cfg"],
                },
                {
                    "name": "pylint",
                    "command": "pylint {}",
                    "features": ["comprehensive", "configurable", "slow"],
                    "config_files": [".pylintrc", "pyproject.toml"],
                },
                {
                    "name": "mypy",
                    "command": "mypy {}",
                    "features": ["type-checking", "gradual-typing"],
                    "config_files": ["mypy.ini", "pyproject.toml"],
                },
            ],
            ToolCategory.FORMATTER: [
                {
                    "name": "black",
                    "command": "black {}",
                    "features": ["opinionated", "consistent", "popular"],
                    "config_files": ["pyproject.toml"],
                },
                {
                    "name": "ruff",
                    "command": "ruff format {}",
                    "features": ["fast", "black-compatible"],
                    "config_files": ["pyproject.toml", "ruff.toml"],
                },
                {
                    "name": "autopep8",
                    "command": "autopep8 --in-place {}",
                    "features": ["pep8-focused", "conservative"],
                    "config_files": ["setup.cfg"],
                },
                {
                    "name": "yapf",
                    "command": "yapf -i {}",
                    "features": ["configurable", "google-style"],
                    "config_files": [".style.yapf", "setup.cfg"],
                },
            ],
            ToolCategory.TEST_RUNNER: [
                {
                    "name": "pytest",
                    "command": "pytest {}",
                    "features": ["popular", "plugins", "fixtures"],
                    "config_files": ["pytest.ini", "pyproject.toml"],
                },
                {
                    "name": "unittest",
                    "command": "python -m unittest {}",
                    "features": ["built-in", "standard"],
                    "config_files": [],
                },
                {
                    "name": "nose2",
                    "command": "nose2 {}",
                    "features": ["extensible", "unittest-compatible"],
                    "config_files": ["nose2.cfg"],
                },
                {
                    "name": "tox",
                    "command": "tox",
                    "features": ["multi-env", "matrix-testing"],
                    "config_files": ["tox.ini"],
                },
            ],
            ToolCategory.BUILD_TOOL: [
                {
                    "name": "setuptools",
                    "command": "python setup.py build",
                    "features": ["standard", "legacy"],
                    "config_files": ["setup.py", "setup.cfg"],
                },
                {
                    "name": "poetry",
                    "command": "poetry build",
                    "features": ["modern", "dependency-resolution"],
                    "config_files": ["pyproject.toml"],
                },
                {
                    "name": "hatch",
                    "command": "hatch build",
                    "features": ["pep517", "environments"],
                    "config_files": ["pyproject.toml"],
                },
                {
                    "name": "flit",
                    "command": "flit build",
                    "features": ["simple", "pep517"],
                    "config_files": ["pyproject.toml"],
                },
            ],
            ToolCategory.TYPE_CHECKER: [
                {
                    "name": "mypy",
                    "command": "mypy {}",
                    "features": ["static-typing", "gradual"],
                    "config_files": ["mypy.ini", "pyproject.toml"],
                },
                {
                    "name": "pyright",
                    "command": "pyright {}",
                    "features": ["microsoft", "fast", "vscode"],
                    "config_files": ["pyrightconfig.json"],
                },
                {
                    "name": "pyre",
                    "command": "pyre check",
                    "features": ["facebook", "incremental"],
                    "config_files": [".pyre_configuration"],
                },
            ],
        },
        "javascript": {
            ToolCategory.LINTER: [
                {
                    "name": "eslint",
                    "command": "npx eslint {}",
                    "features": ["configurable", "plugins", "popular"],
                    "config_files": [".eslintrc.js", ".eslintrc.json"],
                },
                {
                    "name": "standard",
                    "command": "npx standard {}",
                    "features": ["zero-config", "opinionated"],
                    "config_files": [],
                },
                {
                    "name": "jshint",
                    "command": "npx jshint {}",
                    "features": ["legacy", "simple"],
                    "config_files": [".jshintrc"],
                },
            ],
            ToolCategory.FORMATTER: [
                {
                    "name": "prettier",
                    "command": "npx prettier --write {}",
                    "features": ["popular", "opinionated", "multi-language"],
                    "config_files": [".prettierrc", "prettier.config.js"],
                },
                {
                    "name": "standard",
                    "command": "npx standard --fix {}",
                    "features": ["zero-config", "includes-linting"],
                    "config_files": [],
                },
            ],
            ToolCategory.TEST_RUNNER: [
                {
                    "name": "jest",
                    "command": "npx jest {}",
                    "features": ["popular", "snapshot-testing", "coverage"],
                    "config_files": ["jest.config.js"],
                },
                {
                    "name": "mocha",
                    "command": "npx mocha {}",
                    "features": ["flexible", "async", "browser-compatible"],
                    "config_files": [".mocharc.js"],
                },
                {
                    "name": "vitest",
                    "command": "npx vitest {}",
                    "features": ["vite-native", "fast", "jest-compatible"],
                    "config_files": ["vitest.config.js"],
                },
            ],
            ToolCategory.BUILD_TOOL: [
                {
                    "name": "webpack",
                    "command": "npx webpack",
                    "features": ["bundler", "plugins", "loaders"],
                    "config_files": ["webpack.config.js"],
                },
                {
                    "name": "vite",
                    "command": "npx vite build",
                    "features": ["fast", "esm", "modern"],
                    "config_files": ["vite.config.js"],
                },
                {
                    "name": "rollup",
                    "command": "npx rollup -c",
                    "features": ["tree-shaking", "esm", "library-focused"],
                    "config_files": ["rollup.config.js"],
                },
                {
                    "name": "esbuild",
                    "command": "npx esbuild",
                    "features": ["ultra-fast", "go-based"],
                    "config_files": [],
                },
            ],
        },
        "typescript": {
            ToolCategory.TYPE_CHECKER: [
                {
                    "name": "tsc",
                    "command": "npx tsc --noEmit",
                    "features": ["official", "comprehensive"],
                    "config_files": ["tsconfig.json"],
                },
            ],
        },
        "go": {
            ToolCategory.LINTER: [
                {
                    "name": "golangci-lint",
                    "command": "golangci-lint run {}",
                    "features": ["meta-linter", "fast", "configurable"],
                    "config_files": [".golangci.yml"],
                },
                {
                    "name": "go-vet",
                    "command": "go vet {}",
                    "features": ["built-in", "basic"],
                    "config_files": [],
                },
                {
                    "name": "staticcheck",
                    "command": "staticcheck {}",
                    "features": ["advanced", "performance"],
                    "config_files": ["staticcheck.conf"],
                },
            ],
            ToolCategory.FORMATTER: [
                {
                    "name": "gofmt",
                    "command": "gofmt -w {}",
                    "features": ["official", "standard"],
                    "config_files": [],
                },
                {
                    "name": "goimports",
                    "command": "goimports -w {}",
                    "features": ["imports-management", "gofmt-compatible"],
                    "config_files": [],
                },
            ],
            ToolCategory.TEST_RUNNER: [
                {
                    "name": "go-test",
                    "command": "go test {}",
                    "features": ["built-in", "coverage", "benchmarks"],
                    "config_files": [],
                },
                {
                    "name": "ginkgo",
                    "command": "ginkgo {}",
                    "features": ["bdd", "parallel", "watch-mode"],
                    "config_files": [],
                },
            ],
            ToolCategory.BUILD_TOOL: [
                {
                    "name": "go-build",
                    "command": "go build {}",
                    "features": ["official", "cross-compile"],
                    "config_files": ["go.mod"],
                },
            ],
        },
        "rust": {
            ToolCategory.LINTER: [
                {
                    "name": "clippy",
                    "command": "cargo clippy -- -D warnings",
                    "features": ["official", "comprehensive", "pedantic"],
                    "config_files": ["clippy.toml"],
                },
            ],
            ToolCategory.FORMATTER: [
                {
                    "name": "rustfmt",
                    "command": "cargo fmt",
                    "features": ["official", "configurable"],
                    "config_files": ["rustfmt.toml"],
                },
            ],
            ToolCategory.TEST_RUNNER: [
                {
                    "name": "cargo-test",
                    "command": "cargo test",
                    "features": ["built-in", "doc-tests", "benchmarks"],
                    "config_files": [],
                },
            ],
            ToolCategory.BUILD_TOOL: [
                {
                    "name": "cargo",
                    "command": "cargo build",
                    "features": ["official", "dependencies", "workspaces"],
                    "config_files": ["Cargo.toml"],
                },
            ],
        },
    }

    def __init__(self, groq_client: Any | None = None):
        self.groq_client = groq_client

    def check_tool_availability(self, tool_command: str) -> bool:
        """Check if a tool is available in the system."""
        try:
            # Extract the base command (first part before space)
            base_cmd = tool_command.split()[0]

            # Special handling for npx commands
            if base_cmd == "npx":
                # Check if npm/npx is available
                result = subprocess.run(
                    ["which", "npx"], capture_output=True, text=True, check=False
                )
                return result.returncode == 0

            # Check if command exists
            result = subprocess.run(
                ["which", base_cmd], capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except:
            return False

    def get_available_tools(
        self, language: str, category: ToolCategory
    ) -> list[dict[str, Any]]:
        """Get available tools for a language and category."""
        if language not in self.TOOL_DATABASE:
            return []

        if category not in self.TOOL_DATABASE[language]:
            return []

        tools = self.TOOL_DATABASE[language][category]

        # Check availability
        available_tools = []
        for tool in tools:
            # Check if tool is installed or if it's an npx tool (can be installed on demand)
            if self.check_tool_availability(tool["command"]) or tool[
                "command"
            ].startswith("npx "):
                available_tools.append(tool)

        return available_tools

    def score_tool(self, tool: dict[str, Any], project: ProjectAnalysis) -> float:
        """Score a tool based on project characteristics."""
        score = 0.5  # Base score

        # Check if tool's config file exists
        for config_file in tool.get("config_files", []):
            if any(cf.endswith(config_file) for cf in project.config_files):
                score += 0.2
                break

        # Framework compatibility
        if project.framework:
            # Boost score for framework-specific tools
            if (project.framework == "pytest" and tool["name"] == "pytest") or (
                project.framework == "jest" and tool["name"] == "jest"
            ):
                score += 0.3

        # Feature scoring
        features = tool.get("features", [])
        if "fast" in features:
            score += 0.1
        if "popular" in features:
            score += 0.1
        if "modern" in features:
            score += 0.1

        # Project type compatibility
        if project.project_type == "library" and "library-focused" in features:
            score += 0.2
        elif project.project_type == "web" and any(
            f in features for f in ["bundler", "esm"]
        ):
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    async def analyze_with_ai(
        self, project: ProjectAnalysis, available_tools: dict[str, list[dict]]
    ) -> dict[str, str]:
        """Use AI to make final tool selections."""
        if not self.groq_client:
            return self._fallback_selection(available_tools)

        prompt = f"""
        Analyze this project and recommend the best development tools:
        
        Project Details:
        - Primary Language: {project.primary_language}
        - All Languages: {", ".join(project.languages)}
        - Project Type: {project.project_type}
        - Framework: {project.framework or "None detected"}
        - Build System: {project.build_system or "None detected"}
        - Config Files: {", ".join(project.config_files[-10:])}  # Last 10
        
        Available Tools by Category:
        {json.dumps(available_tools, indent=2)}
        
        For each category, recommend the SINGLE BEST tool based on:
        1. Project compatibility
        2. Existing configuration files
        3. Modern best practices
        4. Performance and reliability
        
        Return a JSON object with categories as keys and tool names as values.
        Example: {"linter": "ruff", "formatter": "black", ...}
        """

        try:
            response = await self.groq_client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in software development tooling. Analyze projects and recommend the best tools.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            recommendations = json.loads(response.choices[0].message.content)
            return recommendations

        except Exception as e:
            print(f"AI analysis failed: {e}", file=sys.stderr)
            return self._fallback_selection(available_tools)

    def _fallback_selection(
        self, available_tools: dict[str, list[dict]]
    ) -> dict[str, str]:
        """Fallback tool selection when AI is not available."""
        selections = {}

        for category, tools in available_tools.items():
            if tools:
                # Select first available tool as fallback
                selections[category] = tools[0]["name"]

        return selections


class ToolDecisionCache:
    """Manages caching of tool decisions in SQLite."""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".quickhooks" / "cache"

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "tool_decisions.db"
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_decisions (
                    project_hash TEXT,
                    language TEXT,
                    category TEXT,
                    selected_tool TEXT,
                    command TEXT,
                    confidence REAL,
                    reasons TEXT,
                    detected_configs TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (project_hash, language, category)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_analyses (
                    structure_hash TEXT PRIMARY KEY,
                    primary_language TEXT,
                    languages TEXT,
                    config_files TEXT,
                    dependencies TEXT,
                    project_type TEXT,
                    framework TEXT,
                    test_framework TEXT,
                    build_system TEXT,
                    timestamp TEXT
                )
            """)

            # Create indexes for faster queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_hash ON tool_decisions(project_hash)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON tool_decisions(timestamp)"
            )

    def get_cached_decision(
        self, project_hash: str, language: str, category: str
    ) -> ToolDecision | None:
        """Get a cached tool decision."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM tool_decisions 
                WHERE project_hash = ? AND language = ? AND category = ?
                AND datetime(timestamp) > datetime('now', '-30 days')
                """,
                (project_hash, language, category),
            )

            row = cursor.fetchone()
            if row:
                return ToolDecision(
                    project_hash=row[0],
                    language=row[1],
                    category=row[2],
                    selected_tool=row[3],
                    command=row[4],
                    confidence=row[5],
                    reasons=json.loads(row[6]),
                    detected_configs=json.loads(row[7]),
                    timestamp=row[8],
                )

        return None

    def cache_decision(self, decision: ToolDecision):
        """Cache a tool decision."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tool_decisions 
                (project_hash, language, category, selected_tool, command, 
                 confidence, reasons, detected_configs, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.project_hash,
                    decision.language,
                    decision.category,
                    decision.selected_tool,
                    decision.command,
                    decision.confidence,
                    json.dumps(decision.reasons),
                    json.dumps(decision.detected_configs),
                    decision.timestamp,
                ),
            )

    def cache_project_analysis(self, analysis: ProjectAnalysis):
        """Cache project analysis results."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO project_analyses
                (structure_hash, primary_language, languages, config_files,
                 dependencies, project_type, framework, test_framework,
                 build_system, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.structure_hash,
                    analysis.primary_language,
                    json.dumps(analysis.languages),
                    json.dumps(analysis.config_files),
                    json.dumps(analysis.dependencies),
                    analysis.project_type,
                    analysis.framework,
                    analysis.test_framework,
                    analysis.build_system,
                    datetime.now().isoformat(),
                ),
            )

    def get_cached_analysis(self, structure_hash: str) -> ProjectAnalysis | None:
        """Get cached project analysis."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM project_analyses
                WHERE structure_hash = ?
                AND datetime(timestamp) > datetime('now', '-7 days')
                """,
                (structure_hash,),
            )

            row = cursor.fetchone()
            if row:
                return ProjectAnalysis(
                    structure_hash=row[0],
                    primary_language=row[1],
                    languages=json.loads(row[2]),
                    config_files=json.loads(row[3]),
                    dependencies=json.loads(row[4]),
                    project_type=row[5],
                    framework=row[6],
                    test_framework=row[7],
                    build_system=row[8],
                )

        return None

    def get_statistics(self) -> dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Total cached decisions
            cursor = conn.execute("SELECT COUNT(*) FROM tool_decisions")
            stats["total_decisions"] = cursor.fetchone()[0]

            # Decisions by category
            cursor = conn.execute(
                "SELECT category, COUNT(*) FROM tool_decisions GROUP BY category"
            )
            stats["by_category"] = dict(cursor.fetchall())

            # Most common tools
            cursor = conn.execute(
                """
                SELECT category, selected_tool, COUNT(*) as count
                FROM tool_decisions
                GROUP BY category, selected_tool
                ORDER BY count DESC
                LIMIT 10
                """
            )
            stats["popular_tools"] = [
                {"category": row[0], "tool": row[1], "count": row[2]}
                for row in cursor.fetchall()
            ]

            return stats


class IntelligentToolSelector:
    """Main intelligent tool selection system."""

    def __init__(self, cwd: str):
        self.cwd = Path(cwd)
        self.analyzer = CodebaseAnalyzer(cwd)
        self.cache = ToolDecisionCache()

        # Initialize Groq client if available
        self.groq_client = None
        if Groq and os.getenv("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.discovery = ToolDiscoveryEngine(self.groq_client)

    async def select_tool(
        self, category: ToolCategory, force_analysis: bool = False
    ) -> ToolDecision | None:
        """Select the best tool for a category."""
        # Analyze project
        print("🔍 Analyzing project structure...", file=sys.stderr)

        # Check if we have a recent cached analysis
        quick_hash = self._get_quick_hash()
        cached_analysis = (
            None if force_analysis else self.cache.get_cached_analysis(quick_hash)
        )

        if cached_analysis:
            print("📦 Using cached project analysis", file=sys.stderr)
            analysis = cached_analysis
        else:
            analysis = self.analyzer.analyze()
            self.cache.cache_project_analysis(analysis)

        # Check cache for decision
        if not force_analysis:
            cached_decision = self.cache.get_cached_decision(
                analysis.structure_hash, analysis.primary_language, category.value
            )

            if cached_decision:
                print(
                    f"💾 Using cached tool selection: {cached_decision.selected_tool}",
                    file=sys.stderr,
                )
                return cached_decision

        # Get available tools
        available_tools = self.discovery.get_available_tools(
            analysis.primary_language, category
        )

        if not available_tools:
            print(
                f"⚠️  No {category.value} tools available for {analysis.primary_language}",
                file=sys.stderr,
            )
            return None

        # Score tools
        tool_scores = []
        for tool in available_tools:
            score = self.discovery.score_tool(tool, analysis)
            tool_scores.append((tool, score))

        # Sort by score
        tool_scores.sort(key=lambda x: x[1], reverse=True)

        # Use AI if available for final decision
        if self.groq_client and len(tool_scores) > 1:
            print("🤖 Consulting AI for optimal tool selection...", file=sys.stderr)

            available_by_category = {category.value: available_tools}
            try:
                ai_recommendations = await self.discovery.analyze_with_ai(
                    analysis, available_by_category
                )

                recommended_tool_name = ai_recommendations.get(category.value)
                if recommended_tool_name:
                    # Find the recommended tool
                    for tool, score in tool_scores:
                        if tool["name"] == recommended_tool_name:
                            selected_tool = tool
                            confidence = min(score + 0.2, 1.0)  # AI boost
                            reasons = ["AI recommendation", f"Score: {score:.2f}"]
                            break
                    else:
                        # AI recommended unknown tool, use highest scored
                        selected_tool = tool_scores[0][0]
                        confidence = tool_scores[0][1]
                        reasons = [f"Highest score: {confidence:.2f}"]
                else:
                    # No AI recommendation, use highest scored
                    selected_tool = tool_scores[0][0]
                    confidence = tool_scores[0][1]
                    reasons = [f"Highest score: {confidence:.2f}"]

            except Exception as e:
                print(f"⚠️  AI analysis failed: {e}", file=sys.stderr)
                # Fallback to highest scored
                selected_tool = tool_scores[0][0]
                confidence = tool_scores[0][1]
                reasons = [f"Highest score: {confidence:.2f}"]
        else:
            # Use highest scored tool
            selected_tool = tool_scores[0][0]
            confidence = tool_scores[0][1]
            reasons = [f"Highest score: {confidence:.2f}"]

        # Add more reasons
        if selected_tool.get("config_files"):
            for cf in selected_tool["config_files"]:
                if any(pcf.endswith(cf) for pcf in analysis.config_files):
                    reasons.append(f"Found config: {cf}")
                    break

        if analysis.framework and analysis.framework in selected_tool.get(
            "features", []
        ):
            reasons.append(f"Framework compatible: {analysis.framework}")

        # Create decision
        decision = ToolDecision(
            project_hash=analysis.structure_hash,
            language=analysis.primary_language,
            category=category,
            selected_tool=selected_tool["name"],
            command=selected_tool["command"],
            confidence=confidence,
            reasons=reasons,
            detected_configs=[
                cf
                for cf in analysis.config_files
                if any(
                    cf.endswith(tcf) for tcf in selected_tool.get("config_files", [])
                )
            ],
            timestamp=datetime.now().isoformat(),
        )

        # Cache decision
        self.cache.cache_decision(decision)

        print(
            f"✅ Selected {category.value}: {decision.selected_tool} (confidence: {confidence:.0%})",
            file=sys.stderr,
        )
        for reason in reasons:
            print(f"   - {reason}", file=sys.stderr)

        return decision

    def _get_quick_hash(self) -> str:
        """Get a quick hash for cache lookup."""
        # Use a simpler hash based on key files
        key_files = []
        for pattern in ["*.toml", "*.json", "*.yaml", "*.yml", "go.mod", "Cargo.toml"]:
            key_files.extend(self.cwd.glob(pattern))

        key_files_str = ",".join(sorted(str(f) for f in key_files[:10]))
        return hashlib.sha256(key_files_str.encode()).hexdigest()[:16]

    def transform_command(self, command: str, category: ToolCategory) -> str | None:
        """Transform a command to use the selected tool."""
        # Detect what the command is trying to do
        command_lower = command.lower()

        # Map command patterns to categories
        if any(kw in command_lower for kw in ["lint", "check", "analyze"]):
            target_category = ToolCategory.LINTER
        elif any(kw in command_lower for kw in ["format", "fmt", "prettier", "black"]):
            target_category = ToolCategory.FORMATTER
        elif any(kw in command_lower for kw in ["test", "spec", "pytest", "jest"]):
            target_category = ToolCategory.TEST_RUNNER
        elif any(kw in command_lower for kw in ["build", "compile", "bundle"]):
            target_category = ToolCategory.BUILD_TOOL
        elif any(kw in command_lower for kw in ["type", "mypy", "tsc"]):
            target_category = ToolCategory.TYPE_CHECKER
        else:
            return None

        if target_category != category:
            return None

        # Get the selected tool
        import asyncio

        decision = asyncio.run(self.select_tool(category))

        if not decision:
            return None

        # Extract target files/directories from command
        parts = command.split()
        targets = []

        for i, part in enumerate(parts):
            # Skip command and flags
            if i == 0 or part.startswith("-"):
                continue

            # Check if it's a file or directory
            path = Path(part)
            if path.exists() or "*" in part or "." in part:
                targets.append(part)

        # Build new command
        if targets:
            return decision.command.replace("{}", " ".join(targets))
        # No specific targets, use current directory
        return decision.command.replace("{}", ".")


def main():
    """Main entry point for the intelligent tool dispatcher."""
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

        # Initialize the intelligent selector
        selector = IntelligentToolSelector(cwd)

        # Determine command category
        command_lower = command.lower()
        category = None

        if any(
            kw in command_lower
            for kw in ["lint", "check", "analyze", "flake8", "pylint", "eslint"]
        ):
            category = ToolCategory.LINTER
        elif any(
            kw in command_lower
            for kw in [
                "format",
                "fmt",
                "prettier",
                "black",
                "autopep8",
                "gofmt",
                "rustfmt",
                "beautify",
            ]
        ):
            category = ToolCategory.FORMATTER
        elif any(
            kw in command_lower
            for kw in ["test", "spec", "pytest", "jest", "mocha", "unittest"]
        ):
            category = ToolCategory.TEST_RUNNER
        elif any(
            kw in command_lower
            for kw in ["build", "compile", "bundle", "webpack", "rollup"]
        ):
            category = ToolCategory.BUILD_TOOL
        elif any(
            kw in command_lower
            for kw in ["type", "mypy", "tsc", "pyright", "typecheck"]
        ):
            category = ToolCategory.TYPE_CHECKER
        else:
            # Not a command we handle
            return

        # Get the selected tool
        import asyncio

        decision = asyncio.run(selector.select_tool(category))

        if not decision:
            print(
                f"⚠️  No suitable {category.value} found for this project",
                file=sys.stderr,
            )
            return

        # Extract targets from the original command
        parts = command.split()
        targets = []
        skip_next = False

        for i, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue

            # Skip command and flags
            if i == 0:
                continue

            if part.startswith("-"):
                # Check if this flag takes a value
                if part in ["-c", "--config", "-f", "--file", "-p", "--project"]:
                    skip_next = True
                continue

            # Check if it's a file, directory, or pattern
            path = Path(cwd) / part
            if path.exists() or "*" in part or part == ".":
                targets.append(part)

        # Build the new command
        if targets:
            new_command = decision.command.replace("{}", " ".join(targets))
        else:
            # No specific targets, use current directory
            new_command = decision.command.replace("{}", ".")

        # Check if we need to install the tool first (for npx commands)
        if new_command.startswith("npx "):
            tool_package = new_command.split()[1]
            print(f"📦 Ensuring {tool_package} is available...", file=sys.stderr)

        # Execute the selected tool
        print(f"🚀 Running: {new_command}", file=sys.stderr)
        print(f"💡 Reasons: {', '.join(decision.reasons)}", file=sys.stderr)

        try:
            # Run the command
            result = subprocess.run(
                new_command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,  # 5 minute timeout
            )

            # Output results
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)

            # Cache usage statistics
            stats = selector.cache.get_statistics()
            print(
                f"\n📊 Cache stats: {stats['total_decisions']} decisions cached",
                file=sys.stderr,
            )

            # Return response to prevent original command
            response = {
                "continue": False,  # Don't run the original command
                "suppressOutput": False,
                "exitCode": result.returncode,
                "metadata": {
                    "selected_tool": decision.selected_tool,
                    "confidence": decision.confidence,
                    "category": category.value,
                },
            }
            print(json.dumps(response))

            sys.exit(result.returncode)

        except subprocess.TimeoutExpired:
            print("⏱️  Command timed out after 5 minutes", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Execution failed: {e}", file=sys.stderr)
            # Fall back to original command
            return

    except Exception as e:
        # Always fail safely
        print(f"Intelligent tool dispatcher error: {e!s}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    # Check for required st tool
    st_check = subprocess.run(["which", "st"], capture_output=True, check=False)
    if st_check.returncode != 0:
        print(
            "⚠️  Smart Tree (st) tool not found. Install it for better analysis:",
            file=sys.stderr,
        )
        print("   cargo install smart-tree", file=sys.stderr)

    main()
