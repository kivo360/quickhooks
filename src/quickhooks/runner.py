"""Test runner for QuickHooks framework.

This module provides functionality to run tests for hooks with support for
parallel execution, filtering, timeouts, and multiple report formats.
"""

import asyncio
import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from quickhooks.models import HookOutput


class TestResult:
    """Result of a single test execution."""

    def __init__(
        self,
        test_name: str,
        status: str,
        duration: float,
        output: HookOutput | None = None,
        error: Exception | None = None,
        timestamp: datetime | None = None,
    ):
        self.test_name = test_name
        self.status = status  # 'passed', 'failed', 'error', 'skipped'
        self.duration = duration
        self.output = output
        self.error = error
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert test result to dictionary for serialization."""
        return {
            "test_name": self.test_name,
            "status": self.status,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "error": str(self.error) if self.error else None,
        }


class TestRunner:
    """Runner for executing hook tests.

    Provides functionality to discover, run, and report on hook tests
    with support for parallel execution, filtering, and various output formats.
    """

    def __init__(
        self,
        hooks_directory: str = "./hooks",
        test_directory: str = "./tests",
        timeout: float = 30.0,
        max_workers: int = 4,
    ):
        self.hooks_directory = Path(hooks_directory)
        self.test_directory = Path(test_directory)
        self.timeout = timeout
        self.max_workers = max_workers
        self.results: list[TestResult] = []
        self.setup_hooks: list[Callable] = []
        self.teardown_hooks: list[Callable] = []

    def add_setup_hook(self, hook: Callable) -> None:
        """Add a setup hook to run before tests."""
        self.setup_hooks.append(hook)

    def add_teardown_hook(self, hook: Callable) -> None:
        """Add a teardown hook to run after tests."""
        self.teardown_hooks.append(hook)

    def discover_tests(self, pattern: str = "test_*.py") -> list[Path]:
        """Discover test files matching the given pattern."""
        if not self.test_directory.exists():
            return []

        return list(self.test_directory.glob(pattern))

    async def run_test_case(
        self, test_func: Callable, test_name: str, timeout: float | None = None
    ) -> TestResult:
        """Run a single test case with timeout support."""
        start_time = time.time()

        try:
            # Run setup hooks
            for setup_hook in self.setup_hooks:
                setup_hook()

            # Run the test with timeout
            test_timeout = timeout or self.timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(test_func), timeout=test_timeout
            )

            duration = time.time() - start_time

            # Run teardown hooks
            for teardown_hook in self.teardown_hooks:
                teardown_hook()

            return TestResult(
                test_name=test_name, status="passed", duration=duration, output=result
            )

        except TimeoutError:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status="failed",
                duration=duration,
                error=TimeoutError(f"Test timed out after {test_timeout} seconds"),
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name, status="error", duration=duration, error=e
            )

    async def run_tests_sequentially(
        self, test_cases: list[tuple], filter_pattern: str | None = None
    ) -> list[TestResult]:
        """Run test cases sequentially."""
        results = []

        for test_func, test_name in test_cases:
            # Apply filter if provided
            if filter_pattern and filter_pattern not in test_name:
                continue

            result = await self.run_test_case(test_func, test_name)
            results.append(result)
            self.results.append(result)

        return results

    async def run_tests_in_parallel(
        self, test_cases: list[tuple], filter_pattern: str | None = None
    ) -> list[TestResult]:
        """Run test cases in parallel."""
        # Filter test cases if pattern provided
        if filter_pattern:
            filtered_cases = [
                (func, name) for func, name in test_cases if filter_pattern in name
            ]
        else:
            filtered_cases = test_cases

        # Run tests in parallel
        tasks = [self.run_test_case(func, name) for func, name in filtered_cases]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions from gather
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                # Create error result for exceptions from gather
                error_result = TestResult(
                    test_name="unknown", status="error", duration=0.0, error=result
                )
                processed_results.append(error_result)
                self.results.append(error_result)
            else:
                processed_results.append(result)
                self.results.append(result)

        return processed_results

    def load_test_cases_from_file(self, file_path: Path) -> list[tuple]:
        """Load test cases from a test file."""
        # This is a simplified implementation
        # In a real implementation, we would dynamically import and inspect the file
        test_cases = []

        # For now, return empty list as this requires more complex implementation
        return test_cases

    async def run_all_tests(
        self, parallel: bool = False, filter_pattern: str | None = None
    ) -> list[TestResult]:
        """Run all discovered tests."""
        test_files = self.discover_tests()
        all_results = []

        for test_file in test_files:
            test_cases = self.load_test_cases_from_file(test_file)

            if parallel:
                results = await self.run_tests_in_parallel(test_cases, filter_pattern)
            else:
                results = await self.run_tests_sequentially(test_cases, filter_pattern)

            all_results.extend(results)

        return all_results

    def generate_text_report(self, results: list[TestResult]) -> str:
        """Generate a text report of test results."""
        if not results:
            return "No tests found or executed."

        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")
        skipped = sum(1 for r in results if r.status == "skipped")
        total = len(results)

        duration = sum(r.duration for r in results)

        report = f"""
Test Results
============
Total: {total}
Passed: {passed}
Failed: {failed}
Errors: {errors}
Skipped: {skipped}
Duration: {duration:.2f}s

"""

        # Add details for failed tests
        failed_tests = [r for r in results if r.status in ["failed", "error"]]
        if failed_tests:
            report += "Failed Tests:\n"
            for result in failed_tests:
                report += f"  {result.test_name}: {result.status}\n"
                if result.error:
                    report += f"    Error: {result.error!s}\n"
            report += "\n"

        return report.strip()

    def generate_json_report(self, results: list[TestResult]) -> str:
        """Generate a JSON report of test results."""
        report_data = {
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == "passed"),
                "failed": sum(1 for r in results if r.status == "failed"),
                "errors": sum(1 for r in results if r.status == "error"),
                "skipped": sum(1 for r in results if r.status == "skipped"),
                "duration": sum(r.duration for r in results),
            },
            "results": [r.to_dict() for r in results],
        }

        return json.dumps(report_data, indent=2)

    def generate_junit_report(self, results: list[TestResult]) -> str:
        """Generate a JUnit XML report of test results."""
        # Simplified JUnit XML generation
        timestamp = datetime.now().isoformat()
        total = len(results)
        failures = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")

        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="QuickHooksTests" tests="{total}" failures="{failures}" errors="{errors}" timestamp="{timestamp}">
'''

        for result in results:
            classname = (
                result.test_name.split(".")[0] if "." in result.test_name else "Unknown"
            )
            name = (
                result.test_name.split(".")[-1]
                if "." in result.test_name
                else result.test_name
            )

            if result.status == "passed":
                xml += f'  <testcase classname="{classname}" name="{name}" time="{result.duration}"/>\n'
            elif result.status == "failed":
                xml += f'  <testcase classname="{classname}" name="{name}" time="{result.duration}">\n'
                xml += f'    <failure message="{str(result.error) if result.error else "Test failed"}">\n'
                if result.error:
                    xml += f"      {result.error!s}\n"
                xml += "    </failure>\n"
                xml += "  </testcase>\n"
            elif result.status == "error":
                xml += f'  <testcase classname="{classname}" name="{name}" time="{result.duration}">\n'
                xml += f'    <error message="{str(result.error) if result.error else "Test error"}">\n'
                if result.error:
                    xml += f"      {result.error!s}\n"
                xml += "    </error>\n"
                xml += "  </testcase>\n"

        xml += "</testsuite>"

        return xml

    async def run(
        self,
        parallel: bool = False,
        filter_pattern: str | None = None,
        report_format: str = "text",
    ) -> str:
        """Run all tests and generate a report."""
        results = await self.run_all_tests(parallel, filter_pattern)

        if report_format == "json":
            return self.generate_json_report(results)
        if report_format == "junit":
            return self.generate_junit_report(results)
        return self.generate_text_report(results)
