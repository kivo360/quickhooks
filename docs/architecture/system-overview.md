# QuickHooks System Architecture

## System Overview Diagram

```mermaid
graph TB
    subgraph "User Interface Layer"
        CLI[Claude Code CLI]
        DevServer[Development Server]
        TDD[TDD Framework]
    end

    subgraph "QuickHooks Core"
        MainApp[Main Application]
        HookRunner[Hook Runner]
        TestRunner[Test Runner]
        Executor[Hook Executor]
    end

    subgraph "Agent Analysis System"
        Analyzer[Agent Analyzer]
        Discovery[Agent Discovery]
        ContextMgr[Context Manager]
    end

    subgraph "AI/ML Services"
        Groq[Groq API]
        PydanticAI[Pydantic AI]
        Chroma[Chroma DB]
        SentenceTransformers[Sentence Transformers]
    end

    subgraph "Data Layer"
        SQLite[(SQLite DB)]
        VectorStore[(Vector Store)]
        FileSystem[(File System)]
    end

    subgraph "External Integrations"
        ClaudeCode[Claude Code Settings]
        AgentsDir[~/.claude/agents]
        HooksDir[Hooks Directory]
    end

    CLI --> MainApp
    DevServer --> MainApp
    TDD --> TestRunner

    MainApp --> HookRunner
    MainApp --> Analyzer
    MainApp --> TestRunner

    HookRunner --> Executor
    TestRunner --> Executor

    Analyzer --> Discovery
    Analyzer --> ContextMgr
    Analyzer --> Groq
    Analyzer --> PydanticAI

    Discovery --> Chroma
    Discovery --> AgentsDir
    Discovery --> SentenceTransformers

    ContextMgr --> SQLite
    ContextMgr --> VectorStore

    Executor --> FileSystem
    Executor --> HooksDir

    MainApp --> ClaudeCode
    Discovery --> ClaudeCode
```

## Component Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant MainApp
    participant Analyzer
    participant Discovery
    participant Groq
    participant ClaudeCode

    User->>CLI: quickhooks agents analyze "prompt"
    CLI->>MainApp: Route to agent analysis
    MainApp->>Analyzer: Create analyzer instance

    Analyzer->>Discovery: Scan for local agents
    Discovery->>Discovery: Index agents in ChromaDB
    Discovery-->>Analyzer: Return relevant agents

    Analyzer->>Groq: Send analysis request
    Groq-->>Analyzer: Return agent recommendations

    Analyzer->>ClaudeCode: Update prompt with agent usage
    ClaudeCode-->>User: Modified prompt with agent instructions
```

## Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Processing"
        Prompt[User Prompt]
        Context[Additional Context]
        Config[Configuration]
    end

    subgraph "Analysis Pipeline"
        Chunking[Context Chunking]
        Embedding[Text Embedding]
        Similarity[Similarity Search]
        AIAnalysis[AI Analysis]
    end

    subgraph "Output Generation"
        Recommendations[Agent Recommendations]
        PromptMod[Prompt Modification]
        Report[Analysis Report]
    end

    Prompt --> Chunking
    Context --> Chunking
    Config --> Chunking

    Chunking --> Embedding
    Embedding --> Similarity
    Similarity --> AIAnalysis

    AIAnalysis --> Recommendations
    AIAnalysis --> PromptMod
    AIAnalysis --> Report

    Similarity --> Discovery
    Discovery --> AIAnalysis
```

## Plugin Architecture

```mermaid
graph TB
    subgraph "Core Framework"
        BaseHook[BaseHook Class]
        HookRegistry[Hook Registry]
        EventSystem[Event System]
    end

    subgraph "Hook Types"
        ParallelHook[Parallel Hook]
        SequentialHook[Sequential Hook]
        ConditionalHook[Conditional Hook]
        CustomHook[Custom Hook]
    end

    subgraph "Hook Lifecycle"
        Validation[Input Validation]
        Processing[Hook Processing]
        ErrorHandling[Error Handling]
        Logging[Audit Logging]
    end

    BaseHook --> ParallelHook
    BaseHook --> SequentialHook
    BaseHook --> ConditionalHook
    BaseHook --> CustomHook

    HookRegistry --> BaseHook
    EventSystem --> BaseHook

    ParallelHook --> Validation
    SequentialHook --> Validation
    ConditionalHook --> Validation
    CustomHook --> Validation

    Validation --> Processing
    Processing --> ErrorHandling
    ErrorHandling --> Logging
```

## Technology Stack

```mermaid
graph TB
    subgraph "Languages & Runtime"
        Python[Python 3.12+]
        UV[UV Package Manager]
    end

    subgraph "Web Framework"
        Typer[Typer CLI]
        FastAPI[FastAPI]
        Rich[Rich Console]
    end

    subgraph "Data & Storage"
        Pydantic[Pydantic Models]
        SQLite[SQLite]
        ChromaDB[Chroma DB]
    end

    subgraph "AI/ML"
        GroqAPI[Groq API]
        PydanticAI[Pydantic AI]
        Transformers[Sentence Transformers]
    end

    subgraph "Development Tools"
        Ruff[Ruff Linter]
        MyPy[MyPy Type Checker]
        Pytest[Pytest Testing]
    end

    Python --> UV
    Python --> Typer
    Python --> Pydantic

    Typer --> Rich
    Pydantic --> SQLite
    Pydantic --> ChromaDB

    GroqAPI --> PydanticAI
    ChromaDB --> Transformers

    UV --> Ruff
    UV --> MyPy
    UV --> Pytest
```

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        InputValidation[Input Validation]
        APIAuth[API Authentication]
        DataEncryption[Data Encryption]
        AuditLogging[Audit Logging]
    end

    subgraph "Access Control"
        Permissions[Permission System]
        RateLimiting[Rate Limiting]
        Sandboxing[Hook Sandboxing]
    end

    subgraph "Data Protection"
        SecretsMgmt[Secrets Management]
        BackupRecovery[Backup & Recovery]
        DataRetention[Data Retention]
    end

    InputValidation --> APIAuth
    APIAuth --> DataEncryption
    DataEncryption --> AuditLogging

    APIAuth --> Permissions
    Permissions --> RateLimiting
    RateLimiting --> Sandboxing

    DataEncryption --> SecretsMgmt
    SecretsMgmt --> BackupRecovery
    BackupRecovery --> DataRetention
```

## Performance Architecture

```mermaid
graph TB
    subgraph "Caching Layer"
        AgentCache[Agent Cache]
        ResultCache[Result Cache]
        EmbeddingCache[Embedding Cache]
    end

    subgraph "Processing Pipeline"
        AsyncProcessing[Async Processing]
        ParallelExecution[Parallel Execution]
        QueueManagement[Queue Management]
    end

    subgraph "Resource Management"
        MemoryMgmt[Memory Management]
        ConnectionPooling[Connection Pooling]
        ResourceLimits[Resource Limits]
    end

    AgentCache --> AsyncProcessing
    ResultCache --> ParallelExecution
    EmbeddingCache --> QueueManagement

    AsyncProcessing --> MemoryMgmt
    ParallelExecution --> ConnectionPooling
    QueueManagement --> ResourceLimits
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DevServer[Dev Server]
        HotReload[Hot Reload]
        LocalDB[(Local SQLite)]
    end

    subgraph "Testing Environment"
        TestRunner[Test Runner]
        MockServices[Mock Services]
        TestDB[(Test Database)]
    end

    subgraph "Production Environment"
        AppServer[Application Server]
        LoadBalancer[Load Balancer]
        ProdDB[(Production Database)]
        Monitoring[Monitoring & Logging]
    end

    subgraph "CI/CD Pipeline"
        GitHubActions[GitHub Actions]
        DockerBuild[Docker Build]
        Deployment[Automated Deployment]
    end

    DevServer --> TestRunner
    TestRunner --> AppServer

    AppServer --> LoadBalancer
    LoadBalancer --> ProdDB
    AppServer --> Monitoring

    GitHubActions --> DockerBuild
    DockerBuild --> Deployment
    Deployment --> AppServer
```

## Configuration Management

```mermaid
graph TB
    subgraph "Configuration Sources"
        EnvVars[Environment Variables]
        ConfigFiles[Configuration Files]
        CLISettings[CLI Settings]
        DatabaseConfig[Database Config]
    end

    subgraph "Configuration Processing"
        Validation[Config Validation]
        Merging[Config Merging]
        Resolution[Config Resolution]
    end

    subgraph "Configuration Output"
        RuntimeConfig[Runtime Configuration]
        FeatureFlags[Feature Flags]
        LoggingConfig[Logging Configuration]
    end

    EnvVars --> Validation
    ConfigFiles --> Validation
    CLISettings --> Validation
    DatabaseConfig --> Validation

    Validation --> Merging
    Merging --> Resolution

    Resolution --> RuntimeConfig
    Resolution --> FeatureFlags
    Resolution --> LoggingConfig
```