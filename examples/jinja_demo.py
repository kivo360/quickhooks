#!/usr/bin/env python3
"""Demo of QuickHooks Jinja2 utilities for code generation."""

from quickhooks.utils import CodeGenerator, TemplateRenderer, TemplateEngine


def demo_code_generation():
    """Demonstrate code generation capabilities."""
    print("=== QuickHooks Jinja2 Code Generation Demo ===\n")
    
    # Initialize the code generator
    generator = CodeGenerator()
    
    # Generate a hook class
    print("1. Generating a validation hook class:")
    print("-" * 50)
    
    hook_code = generator.generate_hook_class(
        hook_name="security_validator",
        description="Validates tool calls for security compliance",
        base_class="BaseHook"
    )
    print(hook_code)
    
    print("\n2. Generating a test class:")
    print("-" * 50)
    
    test_code = generator.generate_test_class(
        test_subject="security_validator",
        test_type="unit"
    )
    print(test_code)
    
    print("\n3. Generating a config class:")
    print("-" * 50)
    
    config_fields = {
        "max_file_size": {
            "type": "int",
            "default": 1000000,
            "description": "Maximum file size in bytes"
        },
        "allowed_extensions": {
            "type": "List[str]",
            "default": [".py", ".txt", ".md"],
            "description": "List of allowed file extensions"
        },
        "strict_mode": {
            "type": "bool", 
            "default": True,
            "description": "Enable strict validation mode"
        }
    }
    
    config_code = generator.generate_config_class(
        config_name="file_validator",
        fields=config_fields
    )
    print(config_code)


def demo_template_rendering():
    """Demonstrate template rendering from files."""
    print("\n=== Template File Rendering Demo ===\n")
    
    # Initialize template engine
    engine = TemplateEngine()
    renderer = TemplateRenderer(engine)
    
    # Set up context
    renderer.add_context(
        class_name="AuthenticationHook",
        hook_name="auth_validator",
        description="Validates user authentication tokens",
        version="1.2.0",
        hook_type="validator"
    )
    
    try:
        # Render hook class template
        print("4. Rendering hook class from template:")
        print("-" * 50)
        
        hook_from_template = renderer.render("hook_class.py.j2")
        print(hook_from_template)
        
        print("\n5. Rendering test from template:")
        print("-" * 50)
        
        # Add test-specific context
        test_context = {
            "module_path": "hooks.auth_validator",
            "test_tool_name": "AuthTool",
            "test_input": '{"token": "test_token"}',
            "tool_names": ["AuthTool", "LoginTool"]
        }
        
        test_from_template = renderer.render("test_hook.py.j2", **test_context)
        print(test_from_template)
        
    except Exception as e:
        print(f"Template rendering failed: {e}")
        print("Make sure template files exist in the templates/ directory")


def demo_custom_functions():
    """Demonstrate custom template functions and filters."""
    print("\n=== Custom Functions and Filters Demo ===\n")
    
    renderer = TemplateRenderer()
    
    # Add custom function
    def generate_uuid() -> str:
        import uuid
        return str(uuid.uuid4())
    
    def format_as_constant(text: str) -> str:
        return text.upper().replace(" ", "_")
    
    renderer.add_function("generate_uuid", generate_uuid)
    renderer.add_filter("constant", format_as_constant)
    
    # Template with custom functions
    template = """
# Generated class with UUID: {{ generate_uuid() }}

class {{ class_name }}:
    {{ constant_name | constant }} = "{{ constant_value }}"
    
    def __init__(self):
        self.id = "{{ generate_uuid() }}"
        self.name = "{{ class_name }}"
"""
    
    print("6. Using custom functions and filters:")
    print("-" * 50)
    
    result = renderer.render_string(template,
        class_name="DemoClass",
        constant_name="default value",
        constant_value="demo_value"
    )
    print(result)


def demo_built_in_helpers():
    """Demonstrate built-in helper functions."""
    print("\n=== Built-in Helpers Demo ===\n")
    
    renderer = TemplateRenderer()
    
    template = """
# String conversion helpers:
snake_case: user_profile -> camelCase: {{ snake_to_camel('user_profile') }}
snake_case: user_profile -> PascalCase: {{ snake_to_pascal('user_profile') }}
camelCase: userProfile -> snake_case: {{ camel_to_snake('userProfile') }}

# Pluralization helpers:
user -> {{ pluralize('user') }}
category -> {{ pluralize('category') }}
users -> {{ singularize('users') }}
categories -> {{ singularize('categories') }}

# Code formatting:
{{ 'def example():\n    return "hello"' | indent_code(8) }}

# String quoting:
{{ 'hello world' | quote('single') }}
{{ 'hello world' | quote('double') }}
"""
    
    print("7. Built-in helper functions:")
    print("-" * 50)
    
    result = renderer.render_string(template)
    print(result)


if __name__ == "__main__":
    demo_code_generation()
    demo_template_rendering()
    demo_custom_functions()
    demo_built_in_helpers()
    
    print("\n=== Demo Complete ===")
    print("Check out the generated code above!")
    print("Templates can be found in templates/ directory")
    print("Use these utilities in your QuickHooks development workflow!")