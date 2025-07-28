"""CLI command for agent analysis."""

import asyncio
import sys
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

from .analyzer import AgentAnalyzer
from .types import AgentAnalysisRequest


console = Console()
app = typer.Typer(name="agent-analysis", help="Analyze prompts for optimal agent usage")


@app.command("analyze")
def analyze_prompt(
    prompt: str = typer.Argument(..., help="The prompt to analyze for agent recommendations"),
    context_file: Optional[Path] = typer.Option(
        None, 
        "--context", 
        "-c", 
        help="Path to file containing additional context"
    ),
    context_text: Optional[str] = typer.Option(
        None,
        "--context-text",
        "-t", 
        help="Additional context as text"
    ),
    threshold: float = typer.Option(
        0.7, 
        "--threshold", 
        "-th",
        min=0.0, 
        max=1.0, 
        help="Minimum confidence threshold for recommendations"
    ),
    max_tokens: int = typer.Option(
        128000,
        "--max-tokens",
        "-m",
        help="Maximum context tokens to use"
    ),
    model: str = typer.Option(
        "qwen/qwen3-32b",
        "--model",
        help="Groq model to use for analysis"
    ),
    output_format: str = typer.Option(
        "rich",
        "--format",
        "-f",
        help="Output format: 'rich', 'json', or 'simple'"
    )
):
    """
    Analyze a prompt to determine which agents should be used and how.
    
    This command uses Groq with Pydantic AI to analyze your prompt and recommend
    the most appropriate AI agents based on the task requirements. It handles
    context length management automatically, chunking large contexts when needed.
    """
    try:
        # Load context if provided
        context = None
        if context_file:
            if not context_file.exists():
                console.print(f"[red]Error: Context file {context_file} not found[/red]")
                raise typer.Exit(1)
            context = context_file.read_text(encoding='utf-8')
        elif context_text:
            context = context_text
        
        # Create analysis request
        request = AgentAnalysisRequest(
            prompt=prompt,
            context=context,
            max_context_tokens=max_tokens,
            confidence_threshold=threshold
        )
        
        # Run analysis
        with console.status("Analyzing prompt with Groq and Pydantic AI..."):
            analyzer = AgentAnalyzer(model_name=model)
            response = analyzer.analyze_prompt_sync(request)
        
        # Display results
        if output_format == "json":
            import json
            console.print(json.dumps(response.model_dump(), indent=2))
        elif output_format == "simple":
            _display_simple_output(response)
        else:
            _display_rich_output(response, request)
            
    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("[yellow]Make sure GROQ_API_KEY environment variable is set[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Analysis Error: {e}[/red]")
        raise typer.Exit(1)


def _display_rich_output(response: "AgentAnalysisResponse", request: AgentAnalysisRequest):
    """Display analysis results in rich format."""
    
    # Header
    console.print(Panel.fit(
        "[bold blue]Agent Analysis Results[/bold blue]",
        border_style="blue"
    ))
    
    # Summary
    console.print(Panel(
        Markdown(response.analysis_summary),
        title="[bold green]Analysis Summary[/bold green]",
        border_style="green"
    ))
    
    # Recommendations table
    if response.recommendations:
        table = Table(title="Agent Recommendations", show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan", width=15)
        table.add_column("Confidence", justify="center", width=10)
        table.add_column("Priority", justify="center", width=8)
        table.add_column("Threshold Met", justify="center", width=12)
        table.add_column("Reasoning", width=50)
        
        for rec in sorted(response.recommendations, key=lambda x: x.priority):
            confidence_str = f"{rec.confidence:.2f}"
            confidence_color = "green" if rec.confidence >= request.confidence_threshold else "yellow"
            
            threshold_met = "✅" if rec.threshold_met else "❌"
            
            table.add_row(
                rec.agent_type.value,
                f"[{confidence_color}]{confidence_str}[/{confidence_color}]",
                str(rec.priority),
                threshold_met,
                rec.reasoning
            )
        
        console.print(table)
    
    # Top recommendation highlight
    if response.top_recommendation:
        top = response.top_recommendation
        console.print(Panel(
            f"[bold]{top.agent_type.value.upper()}[/bold] (Confidence: {top.confidence:.2f})\n\n{top.reasoning}",
            title="[bold yellow]Top Recommendation[/bold yellow]",
            border_style="yellow"
        ))
    
    # Context usage info
    if response.context_used:
        context_info = []
        total_chars = sum(len(chunk.content) for chunk in response.context_used)
        context_info.append(f"Context chunks used: {len(response.context_used)}")
        context_info.append(f"Total context characters: {total_chars:,}")
        context_info.append(f"Estimated tokens: {response.total_tokens_used:,}")
        
        for i, chunk in enumerate(response.context_used):
            context_info.append(f"  Chunk {i+1}: {chunk.chunk_type} ({chunk.token_count} tokens)")
        
        console.print(Panel(
            "\n".join(context_info),
            title="[bold blue]Context Usage[/bold blue]",
            border_style="blue"
        ))
    
    # Discovered agents
    if response.discovered_agents:
        table = Table(title="Discovered Local Agents", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green", width=20)
        table.add_column("Similarity", justify="center", width=10)
        table.add_column("Capabilities", width=30)
        table.add_column("Description", width=40)
        
        for agent in response.discovered_agents:
            similarity_str = f"{agent.similarity_score:.2f}"
            capabilities_str = ", ".join(agent.capabilities[:3])  # Show first 3
            if len(agent.capabilities) > 3:
                capabilities_str += "..."
            
            table.add_row(
                agent.name,
                f"[green]{similarity_str}[/green]",
                capabilities_str,
                agent.description[:50] + "..." if len(agent.description) > 50 else agent.description
            )
        
        console.print(table)
    
    # Claude Code prompt modification
    if response.claude_code_prompt_modification:
        console.print(Panel(
            response.claude_code_prompt_modification,
            title="[bold magenta]Modified Prompt for Claude Code[/bold magenta]",
            border_style="magenta"
        ))
    
    # Multiple agents note
    if response.multiple_agents_recommended:
        console.print(Panel(
            "[bold green]Multiple agents working together are recommended for this task![/bold green]",
            border_style="green"
        ))


def _display_simple_output(response: "AgentAnalysisResponse"):
    """Display analysis results in simple text format."""
    
    print("=== AGENT ANALYSIS RESULTS ===")
    print(f"Summary: {response.analysis_summary}")
    print()
    
    if response.top_recommendation:
        top = response.top_recommendation
        print(f"TOP RECOMMENDATION: {top.agent_type.value}")
        print(f"Confidence: {top.confidence:.2f}")
        print(f"Reasoning: {top.reasoning}")
        print()
    
    print("ALL RECOMMENDATIONS:")
    for rec in sorted(response.recommendations, key=lambda x: x.priority):
        status = "✓" if rec.threshold_met else "✗"
        print(f"{status} {rec.agent_type.value} (confidence: {rec.confidence:.2f}, priority: {rec.priority})")
        print(f"   {rec.reasoning}")
        print()
    
    if response.multiple_agents_recommended:
        print("NOTE: Multiple agents working together are recommended.")
    
    print(f"Tokens used: {response.total_tokens_used:,}")


if __name__ == "__main__":
    app()