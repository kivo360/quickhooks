# Automated SemVer with Groq AI

QuickHooks includes an automated semantic versioning system that uses Groq's AI to analyze git commits and determine appropriate version bumps.

## Overview

The `scripts/semver-automation.py` script analyzes git changes between commits and uses AI to determine:

- **MAJOR** (X.y.z): Breaking changes, incompatible API changes
- **MINOR** (x.Y.z): New features, backwards compatible  
- **PATCH** (x.y.Z): Bug fixes, backwards compatible
- **NONE**: No version change needed (docs, tests only)

## Features

✨ **AI-Powered Analysis**: Uses Groq's LLM to understand change context  
🔍 **Git Integration**: Analyzes commit messages, diffs, and file changes  
📦 **Auto Version Bump**: Updates `pyproject.toml` automatically  
🤖 **GitHub Actions**: Fully automated CI/CD integration  
💡 **Fallback Logic**: Heuristic analysis when API is unavailable  
📊 **Confidence Scoring**: Provides confidence levels for decisions  

## Quick Start

### Prerequisites

```bash
# Set up Groq API key
export GROQ_API_KEY="your-groq-api-key"

# Install dependencies (already included in dev deps)
uv sync
```

### Basic Usage

```bash
# Analyze current changes (dry run)
uv run python scripts/semver-automation.py --dry-run --verbose

# Apply version bump
uv run python scripts/semver-automation.py --verbose

# Analyze specific commit range
uv run python scripts/semver-automation.py \
  --from-ref "v0.1.0" \
  --to-ref "HEAD" \
  --dry-run
```

### Example Output

```
=== SEMVER ANALYSIS ===
Current version: 0.1.1
Suggested bump: minor
New version: 0.2.0
Confidence: 0.80

Reasoning: The commit message starts with 'feat:', indicating a new feature. 
The changes include adding comprehensive documentation, reorganizing test files, 
and updating GitHub Actions. No breaking changes detected.

Change Analysis:
  Breaking changes: False
  New features: True
  Bug fixes: False
  Documentation only: False
  Test only: False
  Refactor only: False

✅ Successfully updated version to 0.2.0
```

## GitHub Actions Integration

The system includes a complete GitHub Actions workflow (`.github/workflows/semver.yml`) that:

### On Pull Requests
- Analyzes proposed changes
- Comments on PR with version impact
- Shows what version bump would occur

### On Main Branch Push
- Automatically analyzes commits
- Updates version in `pyproject.toml`
- Creates GitHub release
- Publishes to PyPI
- Sends notifications

### Setup Requirements

Add these secrets to your GitHub repository:

```bash
GROQ_API_KEY=your_groq_api_key
PYPI_API_TOKEN=your_pypi_token
```

## Analysis Logic

### AI Prompt Strategy

The script builds a comprehensive prompt including:

```python
prompt = f"""
COMMITS TO ANALYZE:
--- COMMIT: {hash} ---
Message: {message}
Files changed: {files}
Stats: +{insertions} -{deletions}
Diff sample: {diff_sample}

ANALYSIS CRITERIA:
- Breaking changes: API changes, removed functions, changed signatures
- New features: Added functions/classes, new capabilities
- Bug fixes: Fixed issues, corrected behavior
- Documentation only: Only README, docs, comments changed
- Test only: Only test files changed
"""
```

### Commit Message Patterns

The system recognizes conventional commit patterns:

| Pattern | Bump Type | Examples |
|---------|-----------|-----------|
| `feat:`, `feature:` | MINOR | `feat: add user authentication` |
| `fix:`, `bug:` | PATCH | `fix: resolve memory leak` |
| `BREAKING CHANGE:`, `!:` | MAJOR | `feat!: remove deprecated API` |
| `docs:`, `README` | NONE | `docs: update installation guide` |
| `test:`, `tests/` | NONE | `test: add unit tests for auth` |

### File Pattern Analysis

The system analyzes changed files:

```python
# Documentation changes
docs/, README.md, *.md, LICENSE

# Test changes  
test/, tests/, *_test.py, test_*.py

# Source code changes
src/, *.py, *.js, *.ts

# Configuration changes
pyproject.toml, package.json, requirements.txt
```

### Confidence Scoring

Confidence levels indicate analysis reliability:

- **0.9-1.0**: Very confident (clear patterns)
- **0.7-0.9**: Confident (good indicators)  
- **0.5-0.7**: Moderate (mixed signals)
- **0.0-0.5**: Low confidence (unclear changes)

## Advanced Usage

### Custom Analysis

```python
from scripts.semver_automation import SemVerAnalyzer

analyzer = SemVerAnalyzer(groq_api_key="your-key")

# Get changes
changes = analyzer.get_git_changes("v1.0.0", "HEAD")

# Analyze
analysis = analyzer.analyze_changes(changes)

print(f"Suggested bump: {analysis.suggested_bump}")
print(f"Confidence: {analysis.confidence}")
print(f"Reasoning: {analysis.reasoning}")
```

### Integration with Other Tools

```bash
# Use with conventional commits
git commit -m "feat: add new API endpoint"

# Use with semantic release
npm install -g semantic-release

# Custom hook integration
echo "uv run python scripts/semver-automation.py" > .git/hooks/pre-push
```

### CI/CD Integration

#### GitLab CI

```yaml
# .gitlab-ci.yml
semver-analysis:
  script:
    - pip install -r scripts/requirements-semver.txt
    - python scripts/semver-automation.py --dry-run
  only:
    - merge_requests

auto-release:
  script:
    - python scripts/semver-automation.py
    - uv build && uv publish
  only:
    - main
```

#### Jenkins

```groovy
pipeline {
    agent any
    environment {
        GROQ_API_KEY = credentials('groq-api-key')
    }
    stages {
        stage('SemVer Analysis') {
            steps {
                sh 'python scripts/semver-automation.py --dry-run'
            }
        }
        stage('Release') {
            when { branch 'main' }
            steps {
                sh 'python scripts/semver-automation.py'
                sh 'uv build && uv publish'
            }
        }
    }
}
```

## Configuration

### Script Options

```bash
python scripts/semver-automation.py [OPTIONS]

Options:
  --from-ref TEXT     Git reference to compare from (default: HEAD~1)
  --to-ref TEXT       Git reference to compare to (default: HEAD)
  --dry-run          Show analysis without updating version
  --pyproject TEXT   Path to pyproject.toml (default: pyproject.toml)
  --groq-api-key TEXT Groq API key (or set GROQ_API_KEY env var)
  --verbose, -v      Verbose output
  --help             Show help message
```

### Environment Variables

```bash
# Required
GROQ_API_KEY=your_groq_api_key

# Optional
GROQ_MODEL=llama-3.3-70b-versatile  # AI model to use
SEMVER_LOG_LEVEL=INFO               # Logging level
SEMVER_CONFIDENCE_THRESHOLD=0.7     # Minimum confidence for auto-bump
```

## Troubleshooting

### Common Issues

**Q: Script says "No changes found"**
```bash
# Check git history
git log --oneline -5

# Ensure you're comparing the right refs
python scripts/semver-automation.py --from-ref "origin/main" --to-ref "HEAD"
```

**Q: Low confidence scores**
```bash
# Use more descriptive commit messages
git commit -m "feat: add user authentication system with JWT tokens"

# Instead of:
git commit -m "update stuff"
```

**Q: Wrong version bump detected**
```bash
# Review the reasoning
python scripts/semver-automation.py --dry-run --verbose

# Use manual override if needed
git tag v1.2.3
```

### Fallback Mode

If Groq API is unavailable, the script uses heuristic analysis:

1. **Commit Message Patterns**: Conventional commit detection
2. **File Analysis**: Source vs docs vs tests
3. **Change Statistics**: Insertions vs deletions ratio
4. **Conservative Defaults**: When in doubt, suggests PATCH

### Debug Mode

```bash
# Enable debug logging
export SEMVER_LOG_LEVEL=DEBUG
python scripts/semver-automation.py --verbose

# Check API connectivity
curl -H "Authorization: Bearer $GROQ_API_KEY" \
     https://api.groq.com/openai/v1/models
```

## Best Practices

### 1. Commit Message Standards

Use conventional commits for best results:

```bash
# Good examples
git commit -m "feat: add user dashboard with charts"
git commit -m "fix: resolve authentication timeout issue"
git commit -m "docs: update API documentation"
git commit -m "feat!: remove legacy API endpoints"

# Avoid
git commit -m "updates"
git commit -m "fix stuff"
git commit -m "WIP"
```

### 2. Branch Strategy

```bash
# Feature development
git checkout -b feature/user-auth
# ... make changes ...
git commit -m "feat: implement OAuth2 authentication"

# Bug fixes
git checkout -b fix/memory-leak
# ... make changes ...
git commit -m "fix: resolve memory leak in event handler"

# Breaking changes
git checkout -b breaking/api-redesign
# ... make changes ...
git commit -m "feat!: redesign REST API structure"
```

### 3. Release Process

1. **Development**: Work on feature branches
2. **PR Review**: SemVer analysis runs automatically
3. **Merge**: Merging to main triggers version bump
4. **Release**: Automated publishing to PyPI
5. **Documentation**: Release notes generated automatically

### 4. Version Strategy

- **PATCH**: Bug fixes, security patches, dependency updates
- **MINOR**: New features, API additions, enhancements
- **MAJOR**: Breaking changes, API removals, architecture changes

## Integration Examples

### Pre-commit Hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
python scripts/semver-automation.py --dry-run > /dev/null
if [ $? -ne 0 ]; then
    echo "SemVer analysis failed. Check your changes."
    exit 1
fi
```

### Release Notes Generation

```python
# scripts/generate-release-notes.py
from semver_automation import SemVerAnalyzer

analyzer = SemVerAnalyzer()
changes = analyzer.get_git_changes("v1.0.0", "HEAD")
analysis = analyzer.analyze_changes(changes)

release_notes = f"""
## Release v{new_version}

**Type**: {analysis.suggested_bump.upper()}
**Confidence**: {analysis.confidence:.0%}

### Summary
{analysis.reasoning}

### Changes
- Breaking changes: {'Yes' if analysis.breaking_changes else 'No'}
- New features: {'Yes' if analysis.new_features else 'No'}
- Bug fixes: {'Yes' if analysis.bug_fixes else 'No'}
"""
```

## API Reference

### SemVerAnalyzer Class

```python
class SemVerAnalyzer:
    def __init__(self, groq_api_key: Optional[str] = None)
    
    def get_git_changes(self, from_ref: str, to_ref: str) -> List[GitChange]
    def analyze_changes(self, changes: List[GitChange]) -> CommitAnalysis
    def get_current_version(self, pyproject_path: str) -> str
    def bump_version(self, current_version: str, bump_type: VersionBumpType) -> str
    def update_pyproject_version(self, new_version: str, pyproject_path: str) -> bool
```

### Models

```python
class VersionBumpType(str, Enum):
    MAJOR = "major"
    MINOR = "minor" 
    PATCH = "patch"
    NONE = "none"

class CommitAnalysis(BaseModel):
    breaking_changes: bool
    new_features: bool
    bug_fixes: bool
    documentation_only: bool
    test_only: bool
    refactor_only: bool
    confidence: float
    reasoning: str
    suggested_bump: VersionBumpType
```

This automated SemVer system takes the guesswork out of versioning, ensuring consistent and semantic version management for your QuickHooks projects!