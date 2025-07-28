# QuickHooks Agent Analysis

An intelligent system that analyzes user prompts to determine the optimal AI agents for task completion, with automatic discovery of local agents and seamless Claude Code integration.

## Features

### 🧠 Intelligent Agent Analysis
- Uses Groq with Pydantic AI for sophisticated prompt analysis
- Analyzes prompts for keywords, intent, and complexity
- Provides confidence scores and priority rankings
- Supports multiple agent recommendations for complex tasks

### 🔍 Local Agent Discovery
- Automatically discovers agents in `~/.claude/agents` directory
- Uses Chroma vector database for semantic similarity matching
- Supports Python, Markdown, JSON, and text agent files
- Indexes agent capabilities and descriptions for fast retrieval

### 📏 Context Management
- Intelligent context chunking for large inputs (up to 128K tokens)
- 90% safety margin to prevent token limit issues
- Preserves important information using start/end chunking strategy
- Optimized token estimation for different content types

### 🔗 Claude Code Integration
- Automatic prompt modification for guaranteed agent usage
- Hook-based integration with Claude Code settings
- Environment-based configuration
- Verbose logging and debugging support

## Installation

### Basic Installation
```bash
pip install quickhooks[agent-analysis]
```

### Development Installation
```bash
git clone <repository>
cd quickhooks
pip install -e .[dev]
```

### Required Dependencies
- `groq>=0.13.0` - Groq API client
- `pydantic-ai-slim[groq]>=0.0.49` - Pydantic AI with Groq support
- `chromadb>=0.4.0` - Vector database for agent discovery
- `sentence-transformers>=2.2.0` - Text embeddings

## Configuration

### Environment Variables
```bash
export GROQ_API_KEY=your_groq_api_key_here
export QUICKHOOKS_AGENT_MODEL=qwen/qwen3-32b
export QUICKHOOKS_CONFIDENCE_THRESHOLD=0.7
export QUICKHOOKS_MIN_SIMILARITY=0.3
export QUICKHOOKS_VERBOSE=false
```

### Supported Models
- `qwen/qwen3-32b` (recommended)
- `llama-3.3-70b-versatile`
- `mixtral-8x7b-32768`
- `gemma2-9b-it`

## Usage

### Command Line Interface

#### Basic Analysis
```bash
quickhooks agents analyze "Write a Python function that sorts a list"
```

#### With Context File
```bash
quickhooks agents analyze "Review this code for security issues" --context code.py
```

#### Custom Configuration
```bash
quickhooks agents analyze "Debug this error" \
    --model qwen/qwen3-32b \
    --threshold 0.8 \
    --max-tokens 100000 \
    --format rich
```

#### Output Formats
- `rich` - Rich formatted output with tables and panels (default)
- `json` - JSON output for programmatic use
- `simple` - Plain text output

### Python API

#### Basic Usage
```python
from quickhooks.agent_analysis import AgentAnalyzer, AgentAnalysisRequest

# Initialize analyzer
analyzer = AgentAnalyzer(model_name="qwen/qwen3-32b")

# Create request
request = AgentAnalysisRequest(
    prompt="Write a Python function that calculates factorial",
    confidence_threshold=0.7
)

# Analyze prompt
result = analyzer.analyze_prompt_sync(request)

# Access results
print(f"Top recommendation: {result.top_recommendation.agent_type}")
print(f"Discovered agents: {len(result.discovered_agents)}")
print(f"Modified prompt: {result.claude_code_prompt_modification}")
```

#### Async Usage
```python
import asyncio

async def analyze():
    result = await analyzer.analyze_prompt(request)
    return result

result = asyncio.run(analyze())
```

#### With Context
```python
request = AgentAnalysisRequest(
    prompt="Review this authentication system",
    context=open("auth.py").read(),
    max_context_tokens=50000
)
```

### Agent Discovery

#### Manual Agent Discovery
```python
from quickhooks.agent_analysis import AgentDiscovery

# Initialize discovery
discovery = AgentDiscovery()

# Scan and index agents
count = discovery.scan_and_index_agents(force_reindex=True)
print(f"Indexed {count} agents")

# Find relevant agents
agents = discovery.find_relevant_agents(
    prompt="Help with Python coding",
    limit=5,
    min_similarity=0.3
)

for agent in agents:
    print(f"{agent.name}: {agent.description} (similarity: {agent.similarity_score:.2f})")
```

## Agent File Formats

### Python Agent
```python
"""
A coding assistant that helps with Python development tasks.
Capabilities: coding, testing, debugging
Usage: Use for Python programming tasks
"""

class CodingAgent:
    def help_with_coding(self):
        pass
```

### Markdown Agent
```markdown
# Documentation Writer

A specialized agent for writing technical documentation.

## Capabilities
- documentation
- writing  
- explaining

## Usage
Use this agent when you need to create or improve documentation.
```

### JSON Agent
```json
{
    "description": "Analyzes data and provides insights",
    "capabilities": ["analysis", "data", "research"],
    "usage": "Use for data analysis and research tasks"
}
```

## Claude Code Integration

### Automatic Setup
```bash
python scripts/setup_claude_code_integration.py
```

### Manual Setup

1. **Copy the hook script:**
```bash
cp hooks/agent_analysis_hook.py ~/.quickhooks/hooks/
```

2. **Add to Claude Code settings.json:**
```json
{
  "hooks": {
    "user-prompt-submit": {
      "script": "~/.quickhooks/hooks/agent_analysis_hook.py",
      "function": "on_user_prompt_submit",
      "enabled": true
    }
  }
}
```

3. **Set environment variables:**
```bash
export GROQ_API_KEY=your_api_key
export QUICKHOOKS_AGENT_ANALYSIS_ENABLED=true
```

### Hook Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKHOOKS_AGENT_ANALYSIS_ENABLED` | `true` | Enable/disable hook |
| `QUICKHOOKS_AGENT_MODEL` | `qwen/qwen3-32b` | Groq model to use |
| `QUICKHOOKS_CONFIDENCE_THRESHOLD` | `0.7` | Minimum confidence |
| `QUICKHOOKS_MIN_SIMILARITY` | `0.3` | Minimum similarity |
| `QUICKHOOKS_VERBOSE` | `false` | Verbose logging |

## Examples

### Example 1: Coding Task
**Input:** "Write a Python function that calculates the Fibonacci sequence"

**Output:**
```
┌─ Analysis Summary ─┐
│ This prompt is requesting code generation, specifically a Python function │
│ for calculating Fibonacci numbers. The coding agent is highly recommended. │
└────────────────────┘

┌─ Agent Recommendations ─┐
│ Agent    │ Confidence │ Priority │ Threshold Met │ Reasoning          │
│ coding   │ 0.95       │ 1        │ ✅            │ Clear coding task  │
│ testing  │ 0.75       │ 2        │ ✅            │ May need tests     │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Discovered Local Agents ─┐
│ Name         │ Similarity │ Capabilities      │ Description        │
│ python_expert│ 0.87       │ coding, python    │ Python specialist  │
│ math_helper  │ 0.72       │ algorithms, math  │ Mathematical tasks │
└─────────────────────────────────────────────────────────────────────────┘

┌─ Modified Prompt for Claude Code ─┐
│ Use the 'python_expert' agent to write a Python function that calculates │
│ the Fibonacci sequence. The agent is specifically designed for Python    │
│ development tasks including algorithms and mathematical functions.        │
└──────────────────────────────────────────────────────────────────────────┘
```

### Example 2: Debugging Task
**Input:** "Help me debug this authentication error: 'NoneType' object has no attribute 'split'"

**Output:**
```
┌─ Top Recommendation ─┐
│ DEBUGGING (Confidence: 0.92)                                             │
│ This is clearly a debugging task with a specific error message that      │
│ needs investigation and resolution.                                       │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Discovered Local Agents ─┐
│ Name         │ Similarity │ Capabilities           │ Description         │
│ debug_helper │ 0.91       │ debugging, errors      │ Error resolution    │
│ auth_expert  │ 0.84       │ authentication, security│ Auth specialist     │
└──────────────────────────────────────────────────────────────────────────┘
```

## Testing

### Run All Tests
```bash
pytest tests/test_agent_analysis.py -v
```

### Run Specific Test Categories
```bash
# Context management tests
pytest tests/test_agent_analysis.py::TestContextManager -v

# Agent discovery tests  
pytest tests/test_agent_analysis.py::TestAgentDiscovery -v

# Integration tests (requires GROQ_API_KEY)
pytest tests/test_agent_analysis.py::TestAgentAnalysisIntegration -v
```

### Test Coverage
```bash
pytest tests/test_agent_analysis.py --cov=quickhooks.agent_analysis --cov-report=html
```

## Troubleshooting

### Common Issues

#### "GROQ_API_KEY not set"
```bash
export GROQ_API_KEY=your_groq_api_key_here
```

#### "QuickHooks not found"
```bash
pip install quickhooks[agent-analysis]
```

#### "No agents discovered"
- Ensure `~/.claude/agents` directory exists
- Add agent files in supported formats
- Check file permissions and content

#### "Hook not triggering"
- Verify hook is registered in Claude Code settings
- Check `QUICKHOOKS_AGENT_ANALYSIS_ENABLED=true`
- Enable verbose logging: `QUICKHOOKS_VERBOSE=true`

#### "ChromaDB errors"
- Clear database: `rm -rf ~/.quickhooks/agent_db`
- Reinstall ChromaDB: `pip install --upgrade chromadb`

### Debug Mode
```bash
export QUICKHOOKS_VERBOSE=true
quickhooks agents analyze "your prompt"
```

### Log Files
- Agent analysis logs: `~/.quickhooks/logs/agent_analysis.log`
- ChromaDB logs: `~/.quickhooks/agent_db/chroma.log`

## Performance

### Token Usage
- Typical analysis: 500-2000 tokens
- With large context: 5000-15000 tokens
- Cost estimate: $0.001-0.01 per analysis

### Speed
- Cold start: 2-5 seconds (model loading)
- Warm analysis: 0.5-2 seconds
- Agent discovery: 0.1-0.5 seconds (cached)

### Optimization Tips
- Use smaller models for faster responses
- Enable caching: `QUICKHOOKS_CACHE_ENABLED=true`
- Limit context size for faster processing
- Pre-index agents during setup

## API Reference

### Classes

#### `AgentAnalyzer`
Main class for prompt analysis and agent recommendations.

**Methods:**
- `__init__(groq_api_key, model_name, enable_agent_discovery)`
- `analyze_prompt(request) -> AgentAnalysisResponse`
- `analyze_prompt_sync(request) -> AgentAnalysisResponse`

#### `AgentDiscovery`
Handles discovery and indexing of local agents.

**Methods:**
- `__init__(agents_dir, db_path)`
- `scan_and_index_agents(force_reindex) -> int`
- `find_relevant_agents(prompt, context, limit, min_similarity) -> List[DiscoveredAgent]`

#### `ContextManager`
Manages context chunking and token estimation.

**Methods:**
- `__init__(max_tokens, safety_margin)`
- `chunk_context(context, prompt) -> List[ContextChunk]`
- `estimate_tokens(text) -> int`

### Types

#### `AgentAnalysisRequest`
- `prompt: str` - User prompt to analyze
- `context: Optional[str]` - Additional context
- `max_context_tokens: int` - Maximum context length
- `confidence_threshold: float` - Minimum confidence for recommendations

#### `AgentAnalysisResponse`
- `recommendations: List[AgentRecommendation]` - Agent recommendations
- `discovered_agents: List[DiscoveredAgentInfo]` - Local agents found
- `claude_code_prompt_modification: Optional[str]` - Modified prompt
- `analysis_summary: str` - Analysis summary
- `total_tokens_used: int` - Token usage

## Contributing

### Development Setup
```bash
git clone <repository>
cd quickhooks
pip install -e .[dev]
pre-commit install
```

### Adding New Agent Types
1. Add capability to `AgentCapability` enum
2. Update system prompt in `AgentAnalyzer`
3. Add tests for new capability
4. Update documentation

### Adding New File Formats
1. Implement parser in `AgentDiscovery._parse_*_agent`
2. Add file pattern to `_discover_agents`
3. Add tests for new format
4. Update documentation

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues: <repository>/issues
- Documentation: <repository>/docs
- Examples: <repository>/examples