# QuickHooks Installation & Extras Plan

## Overview

As QuickHooks evolves into a comprehensive AI-powered hook management system with LanceDB, vector search, full-text search, and PyArrow ecosystem integration, we need a flexible installation system that allows users to pick and choose components while maintaining the option to install everything.

## Installation Groups & Extras

### Core Installation
```bash
pip install quickhooks
```
**Includes:**
- Basic hook framework (`quickhooks.hooks`)
- CLI interface (`quickhooks.cli`)
- Configuration system (`quickhooks.config`)
- Simple hook execution (`quickhooks.executor`, `quickhooks.runner`)
- Development server (`quickhooks.dev`)

### Extra Groups

#### 1. AI & Vector Search (`ai`)
```bash
pip install quickhooks[ai]
```
**Components:**
- LanceDB integration (`quickhooks.db`)
- Vector embeddings (sentence-transformers)
- Semantic search capabilities
- Hook recommendations
- AI-powered analysis

**Dependencies:**
- `lancedb>=0.8.0`
- `sentence-transformers>=2.2.0`
- `torch>=2.0.0`
- `transformers>=4.30.0`

#### 2. Full-Text Search (`search`)
```bash
pip install quickhooks[search]
```
**Components:**
- Full-text search integration
- Tantivy-based indexing
- Hybrid search (vector + FTS)
- Advanced filtering

**Dependencies:**
- `tantivy>=0.21.0`
- `lancedb[fts]>=0.8.0`

#### 3. Data Analytics (`analytics`)
```bash
pip install quickhooks[analytics]
```
**Components:**
- PyArrow integration
- Polars support
- DuckDB connectivity
- Advanced analytics dashboards
- Usage metrics and insights

**Dependencies:**
- `pyarrow>=12.0.0`
- `polars>=0.20.0`
- `duckdb>=0.9.0`
- `pandas>=2.0.0`
- `plotly>=5.15.0`

#### 4. Agent Analysis (`agents`)
```bash
pip install quickhooks[agents]
```
**Components:**
- Agent analysis system
- Multi-LLM support (OpenAI, Groq, Anthropic)
- Prompt optimization
- Agent recommendations

**Dependencies:**
- `openai>=1.0.0`
- `groq>=0.4.0`
- `anthropic>=0.18.0`
- `tiktoken>=0.5.0`

#### 5. Scaffolding & Templates (`scaffold`)
```bash
pip install quickhooks[scaffold]
```
**Components:**
- AI-powered scaffolding
- Advanced Jinja2 templates
- Project generation
- Code generation utilities

**Dependencies:**
- `jinja2>=3.1.0`
- `cookiecutter>=2.1.0`
- `black>=23.0.0`
- `isort>=5.12.0`

#### 6. Web Integration (`web`)
```bash
pip install quickhooks[web]
```
**Components:**
- Web dashboard
- REST API
- Real-time updates
- Hook marketplace integration

**Dependencies:**
- `fastapi>=0.100.0`
- `uvicorn>=0.23.0`
- `streamlit>=1.25.0`
- `websockets>=11.0.0`

#### 7. Cloud & Distributed (`cloud`)
```bash
pip install quickhooks[cloud]
```
**Components:**
- Cloud storage integration
- Distributed execution
- Remote hook repositories
- Multi-tenant support

**Dependencies:**
- `boto3>=1.28.0`
- `azure-storage-blob>=12.17.0`
- `google-cloud-storage>=2.10.0`
- `redis>=4.6.0`
- `celery>=5.3.0`

#### 8. Enterprise Features (`enterprise`)
```bash
pip install quickhooks[enterprise]
```
**Components:**
- Advanced security features
- RBAC (Role-Based Access Control)
- Audit logging
- Enterprise SSO integration
- Advanced monitoring

**Dependencies:**
- `cryptography>=41.0.0`
- `pyjwt>=2.8.0`
- `ldap3>=2.9.0`
- `prometheus-client>=0.17.0`

#### 9. Development Tools (`dev`)
```bash
pip install quickhooks[dev]
```
**Components:**
- Enhanced development server
- Hot reload with advanced features
- Debugging tools
- Performance profiling
- Code quality tools

**Dependencies:**
- `watchfiles>=0.19.0`
- `rich>=13.4.0`
- `pytest>=7.4.0`
- `coverage>=7.2.0`
- `pre-commit>=3.3.0`

#### 10. Performance (`performance`)
```bash
pip install quickhooks[performance]
```
**Components:**
- Async execution optimization
- Caching layers
- Memory optimization
- Parallel processing
- Performance monitoring

**Dependencies:**
- `redis>=4.6.0`
- `memcached>=1.59`
- `aiocache>=0.12.0`
- `psutil>=5.9.0`

### Combined Groups

#### Essential (`essential`)
```bash
pip install quickhooks[essential]
```
**Combines:** `ai` + `search` + `dev`
- Core AI functionality
- Full-text search
- Development tools

#### Professional (`pro`)
```bash
pip install quickhooks[pro]
```
**Combines:** `essential` + `analytics` + `scaffold` + `agents`
- All essential features
- Advanced analytics
- Scaffolding system
- Agent analysis

#### Enterprise (`enterprise-full`)
```bash
pip install quickhooks[enterprise-full]
```
**Combines:** `pro` + `web` + `cloud` + `enterprise` + `performance`
- All professional features
- Web dashboard
- Cloud integration
- Enterprise security
- Performance optimization

#### Everything (`all`)
```bash
pip install quickhooks[all]
```
**Includes ALL extras**
- Every single feature and capability
- Maximum functionality
- All integrations and dependencies

## PyArrow Ecosystem Integration

### Core Integration Strategy

#### 1. Unified Data Layer
```python
# quickhooks/data/unified.py
class UnifiedDataLayer:
    """Unified access to PyArrow ecosystem."""
    
    def __init__(self):
        self.arrow_tables = {}
        self.polars_lazy_frames = {}
        self.duckdb_connections = {}
    
    def to_polars(self, data):
        """Convert any data to Polars LazyFrame."""
        pass
    
    def to_duckdb(self, data):
        """Query data with DuckDB."""
        pass
    
    def to_arrow(self, data):
        """Convert to Arrow format."""
        pass
```

#### 2. Analytics Integrations
```python
# With Polars (analytics extra)
df = hooks_db.to_polars()
analysis = (
    df.lazy()
    .group_by("hook_type")
    .agg([
        pl.count().alias("count"),
        pl.col("usage_count").mean().alias("avg_usage")
    ])
    .collect()
)

# With DuckDB (analytics extra)
conn = hooks_db.to_duckdb()
result = conn.execute("""
    SELECT hook_type, 
           COUNT(*) as count,
           AVG(usage_count) as avg_usage
    FROM hooks 
    GROUP BY hook_type
""").fetchall()
```

#### 3. Full-Text Search Integration
```python
# Hybrid search combining vector + FTS
results = hooks_db.search(
    query="authentication security",
    query_type="hybrid",  # vector + fts
    limit=10
).with_columns([
    pl.col("description").alias("matched_text"),
    pl.col("_distance").alias("similarity_score"),
    pl.col("_fts_score").alias("text_relevance")
])
```

## Installation Architecture

### pyproject.toml Structure
```toml
[project]
name = "quickhooks"
dependencies = [
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.4.0",
    "jinja2>=3.1.0",
    "watchfiles>=0.19.0",
]

[project.optional-dependencies]
# Individual extras
ai = [
    "lancedb>=0.8.0",
    "sentence-transformers>=2.2.0",
    "torch>=2.0.0",
    "transformers>=4.30.0",
]

search = [
    "tantivy>=0.21.0",
    "lancedb[fts]>=0.8.0",
]

analytics = [
    "pyarrow>=12.0.0",
    "polars>=0.20.0",
    "duckdb>=0.9.0",
    "pandas>=2.0.0",
    "plotly>=5.15.0",
]

agents = [
    "openai>=1.0.0",
    "groq>=0.4.0",
    "anthropic>=0.18.0",
    "tiktoken>=0.5.0",
]

scaffold = [
    "cookiecutter>=2.1.0",
    "black>=23.0.0",
    "isort>=5.12.0",
]

web = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "streamlit>=1.25.0",
    "websockets>=11.0.0",
]

cloud = [
    "boto3>=1.28.0",
    "azure-storage-blob>=12.17.0",
    "google-cloud-storage>=2.10.0",
    "redis>=4.6.0",
    "celery>=5.3.0",
]

enterprise = [
    "cryptography>=41.0.0",
    "pyjwt>=2.8.0",
    "ldap3>=2.9.0",
    "prometheus-client>=0.17.0",
]

dev = [
    "pytest>=7.4.0",
    "coverage>=7.2.0",
    "pre-commit>=3.3.0",
    "mypy>=1.4.0",
]

performance = [
    "redis>=4.6.0",
    "aiocache>=0.12.0",
    "psutil>=5.9.0",
]

# Combined groups
essential = [
    "quickhooks[ai]",
    "quickhooks[search]", 
    "quickhooks[dev]",
]

pro = [
    "quickhooks[essential]",
    "quickhooks[analytics]",
    "quickhooks[scaffold]",
    "quickhooks[agents]",
]

enterprise-full = [
    "quickhooks[pro]",
    "quickhooks[web]",
    "quickhooks[cloud]",
    "quickhooks[enterprise]",
    "quickhooks[performance]",
]

all = [
    "quickhooks[ai]",
    "quickhooks[search]",
    "quickhooks[analytics]",
    "quickhooks[agents]",
    "quickhooks[scaffold]",
    "quickhooks[web]",
    "quickhooks[cloud]",
    "quickhooks[enterprise]",
    "quickhooks[dev]",
    "quickhooks[performance]",
]
```

## Conditional Imports System

### Dynamic Feature Loading
```python
# quickhooks/features.py
class FeatureRegistry:
    """Manages optional feature loading."""
    
    def __init__(self):
        self.features = {}
        self._scan_features()
    
    def _scan_features(self):
        """Scan for available features based on installed packages."""
        
        # AI Features
        try:
            import lancedb
            import sentence_transformers
            self.features['ai'] = True
        except ImportError:
            self.features['ai'] = False
        
        # Analytics Features
        try:
            import polars
            import duckdb
            self.features['analytics'] = True
        except ImportError:
            self.features['analytics'] = False
        
        # Search Features
        try:
            import tantivy
            self.features['search'] = True
        except ImportError:
            self.features['search'] = False
    
    def require(self, feature: str):
        """Require a feature or raise helpful error."""
        if not self.features.get(feature, False):
            raise ImportError(
                f"Feature '{feature}' is not available. "
                f"Install with: pip install quickhooks[{feature}]"
            )
    
    def has(self, feature: str) -> bool:
        """Check if feature is available."""
        return self.features.get(feature, False)

# Global registry
features = FeatureRegistry()
```

### Smart Import Pattern
```python
# quickhooks/db/__init__.py
from quickhooks.features import features

if features.has('ai'):
    from .manager import GlobalHooksDB
    from .indexer import HookIndexer
    __all__ = ['GlobalHooksDB', 'HookIndexer']
else:
    def GlobalHooksDB(*args, **kwargs):
        features.require('ai')
    
    def HookIndexer(*args, **kwargs):
        features.require('ai')
    
    __all__ = ['GlobalHooksDB', 'HookIndexer']
```

## CLI Integration
```python
# quickhooks/cli/main.py
from quickhooks.features import features

# Core commands always available
app.add_typer(create_app, name="create")
app.add_typer(global_app, name="global")

# Conditional commands
if features.has('ai'):
    from quickhooks.cli.ai import ai_app
    app.add_typer(ai_app, name="ai")

if features.has('analytics'):
    from quickhooks.cli.analytics import analytics_app
    app.add_typer(analytics_app, name="analytics")

if features.has('web'):
    from quickhooks.cli.web import web_app
    app.add_typer(web_app, name="web")

@app.command()
def features_info():
    """Show available features."""
    console.print("Available Features:", style="bold")
    for feature, available in features.features.items():
        status = "✅" if available else "❌"
        console.print(f"{status} {feature}")
```

## Benefits of This Architecture

### 1. **Modularity**
- Users install only what they need
- Reduced dependency conflicts
- Faster installation for basic use cases

### 2. **Scalability**
- Easy to add new feature groups
- Clear separation of concerns
- Maintainable codebase

### 3. **PyArrow Ecosystem Integration**
- Seamless data interchange
- Maximum performance with columnar data
- Access to entire data science ecosystem

### 4. **Developer Experience**
- Clear installation paths
- Helpful error messages for missing features
- Feature discovery through CLI

### 5. **Enterprise Ready**
- Professional and enterprise tiers
- Security and compliance features
- Performance optimization options

## Migration Strategy

### Phase 1: Core Refactoring
1. Implement feature registry system
2. Refactor imports to be conditional
3. Update CLI for conditional commands

### Phase 2: Extra Groups Implementation
1. Implement `ai` and `search` extras
2. Add `analytics` integration
3. Create combined groups (`essential`, `pro`)

### Phase 3: Advanced Features
1. Implement `web` and `cloud` extras
2. Add `enterprise` security features
3. Complete `all` group integration

### Phase 4: Ecosystem Integration
1. Deep PyArrow ecosystem integration
2. Advanced analytics dashboard
3. Performance optimization features

This plan ensures QuickHooks can scale from a simple hook framework to a comprehensive AI-powered development platform while maintaining flexibility and user choice.