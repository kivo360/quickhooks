#!/usr/bin/env python3
"""
Demo script for agent analysis functionality.

This script demonstrates how to use the QuickHooks agent analysis feature
to determine which AI agents should handle different types of prompts.

Usage:
    python examples/agent_analysis_demo.py

Requirements:
    - GROQ_API_KEY environment variable must be set
    - quickhooks must be installed with agent analysis dependencies
"""

import asyncio
import os

from quickhooks.agent_analysis import (
    AgentAnalysisRequest,
    AgentAnalyzer,
    AgentCapability,
)


async def demo_basic_analysis():
    """Demonstrate basic agent analysis."""
    print("🔍 Basic Agent Analysis Demo")
    print("=" * 50)

    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set")
        print("Please set your Groq API key: export GROQ_API_KEY=your_key_here")
        return

    try:
        # Initialize analyzer
        analyzer = AgentAnalyzer()

        # Test prompts for different agent types
        test_prompts = [
            {
                "prompt": "Write a Python function that calculates the Fibonacci sequence",
                "expected": [AgentCapability.CODING],
            },
            {
                "prompt": "Review this code for potential security vulnerabilities and performance issues",
                "expected": [AgentCapability.CODE_REVIEW, AgentCapability.ANALYSIS],
            },
            {
                "prompt": "Create unit tests for a user authentication system",
                "expected": [AgentCapability.TESTING, AgentCapability.CODING],
            },
            {
                "prompt": "Explain how this algorithm works and document the code",
                "expected": [AgentCapability.DOCUMENTATION, AgentCapability.ANALYSIS],
            },
            {
                "prompt": "Debug this error: 'NoneType' object has no attribute 'split'",
                "expected": [AgentCapability.DEBUGGING, AgentCapability.ANALYSIS],
            },
            {
                "prompt": "Research the best practices for implementing microservices in Python",
                "expected": [AgentCapability.RESEARCH, AgentCapability.PLANNING],
            },
        ]

        for i, test_case in enumerate(test_prompts, 1):
            print(f"\n📝 Test {i}: {test_case['prompt'][:50]}...")

            request = AgentAnalysisRequest(
                prompt=test_case["prompt"], confidence_threshold=0.6
            )

            # Analyze the prompt
            result = await analyzer.analyze_prompt(request)

            print(f"   💡 Analysis: {result.analysis_summary[:100]}...")

            # Show top recommendations
            qualified = result.qualified_recommendations
            if qualified:
                print("   🎯 Top Recommendations:")
                for rec in sorted(qualified, key=lambda x: x.priority)[:3]:
                    print(
                        f"      • {rec.agent_type.value} (confidence: {rec.confidence:.2f})"
                    )
            else:
                print("   ⚠️  No recommendations met the confidence threshold")

            # Check if expected agent types were recommended
            recommended_types = {rec.agent_type for rec in qualified}
            expected_types = set(test_case["expected"])

            if recommended_types & expected_types:
                print("   ✅ Expected agent types were recommended!")
            else:
                print("   🤔 Unexpected recommendations (this might be normal)")

            print(f"   📊 Tokens used: {result.total_tokens_used}")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")


async def demo_context_analysis():
    """Demonstrate analysis with context."""
    print("\n\n🔍 Context-Aware Analysis Demo")
    print("=" * 50)

    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set")
        return

    try:
        analyzer = AgentAnalyzer()

        # Simulated large context (like code from a file)
        large_context = (
            """
        # User Authentication System
        import hashlib
        import jwt
        from datetime import datetime, timedelta
        from fastapi import HTTPException, Depends
        from sqlalchemy.orm import Session
        from database import get_db
        from models import User

        class AuthService:
            def __init__(self, secret_key: str):
                self.secret_key = secret_key

            def hash_password(self, password: str) -> str:
                # Simple password hashing (not recommended for production)
                return hashlib.md5(password.encode()).hexdigest()

            def verify_password(self, password: str, hashed: str) -> bool:
                return self.hash_password(password) == hashed

            def create_token(self, user_id: int) -> str:
                payload = {
                    'user_id': user_id,
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }
                return jwt.encode(payload, self.secret_key, algorithm='HS256')

            def verify_token(self, token: str) -> dict:
                try:
                    payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
                    return payload
                except jwt.ExpiredSignatureError:
                    raise HTTPException(status_code=401, detail="Token expired")
                except jwt.InvalidTokenError:
                    raise HTTPException(status_code=401, detail="Invalid token")

        def authenticate_user(username: str, password: str, db: Session = Depends(get_db)):
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None

            auth_service = AuthService("super_secret_key")  # Hardcoded secret (bad practice)
            if auth_service.verify_password(password, user.password_hash):
                return user
            return None
        """
            * 5
        )  # Repeat to make it larger

        request = AgentAnalysisRequest(
            prompt="Analyze this authentication code for security vulnerabilities and suggest improvements",
            context=large_context,
            confidence_threshold=0.7,
            max_context_tokens=100000,  # Allow large context
        )

        print(f"📄 Context size: {len(large_context):,} characters")
        print("🔍 Analyzing with context...")

        result = await analyzer.analyze_prompt(request)

        print("\n💡 Analysis Summary:")
        print(f"   {result.analysis_summary}")

        print("\n🎯 Recommendations:")
        for rec in sorted(result.qualified_recommendations, key=lambda x: x.priority):
            print(f"   • {rec.agent_type.value} (confidence: {rec.confidence:.2f})")
            print(f"     Reasoning: {rec.reasoning}")

        print("\n📊 Context Usage:")
        print(f"   Chunks used: {len(result.context_used)}")
        print(f"   Total tokens: {result.total_tokens_used:,}")

        for i, chunk in enumerate(result.context_used):
            print(f"   Chunk {i + 1}: {chunk.chunk_type} ({chunk.token_count} tokens)")

        if result.multiple_agents_recommended:
            print("\n🤝 Multiple agents working together are recommended!")

    except Exception as e:
        print(f"❌ Error during context analysis: {e}")


async def demo_edge_cases():
    """Demonstrate edge cases and error handling."""
    print("\n\n🔍 Edge Cases Demo")
    print("=" * 50)

    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set")
        return

    try:
        analyzer = AgentAnalyzer()

        # Test with very short prompt
        print("📝 Testing very short prompt...")
        result = await analyzer.analyze_prompt(
            AgentAnalysisRequest(prompt="help", confidence_threshold=0.5)
        )
        print(f"   Result: {len(result.recommendations)} recommendations")

        # Test with very high threshold
        print("\n📝 Testing high confidence threshold...")
        result = await analyzer.analyze_prompt(
            AgentAnalysisRequest(
                prompt="Write a simple hello world program", confidence_threshold=0.95
            )
        )
        qualified = result.qualified_recommendations
        print(f"   Qualified recommendations: {len(qualified)}")
        if not qualified:
            print("   ⚠️  No recommendations met the high threshold (expected)")

        # Test with very long prompt
        print("\n📝 Testing very long prompt...")
        long_prompt = "Please help me " * 1000  # Very repetitive long prompt
        result = await analyzer.analyze_prompt(
            AgentAnalysisRequest(prompt=long_prompt, confidence_threshold=0.6)
        )
        print(f"   Processed prompt of {len(long_prompt)} characters")
        print(f"   Tokens used: {result.total_tokens_used}")

    except Exception as e:
        print(f"❌ Error during edge case testing: {e}")


async def main():
    """Run all demos."""
    print("🚀 QuickHooks Agent Analysis Demo")
    print("This demo shows how to analyze prompts for optimal AI agent selection")
    print()

    await demo_basic_analysis()
    await demo_context_analysis()
    await demo_edge_cases()

    print("\n" + "=" * 50)
    print("✅ Demo completed!")
    print("\nTry the CLI command:")
    print("  quickhooks agents analyze 'Write a Python function to sort a list'")
    print("  quickhooks agents analyze --help")


if __name__ == "__main__":
    asyncio.run(main())
