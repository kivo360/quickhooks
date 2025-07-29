.PHONY: install dev test lint typecheck clean format check setup sync build publish security audit full ci

# Variables
PYTHON_VERSION = 3.12
PACKAGE_NAME = quickhooks
SRC_DIR = src
TESTS_DIR = tests
BUILD_SCRIPT = scripts/build.sh

# UV Commands
UV = uv
UV_RUN = uv run
UV_SYNC = uv sync --all-extras --dev
UV_BUILD = uv build --no-sources
UV_PUBLISH = uv publish

# Default target
all: setup

# Setup development environment
setup:
	@echo "🔧 Setting up development environment..."
	$(UV) python install $(PYTHON_VERSION)
	$(UV_SYNC)
	@echo "✅ Environment ready!"

# Install/sync dependencies
install sync:
	@echo "📦 Syncing dependencies..."
	$(UV_SYNC)

# Run the development server
dev:
	@echo "🚀 Starting development server..."
	$(UV_RUN) python -m $(PACKAGE_NAME).dev run $(SRC_DIR)/ --delay 0.5

# Run tests with various options
test:
	@echo "🧪 Running tests..."
	$(UV_RUN) pytest $(TESTS_DIR)/ -v --cov=$(PACKAGE_NAME) --cov-report=term-missing

test-fast:
	@echo "⚡ Running fast tests..."
	$(UV_RUN) pytest $(TESTS_DIR)/ -x -v -m "not slow"

test-integration:
	@echo "🔗 Running integration tests..."
	$(UV_RUN) pytest $(TESTS_DIR)/ -v -m integration

test-coverage:
	@echo "📊 Running tests with detailed coverage..."
	$(UV_RUN) pytest $(TESTS_DIR)/ --cov=$(PACKAGE_NAME) --cov-report=html --cov-report=xml --cov-report=term-missing

test-parallel:
	@echo "⚡ Running tests in parallel..."
	$(UV_RUN) pytest $(TESTS_DIR)/ -n auto --cov=$(PACKAGE_NAME) --cov-report=term-missing

# Linting and formatting
lint:
	@echo "🔍 Running linter..."
	$(UV_RUN) ruff check $(SRC_DIR)/ $(TESTS_DIR)/

lint-fix:
	@echo "🔧 Fixing linting issues..."
	$(UV_RUN) ruff check --fix $(SRC_DIR)/ $(TESTS_DIR)/

format:
	@echo "🎨 Formatting code..."
	$(UV_RUN) ruff format $(SRC_DIR)/ $(TESTS_DIR)/

format-check:
	@echo "🎨 Checking code formatting..."
	$(UV_RUN) ruff format --check $(SRC_DIR)/ $(TESTS_DIR)/

# Type checking
typecheck:
	@echo "🔍 Running type checker..."
	$(UV_RUN) mypy $(SRC_DIR)/$(PACKAGE_NAME)

# Security and audit
security:
	@echo "🔒 Running security checks..."
	$(UV) add --dev safety bandit[toml] || true
	$(UV_RUN) safety check || true
	$(UV_RUN) bandit -r $(SRC_DIR)/ || true

audit:
	@echo "🕵️ Running dependency audit..."
	$(UV) pip check
	$(UV_RUN) pip-audit || echo "pip-audit not available"

# Building and publishing
build:
	@echo "📦 Building package..."
	rm -rf dist/ build/ *.egg-info/
	$(UV_BUILD)
	$(UV_RUN) twine check dist/*

build-check:
	@echo "✅ Checking build..."
	$(UV_RUN) twine check dist/*

publish-test:
	@echo "🚀 Publishing to Test PyPI..."
	$(UV_PUBLISH) --repository testpypi

publish:
	@echo "🚀 Publishing to PyPI..."
	$(UV_PUBLISH)

# Environment management
venv-create:
	@echo "🐍 Creating virtual environment..."
	$(UV) venv

venv-remove:
	@echo "🗑️ Removing virtual environment..."
	rm -rf .venv

# Lock file management
lock:
	@echo "🔒 Updating lock file..."
	$(UV) lock

lock-upgrade:
	@echo "⬆️ Upgrading dependencies..."
	$(UV) lock --upgrade

# Development utilities
watch:
	@echo "👀 Watching for changes..."
	$(UV_RUN) watchfiles --ignore-paths .git,__pycache__,.pytest_cache,.mypy_cache,.ruff_cache "make test-fast" $(SRC_DIR) $(TESTS_DIR)

docs-serve:
	@echo "📚 Serving documentation..."
	$(UV_RUN) mkdocs serve || echo "MkDocs not configured"

# Quality checks
check: lint typecheck test
	@echo "✅ All quality checks passed!"

check-fast: lint typecheck test-fast
	@echo "⚡ Fast quality checks passed!"

# Comprehensive workflows
full: setup lint typecheck test build
	@echo "🎉 Full build pipeline completed!"

ci: setup lint typecheck test security build
	@echo "🚀 CI pipeline completed!"

# Using build script
build-script-setup:
	@$(BUILD_SCRIPT) setup

build-script-full:
	@$(BUILD_SCRIPT) full

build-script-ci:
	@$(BUILD_SCRIPT) ci

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✨ Cleanup complete!"

clean-all: clean venv-remove
	@echo "🗑️ Deep clean completed!"

# Information
info:
	@echo "📋 Project Information:"
	@echo "  Package: $(PACKAGE_NAME)"
	@echo "  Python: $(PYTHON_VERSION)"
	@echo "  UV Version: $(shell $(UV) --version)"
	@echo "  Virtual Env: $(shell $(UV) python info)"

deps:
	@echo "📦 Dependencies:"
	@$(UV) pip list

deps-outdated:
	@echo "📦 Outdated dependencies:"
	@$(UV) pip list --outdated

# Show help
help:
	@echo "🛠️  QuickHooks Development Commands"
	@echo ""
	@echo "📋 Setup & Environment:"
	@echo "  setup          Set up development environment"
	@echo "  install, sync  Install/sync dependencies"
	@echo "  venv-create    Create virtual environment"
	@echo "  venv-remove    Remove virtual environment"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test           Run full test suite"
	@echo "  test-fast      Run fast tests only"
	@echo "  test-integration Run integration tests"
	@echo "  test-coverage  Run tests with detailed coverage"
	@echo "  test-parallel  Run tests in parallel"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint           Run linter"
	@echo "  lint-fix       Fix linting issues"
	@echo "  format         Format code"
	@echo "  format-check   Check code formatting"
	@echo "  typecheck      Run type checker"
	@echo ""
	@echo "🔒 Security:"
	@echo "  security       Run security checks"
	@echo "  audit          Audit dependencies"
	@echo ""
	@echo "📦 Building & Publishing:"
	@echo "  build          Build package"
	@echo "  build-check    Check built package"
	@echo "  publish-test   Publish to Test PyPI"
	@echo "  publish        Publish to PyPI"
	@echo ""
	@echo "🚀 Development:"
	@echo "  dev            Start development server"
	@echo "  watch          Watch files and run tests"
	@echo "  docs-serve     Serve documentation"
	@echo ""
	@echo "🔒 Lock Files:"
	@echo "  lock           Update lock file"
	@echo "  lock-upgrade   Upgrade dependencies"
	@echo ""
	@echo "✅ Workflows:"
	@echo "  check          Run lint + typecheck + test"
	@echo "  check-fast     Run fast quality checks"
	@echo "  full           Complete build pipeline"
	@echo "  ci             CI pipeline"
	@echo ""
	@echo "🛠️  Build Script (Alternative):"
	@echo "  build-script-setup  Use build script for setup"
	@echo "  build-script-full   Use build script for full pipeline"
	@echo "  build-script-ci     Use build script for CI"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean          Clean build artifacts"
	@echo "  clean-all      Deep clean including venv"
	@echo "  info           Show project information"
	@echo "  deps           List dependencies"
	@echo "  deps-outdated  Show outdated dependencies"

.DEFAULT_GOAL := help
