# Intelligent Tool Selector System

## Overview

The Intelligent Tool Selector is an advanced QuickHook that automatically analyzes your codebase and selects the best development tools (linters, formatters, test runners, build tools, and type checkers) based on:

- Project structure analysis using the `st` (Smart Tree) tool
- AI-powered recommendations via Groq LLM
- Intelligent caching of decisions
- Automatic tool discovery and scoring

## Features

### 🧠 Intelligent Analysis
- **Codebase Analysis**: Uses `st` tool to analyze project structure, languages, and configurations
- **Dependency Detection**: Analyzes package files (package.json, requirements.txt, go.mod, etc.)
- **Framework Detection**: Identifies frameworks like Django, React, Express, etc.
- **Build System Detection**: Recognizes Make, CMake, Maven, Gradle, etc.

### 🤖 AI-Powered Selection
- **Groq LLM Integration**: Uses AI to make optimal tool selections
- **Context-Aware**: Considers project type, existing configs, and best practices
- **Confidence Scoring**: Provides confidence levels for each decision

### 💾 Smart Caching
- **SQLite Cache**: Stores tool decisions for fast repeated access
- **Project Hashing**: Creates unique fingerprints of project structure
- **Time-Based Expiry**: Cached decisions expire after 30 days
- **Statistics Tracking**: Monitors popular tools and usage patterns

### 🔧 Comprehensive Tool Database
Supports tools for:
- **Python**: ruff, black, pytest, mypy, poetry, etc.
- **JavaScript/TypeScript**: eslint, prettier, jest, webpack, etc.
- **Go**: golangci-lint, gofmt, go test, etc.
- **Rust**: clippy, rustfmt, cargo, etc.
- **Ruby**: rubocop, rspec, bundler, etc.
- **Java**: checkstyle, maven, gradle, etc.
- **C/C++**: clang-format, make, cmake, etc.

## Installation

1. **Install Smart Tree (st)**:
   ```bash
   cargo install smart-tree
   ```

2. **Set up Groq API** (optional but recommended):
   ```bash
   export GROQ_API_KEY=your_groq_api_key_here
   ```
   Get a free API key at: https://console.groq.com/keys

3. **Install the hook**:
   ```bash
   cp hooks/intelligent_tool_dispatcher.py ~/.quickhooks/hooks/
   ```

## Usage

The hook automatically intercepts commands like:

```bash
# Linting - automatically selects best linter
lint
check
analyze

# Formatting - automatically selects best formatter
format
fmt

# Testing - automatically selects best test runner
test
run tests

# Building - automatically selects best build tool
build
compile

# Type checking - automatically selects best type checker
typecheck
type check
```

## How It Works

1. **Command Interception**: Detects development tool commands
2. **Project Analysis**: 
   - Runs `st` tool for structure analysis
   - Detects languages, frameworks, and configurations
   - Creates project fingerprint
3. **Cache Check**: Looks for recent decisions in SQLite cache
4. **Tool Discovery**:
   - Finds available tools for detected language
   - Checks tool availability on system
   - Scores tools based on project fit
5. **AI Consultation** (if available):
   - Sends project context to Groq LLM
   - Gets optimal tool recommendation
6. **Execution**: Runs selected tool with appropriate arguments
7. **Caching**: Stores decision for future use

## Architecture

```
┌─────────────────────┐
│   User Command      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  QuickHooks Engine  │
└──────────┬──────────┘
           │
┌──────────▼──────────────┐
│ Intelligent Dispatcher  │
├─────────────────────────┤
│ • Command Detection     │
│ • Category Mapping      │
└──────────┬──────────────┘
           │
┌──────────▼──────────────┐
│  Codebase Analyzer     │
├─────────────────────────┤
│ • st tool integration  │
│ • Dependency parsing   │
│ • Framework detection  │
└──────────┬──────────────┘
           │
┌──────────▼──────────────┐
│   Cache Manager        │
├─────────────────────────┤
│ • SQLite storage       │
│ • Decision history     │
│ • Statistics           │
└──────────┬──────────────┘
           │
┌──────────▼──────────────┐
│  Tool Discovery Engine │
├─────────────────────────┤
│ • Tool database        │
│ • Availability check   │
│ • Scoring algorithm    │
└──────────┬──────────────┘
           │
┌──────────▼──────────────┐
│    AI Recommender      │
├─────────────────────────┤
│ • Groq LLM integration │
│ • Context analysis     │
│ • Best practice rules  │
└──────────┬──────────────┘
           │
┌──────────▼──────────────┐
│    Tool Execution      │
└─────────────────────────┘
```

## Cache Database Schema

### `tool_decisions` table:
- `project_hash`: Unique project identifier
- `language`: Primary programming language
- `category`: Tool category (linter, formatter, etc.)
- `selected_tool`: Chosen tool name
- `command`: Full command to execute
- `confidence`: Decision confidence (0.0-1.0)
- `reasons`: JSON array of selection reasons
- `detected_configs`: JSON array of found config files
- `timestamp`: Decision timestamp

### `project_analyses` table:
- `structure_hash`: Project structure fingerprint
- `primary_language`: Main language
- `languages`: All detected languages
- `config_files`: Configuration files found
- `dependencies`: Package dependencies
- `project_type`: web, cli, library, etc.
- `framework`: Detected framework
- `test_framework`: Test framework
- `build_system`: Build system

## Examples

### Python Project
```bash
$ lint
🔍 Analyzing project structure...
✅ Selected linter: ruff (confidence: 85%)
   - Found config: pyproject.toml
   - AI recommendation
   - Score: 0.80
🚀 Running: ruff check .
```

### JavaScript Project
```bash
$ format
🔍 Analyzing project structure...
📦 Using cached project analysis
✅ Selected formatter: prettier (confidence: 90%)
   - Found config: .prettierrc
   - Framework compatible: react
🚀 Running: npx prettier --write .
```

### Go Project
```bash
$ test
🔍 Analyzing project structure...
🤖 Consulting AI for optimal tool selection...
✅ Selected test_runner: go-test (confidence: 95%)
   - Highest score: 0.95
   - Built-in tool
🚀 Running: go test ./...
```

## Configuration

The system works out-of-the-box but can be customized:

### Environment Variables
- `GROQ_API_KEY`: Enable AI recommendations
- `QUICKHOOKS_CACHE_DIR`: Custom cache location
- `ST_TIMEOUT`: Timeout for st analysis (default: 10s)

### Tool Preferences
Edit the `TOOL_DATABASE` in the hook to add custom tools or modify existing ones.

## Troubleshooting

### "Smart Tree (st) tool not found"
Install st: `cargo install smart-tree`

### "AI analysis failed"
- Check your GROQ_API_KEY
- System falls back to scoring algorithm

### "No suitable tool found"
- Ensure tools are installed or available via npx
- Check language detection worked correctly

### Cache Issues
Clear cache: `rm ~/.quickhooks/cache/tool_decisions.db`

## Performance

- First run: ~2-5 seconds (full analysis)
- Cached runs: <100ms
- AI consultation: +1-2 seconds
- Cache expires: 30 days for decisions, 7 days for analyses

## Future Improvements

- Support for more languages and tools
- Custom tool installation prompts
- Project-specific tool preferences
- Integration with CI/CD systems
- Tool version management
- Performance profiling integration