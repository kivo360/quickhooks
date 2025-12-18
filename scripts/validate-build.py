#!/usr/bin/env python3
"""
QuickHooks Build Validation Script

This script validates built packages before publishing to ensure:
- Package integrity
- Metadata correctness
- Import functionality
- Security compliance
- Dependency consistency

Usage:
    python scripts/validate-build.py [--verbose] [--fix-issues]
"""

import hashlib
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import cyclopts
from cyclopts import Parameter
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class ValidationIssue(BaseModel):
    """Represents a validation issue."""

    severity: str  # "error", "warning", "info"
    category: str
    message: str
    fix_suggestion: str | None = None


class PackageMetadata(BaseModel):
    """Package metadata from built artifacts."""

    name: str
    version: str
    description: str
    dependencies: list[str]
    entry_points: dict[str, str]
    files: list[str]
    size_bytes: int


class BuildValidator:
    """Main build validation class."""

    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose
        self.console = Console()
        self.issues: list[ValidationIssue] = []
        self.dist_path = project_root / "dist"

    def log(self, message: str, level: str = "info"):
        """Log message with appropriate color."""
        if level == "error":
            self.console.print(f"[red]ERROR: {message}[/red]")
        elif level == "warning":
            self.console.print(f"[yellow]WARNING: {message}[/yellow]")
        elif level == "success":
            self.console.print(f"[green]SUCCESS: {message}[/green]")
        elif self.verbose:
            self.console.print(f"[blue]INFO: {message}[/blue]")

    def add_issue(
        self, severity: str, category: str, message: str, fix_suggestion: str = None
    ):
        """Add a validation issue."""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            fix_suggestion=fix_suggestion,
        )
        self.issues.append(issue)
        self.log(f"{category}: {message}", severity)

    def validate_dist_exists(self) -> bool:
        """Validate that dist directory exists with artifacts."""
        if not self.dist_path.exists():
            self.add_issue(
                "error",
                "dist_structure",
                "dist/ directory not found",
                "Run 'uv build' to create distribution artifacts",
            )
            return False

        # Check for wheel and source dist
        wheel_files = list(self.dist_path.glob("*.whl"))
        sdist_files = list(self.dist_path.glob("*.tar.gz"))

        if not wheel_files:
            self.add_issue(
                "error",
                "dist_artifacts",
                "No wheel (.whl) files found in dist/",
                "Ensure 'uv build --wheel' completed successfully",
            )

        if not sdist_files:
            self.add_issue(
                "warning",
                "dist_artifacts",
                "No source distribution (.tar.gz) files found in dist/",
                "Consider running 'uv build --sdist' for complete distribution",
            )

        return len(wheel_files) > 0

    def extract_wheel_metadata(self, wheel_path: Path) -> PackageMetadata | None:
        """Extract metadata from wheel file."""
        try:
            with zipfile.ZipFile(wheel_path, "r") as wheel:
                # Find METADATA file
                metadata_path = None
                for file_path in wheel.namelist():
                    if file_path.endswith("METADATA"):
                        metadata_path = file_path
                        break

                if not metadata_path:
                    self.add_issue(
                        "error",
                        "wheel_metadata",
                        f"METADATA file not found in {wheel_path.name}",
                    )
                    return None

                # Read metadata
                metadata_content = wheel.read(metadata_path).decode("utf-8")

                # Parse metadata
                name = ""
                version = ""
                description = ""
                dependencies = []

                for line in metadata_content.split("\n"):
                    if line.startswith("Name: "):
                        name = line[6:].strip()
                    elif line.startswith("Version: "):
                        version = line[9:].strip()
                    elif line.startswith("Summary: "):
                        description = line[9:].strip()
                    elif line.startswith("Requires-Dist: "):
                        dep = line[15:].strip()
                        if dep:
                            dependencies.append(dep)

                # Get entry points
                entry_points = {}
                try:
                    entry_points_path = None
                    for file_path in wheel.namelist():
                        if file_path.endswith("entry_points.txt"):
                            entry_points_path = file_path
                            break

                    if entry_points_path:
                        ep_content = wheel.read(entry_points_path).decode("utf-8")
                        # Parse entry points (simplified)
                        current_section = None
                        for line in ep_content.split("\n"):
                            line = line.strip()
                            if line.startswith("[") and line.endswith("]"):
                                current_section = line[1:-1]
                            elif "=" in line and current_section:
                                key, value = line.split("=", 1)
                                entry_points[key.strip()] = value.strip()
                except Exception:  # noqa: S110
                    pass  # Entry points are optional

                return PackageMetadata(
                    name=name,
                    version=version,
                    description=description,
                    dependencies=dependencies,
                    entry_points=entry_points,
                    files=wheel.namelist(),
                    size_bytes=wheel_path.stat().st_size,
                )

        except Exception as e:
            self.add_issue(
                "error",
                "wheel_parsing",
                f"Failed to parse wheel {wheel_path.name}: {e}",
            )
            return None

    def validate_metadata_consistency(self, metadata: PackageMetadata) -> bool:
        """Validate metadata consistency with pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"

        if not pyproject_path.exists():
            self.add_issue(
                "error",
                "metadata_consistency",
                "pyproject.toml not found for metadata validation",
            )
            return False

        # Read pyproject.toml
        with open(pyproject_path) as f:
            content = f.read()

        # Extract project info (simple parsing)
        project_name = ""
        project_version = ""
        project_description = ""

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("name = "):
                project_name = line.split("=")[1].strip().strip("\"'")
            elif line.startswith("version = "):
                project_version = line.split("=")[1].strip().strip("\"'")
            elif line.startswith("description = "):
                project_description = line.split("=")[1].strip().strip("\"'")

        # Validate consistency
        success = True

        if metadata.name != project_name:
            self.add_issue(
                "error",
                "metadata_consistency",
                f"Package name mismatch: wheel has '{metadata.name}', pyproject.toml has '{project_name}'",
            )
            success = False

        if metadata.version != project_version:
            self.add_issue(
                "error",
                "metadata_consistency",
                f"Version mismatch: wheel has '{metadata.version}', pyproject.toml has '{project_version}'",
            )
            success = False

        if metadata.description != project_description:
            self.add_issue(
                "warning",
                "metadata_consistency",
                "Description mismatch between wheel and pyproject.toml",
            )

        return success

    def validate_import_structure(self, metadata: PackageMetadata) -> bool:
        """Validate that the package can be imported."""
        # Check for __init__.py files
        init_files = [f for f in metadata.files if f.endswith("__init__.py")]

        if not init_files:
            self.add_issue(
                "warning", "import_structure", "No __init__.py files found in package"
            )
            return False

        # Check for main package structure
        package_dirs = set()
        for file_path in metadata.files:
            if "/" in file_path:
                parts = file_path.split("/")
                if len(parts) > 1 and not parts[0].endswith(".dist-info"):
                    package_dirs.add(parts[0])

        if not package_dirs:
            self.add_issue(
                "error",
                "import_structure",
                "No recognizable package structure found in wheel",
            )
            return False

        self.log(f"Found package directories: {', '.join(package_dirs)}")
        return True

    def validate_security(self, metadata: PackageMetadata) -> bool:
        """Perform basic security validation."""
        success = True

        # Check for suspicious files
        suspicious_patterns = [
            r"\.exe$",
            r"\.dll$",
            r"\.so$",
            r"\.dylib$",
            r"eval\(",
            r"exec\(",
            r"__import__",
        ]

        for file_path in metadata.files:
            for pattern in suspicious_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    self.add_issue(
                        "warning",
                        "security",
                        f"Potentially suspicious file pattern: {file_path}",
                        "Review file contents for security implications",
                    )
                    break

        # Check dependencies for known issues
        risky_dependencies = [
            "pickle",
            "marshal",
            "subprocess",
            "os.system",
        ]

        for dep in metadata.dependencies:
            dep_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
            if dep_name.lower() in risky_dependencies:
                self.add_issue(
                    "info",
                    "security",
                    f"Dependency '{dep_name}' may require security review",
                )

        return success

    def validate_size_limits(self, metadata: PackageMetadata) -> bool:
        """Validate package size is reasonable."""
        # Check overall size
        size_mb = metadata.size_bytes / (1024 * 1024)

        if size_mb > 100:
            self.add_issue(
                "warning",
                "package_size",
                f"Package is quite large: {size_mb:.1f}MB",
                "Consider optimizing package size or using optional dependencies",
            )
        elif size_mb > 500:
            self.add_issue(
                "error",
                "package_size",
                f"Package is extremely large: {size_mb:.1f}MB",
                "Package size may cause installation issues",
            )

        # Check for large individual files
        for file_path in metadata.files:
            if any(
                ext in file_path.lower()
                for ext in [".jpg", ".png", ".gif", ".pdf", ".zip"]
            ):
                self.add_issue(
                    "warning",
                    "package_content",
                    f"Large binary file included: {file_path}",
                    "Consider moving large assets to external storage",
                )

        return True

    def test_package_installation(self, metadata: PackageMetadata) -> bool:
        """Test package installation in a clean environment."""
        wheel_files = list(self.dist_path.glob("*.whl"))
        if not wheel_files:
            return False

        wheel_path = wheel_files[0]

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create virtual environment
                venv_path = Path(temp_dir) / "test_venv"
                subprocess.run(
                    ["uv", "venv", str(venv_path)],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Install package
                subprocess.run(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        str(venv_path / "bin" / "python"),
                        str(wheel_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Test import
                python_path = venv_path / "bin" / "python"
                if not python_path.exists():
                    python_path = venv_path / "Scripts" / "python.exe"  # Windows

                import_cmd = [
                    str(python_path),
                    "-c",
                    f"import {metadata.name.replace('-', '_')}; print('Import successful')",
                ]

                subprocess.run(import_cmd, capture_output=True, text=True, check=True)

                self.log("Package installation and import test passed", "success")
                return True

        except subprocess.CalledProcessError as e:
            self.add_issue(
                "error",
                "installation_test",
                f"Package installation test failed: {e.stderr}",
                "Check package dependencies and structure",
            )
            return False
        except Exception as e:
            self.add_issue(
                "warning", "installation_test", f"Could not run installation test: {e}"
            )
            return True  # Don't fail validation for test issues

    def generate_validation_report(self) -> Table:
        """Generate validation report table."""
        table = Table(title="Build Validation Report")
        table.add_column("Category", style="cyan")
        table.add_column("Severity", style="magenta")
        table.add_column("Message", style="white")
        table.add_column("Fix Suggestion", style="yellow")

        # Group issues by severity
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]

        for issue in errors + warnings + info:
            severity_color = {
                "error": "[red]ERROR[/red]",
                "warning": "[yellow]WARNING[/yellow]",
                "info": "[blue]INFO[/blue]",
            }

            table.add_row(
                issue.category,
                severity_color[issue.severity],
                issue.message,
                issue.fix_suggestion or "N/A",
            )

        return table

    def run_validation(self) -> bool:
        """Run complete validation process."""
        self.console.print(
            Panel.fit(
                "[bold blue]QuickHooks Build Validation[/bold blue]\n"
                "Validating package integrity, metadata, and security"
            )
        )

        # Check dist directory exists
        if not self.validate_dist_exists():
            return False

        # Get wheel files
        wheel_files = list(self.dist_path.glob("*.whl"))
        if not wheel_files:
            return False

        wheel_path = wheel_files[0]
        self.log(f"Validating: {wheel_path.name}")

        # Extract metadata
        metadata = self.extract_wheel_metadata(wheel_path)
        if not metadata:
            return False

        # Run validations
        validations = [
            ("Metadata Consistency", self.validate_metadata_consistency),
            ("Import Structure", self.validate_import_structure),
            ("Security Check", self.validate_security),
            ("Size Limits", self.validate_size_limits),
            ("Installation Test", self.test_package_installation),
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            for name, validation_func in validations:
                task = progress.add_task(f"Running {name}...", total=1)

                try:
                    result = validation_func(metadata)
                    if not result:
                        pass
                except Exception as e:
                    self.add_issue(
                        "error",
                        name.lower().replace(" ", "_"),
                        f"Validation failed: {e}",
                    )

                progress.update(task, completed=1)

        # Display report
        self.console.print("\n")
        self.console.print(self.generate_validation_report())

        # Summary
        error_count = len([i for i in self.issues if i.severity == "error"])
        warning_count = len([i for i in self.issues if i.severity == "warning"])
        info_count = len([i for i in self.issues if i.severity == "info"])

        self.console.print("\nValidation Summary:")
        self.console.print(f"  Errors: {error_count}")
        self.console.print(f"  Warnings: {warning_count}")
        self.console.print(f"  Info: {info_count}")

        if error_count == 0:
            self.console.print("\n[green]✅ Build validation passed![/green]")
        else:
            self.console.print(
                f"\n[red]❌ Build validation failed with {error_count} errors[/red]"
            )

        return error_count == 0


app = cyclopts.App(help="QuickHooks Build Validation")


@app.command
def validate(
    verbose: bool = Parameter(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    fix_issues: bool = Parameter(
        False, "--fix-issues", help="Attempt to fix detected issues"
    ),
):
    """Validate built packages before deployment."""

    project_root = Path(__file__).parent.parent
    validator = BuildValidator(project_root, verbose=verbose)

    success = validator.run_validation()

    if fix_issues and not success:
        console.print("\n[yellow]Auto-fix functionality not yet implemented[/yellow]")
        console.print("Please review the issues above and fix them manually")

    sys.exit(0 if success else 1)


@app.command
def checksum(algorithm: str = Parameter("sha256", help="Hash algorithm to use")):
    """Generate checksums for built packages."""

    project_root = Path(__file__).parent.parent
    dist_path = project_root / "dist"

    if not dist_path.exists():
        console.print("[red]dist/ directory not found[/red]")
        sys.exit(1)

    artifacts = list(dist_path.glob("*"))
    if not artifacts:
        console.print("[red]No artifacts found in dist/[/red]")
        sys.exit(1)

    table = Table(title="Package Checksums")
    table.add_column("File", style="cyan")
    table.add_column("Algorithm", style="magenta")
    table.add_column("Checksum", style="white")

    for artifact in artifacts:
        if artifact.is_file():
            hasher = hashlib.new(algorithm)
            with open(artifact, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            table.add_row(artifact.name, algorithm.upper(), hasher.hexdigest())

    console.print(table)


if __name__ == "__main__":
    app()
