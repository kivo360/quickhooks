"""Jinja2 utilities for QuickHooks template rendering and code generation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Template,
    select_autoescape,
)
from pydantic import BaseModel, Field


class TemplateConfig(BaseModel):
    """Configuration for template engine."""
    
    template_dirs: List[Union[str, Path]] = Field(
        default_factory=lambda: ["templates", "src/quickhooks/templates"]
    )
    auto_escape: bool = Field(default=True)
    strict_mode: bool = Field(default=True)
    trim_blocks: bool = Field(default=True)
    lstrip_blocks: bool = Field(default=True)
    cache_size: int = Field(default=400)


class TemplateContext(BaseModel):
    """Context data for template rendering."""
    
    variables: Dict[str, Any] = Field(default_factory=dict)
    functions: Dict[str, Any] = Field(default_factory=dict)
    filters: Dict[str, Any] = Field(default_factory=dict)
    
    def add_variable(self, name: str, value: Any) -> None:
        """Add a variable to the context."""
        self.variables[name] = value
    
    def add_function(self, name: str, func: Any) -> None:
        """Add a function to the context."""
        self.functions[name] = func
    
    def add_filter(self, name: str, filter_func: Any) -> None:
        """Add a filter to the context."""
        self.filters[name] = filter_func
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Jinja2."""
        return self.variables


class TemplateEngine:
    """Advanced Jinja2 template engine for QuickHooks."""
    
    def __init__(self, config: Optional[TemplateConfig] = None, template_dir: Optional[str] = None):
        """Initialize the template engine."""
        if template_dir:
            config = TemplateConfig(template_directory=template_dir)
        self.config = config or TemplateConfig()
        self.env = self._create_environment()
        self._setup_built_in_functions()
        self._setup_built_in_filters()
    
    def _create_environment(self) -> Environment:
        """Create and configure Jinja2 environment."""
        # Convert paths to strings for FileSystemLoader
        template_paths = [str(path) for path in self.config.template_dirs if Path(path).exists()]
        
        if not template_paths:
            # Create default template directory if none exist
            default_dir = Path("templates")
            default_dir.mkdir(exist_ok=True)
            template_paths = ["templates"]
        
        loader = FileSystemLoader(template_paths)
        
        env = Environment(
            loader=loader,
            autoescape=select_autoescape(['html', 'xml']) if self.config.auto_escape else False,
            undefined=StrictUndefined if self.config.strict_mode else None,
            trim_blocks=self.config.trim_blocks,
            lstrip_blocks=self.config.lstrip_blocks,
            cache_size=self.config.cache_size,
        )
        
        return env
    
    def _setup_built_in_functions(self) -> None:
        """Set up built-in template functions."""
        def snake_to_camel(snake_str: str) -> str:
            """Convert snake_case to camelCase."""
            components = snake_str.split('_')
            return components[0] + ''.join(word.capitalize() for word in components[1:])
        
        def snake_to_pascal(snake_str: str) -> str:
            """Convert snake_case to PascalCase."""
            return ''.join(word.capitalize() for word in snake_str.split('_'))
        
        def camel_to_snake(camel_str: str) -> str:
            """Convert camelCase to snake_case."""
            import re
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', camel_str).lower()
        
        def pluralize(word: str) -> str:
            """Simple pluralization."""
            if word.endswith('y'):
                return word[:-1] + 'ies'
            elif word.endswith(('s', 'sh', 'ch', 'x', 'z')):
                return word + 'es'
            else:
                return word + 's'
        
        def singularize(word: str) -> str:
            """Simple singularization."""
            if word.endswith('ies'):
                return word[:-3] + 'y'
            elif word.endswith('es') and len(word) > 3:
                return word[:-2]
            elif word.endswith('s') and len(word) > 1:
                return word[:-1]
            else:
                return word
        
        # Add functions to environment
        self.env.globals.update({
            'snake_to_camel': snake_to_camel,
            'snake_to_pascal': snake_to_pascal,
            'camel_to_snake': camel_to_snake,
            'pluralize': pluralize,
            'singularize': singularize,
        })
    
    def _setup_built_in_filters(self) -> None:
        """Set up built-in template filters."""
        def indent_code(text: str, spaces: int = 4) -> str:
            """Indent code blocks."""
            indent = ' ' * spaces
            return '\n'.join(indent + line if line.strip() else line for line in text.split('\n'))
        
        def quote_string(text: str, quote_type: str = 'double') -> str:
            """Quote a string."""
            if quote_type == 'single':
                return f"'{text}'"
            else:
                return f'"{text}"'
        
        def format_docstring(text: str, indent: int = 4) -> str:
            """Format a docstring with proper indentation."""
            lines = text.strip().split('\n')
            if len(lines) == 1:
                return f'"""{lines[0]}"""'
            
            indent_str = ' ' * indent
            formatted_lines = ['"""' + lines[0]]
            for line in lines[1:]:
                if line.strip():
                    formatted_lines.append(indent_str + line)
                else:
                    formatted_lines.append('')
            formatted_lines.append(indent_str + '"""')
            return '\n'.join(formatted_lines)
        
        def list_to_imports(items: List[str], from_module: str = None) -> str:
            """Convert list to import statement."""
            if from_module:
                return f"from {from_module} import {', '.join(items)}"
            else:
                return '\n'.join(f"import {item}" for item in items)
        
        # Add filters to environment
        self.env.filters.update({
            'indent_code': indent_code,
            'quote': quote_string,
            'docstring': format_docstring,
            'imports': list_to_imports,
            'repr': repr,
        })
    
    def add_function(self, name: str, func: Any) -> None:
        """Add a custom function to the environment."""
        self.env.globals[name] = func
    
    def add_filter(self, name: str, filter_func: Any) -> None:
        """Add a custom filter to the environment."""
        self.env.filters[name] = filter_func
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template by name."""
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template from string."""
        template = self.env.from_string(template_string)
        return template.render(**context)
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        return self.env.list_templates()
    
    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        try:
            self.env.get_template(template_name)
            return True
        except:
            return False


class TemplateRenderer:
    """High-level template renderer with context management."""
    
    def __init__(self, template_engine: Optional[TemplateEngine] = None, template_dir: Optional[str] = None):
        """Initialize the renderer."""
        if template_dir:
            self.engine = TemplateEngine(template_dir=template_dir)
        else:
            self.engine = template_engine or TemplateEngine()
        self.context = TemplateContext()
    
    def add_context(self, **kwargs) -> None:
        """Add variables to the rendering context."""
        for key, value in kwargs.items():
            self.context.add_variable(key, value)
    
    def add_function(self, name: str, func: Any) -> None:
        """Add a function to both context and engine."""
        self.context.add_function(name, func)
        self.engine.add_function(name, func)
    
    def add_filter(self, name: str, filter_func: Any) -> None:
        """Add a filter to both context and engine."""
        self.context.add_filter(name, filter_func)
        self.engine.add_filter(name, filter_func)
    
    def render(self, template_name: str, **extra_context) -> str:
        """Render a template with context."""
        full_context = {**self.context.to_dict(), **extra_context}
        return self.engine.render_template(template_name, full_context)
    
    def render_string(self, template_string: str, **extra_context) -> str:
        """Render a template string with context."""
        full_context = {**self.context.to_dict(), **extra_context}
        return self.engine.render_string(template_string, full_context)
    
    def clear_context(self) -> None:
        """Clear the rendering context."""
        self.context = TemplateContext()


class CodeGenerator:
    """Code generation utilities using Jinja2 templates."""
    
    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        """Initialize the code generator."""
        config = TemplateConfig()
        if template_dir:
            config.template_dirs = [str(template_dir)]
        
        self.renderer = TemplateRenderer(TemplateEngine(config))
        self._setup_code_generation_context()
    
    def _setup_code_generation_context(self) -> None:
        """Set up context specific for code generation."""
        import datetime
        
        self.renderer.add_context(
            timestamp=datetime.datetime.now().isoformat(),
            year=datetime.datetime.now().year,
            generator="QuickHooks",
        )
        
        # Add code-specific functions
        def generate_imports(modules: List[str], from_modules: Dict[str, List[str]] = None) -> str:
            """Generate import statements."""
            imports = []
            
            # Standard imports
            for module in modules:
                imports.append(f"import {module}")
            
            # From imports
            if from_modules:
                for module, items in from_modules.items():
                    imports.append(f"from {module} import {', '.join(items)}")
            
            return '\n'.join(imports)
        
        def generate_class_def(class_name: str, base_classes = None, 
                             docstring = None) -> str:
            """Generate class definition."""
            bases = f"({', '.join(base_classes)})" if base_classes else ""
            class_def = f"class {class_name}{bases}:"
            
            if docstring:
                class_def += f'\n    """{docstring}"""'
            
            return class_def
        
        def generate_method_def(method_name: str, args = None, 
                              return_type = None, docstring = None) -> str:
            """Generate method definition."""
            args_str = ', '.join(['self'] + (args or []))
            return_annotation = f" -> {return_type}" if return_type else ""
            
            method_def = f"def {method_name}({args_str}){return_annotation}:"
            
            if docstring:
                method_def += f'\n    """{docstring}"""'
            
            return method_def
        
        self.renderer.add_function('generate_imports', generate_imports)
        self.renderer.add_function('generate_class_def', generate_class_def)
        self.renderer.add_function('generate_method_def', generate_method_def)
    
    def generate_hook_class(self, hook_name: str, description: str = None, 
                          base_class: str = "BaseHook") -> str:
        """Generate a QuickHooks hook class."""
        template = """{{ generate_imports(['quickhooks.hooks.base', 'quickhooks.models']) }}

{{ generate_class_def(class_name, [base_class], description) }}
    name = {{ hook_name | quote }}
    description = {{ description | quote }}
    version = "1.0.0"
    
    {{ generate_method_def('process', ['hook_input: HookInput'], 'HookOutput', 'Process the hook input and return output.') }}
        # TODO: Implement hook logic here
        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Hook processed successfully"
        )
"""
        
        context = {
            'class_name': self._snake_to_pascal(hook_name),
            'hook_name': hook_name,
            'description': description or f"A QuickHook for {hook_name}",
            'base_class': base_class,
        }
        
        return self.renderer.render_string(template, **context)
    
    def generate_test_class(self, test_subject: str, test_type: str = "unit") -> str:
        """Generate a test class."""
        template = """import pytest
from quickhooks.models import HookInput, HookOutput, ExecutionContext
from {{ module_name }} import {{ class_name }}

class Test{{ class_name }}:
    \"\"\"Test suite for {{ class_name }}.\"\"\"
    
    def setup_method(self):
        \"\"\"Set up test fixtures.\"\"\"
        self.{{ instance_name }} = {{ class_name }}()
        self.context = ExecutionContext()
    
    def test_{{ method_name }}_success(self):
        \"\"\"Test successful {{ method_name }}.\"\"\"
        # Arrange
        hook_input = HookInput(
            tool_name="TestTool",
            tool_input={"test": "data"},
            context=self.context
        )
        
        # Act
        result = self.{{ instance_name }}.process(hook_input)
        
        # Assert
        assert isinstance(result, HookOutput)
        assert result.allowed is True
        assert result.tool_name == "TestTool"
    
    def test_{{ method_name }}_edge_case(self):
        \"\"\"Test {{ method_name }} edge case.\"\"\"
        # TODO: Implement edge case test
        pass
"""
        
        class_name = self._snake_to_pascal(test_subject)
        instance_name = test_subject.lower()
        module_name = f"hooks.{test_subject}"
        
        context = {
            'class_name': class_name,
            'instance_name': instance_name,
            'module_name': module_name,
            'method_name': test_subject.lower(),
        }
        
        return self.renderer.render_string(template, **context)
    
    def generate_config_class(self, config_name: str, fields: Dict[str, Dict[str, Any]]) -> str:
        """Generate a Pydantic configuration class."""
        template = """from pydantic import BaseModel, Field
from typing import Optional

class {{ class_name }}(BaseModel):
    \"\"\"Configuration for {{ config_name }}.\"\"\"
    
{% for field_name, field_config in fields.items() %}
    {{ field_name }}: {{ field_config.type }} = Field(
        default={{ field_config.default | repr }},
        description="{{ field_config.description }}"
    )
{% endfor %}
"""
        
        context = {
            'class_name': self._snake_to_pascal(config_name) + "Config",
            'config_name': config_name,
            'fields': fields,
        }
        
        return self.renderer.render_string(template, **context)
    
    def _snake_to_pascal(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))


# Convenience functions
def render_template(template_name: str, context: Dict[str, Any], 
                   template_dirs: List[str] = None) -> str:
    """Render a template with the given context."""
    config = TemplateConfig()
    if template_dirs:
        config.template_dirs = template_dirs
    
    engine = TemplateEngine(config)
    return engine.render_template(template_name, context)


def render_from_string(template_string: str, context: Dict[str, Any]) -> str:
    """Render a template string with the given context."""
    engine = TemplateEngine()
    return engine.render_string(template_string, context)


def load_templates(template_dir: Union[str, Path]) -> TemplateEngine:
    """Load templates from a directory."""
    config = TemplateConfig(template_dirs=[str(template_dir)])
    return TemplateEngine(config)