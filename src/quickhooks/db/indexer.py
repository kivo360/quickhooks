"""Hook indexing and analysis for the global LanceDB system."""

import ast
import inspect
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Dict, Any

from quickhooks.db.models import (
    HookMetadata, 
    HookType, 
    HookComplexity, 
    Environment
)
from quickhooks.hooks.base import BaseHook


class HookIndexer:
    """Analyzes Python hook files and extracts metadata for LanceDB storage."""
    
    def __init__(self):
        """Initialize the hook indexer."""
        pass
    
    def index_hook_file(self, file_path: Path) -> Optional[HookMetadata]:
        """Index a single hook file and extract metadata.
        
        Args:
            file_path: Path to the hook Python file
            
        Returns:
            HookMetadata if successfully analyzed, None otherwise
        """
        try:
            # Read and parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract hook class information
            hook_class = self._find_hook_class(tree)
            if not hook_class:
                return None
            
            # Load the module to get runtime information
            spec = importlib.util.spec_from_file_location("hook_module", file_path)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get the actual hook class
            hook_cls = getattr(module, hook_class.name, None)
            if not hook_cls or not issubclass(hook_cls, BaseHook):
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, hook_class, hook_cls, content, tree)
            return metadata
            
        except Exception as e:
            print(f"Error indexing hook file {file_path}: {e}")
            return None
    
    def _find_hook_class(self, tree: ast.AST) -> Optional[ast.ClassDef]:
        """Find the hook class in the AST.
        
        Args:
            tree: Parsed AST
            
        Returns:
            Hook class node if found
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from BaseHook
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'BaseHook':
                        return node
                    elif isinstance(base, ast.Attribute) and base.attr == 'BaseHook':
                        return node
        return None
    
    def _extract_metadata(self, 
                         file_path: Path,
                         hook_class: ast.ClassDef,
                         hook_cls: type,
                         content: str,
                         tree: ast.AST) -> HookMetadata:
        """Extract comprehensive metadata from the hook.
        
        Args:
            file_path: Path to the hook file
            hook_class: AST node of the hook class
            hook_cls: Actual hook class
            content: File content
            tree: Parsed AST
            
        Returns:
            Complete hook metadata
        """
        # Basic information
        name = getattr(hook_cls, 'name', hook_class.name.lower().replace('hook', ''))
        display_name = getattr(hook_cls, 'display_name', hook_class.name)
        description = self._extract_description(hook_class, hook_cls)
        
        # Categorization
        hook_type = self._determine_hook_type(hook_cls, content)
        complexity = self._analyze_complexity(hook_class, content)
        tags = self._extract_tags(hook_cls, content)
        
        # File system information
        test_path = self._find_test_file(file_path)
        config_path = self._find_config_file(file_path)
        
        # Code analysis
        lines_of_code = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
        dependencies = self._extract_dependencies(tree)
        imports = self._extract_imports(tree)
        
        # Environment and context
        environments = self._determine_environments(hook_cls, content)
        use_cases = self._extract_use_cases(hook_cls, content)
        examples = self._extract_examples(hook_cls, content)
        
        # Authoring information
        author = self._extract_author(content)
        version = getattr(hook_cls, 'version', '1.0.0')
        
        # Quality metrics
        test_coverage = self._estimate_test_coverage(test_path)
        documentation_score = self._score_documentation(hook_class, hook_cls, content)
        complexity_score = self._calculate_complexity_score(hook_class, content)
        
        return HookMetadata(
            name=name,
            display_name=display_name,
            description=description,
            hook_type=hook_type,
            complexity=complexity,
            tags=tags,
            file_path=str(file_path.absolute()),
            test_path=str(test_path) if test_path else None,
            config_path=str(config_path) if config_path else None,
            lines_of_code=lines_of_code,
            dependencies=dependencies,
            imports=imports,
            environments=environments,
            use_cases=use_cases,
            examples=examples,
            author=author,
            version=version,
            test_coverage=test_coverage,
            documentation_score=documentation_score,
            complexity_score=complexity_score,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _extract_description(self, hook_class: ast.ClassDef, hook_cls: type) -> str:
        """Extract hook description from docstring or class attribute."""
        # Try class attribute first
        if hasattr(hook_cls, 'description'):
            return hook_cls.description
        
        # Try docstring
        if hook_class.body and isinstance(hook_class.body[0], ast.Expr):
            if isinstance(hook_class.body[0].value, ast.Constant):
                return hook_class.body[0].value.value
        
        # Fallback to class name
        return f"Hook: {hook_class.name}"
    
    def _determine_hook_type(self, hook_cls: type, content: str) -> HookType:
        """Determine the primary type of the hook."""
        # Check class attribute
        if hasattr(hook_cls, 'hook_type'):
            try:
                return HookType(hook_cls.hook_type)
            except ValueError:
                pass
        
        # Analyze method names and content
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['validate', 'check', 'verify', 'ensure']):
            return HookType.VALIDATOR
        elif any(word in content_lower for word in ['transform', 'modify', 'convert', 'change']):
            return HookType.TRANSFORMER
        elif any(word in content_lower for word in ['analyze', 'parse', 'extract', 'detect']):
            return HookType.ANALYZER
        elif any(word in content_lower for word in ['enhance', 'improve', 'optimize', 'enrich']):
            return HookType.ENHANCER
        elif any(word in content_lower for word in ['log', 'record', 'track', 'monitor']):
            return HookType.LOGGER
        
        return HookType.TRANSFORMER  # Default
    
    def _analyze_complexity(self, hook_class: ast.ClassDef, content: str) -> HookComplexity:
        """Analyze the complexity level of the hook."""
        # Count methods
        methods = [node for node in hook_class.body if isinstance(node, ast.FunctionDef)]
        method_count = len(methods)
        
        # Count lines of code
        lines = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
        
        # Count imports
        tree = ast.parse(content)
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        import_count = len(imports)
        
        # Complexity scoring
        complexity_score = 0
        complexity_score += min(method_count * 2, 10)  # Max 10 for methods
        complexity_score += min(lines // 10, 15)       # Max 15 for lines
        complexity_score += min(import_count, 5)       # Max 5 for imports
        
        if complexity_score <= 8:
            return HookComplexity.SIMPLE
        elif complexity_score <= 16:
            return HookComplexity.MODERATE
        elif complexity_score <= 24:
            return HookComplexity.ADVANCED
        else:
            return HookComplexity.EXPERT
    
    def _extract_tags(self, hook_cls: type, content: str) -> List[str]:
        """Extract relevant tags from the hook."""
        tags = []
        
        # From class attribute
        if hasattr(hook_cls, 'tags'):
            tags.extend(hook_cls.tags)
        
        # From content analysis
        content_lower = content.lower()
        
        # Technology tags
        if 'async' in content_lower or 'await' in content_lower:
            tags.append('async')
        if 'typing' in content_lower:
            tags.append('typed')
        if 'dataclass' in content_lower:
            tags.append('dataclass')
        if 'pydantic' in content_lower:
            tags.append('pydantic')
        
        # Functionality tags
        if 'file' in content_lower or 'path' in content_lower:
            tags.append('filesystem')
        if 'network' in content_lower or 'http' in content_lower:
            tags.append('network')
        if 'security' in content_lower or 'auth' in content_lower:
            tags.append('security')
        if 'performance' in content_lower or 'cache' in content_lower:
            tags.append('performance')
        
        return list(set(tags))  # Remove duplicates
    
    def _find_test_file(self, hook_path: Path) -> Optional[Path]:
        """Find the corresponding test file."""
        test_patterns = [
            f"test_{hook_path.stem}.py",
            f"{hook_path.stem}_test.py",
            f"test{hook_path.stem.title()}.py"
        ]
        
        # Check in same directory
        for pattern in test_patterns:
            test_file = hook_path.parent / pattern
            if test_file.exists():
                return test_file
        
        # Check in tests directory
        tests_dir = hook_path.parent / "tests"
        if tests_dir.exists():
            for pattern in test_patterns:
                test_file = tests_dir / pattern
                if test_file.exists():
                    return test_file
        
        return None
    
    def _find_config_file(self, hook_path: Path) -> Optional[Path]:
        """Find the corresponding config file."""
        config_patterns = [
            f"{hook_path.stem}_config.py",
            f"{hook_path.stem}.config.py",
            "config.py"
        ]
        
        for pattern in config_patterns:
            config_file = hook_path.parent / pattern
            if config_file.exists():
                return config_file
        
        return None
    
    def _extract_dependencies(self, tree: ast.AST) -> List[str]:
        """Extract external dependencies from imports."""
        dependencies = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and not node.module.startswith('.'):
                    # Extract top-level package name
                    top_level = node.module.split('.')[0]
                    dependencies.add(top_level)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split('.')[0]
                    dependencies.add(top_level)
        
        # Filter out standard library modules
        stdlib_modules = {
            'os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 're', 'collections',
            'itertools', 'functools', 'asyncio', 'logging', 'unittest', 'pytest'
        }
        
        return [dep for dep in dependencies if dep not in stdlib_modules]
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all import statements."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(f"from {node.module} import {', '.join(alias.name for alias in node.names)}")
            elif isinstance(node, ast.Import):
                imports.append(f"import {', '.join(alias.name for alias in node.names)}")
        
        return imports
    
    def _determine_environments(self, hook_cls: type, content: str) -> List[Environment]:
        """Determine which environments the hook supports."""
        environments = [Environment.GLOBAL]  # All global hooks support global env
        
        # Check for environment-specific code
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['test', 'mock', 'fixture']):
            environments.append(Environment.TESTING)
        if 'development' in content_lower or 'dev' in content_lower:
            environments.append(Environment.DEVELOPMENT)
        if 'production' in content_lower or 'prod' in content_lower:
            environments.append(Environment.PRODUCTION)
        if 'staging' in content_lower:
            environments.append(Environment.STAGING)
        
        return environments
    
    def _extract_use_cases(self, hook_cls: type, content: str) -> List[str]:
        """Extract common use cases from documentation and code."""
        use_cases = []
        
        # From class attribute
        if hasattr(hook_cls, 'use_cases'):
            use_cases.extend(hook_cls.use_cases)
        
        # From docstring analysis
        docstring = inspect.getdoc(hook_cls) or ""
        if docstring:
            # Simple extraction of sentences that might describe use cases
            sentences = docstring.split('.')
            for sentence in sentences:
                if any(word in sentence.lower() for word in ['use', 'for', 'when', 'during']):
                    use_cases.append(sentence.strip())
        
        return use_cases[:5]  # Limit to 5 use cases
    
    def _extract_examples(self, hook_cls: type, content: str) -> List[str]:
        """Extract usage examples from documentation."""
        examples = []
        
        # From class attribute
        if hasattr(hook_cls, 'examples'):
            examples.extend(hook_cls.examples)
        
        # From docstring
        docstring = inspect.getdoc(hook_cls) or ""
        if 'example' in docstring.lower():
            # Extract code blocks that might be examples
            lines = docstring.split('\n')
            in_example = False
            current_example = []
            
            for line in lines:
                if 'example' in line.lower():
                    in_example = True
                    current_example = []
                elif in_example:
                    if line.strip().startswith('>>>') or line.strip().startswith('```'):
                        if current_example:
                            examples.append('\n'.join(current_example))
                            current_example = []
                    else:
                        current_example.append(line)
        
        return examples[:3]  # Limit to 3 examples
    
    def _extract_author(self, content: str) -> str:
        """Extract author information from file."""
        lines = content.split('\n')
        
        for line in lines[:20]:  # Check first 20 lines
            line_lower = line.lower()
            if 'author' in line_lower and ':' in line:
                return line.split(':')[1].strip().strip('\'"')
        
        return "unknown"
    
    def _estimate_test_coverage(self, test_path: Optional[Path]) -> float:
        """Estimate test coverage based on test file existence and size."""
        if not test_path or not test_path.exists():
            return 0.0
        
        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                test_content = f.read()
            
            # Count test methods
            test_methods = test_content.count('def test_')
            
            # Simple heuristic: more test methods = higher coverage
            if test_methods >= 10:
                return 90.0
            elif test_methods >= 5:
                return 70.0
            elif test_methods >= 3:
                return 50.0
            elif test_methods >= 1:
                return 30.0
            else:
                return 10.0
                
        except Exception:
            return 0.0
    
    def _score_documentation(self, hook_class: ast.ClassDef, hook_cls: type, content: str) -> float:
        """Score the quality of documentation."""
        score = 0.0
        
        # Class docstring (3 points)
        if hook_class.body and isinstance(hook_class.body[0], ast.Expr):
            if isinstance(hook_class.body[0].value, ast.Constant):
                docstring = hook_class.body[0].value.value
                if len(docstring) > 50:
                    score += 3.0
                elif len(docstring) > 20:
                    score += 2.0
                else:
                    score += 1.0
        
        # Method docstrings (2 points)
        methods_with_docs = 0
        total_methods = 0
        
        for node in hook_class.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                total_methods += 1
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant)):
                    methods_with_docs += 1
        
        if total_methods > 0:
            score += (methods_with_docs / total_methods) * 2.0
        
        # Type hints (2 points)
        has_type_hints = 'typing' in content or '->' in content or ':' in content
        if has_type_hints:
            score += 2.0
        
        # Comments (1 point)
        comment_lines = len([line for line in content.split('\n') if line.strip().startswith('#')])
        total_lines = len([line for line in content.split('\n') if line.strip()])
        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            score += min(comment_ratio * 10, 1.0)  # Max 1 point for comments
        
        # Examples in docstring (2 points)
        if 'example' in content.lower():
            score += 2.0
        
        return min(score, 10.0)  # Cap at 10
    
    def _calculate_complexity_score(self, hook_class: ast.ClassDef, content: str) -> float:
        """Calculate complexity score (higher = more complex)."""
        score = 0.0
        
        # Lines of code
        lines = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
        score += min(lines / 10, 5.0)  # Max 5 points for LOC
        
        # Number of methods
        methods = [node for node in hook_class.body if isinstance(node, ast.FunctionDef)]
        score += min(len(methods) * 0.5, 2.0)  # Max 2 points for methods
        
        # Nesting depth
        max_depth = self._calculate_max_nesting_depth(hook_class)
        score += min(max_depth * 0.5, 2.0)  # Max 2 points for nesting
        
        # Dependencies
        tree = ast.parse(content)
        imports = len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))])
        score += min(imports * 0.1, 1.0)  # Max 1 point for imports
        
        return min(score, 10.0)  # Cap at 10
    
    def _calculate_max_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth in the AST."""
        max_depth = current_depth
        
        # Nodes that increase nesting depth
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.FunctionDef, ast.ClassDef)
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                child_depth = self._calculate_max_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_max_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def index_directory(self, directory: Path) -> List[HookMetadata]:
        """Index all hook files in a directory.
        
        Args:
            directory: Directory containing hook files
            
        Returns:
            List of extracted hook metadata
        """
        hook_metadata = []
        
        # Find all Python files
        for py_file in directory.rglob("*.py"):
            if py_file.name.startswith('__') or py_file.name.startswith('test_'):
                continue
            
            metadata = self.index_hook_file(py_file)
            if metadata:
                hook_metadata.append(metadata)
        
        return hook_metadata