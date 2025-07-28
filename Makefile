.PHONY: install dev test lint typecheck clean format check

# Variables
PYTHON = python3
PIP = uv pip
PYTEST = uv run pytest
PYTHONPATH = $(shell pwd)/src

# Default target
all: install

# Install dependencies
install:
	@echo "Installing dependencies..."
	$(PIP) install -e ".[dev]"
	$(PIP) install -e .

# Run the development server
dev:
	@echo "Starting development server..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m quickhooks.dev run src/ --delay 0.5

# Run tests
test:
	@echo "Running tests..."
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/ -v --cov=quickhooks --cov-report=term-missing

# Run linter
lint:
	@echo "Running linter..."
	uv run ruff check src/ tests/

# Run type checker
typecheck:
	@echo "Running type checker..."
	uv run mypy src/quickhooks

# Format code
format:
	@echo "Formatting code..."
	uv run black src/ tests/
	uv run ruff --fix src/ tests/

# Check code quality
check: lint typecheck test

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache build/ dist/ *.egg-info/

# Show help
help:
	@echo "Available targets:"
	@echo "  install    Install dependencies"
	@echo "  dev       Run development server with hot-reload"
	@echo "  test      Run tests"
	@echo "  lint      Run linter"
	@echo "  typecheck Run type checker"
	@echo "  format    Format code"
	@echo "  check     Run all checks (lint, typecheck, test)"
	@echo "  clean     Clean up temporary files"
	@echo "  help      Show this help message"

.DEFAULT_GOAL := help
