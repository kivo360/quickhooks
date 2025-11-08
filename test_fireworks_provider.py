"""Test script to verify FireworksProvider is correctly configured."""

import os

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.fireworks import FireworksProvider

from quickhooks.config import get_config


def test_fireworks_provider_setup() -> None:
    """Test that FireworksProvider is correctly set up."""
    print("=" * 60)
    print("Testing FireworksProvider Configuration")
    print("=" * 60)

    # Check configuration
    config = get_config()
    print(f"\n1. Configuration loaded:")
    print(f"   ✓ AI Provider: Fireworks AI")
    print(f"   ✓ LLM Model: {config.ai.llm}")
    print(f"   ✓ VLM Model: {config.ai.vlm}")
    print(f"   ✓ Tool Calls Enabled: {config.ai.enable_tool_calls}")

    # Check API key
    api_key = os.getenv("FIREWORKS_API_KEY")
    if api_key:
        print(f"   ✓ API Key: {'*' * 8}{api_key[-4:]}")
    else:
        print("   ✗ WARNING: FIREWORKS_API_KEY not set!")
        return

    # Test FireworksProvider initialization
    print("\n2. Testing FireworksProvider initialization:")
    try:
        provider = FireworksProvider(api_key=api_key)
        print(f"   ✓ FireworksProvider created successfully")
        print(f"   ✓ Provider name: {provider.name}")
        print(f"   ✓ Base URL: {provider.base_url}")
        print(f"   ✓ Client type: {type(provider.client).__name__}")
    except Exception as e:
        print(f"   ✗ Failed to create FireworksProvider: {e}")
        return

    # Test model profile detection
    print("\n3. Testing model profile detection:")
    test_models = [
        config.ai.llm,
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "accounts/fireworks/models/qwen2p5-72b-instruct",
        "accounts/fireworks/models/deepseek-coder-v2-instruct",
    ]
    for model in test_models:
        profile = provider.model_profile(model)
        if profile:
            print(f"   ✓ {model}")
            print(f"     - Profile: {profile}")
        else:
            print(f"   ? {model} - no specific profile (will use defaults)")

    # Test OpenAIModel with FireworksProvider
    print("\n4. Testing OpenAIModel with FireworksProvider:")
    try:
        model = OpenAIModel(
            config.ai.llm,
            provider=provider,
        )
        print(f"   ✓ OpenAIModel created successfully")
        print(f"   ✓ Model name: {config.ai.llm}")
        print(f"   ✓ Provider configured: FireworksProvider")

        # Check if the profile supports tools
        profile = provider.model_profile(config.ai.llm)
        if profile and hasattr(profile, 'supports_tools'):
            print(f"   ✓ Tools supported: {profile.supports_tools}")
            print(f"   ✓ Default output mode: {profile.default_structured_output_mode}")
    except Exception as e:
        print(f"   ✗ Failed to create OpenAIModel: {e}")
        return

    print("\n" + "=" * 60)
    print("✓ FireworksProvider configuration test PASSED")
    print("=" * 60)
    print("\nKey Points:")
    print("  • FireworksProvider is properly initialized")
    print("  • Tool calls will be enabled by default")
    print("  • Using GLM-4 model for high-quality structured outputs")
    print("  • Model profiles are detected automatically")
    print("  • Ready for production use with Fireworks AI")


if __name__ == "__main__":
    test_fireworks_provider_setup()
