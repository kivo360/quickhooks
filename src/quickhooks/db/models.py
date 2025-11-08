"""Database models for QuickHooks using LanceDB and Pydantic."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from pydantic import Field, field_validator


class HookType(str, Enum):
    """Types of hooks available in the system."""
    VALIDATOR = "validator"
    TRANSFORMER = "transformer"
    ANALYZER = "analyzer"
    ENHANCER = "enhancer"
    LOGGER = "logger"


class HookComplexity(str, Enum):
    """Complexity levels for hooks."""
    SIMPLE = "simple"      # Basic single-purpose hooks
    MODERATE = "moderate"  # Multi-feature hooks
    ADVANCED = "advanced"  # Complex hooks with dependencies
    EXPERT = "expert"      # Highly specialized hooks


class Environment(str, Enum):
    """Environment types for hooks."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    GLOBAL = "global"


# Initialize embeddings for text-to-vector conversion
embedder = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")


class HookMetadata(LanceModel):
    """Core hook metadata stored in LanceDB with vector embeddings."""
    
    # Basic Information
    name: str = Field(description="Unique hook name")
    display_name: str = Field(description="Human-readable hook name")
    description: str = embedder.SourceField()  # This will be embedded
    
    # Vector embedding for semantic search
    description_vector: Vector(embedder.ndims()) = embedder.VectorField()
    
    # Categorization
    hook_type: HookType = Field(description="Primary hook type")
    complexity: HookComplexity = Field(description="Hook complexity level")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    
    # File System Information
    file_path: str = Field(description="Absolute path to hook file")
    test_path: Optional[str] = Field(None, description="Path to test file")
    config_path: Optional[str] = Field(None, description="Path to config file")
    
    # Code Analysis
    lines_of_code: int = Field(default=0, description="Total lines of code")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    imports: List[str] = Field(default_factory=list, description="Python imports used")
    
    # Usage Information
    usage_count: int = Field(default=0, description="Number of times used")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    
    # Environment and Context
    environments: List[Environment] = Field(default_factory=list, description="Supported environments")
    use_cases: List[str] = Field(default_factory=list, description="Common use cases")
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    
    # Authoring Information
    author: str = Field(default="unknown", description="Hook author")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0", description="Hook version")
    
    # Quality Metrics
    test_coverage: float = Field(default=0.0, ge=0.0, le=100.0, description="Test coverage percentage")
    documentation_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Documentation quality score")
    complexity_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Code complexity score")
    
    # AI Enhancement Data
    ai_generated: bool = Field(default=False, description="Whether hook was AI-generated")
    ai_suggestions: List[str] = Field(default_factory=list, description="AI improvement suggestions")
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate that file path exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Hook file does not exist: {v}")
        return str(path.absolute())


class EnvironmentConfig(LanceModel):
    """Environment configuration metadata."""
    
    name: str = Field(description="Environment name")
    description: str = embedder.SourceField()
    description_vector: Vector(embedder.ndims()) = embedder.VectorField()
    
    # Environment Details
    environment_type: Environment = Field(description="Environment type")
    path: str = Field(description="Environment path")
    python_version: str = Field(description="Python version requirement")
    
    # Dependencies and Configuration
    dependencies: List[str] = Field(default_factory=list)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    config_files: List[str] = Field(default_factory=list)
    
    # Hooks in this environment
    hooks: List[str] = Field(default_factory=list, description="Hook names in this environment")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True)


class HookTemplate(LanceModel):
    """Template metadata for rapid scaffolding."""
    
    name: str = Field(description="Template name")
    description: str = embedder.SourceField()
    description_vector: Vector(embedder.ndims()) = embedder.VectorField()
    
    # Template Details
    template_type: str = Field(description="Type of template (hook, config, cli)")
    category: str = Field(description="Template category")
    complexity: HookComplexity = Field(description="Generated code complexity")
    
    # Template Content
    template_path: str = Field(description="Path to Jinja2 template file")
    variables: Dict[str, str] = Field(default_factory=dict, description="Template variables")
    examples: List[Dict[str, str]] = Field(default_factory=list, description="Example configurations")
    
    # AI Enhancement
    ai_prompts: List[str] = Field(default_factory=list, description="AI prompts for customization")
    suggested_modifications: List[str] = Field(default_factory=list)
    
    # Usage Statistics
    usage_count: int = Field(default=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScaffoldingProject(LanceModel):
    """Project scaffolding metadata and AI-generated suggestions."""
    
    name: str = Field(description="Project name")
    description: str = embedder.SourceField()
    description_vector: Vector(embedder.ndims()) = embedder.VectorField()
    
    # Project Configuration
    project_type: str = Field(description="Type of project to scaffold")
    requirements: List[str] = Field(default_factory=list, description="Project requirements")
    technologies: List[str] = Field(default_factory=list, description="Technologies to use")
    
    # AI-Generated Architecture
    suggested_hooks: List[str] = Field(default_factory=list, description="AI-suggested hooks")
    architecture_components: List[str] = Field(default_factory=list)
    file_structure: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Generation Status
    status: str = Field(default="planned", description="Generation status")
    generated_files: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class HookUsageAnalytics(LanceModel):
    """Analytics and usage patterns for hooks."""
    
    hook_name: str = Field(description="Hook name")
    
    # Usage Patterns
    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)
    
    # Performance Metrics
    avg_execution_time: float = Field(default=0.0, description="Average execution time in ms")
    max_execution_time: float = Field(default=0.0, description="Maximum execution time in ms")
    min_execution_time: float = Field(default=0.0, description="Minimum execution time in ms")
    
    # Usage Context
    common_inputs: List[str] = Field(default_factory=list)
    common_outputs: List[str] = Field(default_factory=list)
    error_patterns: List[str] = Field(default_factory=list)
    
    # Temporal Data
    usage_by_hour: Dict[str, int] = Field(default_factory=dict)
    usage_by_day: Dict[str, int] = Field(default_factory=dict)
    usage_trends: List[Dict[str, float]] = Field(default_factory=list)
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)