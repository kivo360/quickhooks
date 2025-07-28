# QuickHooks

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

A streamlined TDD framework for Claude Code hooks with intelligent agent analysis and discovery. Built with Python 3.11+, featuring automatic agent detection from your `~/.claude/agents` directory and smart prompt modification for optimal AI collaboration.

## Features

### 🧠 Intelligent Agent Analysis
- **AI-powered prompt analysis** using Groq and Pydantic AI
- **Automatic agent discovery** from `~/.claude/agents` directory
- **Semantic similarity matching** with Chroma vector database
- **Smart prompt modification** for guaranteed agent usage
- **Context-aware chunking** for large inputs (up to 128K tokens)

### 🔧 Development Tools
- **Hot-reload development server** with `watchfiles`
- **Test-driven development** workflow
- **Fast** and **efficient** file watching
- **Modern Python** with type hints and async/await
- **Developer-friendly** CLI with rich output

### 🔗 Claude Code Integration
- **Seamless hook integration** with Claude Code settings
- **Automatic prompt interception** and modification
- **Environment-based configuration**
- **Verbose logging** and debugging support

## Installation

### Quick Start
```bash
pip install quickhooks[agent-analysis]
export GROQ_API_KEY=your_groq_api_key_here
quickhooks agents analyze "Write a Python function"
```

### Development Installation

1. Make sure you have Python 3.11 or later installed
2. Install [UV](https://github.com/astral-sh/uv) for fast dependency management:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Clone the repository:
   ```bash
   git clone https://github.com/kivo360/quickhooks.git
   cd quickhooks
   ```
4. Install dependencies:
   ```bash
   make install
   ```

### Claude Code Integration Setup
```bash
python scripts/setup_claude_code_integration.py
```

## Development Workflow

### Start the development server

```bash
make dev
```

This will start the development server with hot-reload enabled. The server will automatically restart when you make changes to your code.

### Run tests

```bash
make test
```

### Lint and format code

```bash
make lint    # Run linter
make format  # Format code
make check   # Run all checks (lint, typecheck, test)
```

## Project Structure

```
quickhooks/
├── src/
│   └── quickhooks/          # Main package
│       ├── __init__.py      # Package initialization
│       ├── cli/             # CLI commands
│       ├── agent_analysis/  # Agent analysis system
│       │   ├── analyzer.py  # Core analysis engine
│       │   ├── agent_discovery.py # Local agent discovery
│       │   ├── context_manager.py # Context chunking
│       │   ├── command.py   # CLI commands
│       │   └── types.py     # Type definitions
│       ├── dev.py           # Development server
│       └── ...
├── hooks/                   # Claude Code hooks
│   └── agent_analysis_hook.py # Main integration hook
├── examples/                # Example configurations
│   ├── claude_code_settings.json
│   └── agent_analysis_demo.py
├── scripts/                 # Setup and utility scripts
│   └── setup_claude_code_integration.py
├── tests/                   # Test files
├── .gitignore
├── Makefile                 # Development commands
├── pyproject.toml          # Project configuration
├── README.md
└── AGENT_ANALYSIS_README.md # Detailed agent analysis docs
```

## Development Server

The development server provides a smooth development experience with:

- Automatic reload on file changes
- Rich console output
- Clean error reporting
- Configurable watch paths and reload delay

### Usage

```bash
# Start the development server
python -m quickhooks.dev run src/

# With custom reload delay (in seconds)
python -m quickhooks.dev run src/ --delay 1.0
```

Or using the CLI:

```bash
quickhooks-dev run src/
```

## CLI Commands

### Agent Analysis
```bash
# Analyze a prompt for agent recommendations
quickhooks agents analyze "Write a Python function that sorts a list"

# With context file
quickhooks agents analyze "Review this code for security issues" --context code.py

# Custom configuration
quickhooks agents analyze "Debug this error" \
    --model qwen/qwen3-32b \
    --threshold 0.8 \
    --format rich
```

### Development Commands
```bash
# Show version
quickhooks version

# Say hello
quickhooks hello
quickhooks hello --name "Your Name"

# Development server
quickhooks-dev run src/
```

## Agent Analysis Documentation

For detailed documentation on the agent analysis system, see [AGENT_ANALYSIS_README.md](AGENT_ANALYSIS_README.md).

Key topics covered:
- **Complete API Reference** - All classes, methods, and types
- **Agent File Formats** - Python, Markdown, JSON examples  
- **Claude Code Integration** - Step-by-step setup guide
- **Troubleshooting** - Common issues and solutions
- **Performance Optimization** - Tips for faster analysis

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a pull request

### Development

```bash
# Run tests
make test

# Run agent analysis tests
pytest tests/test_agent_analysis.py -v

# Format code
make format

# Run all checks
make check
```

## License

MIT

---

<p align="center">
  Made with ❤️ for the Claude Code community
</p>