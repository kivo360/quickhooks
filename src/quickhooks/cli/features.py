"""CLI commands for managing QuickHooks features."""

import typer
from rich.console import Console
from rich.table import Table

from quickhooks.features import features

console = Console()
app = typer.Typer(help="Manage QuickHooks features and optional dependencies")


@app.command()
def list() -> None:
    """List all available features and their installation status."""
    table = Table(title="QuickHooks Features")
    table.add_column("Feature", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Description", style="dim")
    
    feature_descriptions = {
        'ai': 'AI-powered search and recommendations using LanceDB',
        'search': 'Full-text search capabilities with Tantivy',
        'analytics': 'Advanced analytics with PyArrow, Polars, and DuckDB',
        'agents': 'Multi-LLM agent analysis (OpenAI, Groq, Anthropic)',
        'scaffold': 'AI-powered scaffolding and code generation',
        'web': 'Web dashboard and API with FastAPI and Streamlit',
        'cloud': 'Cloud storage and distributed execution',
        'enterprise': 'Enterprise security and authentication features',
        'performance': 'Performance optimization and caching',
        'dev': 'Development tools and testing utilities',
        'essential': 'Essential features (ai + search + dev)',
        'pro': 'Professional features (essential + analytics + scaffold + agents)',
        'enterprise-full': 'Full enterprise features (pro + web + cloud + enterprise + performance)',
        'all': 'All available features'
    }
    
    for feature, available in features.list_available().items():
        status = "✅ Available" if available else "❌ Missing"
        description = feature_descriptions.get(feature, "")
        table.add_row(feature, status, description)
    
    console.print(table)


@app.command()
def check(feature: str) -> None:
    """Check if a specific feature is available.
    
    Args:
        feature: Feature name to check
    """
    if features.has(feature):
        console.print(f"✅ Feature '{feature}' is available", style="green")
    else:
        console.print(f"❌ Feature '{feature}' is not available", style="red")
        missing_deps = features._get_missing_dependencies(feature)
        if missing_deps:
            console.print(f"Missing dependencies: {', '.join(missing_deps)}")
        console.print(f"Install with: pip install quickhooks[{feature}]")


@app.command()
def install_commands() -> None:
    """Show installation commands for missing features."""
    missing = features.list_missing()
    
    if not missing:
        console.print("✅ All features are available!", style="green")
        return
    
    console.print("Missing features and their installation commands:", style="bold")
    console.print()
    
    for feature in missing:
        console.print(f"Feature: {feature}")
        console.print(f"Command: pip install quickhooks[{feature}]", style="cyan")
        console.print()
    
    # Suggest combined installs
    if len(missing) > 1:
        console.print("Combined installations:", style="bold")
        
        # Check if essential covers most missing features
        essential_features = {'ai', 'search', 'dev'}
        if essential_features.intersection(set(missing)):
            console.print("Essential features: pip install quickhooks[essential]", style="yellow")
        
        # Check if pro covers most missing features
        pro_features = {'ai', 'search', 'dev', 'analytics', 'scaffold', 'agents'}
        if len(pro_features.intersection(set(missing))) >= 3:
            console.print("Professional features: pip install quickhooks[pro]", style="yellow")
        
        # Suggest all if many features are missing
        if len(missing) >= 5:
            console.print("All features: pip install quickhooks[all]", style="green")


@app.command()
def suggest(
    required: str = typer.Argument(..., help="Comma-separated list of required features")
) -> None:
    """Suggest the best installation group for required features.
    
    Args:
        required: Comma-separated feature names
    """
    required_features = [f.strip() for f in required.split(',')]
    
    # Validate feature names
    all_features = set(features.list_available().keys())
    invalid_features = [f for f in required_features if f not in all_features]
    
    if invalid_features:
        console.print(f"Invalid features: {', '.join(invalid_features)}", style="red")
        console.print(f"Available features: {', '.join(sorted(all_features))}")
        return
    
    suggestion = features.suggest_install_group(required_features)
    
    if suggestion:
        console.print(f"Suggested installation group: {suggestion}", style="green")
        console.print(f"Command: pip install quickhooks[{suggestion}]", style="cyan")
    else:
        individual_command = features.get_installation_command(required_features)
        console.print("No single group covers all required features.", style="yellow")
        console.print(f"Individual install: {individual_command}", style="cyan")


@app.command()
def diagnose() -> None:
    """Diagnose feature installation issues."""
    console.print("🔍 Diagnosing QuickHooks feature installation...", style="bold")
    console.print()
    
    all_features = features.list_available()
    available_count = sum(all_features.values())
    total_count = len(all_features)
    
    console.print(f"Features available: {available_count}/{total_count}")
    console.print()
    
    if available_count == total_count:
        console.print("✅ All features are working correctly!", style="green")
        return
    
    # Group missing features by category
    missing_by_category = {
        'Core AI': [],
        'Analytics': [],
        'Web/Cloud': [],
        'Enterprise': [],
        'Development': []
    }
    
    category_mapping = {
        'ai': 'Core AI',
        'search': 'Core AI', 
        'analytics': 'Analytics',
        'agents': 'Core AI',
        'scaffold': 'Development',
        'web': 'Web/Cloud',
        'cloud': 'Web/Cloud',
        'enterprise': 'Enterprise',
        'performance': 'Enterprise',
        'dev': 'Development'
    }
    
    for feature, available in all_features.items():
        if not available and feature in category_mapping:
            category = category_mapping[feature]
            missing_by_category[category].append(feature)
    
    # Show missing features by category
    for category, missing_features in missing_by_category.items():
        if missing_features:
            console.print(f"{category}:", style="bold red")
            for feature in missing_features:
                console.print(f"  ❌ {feature}")
            console.print()
    
    # Provide recommendations
    console.print("Recommendations:", style="bold yellow")
    
    if 'ai' in [f for features_list in missing_by_category.values() for f in features_list]:
        console.print("• For AI features: pip install quickhooks[ai]")
    
    if any(f in ['analytics'] for features_list in missing_by_category.values() for f in features_list):
        console.print("• For analytics: pip install quickhooks[analytics]")
    
    if len([f for features_list in missing_by_category.values() for f in features_list]) >= 3:
        console.print("• For most features: pip install quickhooks[pro]")
        console.print("• For everything: pip install quickhooks[all]")


@app.command()
def demo(feature: str) -> None:
    """Show a demo of what a feature provides (without actually using it).
    
    Args:
        feature: Feature name to demo
    """
    demos = {
        'ai': """
🧠 AI Features Demo:
• Semantic search: Find hooks by describing what you want to do
• Smart recommendations: Get AI-suggested hooks based on your needs  
• Vector embeddings: Hooks are indexed using sentence transformers
• LanceDB integration: Fast vector similarity search

Example commands:
  quickhooks search "validate user input"
  quickhooks recommend "security authentication" 
  quickhooks similar my-existing-hook
        """,
        
        'search': """
🔍 Full-Text Search Demo:
• Fast text search across all hook content
• Fuzzy matching and typo tolerance
• Combined vector + text search (hybrid)
• Advanced filtering by tags, complexity, etc.

Example commands:
  quickhooks search --text "file validation"
  quickhooks search --hybrid "security check" 
  quickhooks filter --complexity simple --type validator
        """,
        
        'analytics': """
📊 Analytics Features Demo:
• PyArrow-based columnar data processing
• Polars for fast data transformations
• DuckDB for SQL analytics on hook data
• Interactive dashboards and visualizations

Example commands:
  quickhooks analytics usage-report
  quickhooks analytics performance-metrics
  quickhooks analytics hook-trends --format plotly
        """,
        
        'web': """
🌐 Web Features Demo:
• FastAPI-based REST API for hook management
• Streamlit dashboard for visual hook exploration
• Real-time updates via WebSockets
• Hook marketplace integration

Example usage:
  quickhooks web start-api --port 8000
  quickhooks web dashboard --port 8501
  quickhooks web marketplace sync
        """,
        
        'scaffold': """
🏗️ Scaffolding Features Demo:
• AI-powered project scaffolding
• Smart template generation based on requirements
• Code formatting with Black and isort
• Cookiecutter integration for project templates

Example commands:
  quickhooks scaffold project --type "FastAPI microservice"
  quickhooks scaffold hook --description "validate API tokens"
  quickhooks scaffold config --format json
        """
    }
    
    demo_text = demos.get(feature)
    if demo_text:
        if features.has(feature):
            console.print(f"✅ {feature.title()} features are available!", style="green")
        else:
            console.print(f"❌ {feature.title()} features are not available", style="red")
            console.print(f"Install with: pip install quickhooks[{feature}]", style="cyan")
        
        console.print(demo_text, style="dim")
    else:
        console.print(f"No demo available for feature: {feature}", style="red")
        available_demos = list(demos.keys())
        console.print(f"Available demos: {', '.join(available_demos)}")


if __name__ == "__main__":
    app()