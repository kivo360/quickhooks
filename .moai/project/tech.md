# Technology Stack & Technical Policies

## Technology Stack Overview

QuickHooks leverages modern Python technologies and best-in-class tools to deliver a robust, performant, and maintainable TDD framework for Claude Code hooks.

### Core Technology Summary

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.12+ | Core implementation language |
| **Package Manager** | UV | 0.9.6+ | Fast dependency management and builds |
| **CLI Framework** | Cyclopts | 1.0.0+ | Type-safe command-line interface |
| **AI Framework** | Pydantic AI | 0.0.49+ | Structured AI interactions |
| **AI Provider** | Fireworks AI | Latest | Cost-effective LLM inference |
| **Vector Database** | LanceDB | 0.24.2+ | Agent embeddings and search |
| **Embeddings** | FastEmbed | 0.2.0+ | Lightweight embedding generation |
| **Async Runtime** | anyio | 4.0.0+ | Async I/O abstractions |
| **File Watching** | watchfiles | 0.20.0+ | Hot-reload development server |
| **Console Output** | Rich | 13.7.0+ | Beautiful terminal formatting |
| **Validation** | Pydantic | 2.5.0+ | Data validation and settings |
| **Schema Validation** | jsonschema | 4.25.0+ | JSON schema validation |
| **Templating** | Jinja2 | 3.1.0+ | Code generation templates |
| **Diagrams** | Mermaid-py | 0.8.0+ | Workflow visualization |
| **Testing** | pytest | 7.4.0+ | Test framework |
| **Coverage** | pytest-cov | 4.1.0+ | Code coverage reporting |
| **Type Checking** | mypy | 1.8.0+ | Static type analysis |
| **Linting** | Ruff | 0.1.9+ | Fast Python linter and formatter |

## Language & Runtime

### Python 3.12+

**Selection Rationale**:
- Modern type hints and generics
- Performance improvements over 3.11
- Enhanced error messages
- Better async/await support

**Version Policy**:
- **Minimum**: Python 3.12 (required for type features)
- **Tested**: Python 3.12, 3.13
- **Recommended**: Python 3.13 (latest stable)

**Key Features Used**:
```python
# PEP 695: Type parameter syntax
class ParallelProcessor[T]:
    async def process(self, items: list[T]) -> list[T]:
        ...

# PEP 701: Improved f-string parsing
result = f"{
    complex_expression
    .with_multiple_lines()
}"

# PEP 688: Type hint for Ellipsis
def incomplete_function() -> ...:
    ...
```

### UV Package Manager (0.9.6+)

**Selection Rationale**:
- 10-100x faster than pip for dependency resolution
- Built-in build backend support
- PEP 723 (inline script metadata) support
- Modern Python project structure

**Configuration** (`pyproject.toml`):
```toml
[build-system]
requires = ["uv_build>=0.9.6,<0.10.0"]
build-backend = "uv_build"

[tool.uv]
default-groups = ["dev"]
```

**Usage Patterns**:
```bash
# Dependency management
uv sync --all-extras              # Install all dependencies
uv add package-name               # Add new dependency
uv remove package-name            # Remove dependency
uv lock                           # Update lock file

# Development workflow
uv run pytest                     # Run tests
uv run quickhooks-dev run src/    # Start dev server
uv build --no-sources            # Build package
```

**Benefits**:
- ✅ Faster CI/CD pipelines (5-10x speedup)
- ✅ Deterministic builds via `uv.lock`
- ✅ Better developer experience
- ✅ PEP 723 self-contained scripts

## Frameworks & Libraries

### CLI Framework: Cyclopts (1.0.0+)

**Selection Rationale**:
- Superior type safety compared to Typer
- Clean, intuitive API
- Excellent support for command groups
- Full mypy compliance

**Architecture**:
```python
from cyclopts import App, Group

app = App(name="quickhooks")

# Grouped commands
agents_group = Group("agents")

@app.command(group=agents_group)
def analyze(prompt: str, context: str | None = None) -> None:
    """Analyze prompt for agent recommendations."""
    ...
```

**Migration from Typer**:
- Completed in v0.2.0
- All commands migrated to Cyclopts
- 100% mypy compliance achieved

### AI Framework: Pydantic AI (0.0.49+)

**Selection Rationale**:
- Type-safe structured outputs via Pydantic
- Multi-provider support (OpenAI, Fireworks, Anthropic, etc.)
- Excellent error handling
- Lightweight and focused

**Integration Pattern**:
```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.fireworks import FireworksProvider

# Create Fireworks provider
provider = FireworksProvider(api_key=api_key)

# Create OpenAI-compatible model
model = OpenAIModel(model_name, provider=provider)

# Create typed agent
agent = Agent(
    model,
    output_type=AgentAnalysisResponse,
    system_prompt=system_prompt,
)

# Get structured output
response = await agent.run(prompt)
result: AgentAnalysisResponse = response.data
```

**Supported Providers**:
- Fireworks AI (primary)
- OpenAI (fallback)
- Anthropic (future)
- Local models via llama.cpp (future)

### Vector Database: LanceDB (0.24.2+)

**Selection Rationale**:
- Serverless, embedded in Python process
- No separate database server required
- Good performance for <10K agents
- Simple API and minimal setup

**Usage Pattern**:
```python
import lancedb
from fastembed import TextEmbedding

# Initialize database
db = lancedb.connect("~/.quickhooks/agents.lance")

# Create/open table
table = db.create_table(
    "agents",
    data=[
        {
            "name": "agent-name",
            "description": "agent description",
            "vector": embedding,
        }
    ],
    mode="overwrite",
)

# Semantic search
results = table.search(query_vector).limit(10).to_pandas()
```

**Performance Characteristics**:
- Search latency: <500ms for 1,000 agents
- Index size: ~1MB per 1,000 agents
- Memory usage: ~50MB baseline + 5MB per 1,000 agents

### Embeddings: FastEmbed (0.2.0+)

**Selection Rationale**:
- Lightweight (no sentence-transformers dependency)
- Fast inference
- Good quality embeddings
- Multiple model options

**Supported Models**:
```python
from fastembed import TextEmbedding

# Default model (BAAI/bge-small-en-v1.5)
embedding_model = TextEmbedding()

# Custom model
embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
```

**Performance**:
- Embedding generation: ~10ms per short text
- Model size: ~80MB (default model)
- Batch processing: ~100 texts/second

## Development Environment

### Build System

**UV Build Backend**:
```toml
[build-system]
requires = ["uv_build>=0.9.6,<0.10.0"]
build-backend = "uv_build"
```

**Build Commands**:
```bash
# Build wheel and sdist
uv build

# Build wheel only (faster)
uv build --no-sources

# Build with specific Python version
uv build --python 3.12
```

### Hot-Reload Development Server

**Implementation** (`src/quickhooks/dev.py`):
```python
from watchfiles import awatch

async def watch_and_reload(watch_path: Path, delay: float = 0.5):
    """Watch files and reload on changes."""
    async for changes in awatch(watch_path):
        console.print(f"[yellow]Detected changes: {changes}[/yellow]")
        await asyncio.sleep(delay)  # Debounce
        reload_application()
```

**Usage**:
```bash
# Start development server
uv run quickhooks-dev run src/ --delay 0.5

# With custom watch path
uv run quickhooks-dev run src/quickhooks/agent_analysis/
```

**Features**:
- Sub-second reload times
- Configurable watch paths
- Debouncing to prevent rapid reloads
- Clear console output on changes

### Testing Strategy

**Framework**: pytest 7.4.0+

**Test Structure**:
```
tests/
├── conftest.py              # Shared fixtures
├── test_*.py                # Unit tests
├── integration/             # Integration tests
│   ├── test_fireworks_integration.py
│   └── test_fireworks_provider.py
└── hooks_test/              # Hook-specific tests
```

**Coverage Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=quickhooks",
    "--cov-report=term-missing",
    "--cov-report=xml",
    "--cov-report=html",
    "--cov-fail-under=80",
]
```

**Test Categories**:
```python
import pytest

@pytest.mark.unit
def test_hook_validation():
    """Unit test for hook validation logic."""
    ...

@pytest.mark.integration
async def test_fireworks_integration():
    """Integration test for Fireworks AI."""
    ...

@pytest.mark.slow
async def test_large_workflow():
    """Slow test for large workflows."""
    ...
```

**Running Tests**:
```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest -m unit

# With coverage
uv run pytest --cov=quickhooks --cov-report=html

# Specific test file
uv run pytest tests/test_agent_analysis.py -v
```

### Code Quality Tools

#### Ruff (0.1.9+)

**Purpose**: Fast, all-in-one linter and formatter

**Configuration** (`ruff.toml`):
```toml
[lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "ANN", # flake8-annotations
    "S",   # flake8-bandit
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "DTZ", # flake8-datetimez
    "T10", # flake8-debugger
    "RUF", # Ruff-specific rules
]

[format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

**Usage**:
```bash
# Format code
uv run ruff format src/ tests/

# Check linting
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/
```

#### Mypy (1.8.0+)

**Purpose**: Static type checking

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
disallow_any_generics = true
no_implicit_optional = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

**Usage**:
```bash
# Type check entire codebase
uv run mypy src/quickhooks

# Type check specific module
uv run mypy src/quickhooks/agent_analysis/
```

**Type Coverage Goals**:
- 100% of public APIs fully typed
- 90%+ overall type coverage
- Zero `Any` types in core modules

## CI/CD & Deployment

### Continuous Integration

**GitHub Actions Workflow**:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run tests
        run: uv run pytest --cov=quickhooks
      - name: Type check
        run: uv run mypy src/quickhooks
      - name: Lint
        run: uv run ruff check src/ tests/
```

**Quality Gates**:
- ✅ All tests pass (pytest)
- ✅ Coverage ≥80% (pytest-cov)
- ✅ Type checks pass (mypy)
- ✅ Linting passes (ruff)
- ✅ Build succeeds (uv build)

### Deployment Pipeline

**PyPI Publishing**:
```bash
# Build distribution
uv build --no-sources

# Publish to PyPI (requires PYPI_TOKEN)
uv publish
```

**Versioning Strategy**:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Automated version bumping via `scripts/semver-automation.py`
- Git tags for releases
- CHANGELOG.md maintained manually

**Release Process**:
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag (`git tag v0.2.0`)
4. Push tag (`git push --tags`)
5. GitHub Actions builds and publishes to PyPI

### Environment Configuration

**Environment Variables**:
```bash
# Required for AI features
FIREWORKS_API_KEY=your_api_key_here

# Optional configuration
QUICKHOOKS_LOG_LEVEL=INFO
QUICKHOOKS_AGENT_DIR=~/.claude/agents
QUICKHOOKS_DB_PATH=~/.quickhooks/agents.lance
QUICKHOOKS_CONFIG_PATH=~/.quickhooks/config.json

# Agent OS integration (optional)
AGENT_OS_PATH=~/.agent-os
```

**Configuration Management**:
```python
from pydantic_settings import BaseSettings

class QuickHooksConfig(BaseSettings):
    """QuickHooks configuration."""

    # AI settings
    fireworks_api_key: str
    fireworks_llm: str = "qwen/qwen3-32b"
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"

    # Agent discovery
    agent_dir: Path = Path.home() / ".claude" / "agents"
    db_path: Path = Path.home() / ".quickhooks" / "agents.lance"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_prefix = "QUICKHOOKS_"
        env_file = ".env"
```

## Performance & Scalability

### Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Agent analysis | <2s | ~1.5s |
| Hot reload | <1s | ~0.5s |
| Hook execution overhead | <100ms | ~50ms |
| Vector search (1K agents) | <500ms | ~300ms |
| Workflow execution (10 steps) | <10s | ~8s |

### Performance Optimization Strategies

**1. Async-First Architecture**:
```python
# Concurrent API calls
async def analyze_with_multiple_providers(prompt: str):
    tasks = [
        fireworks_analyze(prompt),
        openai_analyze(prompt),
    ]
    results = await asyncio.gather(*tasks)
    return combine_results(results)
```

**2. Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_agent_embedding(agent_name: str) -> list[float]:
    """Cache agent embeddings to avoid recomputation."""
    return compute_embedding(agent_name)
```

**3. Batching**:
```python
async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts for efficiency."""
    return embedding_model.embed(texts, batch_size=32)
```

**4. Resource Pooling**:
```python
class DatabasePool:
    """Connection pool for LanceDB."""

    def __init__(self, max_connections: int = 10):
        self._pool = asyncio.Queue(maxsize=max_connections)
        # Initialize pool...
```

### Scalability Considerations

**Current Scale**:
- Up to 10,000 local agents
- Concurrent execution of 100 hooks
- Workflow state up to 1GB
- Context size up to 128K tokens

**Future Scalability**:
- Distributed agent registry (Redis/PostgreSQL)
- Multi-node workflow execution
- Cloud-based vector search (Pinecone/Weaviate)
- Horizontal scaling via Kubernetes

## Security & Compliance

### Security Policies

**1. API Key Management**:
```python
# ✅ Correct: Environment variables
api_key = os.getenv("FIREWORKS_API_KEY")

# ❌ Wrong: Hardcoded secrets
api_key = "sk-abc123..."  # NEVER DO THIS
```

**2. Input Validation**:
```python
from pydantic import BaseModel, validator

class AgentAnalysisRequest(BaseModel):
    prompt: str
    context: str | None = None
    threshold: float = 0.5

    @validator("threshold")
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v
```

**3. Dependency Security**:
```yaml
# Dependabot configuration
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

**4. Safe Template Rendering**:
```python
from jinja2 import Environment, select_autoescape

env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    # Disable unsafe features
    trim_blocks=True,
    lstrip_blocks=True,
)
```

### Compliance Requirements

**Open Source License**: MIT License
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ⚠️ No warranty provided

**Dependencies**: All dependencies use permissive licenses
- MIT, Apache 2.0, BSD

**Data Privacy**:
- No user data collected by QuickHooks
- AI API calls respect user's Fireworks account settings
- Local agent data never leaves user's machine (unless using cloud features)

## Operational Requirements

### Logging

**Structured Logging**:
```python
import logging

logger = logging.getLogger("quickhooks")

# Configure handler
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Usage
logger.info("Agent analysis started", extra={"prompt": prompt})
logger.warning("API rate limit approaching", extra={"remaining": 10})
logger.error("Hook execution failed", exc_info=True)
```

**Log Levels**:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (e.g., deprecations)
- **ERROR**: Error messages (recoverable)
- **CRITICAL**: Critical errors (unrecoverable)

### Monitoring

**Key Metrics**:
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExecutionMetrics:
    """Metrics for hook execution."""

    hook_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error: str | None = None
```

**Metric Collection**:
- Execution time per operation
- Success/failure rates
- API call latencies
- Memory usage
- Cache hit rates

**Export Formats**:
- JSON logs for aggregation
- Prometheus metrics (future)
- OpenTelemetry traces (future)

### Incident Response

**Error Handling Patterns**:
```python
from quickhooks.exceptions import QuickHooksError

class HookExecutionError(QuickHooksError):
    """Raised when hook execution fails."""

    def __init__(self, hook_name: str, cause: Exception):
        self.hook_name = hook_name
        self.cause = cause
        super().__init__(f"Hook {hook_name} failed: {cause}")

# Usage
try:
    await hook.execute(input_data, context)
except Exception as e:
    raise HookExecutionError(hook.name, e) from e
```

**Recovery Strategies**:
- Retry with exponential backoff for transient failures
- Fallback to cached results when API unavailable
- Graceful degradation (disable non-essential features)
- Clear error messages with actionable guidance

## Technical Constraints

### Hard Requirements

1. **Python 3.12+**: Required for type system features
2. **UV Package Manager**: Required for build and dependency management
3. **Fireworks API Key**: Required for AI-powered features
4. **~/.claude/agents**: Required for local agent discovery

### Soft Requirements

1. **Agent OS Installation**: Optional, enables workflow features
2. **LanceDB Storage**: ~100MB for 10,000 agents
3. **Network Access**: Required for AI API calls
4. **Write Permissions**: ~/.quickhooks/ directory for database and cache

### Platform Support

**Officially Supported**:
- ✅ macOS 12+ (Intel and Apple Silicon)
- ✅ Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
- ⚠️ Windows via WSL2 (native Windows support planned)

**Tested Environments**:
- Docker containers (python:3.12-slim)
- GitHub Actions runners (ubuntu-latest)
- Local development machines

## Future Technology Roadmap

### Short-Term (v0.3.0)
- Plugin system for custom AI providers
- Multi-provider support (OpenAI, Anthropic)
- Performance monitoring dashboard
- Enhanced caching strategies

### Medium-Term (v0.5.0)
- GUI for hook configuration (Streamlit)
- Cloud-hosted agent registry
- Distributed workflow execution
- WebSocket support for real-time updates

### Long-Term (v1.0.0+)
- Kubernetes operator for scaling
- Multi-language support (TypeScript SDK)
- Enterprise features (SSO, RBAC)
- Marketplace for community hooks and workflows

---

**Document Version**: 1.0
**Last Updated**: 2025-01-08
**Owner**: @user
**Status**: Active Development
