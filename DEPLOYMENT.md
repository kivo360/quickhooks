# QuickHooks Deployment System

A comprehensive deployment system built for QuickHooks using UV package manager, featuring automated PyPI publishing, parallel agent coordination, and one-command deployment.

## 🚀 Features

- **One-Command Deployment**: Deploy entire project with a single command
- **UV Package Manager Integration**: Native support for UV build and publish
- **Parallel Agent Coordination**: Execute tasks simultaneously for faster deployments
- **Automated Version Management**: Semantic version bumping with UV
- **Build Artifact Validation**: Comprehensive package validation before publishing
- **Multi-Environment Support**: Development, staging, and production environments
- **Security Scanning**: Built-in security and vulnerability checks
- **Rollback Procedures**: Automated rollback capabilities
- **GitHub Actions Integration**: Complete CI/CD pipeline

## 📋 Quick Start

### Prerequisites

- Python 3.11+
- UV package manager installed
- Git repository initialized
- PyPI account and API tokens (for publishing)

### Basic Deployment

```bash
# Deploy to development environment
python scripts/deploy.py --env dev

# Deploy with version bump and publish to staging
python scripts/deploy.py --env staging --version patch --publish

# Deploy to production with full validation
python scripts/deploy.py --env prod --version minor --publish
```

### Agent Coordination

```bash
# Run parallel build tasks
python scripts/agent-coordinator.py build

# Run comprehensive test suite
python scripts/agent-coordinator.py test

# Orchestrate full deployment pipeline
python scripts/agent-coordinator.py orchestrate --monitor
```

### Build Validation

```bash
# Validate built packages
python scripts/validate-build.py

# Generate package checksums
python scripts/validate-build.py checksum

# Verbose validation with details
python scripts/validate-build.py --verbose
```

## 🏗️ Architecture

### Core Components

1. **Deploy Script** (`scripts/deploy.py`)
   - Main deployment orchestrator
   - Version management
   - Environment coordination
   - PyPI publishing

2. **Agent Coordinator** (`scripts/agent-coordinator.py`)
   - Parallel task execution
   - Agent management
   - Resource optimization
   - Real-time monitoring

3. **Build Validator** (`scripts/validate-build.py`)
   - Package integrity checks
   - Security scanning
   - Metadata validation
   - Installation testing

4. **GitHub Actions** (`.github/workflows/release.yml`)
   - Automated CI/CD pipeline
   - Multi-platform testing
   - Trusted publishing
   - Release management

### Agent Types

- **BuildAgent**: Package building and artifact creation
- **TestAgent**: Test execution and coverage analysis  
- **ValidationAgent**: Build validation and security checks
- **DeploymentAgent**: Publishing and deployment tasks
- **MonitoringAgent**: Health checks and metrics collection

## ⚙️ Configuration

### Environment Configuration

Configure environments in `deployment-config.yml`:

```yaml
environments:
  development:
    python_version: "3.12"
    publish_to_pypi: false
    parallel_agents: true
    
  staging:
    python_version: "3.12"
    publish_to_pypi: true
    publish_index: "testpypi"
    
  production:
    python_version: "3.12"
    publish_to_pypi: true
    publish_index: "pypi"
    require_clean_git: true
```

### PyPI Configuration

Set up PyPI publishing in `pyproject.toml`:

```toml
# PyPI Publishing Configuration
[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple/"
publish-url = "https://upload.pypi.org/legacy/"
default = true

[[tool.uv.index]]
name = "testpypi"
url = "https://test.pypi.org/simple/"
publish-url = "https://test.pypi.org/legacy/"
explicit = true
```

### Environment Variables

Required environment variables for PyPI publishing:

```bash
# For PyPI
export UV_PUBLISH_TOKEN="pypi-..."

# For TestPyPI
export UV_PUBLISH_TOKEN_TESTPYPI="pypi-..."

# For GitHub Actions (using trusted publishing)
# No tokens needed - uses OIDC
```

## 🔄 Deployment Workflows

### Development Workflow

```bash
# 1. Make changes to code
git add .
git commit -m "Add new feature"

# 2. Run development deployment
python scripts/deploy.py --env dev --skip-tests

# 3. Quick build validation
python scripts/validate-build.py
```

### Staging Workflow

```bash
# 1. Bump version and run full validation
python scripts/deploy.py --env staging --version patch --publish

# 2. Verify on TestPyPI
pip install -i https://test.pypi.org/simple/ quickhooks

# 3. Run integration tests
python scripts/agent-coordinator.py test
```

### Production Workflow

```bash
# 1. Create release tag
git tag v1.0.0
git push origin v1.0.0

# 2. GitHub Actions automatically:
#    - Runs comprehensive tests
#    - Builds packages
#    - Validates security
#    - Publishes to PyPI
#    - Creates GitHub release

# 3. Manual production deployment (if needed)
python scripts/deploy.py --env prod --publish
```

## 🧪 Testing and Validation

### Comprehensive Test Suite

```bash
# Run all tests with coverage
uv run pytest --cov=src/quickhooks --cov-report=html

# Run specific test categories
uv run pytest tests/test_unit.py -v
uv run pytest tests/test_integration.py -v
uv run pytest tests/test_performance.py -v
```

### Build Validation

The build validation includes:

- **Package Integrity**: Wheel and sdist validation
- **Metadata Consistency**: pyproject.toml vs package metadata
- **Import Structure**: Proper package organization
- **Security Scanning**: Vulnerability and risk assessment
- **Size Validation**: Package size optimization
- **Installation Testing**: Clean environment installation

### Security Checks

```bash
# Run security audit
uv run safety check

# Static analysis security scan
uv run bandit -r src/

# Dependency vulnerability scan
python scripts/validate-build.py --verbose
```

## 📊 Monitoring and Metrics

### Real-Time Monitoring

```bash
# Monitor deployment with live updates
python scripts/agent-coordinator.py orchestrate --monitor

# Check deployment status
python scripts/deploy.py status

# View agent performance
python scripts/agent-coordinator.py status
```

### Performance Metrics

- **Build Time**: Package build duration
- **Test Duration**: Complete test suite execution time
- **Success Rate**: Deployment success percentage
- **Agent Efficiency**: Resource utilization and task completion
- **Package Size**: Optimized artifact sizes

## 🔧 Advanced Features

### Parallel Agent Execution

```python
# Configure custom agents
from scripts.agent_coordinator import Agent, AgentCoordinator

coordinator = AgentCoordinator()
coordinator.add_agent(Agent("CustomAgent", "custom", max_concurrent=3))

# Execute tasks in parallel
tasks = [build_task, test_task, validate_task]
results = await coordinator.execute_tasks(tasks)
```

### Custom Validation Rules

```python
# Add custom validation in validate-build.py
def custom_validation(metadata):
    # Your custom validation logic
    if metadata.size_bytes > MAX_SIZE:
        return False
    return True
```

### Environment-Specific Configurations

```yaml
# deployment-config.yml
environments:
  custom_env:
    name: "Custom Environment"
    custom_settings:
      api_endpoint: "https://api.custom.com"
      feature_flags: ["experimental"]
```

## 🐛 Troubleshooting

### Common Issues

1. **UV Not Found**
   ```bash
   # Install UV
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **PyPI Authentication Failed**
   ```bash
   # Check token
   echo $UV_PUBLISH_TOKEN
   
   # Verify token format
   # Should start with "pypi-"
   ```

3. **Build Validation Failed**
   ```bash
   # Check build artifacts
   ls -la dist/
   
   # Run verbose validation
   python scripts/validate-build.py --verbose
   ```

4. **Tests Failing**
   ```bash
   # Run tests with detailed output
   uv run pytest -vvv --tb=long
   
   # Check test dependencies
   uv sync --all-groups
   ```

### Debug Mode

```bash
# Enable debug logging
export QUICKHOOKS_DEBUG=1

# Run deployment with verbose output
python scripts/deploy.py --env dev --verbose

# Check agent logs
python scripts/agent-coordinator.py orchestrate --verbose
```

## 📚 Documentation

### Additional Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [GitHub Actions Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging Best Practices](https://packaging.python.org/guides/)

### API Reference

- **Deploy Script**: `scripts/deploy.py --help`
- **Agent Coordinator**: `scripts/agent-coordinator.py --help`
- **Build Validator**: `scripts/validate-build.py --help`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run the deployment system locally
5. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone https://github.com/user/quickhooks.git
cd quickhooks

# Install dependencies
uv sync --all-groups

# Run pre-commit hooks
pre-commit install

# Test deployment system
python scripts/deploy.py --env dev --dry-run
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [UV Team](https://github.com/astral-sh/uv) for the excellent package manager
- [PyPA](https://www.pypa.io/) for Python packaging standards
- [GitHub Actions](https://github.com/features/actions) for CI/CD infrastructure
- [Pydantic](https://pydantic.dev/) for data validation
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output