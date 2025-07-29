#!/bin/bash

# QuickHooks Build Automation Script
# This script provides comprehensive build automation using UV

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.12"
PROJECT_NAME="quickhooks"
SRC_DIR="src"
TESTS_DIR="tests"
DOCS_DIR="docs"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        log_error "UV is not installed. Please install UV first:"
        echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    log_success "UV is available"
}

setup_environment() {
    log_info "Setting up Python environment..."
    
    # Ensure correct Python version
    uv python install ${PYTHON_VERSION}
    
    # Sync dependencies
    log_info "Installing dependencies..."
    uv sync --all-extras --dev
    
    log_success "Environment setup complete"
}

run_linting() {
    log_info "Running linting checks..."
    
    # Ruff linting
    log_info "Running ruff linting..."
    if uv run ruff check ${SRC_DIR}/ ${TESTS_DIR}/; then
        log_success "Linting passed"
    else
        log_error "Linting failed"
        return 1
    fi
    
    # Ruff formatting check
    log_info "Checking code formatting..."
    if uv run ruff format --check ${SRC_DIR}/ ${TESTS_DIR}/; then
        log_success "Formatting check passed"
    else
        log_warning "Code formatting issues found. Run 'make format' to fix."
        return 1
    fi
}

run_typecheck() {
    log_info "Running type checking..."
    
    if uv run mypy ${SRC_DIR}/${PROJECT_NAME}; then
        log_success "Type checking passed"
    else
        log_error "Type checking failed"
        return 1
    fi
}

run_tests() {
    log_info "Running test suite..."
    
    local test_args=""
    
    # Add coverage reporting
    test_args="--cov=${PROJECT_NAME} --cov-report=term-missing --cov-report=xml --cov-report=html"
    
    # Run tests with optional parallelization
    if uv run pytest ${TESTS_DIR}/ -v ${test_args} "$@"; then
        log_success "All tests passed"
    else
        log_error "Tests failed"
        return 1
    fi
    
    # Check coverage
    log_info "Checking test coverage..."
    local coverage_threshold=80
    local coverage_result=$(uv run coverage report --show-missing | grep "TOTAL" | awk '{print $4}' | sed 's/%//')
    
    if [[ ${coverage_result%.*} -ge ${coverage_threshold} ]]; then
        log_success "Coverage threshold met: ${coverage_result}%"
    else
        log_warning "Coverage below threshold: ${coverage_result}% < ${coverage_threshold}%"
    fi
}

run_security_checks() {
    log_info "Running security checks..."
    
    # Install security tools if not available
    uv add --dev safety bandit[toml] 2>/dev/null || true
    
    # Safety check for known vulnerabilities
    log_info "Checking for known vulnerabilities..."
    if uv run safety check --json > safety_report.json 2>/dev/null; then
        log_success "No known vulnerabilities found"
        rm -f safety_report.json
    else
        log_warning "Security vulnerabilities found. Check safety_report.json"
    fi
    
    # Bandit security linter
    log_info "Running bandit security analysis..."
    if uv run bandit -r ${SRC_DIR}/ -f json -o bandit_report.json 2>/dev/null; then
        log_success "Bandit security check passed"
        rm -f bandit_report.json
    else
        log_warning "Bandit found potential security issues. Check bandit_report.json"
    fi
}

run_build() {
    log_info "Building package..."
    
    # Clean previous builds
    rm -rf dist/ build/ *.egg-info/
    
    # Build with UV
    if uv build --no-sources; then
        log_success "Package built successfully"
    else
        log_error "Package build failed"
        return 1
    fi
    
    # Verify build
    log_info "Verifying package integrity..."
    if uv run twine check dist/*; then
        log_success "Package verification passed"
    else
        log_error "Package verification failed"
        return 1
    fi
    
    # Display build info
    log_info "Build artifacts:"
    ls -la dist/
}

test_installation() {
    log_info "Testing package installation..."
    
    # Create temporary environment
    local temp_env="temp_test_env"
    uv venv ${temp_env}
    
    # Activate and test installation
    source ${temp_env}/bin/activate
    
    if uv pip install dist/*.whl; then
        log_info "Testing installed package..."
        if quickhooks --help > /dev/null; then
            log_success "Package installation test passed"
        else
            log_error "Package installation test failed - CLI not working"
            deactivate
            rm -rf ${temp_env}
            return 1
        fi
    else
        log_error "Package installation failed"
        deactivate
        rm -rf ${temp_env}
        return 1
    fi
    
    deactivate
    rm -rf ${temp_env}
}

clean_build() {
    log_info "Cleaning build artifacts..."
    
    # Remove build artifacts
    rm -rf dist/ build/ *.egg-info/
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    rm -rf htmlcov/ .coverage coverage.xml
    rm -f safety_report.json bandit_report.json
    
    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "Cleanup complete"
}

show_help() {
    cat << EOF
QuickHooks Build Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup       Set up development environment
    lint        Run linting checks
    typecheck   Run type checking
    test        Run test suite
    security    Run security checks
    build       Build package
    install-test Test package installation
    clean       Clean build artifacts
    full        Run full build pipeline (lint + typecheck + test + build)
    ci          Run CI pipeline (full + security + install-test)
    help        Show this help message

Options:
    -q, --quiet    Suppress verbose output
    -v, --verbose  Enable verbose output
    
Examples:
    $0 setup                # Set up development environment
    $0 test --parallel      # Run tests in parallel
    $0 full                 # Run complete build pipeline
    $0 ci                   # Run full CI pipeline
    
EOF
}

# Main execution
main() {
    local command="${1:-help}"
    shift || true
    
    case "${command}" in
        setup)
            check_uv
            setup_environment
            ;;
        lint)
            check_uv
            run_linting
            ;;
        typecheck)
            check_uv
            run_typecheck
            ;;
        test)
            check_uv
            run_tests "$@"
            ;;
        security)
            check_uv
            run_security_checks
            ;;
        build)
            check_uv
            run_build
            ;;
        install-test)
            check_uv
            test_installation
            ;;
        clean)
            clean_build
            ;;
        full)
            check_uv
            setup_environment
            run_linting
            run_typecheck
            run_tests "$@"
            run_build
            log_success "Full build pipeline completed successfully!"
            ;;
        ci)
            check_uv
            setup_environment
            run_linting
            run_typecheck
            run_tests "$@"
            run_security_checks
            run_build
            test_installation
            log_success "CI pipeline completed successfully!"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: ${command}"
            show_help
            exit 1
            ;;
    esac
}

# Trap errors
trap 'log_error "Build script failed at line $LINENO"' ERR

# Execute main function
main "$@"