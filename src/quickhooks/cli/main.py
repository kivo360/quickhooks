"""Main CLI module for QuickHooks.

This module defines the root command and sets up the CLI interface.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import Parameter

from quickhooks import __version__, console
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput
from quickhooks.runner import TestRunner

# Create the main Cyclopts app
app = cyclopts.App(
    name="quickhooks",
    help="A streamlined TDD framework for Claude Code hooks with real-time feedback",
)

# Create groups for subcommands and register migrated sub-apps
# All sub-apps have been migrated to Cyclopts

# Features group
from cyclopts import Group

features_group = Group("features")
from quickhooks.cli.features import check, demo, diagnose, install_commands, suggest
from quickhooks.cli.features import list as features_list

app.command(features_list, group=features_group, name="features.list")
app.command(check, group=features_group, name="features.check")
app.command(install_commands, group=features_group, name="features.install-commands")
app.command(suggest, group=features_group, name="features.suggest")
app.command(diagnose, group=features_group, name="features.diagnose")
app.command(demo, group=features_group, name="features.demo")

# Create group
create_group = Group("create")
from quickhooks.cli.create import cli_command, config, hook, list_global

app.command(hook, group=create_group, name="create.hook")
app.command(config, group=create_group, name="create.config")
app.command(cli_command, group=create_group, name="create.cli-command")
app.command(list_global, group=create_group, name="create.list-global")

# Install group
install_group = Group("install")
from quickhooks.cli.install import install_hook, show_status, validate_settings

app.command(install_hook, group=install_group, name="install.hook")
app.command(validate_settings, group=install_group, name="install.validate")
app.command(show_status, group=install_group, name="install.status")

# Global hooks group
global_group = Group("global")
from quickhooks.cli.global_hooks import add_to_path, import_hook, info, setup

app.command(setup, group=global_group, name="global.setup")
app.command(add_to_path, group=global_group, name="global.add-to-path")
app.command(import_hook, group=global_group, name="global.import-hook")
app.command(info, group=global_group, name="global.info")

# Smart group
smart_group = Group("smart")
from quickhooks.cli.smart import generate

app.command(generate, group=smart_group, name="smart.generate")

# Deploy group
deploy_group = Group("deploy")
from quickhooks.cli.deploy import (
    deploy_all,
    list_deployed,
    search_hooks,
    show_statistics,
    sync_hooks,
)

app.command(deploy_all, group=deploy_group, name="deploy.all")
app.command(list_deployed, group=deploy_group, name="deploy.list")
app.command(search_hooks, group=deploy_group, name="deploy.search")
app.command(show_statistics, group=deploy_group, name="deploy.stats")
app.command(sync_hooks, group=deploy_group, name="deploy.sync")

# Settings group
settings_group = Group("settings")
from quickhooks.cli.settings import (
    add_hook,
    add_permission,
    init,
    list_env,
    list_hooks,
    remove_hook,
    set_env,
    show,
    validate,
)

app.command(init, group=settings_group, name="settings.init")
app.command(validate, group=settings_group, name="settings.validate")
app.command(show, group=settings_group, name="settings.show")
app.command(add_hook, group=settings_group, name="settings.add-hook")
app.command(remove_hook, group=settings_group, name="settings.remove-hook")
app.command(list_hooks, group=settings_group, name="settings.list-hooks")
app.command(set_env, group=settings_group, name="settings.set-env")
app.command(list_env, group=settings_group, name="settings.list-env")
app.command(add_permission, group=settings_group, name="settings.add-permission")

# Agent OS group
agent_os_group = Group("agent-os")
from quickhooks.cli.agent_os import (
    create_workflow,
    execute_instruction,
    execute_workflow,
    init_workflows,
    list_instructions,
    list_workflows,
    show_instruction,
)
from quickhooks.cli.agent_os import version as agent_os_version

app.command(agent_os_version, group=agent_os_group, name="agent-os.version")
app.command(list_instructions, group=agent_os_group, name="agent-os.list-instructions")
app.command(execute_instruction, group=agent_os_group, name="agent-os.execute-instruction")
app.command(list_workflows, group=agent_os_group, name="agent-os.list-workflows")
app.command(create_workflow, group=agent_os_group, name="agent-os.create-workflow")
app.command(execute_workflow, group=agent_os_group, name="agent-os.execute-workflow")
app.command(init_workflows, group=agent_os_group, name="agent-os.init-workflows")
app.command(show_instruction, group=agent_os_group, name="agent-os.show-instruction")

# Agents (agent analysis) group
agents_group = Group("agents")
from quickhooks.agent_analysis.command import analyze_prompt

app.command(analyze_prompt, group=agents_group, name="agents.analyze")

# Agent discovery commands
from quickhooks.cli.agents import search, list, rebuild, types, info

app.command(search, group=agents_group, name="agents.search")
app.command(list, group=agents_group, name="agents.list")
app.command(rebuild, group=agents_group, name="agents.rebuild")
app.command(types, group=agents_group, name="agents.types")
app.command(info, group=agents_group, name="agents.info")


@app.command
def version() -> None:
    """Show the version and exit."""
    console.print(f"QuickHooks v{__version__}")


@app.command
def hello(name: str | None = None) -> None:
    """Say hello.

    Parameters
    ----------
    name
        Optional name to greet
    """
    if name:
        console.print(f"Hello, {name}!")
    else:
        console.print("Hello, World!")


@app.command
def run(
    hook_path: Path,
    input_data: Annotated[
        str, Parameter("--input", alias="-i", help="JSON input data for the hook")
    ] = "{}",
) -> None:
    """Run a hook with the provided input data.

    Parameters
    ----------
    hook_path
        Path to the hook file to execute
    input_data
        JSON input data for the hook (default: "{}")
    """
    # Load the hook module
    spec = importlib.util.spec_from_file_location("hook_module", hook_path)
    if spec is None or spec.loader is None:
        console.print(
            f"Error: Could not load module from {hook_path}", style="bold red"
        )
        sys.exit(1)

    hook_module = importlib.util.module_from_spec(spec)
    sys.modules["hook_module"] = hook_module
    spec.loader.exec_module(hook_module)

    # Find the hook class
    hook_class = None
    for attr_name in dir(hook_module):
        attr = getattr(hook_module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseHook) and attr != BaseHook:
            hook_class = attr
            break

    if hook_class is None:
        console.print("Error: No hook class found in the module", style="bold red")
        sys.exit(1)

    # Parse input data
    try:
        input_dict = json.loads(input_data)
    except json.JSONDecodeError as e:
        console.print(f"Error: Invalid JSON input - {e}", style="bold red")
        sys.exit(1)

    # Create hook instance and run
    hook_instance = hook_class()
    hook_input = HookInput(**input_dict)

    async def run_hook():
        result = await hook_instance.run(hook_input)
        console.print(json.dumps(result.dict(), indent=2))

    asyncio.run(run_hook())


@app.command
def test(
    hooks_directory: Annotated[
        Path, Parameter("--hooks-dir", alias="-d", help="Directory containing hook files")
    ] = "./hooks",
    tests_directory: Annotated[
        Path, Parameter("--tests-dir", alias="-t", help="Directory containing test files")
    ] = "./tests",
    pattern: Annotated[
        str | None,
        Parameter("--pattern", alias="-p", help="Pattern to filter test files by name"),
    ] = None,
    parallel: Annotated[
        bool, Parameter("--parallel", alias="-P", help="Run tests in parallel")
    ] = False,
    timeout: Annotated[
        int, Parameter("--timeout", alias="-T", help="Timeout for each test in seconds")
    ] = 30,
    format: Annotated[
        str, Parameter("--format", alias="-f", help="Report format: text, json, or junit")
    ] = "text",
    verbose: Annotated[
        bool, Parameter("--verbose", alias="-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Run tests for hooks and generate reports.

    Parameters
    ----------
    hooks_directory
        Directory containing hook files (default: "./hooks")
    tests_directory
        Directory containing test files (default: "./tests")
    pattern
        Pattern to filter test files by name
    parallel
        Run tests in parallel (default: False)
    timeout
        Timeout for each test in seconds (default: 30)
    format
        Report format: text, json, or junit (default: "text")
    verbose
        Enable verbose output (default: False)
    """
    # Initialize the test runner
    runner = TestRunner(
        hooks_directory=hooks_directory,
        tests_directory=tests_directory,
        timeout=timeout,
    )

    # Run tests
    results = runner.run_tests(
        pattern=pattern,
        parallel=parallel,
        verbose=verbose,
    )

    # Generate and print report
    if format == "json":
        report = runner.generate_json_report(results)
        console.print(report)
    elif format == "junit":
        report = runner.generate_junit_report(results)
        console.print(report)
    else:  # text format
        report = runner.generate_text_report(results)
        console.print(report)

    # Exit with error code if there were test failures
    if any(not result.passed for result in results.values()):
        sys.exit(1)


# This ensures the CLI works when run with `python -m quickhooks.cli.main`
if __name__ == "__main__":
    app()
