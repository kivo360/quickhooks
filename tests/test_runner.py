"""Tests for the TestRunner class."""

import time
from unittest.mock import patch

import pytest

from quickhooks.runner import TestRunner, TestResult


class TestTestResult:
    """Test suite for the TestResult class."""

    def test_test_result_creation(self):
        """Test creating a TestResult instance."""
        result = TestResult(test_name="test_example", status="passed", duration=1.5)

        assert result.test_name == "test_example"
        assert result.status == "passed"
        assert result.duration == 1.5
        assert result.output is None
        assert result.error is None

    def test_test_result_with_output_and_error(self):
        """Test creating a TestResult with output and error."""
        error = Exception("Test error")
        result = TestResult(
            test_name="test_example", status="failed", duration=2.0, error=error
        )

        assert result.test_name == "test_example"
        assert result.status == "failed"
        assert result.duration == 2.0
        assert result.error == error

    def test_to_dict(self):
        """Test converting TestResult to dictionary."""
        result = TestResult(test_name="test_example", status="passed", duration=1.5)

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["test_name"] == "test_example"
        assert result_dict["status"] == "passed"
        assert result_dict["duration"] == 1.5
        assert "timestamp" in result_dict


class TestTestRunner:
    """Test suite for the TestRunner class."""

    @pytest.fixture
    def runner(self):
        """Create a TestRunner instance for testing."""
        return TestRunner(
            hooks_directory="./hooks",
            test_directory="./tests",
            timeout=5.0,
            max_workers=2,
        )

    def test_runner_initialization(self, runner):
        """Test TestRunner initialization."""
        assert runner.hooks_directory.name == "hooks"
        assert runner.test_directory.name == "tests"
        assert runner.timeout == 5.0
        assert runner.max_workers == 2
        assert runner.results == []
        assert runner.setup_hooks == []
        assert runner.teardown_hooks == []

    def test_add_setup_hook(self, runner):
        """Test adding a setup hook."""

        def setup_func():
            pass

        runner.add_setup_hook(setup_func)
        assert len(runner.setup_hooks) == 1
        assert runner.setup_hooks[0] == setup_func

    def test_add_teardown_hook(self, runner):
        """Test adding a teardown hook."""

        def teardown_func():
            pass

        runner.add_teardown_hook(teardown_func)
        assert len(runner.teardown_hooks) == 1
        assert runner.teardown_hooks[0] == teardown_func

    def test_discover_tests(self, runner):
        """Test discovering test files."""
        # This test will depend on the actual file structure
        # For now, we'll just check that it returns a list
        with patch.object(runner.test_directory, "exists", return_value=True):
            with patch.object(runner.test_directory, "glob", return_value=[]):
                tests = runner.discover_tests()
                assert isinstance(tests, list)

    @pytest.mark.asyncio
    async def test_run_test_case_success(self, runner):
        """Test running a successful test case."""

        def successful_test():
            return "success"

        result = await runner.run_test_case(successful_test, "test_success")

        assert result.test_name == "test_success"
        assert result.status == "passed"
        assert result.duration >= 0
        assert result.output == "success"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_test_case_failure(self, runner):
        """Test running a test case that raises an exception."""

        def failing_test():
            raise ValueError("Test failure")

        result = await runner.run_test_case(failing_test, "test_failure")

        assert result.test_name == "test_failure"
        assert result.status == "error"
        assert result.duration >= 0
        assert result.error is not None
        assert isinstance(result.error, ValueError)

    @pytest.mark.asyncio
    async def test_run_test_case_timeout(self, runner):
        """Test running a test case that times out."""

        def slow_test():
            time.sleep(2)  # Longer than the runner's timeout
            return "slow"

        # Set a very short timeout for testing
        result = await runner.run_test_case(slow_test, "test_timeout", timeout=0.1)

        assert result.test_name == "test_timeout"
        assert result.status == "failed"
        assert result.duration >= 0
        assert result.error is not None
        assert "timed out" in str(result.error)

    @pytest.mark.asyncio
    async def test_run_tests_sequentially(self, runner):
        """Test running test cases sequentially."""

        def test1():
            return "result1"

        def test2():
            return "result2"

        test_cases = [(test1, "test1"), (test2, "test2")]

        results = await runner.run_tests_sequentially(test_cases)

        assert len(results) == 2
        assert results[0].test_name == "test1"
        assert results[0].status == "passed"
        assert results[1].test_name == "test2"
        assert results[1].status == "passed"

    @pytest.mark.asyncio
    async def test_run_tests_sequentially_with_filter(self, runner):
        """Test running test cases sequentially with filtering."""

        def test1():
            return "result1"

        def test2():
            return "result2"

        test_cases = [(test1, "test_example_1"), (test2, "test_other_2")]

        results = await runner.run_tests_sequentially(
            test_cases, filter_pattern="example"
        )

        assert len(results) == 1
        assert results[0].test_name == "test_example_1"

    @pytest.mark.asyncio
    async def test_run_tests_in_parallel(self, runner):
        """Test running test cases in parallel."""

        def test1():
            return "result1"

        def test2():
            return "result2"

        test_cases = [(test1, "test1"), (test2, "test2")]

        results = await runner.run_tests_in_parallel(test_cases)

        assert len(results) == 2
        # Order may vary in parallel execution
        test_names = {r.test_name for r in results}
        statuses = {r.status for r in results}
        assert test_names == {"test1", "test2"}
        assert statuses == {"passed"}

    def test_load_test_cases_from_file(self, runner):
        """Test loading test cases from a file."""
        # This is a simplified test since the actual implementation
        # would require complex dynamic importing
        result = runner.load_test_cases_from_file("dummy_path.py")
        assert isinstance(result, list)
        assert len(result) == 0  # Current implementation returns empty list

    def test_generate_text_report_empty(self, runner):
        """Test generating text report with no results."""
        report = runner.generate_text_report([])
        assert "No tests found or executed" in report

    def test_generate_text_report_with_results(self, runner):
        """Test generating text report with results."""
        results = [
            TestResult("test1", "passed", 1.0),
            TestResult("test2", "failed", 2.0, error=ValueError("Test error")),
        ]

        report = runner.generate_text_report(results)
        assert "Test Results" in report
        assert "Total: 2" in report
        assert "Passed: 1" in report
        assert "Failed: 1" in report
        assert "test2: failed" in report

    def test_generate_json_report(self, runner):
        """Test generating JSON report."""
        results = [
            TestResult("test1", "passed", 1.0),
            TestResult("test2", "failed", 2.0, error=ValueError("Test error")),
        ]

        report = runner.generate_json_report(results)
        assert isinstance(report, str)
        # Should be valid JSON
        import json

        data = json.loads(report)
        assert "summary" in data
        assert "results" in data
        assert data["summary"]["total"] == 2

    def test_generate_junit_report(self, runner):
        """Test generating JUnit XML report."""
        results = [
            TestResult("test1", "passed", 1.0),
            TestResult("test2", "failed", 2.0, error=ValueError("Test error")),
        ]

        report = runner.generate_junit_report(results)
        assert isinstance(report, str)
        assert "<?xml" in report
        assert "<testsuite" in report
        assert "<testcase" in report
        assert "failures=" in report
