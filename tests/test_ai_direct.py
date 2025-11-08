#!/usr/bin/env python3
"""Direct test of AI analysis without background processing"""

import os
import asyncio
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

class ConceptExtraction(BaseModel):
    """Extracted concepts from tool usage"""
    concepts: list[str] = Field(default_factory=list, description="Key concepts identified")
    importance_score: float = Field(0.0, ge=0.0, le=1.0, description="Importance of concepts")
    categories: list[str] = Field(default_factory=list, description="Concept categories")

async def test_direct_ai():
    """Test AI analysis directly"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("GROQ_API_KEY not set")
        return
    
    # Create concept extraction agent
    concept_agent = Agent(
        GroqModel('qwen/qwen3-32b', provider=GroqProvider(api_key=groq_api_key)),
        output_type=ConceptExtraction,
        system_prompt="""You are an expert at extracting key concepts from developer tool usage.
        
Analyze the tool usage and extract:
1. Key concepts being introduced or worked with
2. Importance score based on context and complexity
3. Categories (technical, business, architectural, etc.)

Focus on concepts that should be remembered for future development sessions."""
    )
    
    prompt = """
Tool: Edit
Command/Context: {"file_path": "/Users/kevinhill/Coding/Tooling/ClaudeCode/quickhooks/src/quickhooks/config.py", "old_string": "implement new architecture", "new_string": "refactor database design"}
Session: ai_test_session

Extract and analyze key concepts from this development activity.
"""
    
    try:
        print("Testing concept extraction...")
        result = await concept_agent.run(prompt)
        concept_data = result.data
        print(f"Concepts: {concept_data.concepts}")
        print(f"Importance: {concept_data.importance_score}")
        print(f"Categories: {concept_data.categories}")
        return True
    except Exception as e:
        print(f"AI analysis failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_ai())
    print(f"Test {'passed' if success else 'failed'}")