#!/usr/bin/env python3
"""Comprehensive schema compliance audit for all parts of the application."""

import json
import re
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from quickhooks.schema.validator import (
    ClaudeSettingsValidator,
)


def audit_documentation_examples():
    """Audit all documentation for schema-compliant examples."""
    print("📚 Auditing Documentation Examples")
    print("=" * 50)

    validator = ClaudeSettingsValidator()
    issues = []

    # Find all markdown files
    md_files = list(Path(".").glob("**/*.md"))

    for md_file in md_files:
        print(f"\n📄 Checking {md_file.name}...")

        try:
            content = md_file.read_text()

            # Find JSON code blocks
            json_blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)

            for i, json_block in enumerate(json_blocks):
                try:
                    config = json.loads(json_block)

                    # Check if it's a Claude Code settings file
                    if "hooks" in config:
                        is_valid, errors = validator.validate_settings(config)
                        if not is_valid:
                            issues.append(
                                {"file": str(md_file), "block": i + 1, "errors": errors}
                            )
                            print(f"   ❌ JSON block {i + 1}: Schema validation failed")
                            for error in errors[:2]:  # Show first 2 errors
                                print(f"      • {error}")
                        else:
                            print(f"   ✅ JSON block {i + 1}: Valid")

                except json.JSONDecodeError:
                    print(
                        f"   ⚠️  JSON block {i + 1}: Invalid JSON (may be example fragment)"
                    )

        except Exception as e:
            print(f"   ❌ Error reading {md_file}: {e}")

    return issues


def audit_test_configurations():
    """Audit all test files for schema-compliant configurations."""
    print("\n🧪 Auditing Test Configurations")
    print("=" * 50)

    ClaudeSettingsValidator()
    issues = []

    # Find all test files
    test_files = list(Path(".").glob("test*.py")) + list(
        Path("tests").glob("*.py") if Path("tests").exists() else []
    )

    for test_file in test_files:
        print(f"\n📄 Checking {test_file.name}...")

        try:
            content = test_file.read_text()

            # Look for hardcoded hook configurations
            # Find dictionary literals that might be settings
            dict_patterns = [
                r'"hooks"\s*:\s*{[^}]+}',
                r'"PreToolUse"\s*:\s*\[[^\]]+\]',
                r'"matcher"\s*:\s*\[[^\]]+\]',  # Old array format
            ]

            for pattern in dict_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                if matches:
                    print(
                        f"   ⚠️  Found potential configuration patterns: {len(matches)}"
                    )

            # Look for specific schema violations (but exclude this audit file itself)
            if (
                '"matcher": [' in content
                and "test_schema_compliance_audit.py" not in str(test_file)
            ):
                issues.append(
                    {
                        "file": str(test_file),
                        "issue": "Uses old array format for matcher (should be string with | separator)",
                    }
                )
                print("   ❌ Uses old array format for matcher")

            # Look for the specific pattern of description inside hook command objects
            hook_desc_pattern = r'"type"\s*:\s*"command"[^}]*"description"'
            if re.search(hook_desc_pattern, content, re.DOTALL):
                issues.append(
                    {
                        "file": str(test_file),
                        "issue": "Hook command includes invalid description field",
                    }
                )
                print("   ❌ Hook command includes invalid description field")

        except Exception as e:
            print(f"   ❌ Error reading {test_file}: {e}")

    return issues


def audit_hook_implementations():
    """Audit hook implementations for correct input/output format."""
    print("\n🔧 Auditing Hook Implementations")
    print("=" * 50)

    issues = []
    hook_files = list(Path("hooks").glob("*.py") if Path("hooks").exists() else [])

    for hook_file in hook_files:
        print(f"\n📄 Checking {hook_file.name}...")

        try:
            content = hook_file.read_text()

            # Check for correct input format handling
            required_fields = [
                "session_id",
                "tool_name",
                "tool_input",
                "hook_event_name",
            ]
            missing_fields = []

            for field in required_fields:
                if field not in content:
                    missing_fields.append(field)

            if missing_fields:
                issues.append(
                    {
                        "file": str(hook_file),
                        "issue": f"Missing input field handling: {missing_fields}",
                    }
                )
                print(f"   ❌ Missing input fields: {missing_fields}")
            else:
                print("   ✅ Handles all required input fields")

            # Check for correct output format
            valid_output_patterns = [
                r'"continue"\s*:\s*(true|false)',
                r'"suppressOutput"\s*:\s*(true|false)',
                r'"stopReason"\s*:\s*"',
                r"sys\.exit\(0\)",  # Simple exit code approach
            ]

            has_valid_output = any(
                re.search(pattern, content) for pattern in valid_output_patterns
            )

            if has_valid_output:
                print("   ✅ Uses valid output format")
            else:
                issues.append(
                    {
                        "file": str(hook_file),
                        "issue": "May not use correct output format (JSON with continue/suppressOutput or exit code)",
                    }
                )
                print("   ⚠️  Output format may need verification")

        except Exception as e:
            print(f"   ❌ Error reading {hook_file}: {e}")

    return issues


def audit_generated_configurations():
    """Test that our installation system generates schema-compliant configurations."""
    print("\n⚙️  Auditing Generated Configurations")
    print("=" * 50)

    validator = ClaudeSettingsValidator()
    issues = []

    # Test various configuration scenarios
    test_scenarios = [
        {
            "name": "Standard Context Portal Hook",
            "tools": [
                "Bash",
                "Edit",
                "Write",
                "Read",
                "Grep",
                "Glob",
                "Task",
                "WebFetch",
                "WebSearch",
            ],
            "timeout": 30,
        },
        {"name": "Minimal Hook", "tools": ["Bash"], "timeout": None},
        {
            "name": "All Valid Tools",
            "tools": validator.get_valid_tools_for_matcher(),
            "timeout": 60,
        },
    ]

    for scenario in test_scenarios:
        print(f"\n📝 Testing: {scenario['name']}")

        try:
            pattern = validator.suggest_matcher_pattern(scenario["tools"])
            hook_config = validator.create_valid_hook_config(
                hook_type="PreToolUse",
                matcher=pattern,
                command="/path/to/hook.py",
                timeout=scenario["timeout"],
            )

            # Validate the generated configuration
            is_valid, errors = validator.validate_hook_configuration(hook_config)

            if is_valid:
                print("   ✅ Generated valid configuration")
                print(f"   Pattern: {pattern}")
            else:
                issues.append({"scenario": scenario["name"], "errors": errors})
                print("   ❌ Generated invalid configuration:")
                for error in errors:
                    print(f"      • {error}")

        except Exception as e:
            issues.append({"scenario": scenario["name"], "error": str(e)})
            print(f"   ❌ Configuration generation failed: {e}")

    return issues


def create_schema_compliance_report():
    """Generate a comprehensive schema compliance report."""
    print("🔍 Claude Code Schema Compliance Audit")
    print("=" * 60)
    print("Ensuring all parts of the application are future-proof and schema-compliant")
    print("=" * 60)

    all_issues = []

    # Run all audits
    doc_issues = audit_documentation_examples()
    test_issues = audit_test_configurations()
    hook_issues = audit_hook_implementations()
    gen_issues = audit_generated_configurations()

    all_issues.extend(doc_issues)
    all_issues.extend(test_issues)
    all_issues.extend(hook_issues)
    all_issues.extend(gen_issues)

    # Generate summary report
    print("\n📊 Schema Compliance Summary")
    print("=" * 60)

    categories = {
        "Documentation": len(doc_issues),
        "Test Configurations": len(test_issues),
        "Hook Implementations": len(hook_issues),
        "Generated Configurations": len(gen_issues),
    }

    for category, issue_count in categories.items():
        status = "✅ COMPLIANT" if issue_count == 0 else f"❌ {issue_count} ISSUES"
        print(f"   {category}: {status}")

    total_issues = len(all_issues)
    overall_status = (
        "✅ FULLY COMPLIANT" if total_issues == 0 else f"⚠️  {total_issues} ISSUES FOUND"
    )

    print(f"\n🎯 Overall Status: {overall_status}")

    if all_issues:
        print("\n🔧 Issues to Fix:")
        for i, issue in enumerate(all_issues[:10], 1):  # Show first 10 issues
            print(f"   {i}. {issue}")

        if len(all_issues) > 10:
            print(f"   ... and {len(all_issues) - 10} more issues")

    print("\n💡 Recommendations:")
    print("• All hook configurations should use schema validation")
    print("• Documentation examples should be automatically tested")
    print("• Test configurations should use schema-generated examples")
    print("• Hook implementations should follow official input/output format")
    print("• Regular schema compliance checks should be part of CI/CD")

    return len(all_issues) == 0


if __name__ == "__main__":
    success = create_schema_compliance_report()
    sys.exit(0 if success else 1)
