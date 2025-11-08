"""LanceDB database manager for QuickHooks global system."""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

from quickhooks.config import get_global_hooks_dir
from quickhooks.db.models import (
    HookMetadata,
    EnvironmentConfig,
    HookTemplate,
    ScaffoldingProject,
    HookUsageAnalytics,
    HookType,
    HookComplexity,
    Environment
)


class GlobalHooksDB:
    """LanceDB manager for global hooks system with AI-powered search."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection.
        
        Args:
            db_path: Optional custom database path. Defaults to global hooks directory.
        """
        if db_path is None:
            db_path = get_global_hooks_dir() / "lancedb"
        
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database connection
        self.db = lancedb.connect(str(self.db_path))
        
        # Initialize embedding model for semantic search
        self.embedder = get_registry().get("sentence-transformers").create(
            name="all-MiniLM-L6-v2"
        )
        
        # Table references
        self._hooks_table = None
        self._environments_table = None
        self._templates_table = None
        self._projects_table = None
        self._analytics_table = None
    
    @property
    def hooks_table(self):
        """Get or create hooks metadata table."""
        if self._hooks_table is None:
            try:
                self._hooks_table = self.db.open_table("hooks")
            except Exception:
                self._hooks_table = self.db.create_table("hooks", schema=HookMetadata)
        return self._hooks_table
    
    @property
    def environments_table(self):
        """Get or create environments table."""
        if self._environments_table is None:
            try:
                self._environments_table = self.db.open_table("environments")
            except Exception:
                self._environments_table = self.db.create_table("environments", schema=EnvironmentConfig)
        return self._environments_table
    
    @property
    def templates_table(self):
        """Get or create templates table."""
        if self._templates_table is None:
            try:
                self._templates_table = self.db.open_table("templates")
            except Exception:
                self._templates_table = self.db.create_table("templates", schema=HookTemplate)
        return self._templates_table
    
    @property
    def projects_table(self):
        """Get or create scaffolding projects table."""
        if self._projects_table is None:
            try:
                self._projects_table = self.db.open_table("projects")
            except Exception:
                self._projects_table = self.db.create_table("projects", schema=ScaffoldingProject)
        return self._projects_table
    
    @property
    def analytics_table(self):
        """Get or create analytics table."""
        if self._analytics_table is None:
            try:
                self._analytics_table = self.db.open_table("analytics")
            except Exception:
                self._analytics_table = self.db.create_table("analytics", schema=HookUsageAnalytics)
        return self._analytics_table
    
    # Hook Management Methods
    
    def add_hook(self, hook_metadata: HookMetadata) -> None:
        """Add a hook to the database.
        
        Args:
            hook_metadata: Hook metadata to store
        """
        self.hooks_table.add([hook_metadata.dict()])
    
    def search_hooks(self, query: str, limit: int = 10) -> List[HookMetadata]:
        """Search hooks using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching hook metadata
        """
        results = (
            self.hooks_table
            .search(query)
            .limit(limit)
            .to_pydantic(HookMetadata)
        )
        return results
    
    def get_hook_by_name(self, name: str) -> Optional[HookMetadata]:
        """Get a hook by its name.
        
        Args:
            name: Hook name
            
        Returns:
            Hook metadata if found, None otherwise
        """
        results = (
            self.hooks_table
            .search()
            .where(f"name = '{name}'")
            .limit(1)
            .to_pydantic(HookMetadata)
        )
        return results[0] if results else None
    
    def update_hook(self, hook_metadata: HookMetadata) -> None:
        """Update existing hook metadata.
        
        Args:
            hook_metadata: Updated hook metadata
        """
        # Delete existing entry
        self.hooks_table.delete(f"name = '{hook_metadata.name}'")
        # Add updated entry
        self.add_hook(hook_metadata)
    
    def delete_hook(self, name: str) -> None:
        """Delete a hook from the database.
        
        Args:
            name: Hook name to delete
        """
        self.hooks_table.delete(f"name = '{name}'")
    
    def list_hooks(self, 
                   hook_type: Optional[HookType] = None,
                   complexity: Optional[HookComplexity] = None,
                   tags: Optional[List[str]] = None) -> List[HookMetadata]:
        """List hooks with optional filtering.
        
        Args:
            hook_type: Filter by hook type
            complexity: Filter by complexity level
            tags: Filter by tags (any match)
            
        Returns:
            List of hook metadata
        """
        query = self.hooks_table.search()
        
        conditions = []
        if hook_type:
            conditions.append(f"hook_type = '{hook_type.value}'")
        if complexity:
            conditions.append(f"complexity = '{complexity.value}'")
        
        if conditions:
            where_clause = " AND ".join(conditions)
            query = query.where(where_clause)
        
        results = query.to_pydantic(HookMetadata)
        
        # Filter by tags if specified
        if tags:
            filtered_results = []
            for hook in results:
                if any(tag in hook.tags for tag in tags):
                    filtered_results.append(hook)
            return filtered_results
        
        return results
    
    # Environment Management Methods
    
    def add_environment(self, env_config: EnvironmentConfig) -> None:
        """Add an environment configuration.
        
        Args:
            env_config: Environment configuration to store
        """
        self.environments_table.add([env_config.dict()])
    
    def get_environment(self, name: str) -> Optional[EnvironmentConfig]:
        """Get environment by name.
        
        Args:
            name: Environment name
            
        Returns:
            Environment configuration if found
        """
        results = (
            self.environments_table
            .search()
            .where(f"name = '{name}'")
            .limit(1)
            .to_pydantic(EnvironmentConfig)
        )
        return results[0] if results else None
    
    def list_environments(self, 
                         env_type: Optional[Environment] = None,
                         active_only: bool = True) -> List[EnvironmentConfig]:
        """List environments with optional filtering.
        
        Args:
            env_type: Filter by environment type
            active_only: Only return active environments
            
        Returns:
            List of environment configurations
        """
        query = self.environments_table.search()
        
        conditions = []
        if env_type:
            conditions.append(f"environment_type = '{env_type.value}'")
        if active_only:
            conditions.append("active = true")
        
        if conditions:
            where_clause = " AND ".join(conditions)
            query = query.where(where_clause)
        
        return query.to_pydantic(EnvironmentConfig)
    
    # Template Management Methods
    
    def add_template(self, template: HookTemplate) -> None:
        """Add a hook template.
        
        Args:
            template: Template to store
        """
        self.templates_table.add([template.dict()])
    
    def search_templates(self, query: str, limit: int = 10) -> List[HookTemplate]:
        """Search templates using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching templates
        """
        results = (
            self.templates_table
            .search(query)
            .limit(limit)
            .to_pydantic(HookTemplate)
        )
        return results
    
    def get_template_by_name(self, name: str) -> Optional[HookTemplate]:
        """Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template if found
        """
        results = (
            self.templates_table
            .search()
            .where(f"name = '{name}'")
            .limit(1)
            .to_pydantic(HookTemplate)
        )
        return results[0] if results else None
    
    # Project Scaffolding Methods
    
    def add_project(self, project: ScaffoldingProject) -> None:
        """Add a scaffolding project.
        
        Args:
            project: Project configuration to store
        """
        self.projects_table.add([project.dict()])
    
    def search_projects(self, query: str, limit: int = 10) -> List[ScaffoldingProject]:
        """Search projects using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching projects
        """
        results = (
            self.projects_table
            .search(query)
            .limit(limit)
            .to_pydantic(ScaffoldingProject)
        )
        return results
    
    def get_project_by_name(self, name: str) -> Optional[ScaffoldingProject]:
        """Get project by name.
        
        Args:
            name: Project name
            
        Returns:
            Project if found
        """
        results = (
            self.projects_table
            .search()
            .where(f"name = '{name}'")
            .limit(1)
            .to_pydantic(ScaffoldingProject)
        )
        return results[0] if results else None
    
    # Analytics Methods
    
    def record_hook_usage(self, hook_name: str, 
                         execution_time: float,
                         success: bool,
                         input_data: str = "",
                         output_data: str = "",
                         error_message: str = "") -> None:
        """Record hook usage analytics.
        
        Args:
            hook_name: Name of the hook
            execution_time: Execution time in milliseconds
            success: Whether execution was successful
            input_data: Input data used
            output_data: Output data generated
            error_message: Error message if failed
        """
        # Get or create analytics record
        analytics = self.get_hook_analytics(hook_name)
        if analytics is None:
            analytics = HookUsageAnalytics(hook_name=hook_name)
        
        # Update statistics
        analytics.total_executions += 1
        if success:
            analytics.successful_executions += 1
        else:
            analytics.failed_executions += 1
            if error_message and error_message not in analytics.error_patterns:
                analytics.error_patterns.append(error_message)
        
        # Update execution times
        if analytics.min_execution_time == 0.0 or execution_time < analytics.min_execution_time:
            analytics.min_execution_time = execution_time
        if execution_time > analytics.max_execution_time:
            analytics.max_execution_time = execution_time
        
        # Calculate new average
        total_time = analytics.avg_execution_time * (analytics.total_executions - 1) + execution_time
        analytics.avg_execution_time = total_time / analytics.total_executions
        
        # Update common patterns
        if input_data and input_data not in analytics.common_inputs:
            analytics.common_inputs.append(input_data)
        if output_data and output_data not in analytics.common_outputs:
            analytics.common_outputs.append(output_data)
        
        # Save or update analytics
        if self.get_hook_analytics(hook_name) is None:
            self.analytics_table.add([analytics.dict()])
        else:
            self.analytics_table.delete(f"hook_name = '{hook_name}'")
            self.analytics_table.add([analytics.dict()])
    
    def get_hook_analytics(self, hook_name: str) -> Optional[HookUsageAnalytics]:
        """Get analytics for a specific hook.
        
        Args:
            hook_name: Hook name
            
        Returns:
            Analytics data if found
        """
        results = (
            self.analytics_table
            .search()
            .where(f"hook_name = '{hook_name}'")
            .limit(1)
            .to_pydantic(HookUsageAnalytics)
        )
        return results[0] if results else None
    
    # AI-Powered Recommendations
    
    def recommend_hooks(self, description: str, limit: int = 5) -> List[HookMetadata]:
        """Recommend hooks based on a description of what user wants to do.
        
        Args:
            description: Description of the task or requirement
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended hooks
        """
        return self.search_hooks(description, limit)
    
    def suggest_similar_hooks(self, hook_name: str, limit: int = 5) -> List[HookMetadata]:
        """Suggest hooks similar to a given hook.
        
        Args:
            hook_name: Name of the reference hook
            limit: Maximum number of suggestions
            
        Returns:
            List of similar hooks
        """
        hook = self.get_hook_by_name(hook_name)
        if not hook:
            return []
        
        # Search using the hook's description
        similar = self.search_hooks(hook.description, limit + 1)
        # Remove the original hook from results
        return [h for h in similar if h.name != hook_name][:limit]
    
    def get_popular_hooks(self, limit: int = 10) -> List[HookMetadata]:
        """Get most popular hooks based on usage analytics.
        
        Args:
            limit: Maximum number of hooks to return
            
        Returns:
            List of popular hooks sorted by usage
        """
        # Get all analytics, sorted by usage count
        analytics_results = (
            self.analytics_table
            .search()
            .to_pydantic(HookUsageAnalytics)
        )
        
        # Sort by total executions
        analytics_results.sort(key=lambda x: x.total_executions, reverse=True)
        
        # Get corresponding hooks
        popular_hooks = []
        for analytics in analytics_results[:limit]:
            hook = self.get_hook_by_name(analytics.hook_name)
            if hook:
                popular_hooks.append(hook)
        
        return popular_hooks
    
    def close(self) -> None:
        """Close database connection."""
        # LanceDB connections are automatically managed
        pass


# Global instance
_global_db = None

def get_global_db() -> GlobalHooksDB:
    """Get the global database instance."""
    global _global_db
    if _global_db is None:
        _global_db = GlobalHooksDB()
    return _global_db