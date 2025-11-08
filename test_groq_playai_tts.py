#!/usr/bin/env python3
"""
Test Groq PlayAI TTS voices and functionality
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hooks.groq_playai_tts_reader import GroqPlayAITTSReader

def test_voice_samples():
    """Test different PlayAI voices with sample text"""
    
    # Sample texts for different contexts
    samples = {
        "code_analysis": "I've analyzed your code and found three issues. The main function has a memory leak on line 42, and the API endpoint needs authentication. Would you like me to fix these problems?",
        
        "code_summary": "I've created a new function called process_data. [python code block with 15 lines containing 2 functions and a class]. The implementation includes error handling and validation.",
        
        "task_complete": "Task completed successfully. I've updated the configuration file, fixed the type errors, and added comprehensive tests. All tests are passing.",
        
        "error_message": "Error encountered: The build failed due to a missing dependency. Running npm install should resolve this issue.",
        
        "table_summary": "Here are the test results: [table with columns Test, Status, Time and 5 rows]. Three tests passed, two failed."
    }
    
    # Initialize reader
    reader = GroqPlayAITTSReader()
    
    if not reader.groq_api_key:
        print("❌ Error: GROQ_API_KEY not set in environment")
        print("Please set: export GROQ_API_KEY=your_api_key")
        return
    
    if not reader.client:
        print("❌ Error: Could not initialize Groq client")
        return
    
    print("🎙️  GROQ PLAYAI TTS VOICE TESTER")
    print("=" * 80)
    print(f"Current voice: {reader.voice}")
    print(f"Audio player: {reader.audio_player}")
    print()
    
    # Test current voice with different samples
    print("📝 Testing different content types with current voice:")
    print("-" * 60)
    
    for content_type, text in samples.items():
        print(f"\n{content_type.upper()}:")
        print(f"Text: {text[:60]}...")
        
        # Process text
        processed = reader.process_for_tts(text)
        print(f"Processed: {processed[:60]}...")
        
        # Generate and play
        audio_file = reader.generate_speech(processed)
        if audio_file:
            print(f"✅ Generated: {audio_file.name}")
            if reader.play_audio(audio_file):
                print("🔊 Playing...")
                time.sleep(3)  # Give time to listen
            else:
                print("❌ Playback failed")
        else:
            print("❌ Generation failed")
    
    # Test different voices
    print("\n\n🎭 TESTING DIFFERENT VOICES:")
    print("-" * 60)
    
    # Recommended voices to test (actual available voices)
    test_voices = [
        ("Aaliyah-PlayAI", "Soprano female voice"),
        ("Adelaide-PlayAI", "Warm female voice"),
        ("Angelo-PlayAI", "Strong male voice"),
        ("Basil-PlayAI", "British male voice"),
        ("Fritz-PlayAI", "Clear male voice"),
        ("Gail-PlayAI", "Professional female voice"),
        ("Thunder-PlayAI", "Deep male voice"),
        ("Quinn-PlayAI", "Neutral voice")
    ]
    
    test_text = samples["code_analysis"]
    
    for voice_name, description in test_voices:
        print(f"\n🎤 {voice_name}")
        print(f"   {description}")
        
        # Temporarily change voice
        reader.voice = voice_name
        
        # Generate and play
        audio_file = reader.generate_speech(test_text)
        if audio_file:
            print(f"✅ Generated audio")
            if reader.play_audio(audio_file):
                print("🔊 Playing... (listen for quality)")
                time.sleep(4)  # Give time to listen
            else:
                print("❌ Playback failed")
        else:
            print("❌ Generation failed")
        
        print("   Press Enter for next voice or 's' to select this voice...")
        try:
            choice = input().strip().lower()
            if choice == 's':
                print(f"\n✨ Selected: {voice_name}")
                print(f"To use this voice, set:")
                print(f"export QUICKHOOKS_TTS_VOICE='{voice_name}'")
                return voice_name
        except:
            pass


def test_hook_integration():
    """Test the hook with simulated Claude Code output"""
    
    print("\n\n🔧 TESTING HOOK INTEGRATION:")
    print("-" * 60)
    
    # Simulate different tool outputs
    test_cases = [
        {
            "name": "Task completion",
            "input": {
                "tool_name": "Task",
                "tool_output": {
                    "message": "I've successfully refactored the authentication module. The code is now more modular with separate concerns for validation and token generation."
                }
            }
        },
        {
            "name": "Code with explanation",
            "input": {
                "tool_name": "Write",
                "response": """I've created a new utility function:

```python
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

This function uses regex to validate email addresses."""
            }
        },
        {
            "name": "Web search results",
            "input": {
                "tool_name": "WebSearch",
                "tool_output": {
                    "content": "Found 3 relevant results about Python async programming. The official documentation recommends using asyncio for concurrent operations. FastAPI provides excellent async support out of the box."
                }
            }
        }
    ]
    
    reader = GroqPlayAITTSReader()
    
    for test in test_cases:
        print(f"\n📋 {test['name']}:")
        
        # Run the hook
        result = reader.run(test['input'])
        print(f"Result: {result}")
        
        if result.get('message', '').startswith('TTS: Playing'):
            print("✅ Hook executed successfully")
            time.sleep(3)
        else:
            print("❌ Hook did not play audio")


def interactive_test():
    """Interactive testing mode"""
    
    print("\n\n💬 INTERACTIVE TEST MODE:")
    print("-" * 60)
    print("Type any text to hear it spoken (or 'quit' to exit)")
    print("Use 'voice:Name-PlayAI' to change voice")
    print()
    
    reader = GroqPlayAITTSReader()
    
    while True:
        try:
            text = input("> ").strip()
            
            if text.lower() == 'quit':
                break
            
            if text.startswith('voice:'):
                new_voice = text[6:].strip()
                if new_voice in reader.VOICES:
                    reader.voice = new_voice
                    print(f"✅ Changed voice to: {new_voice}")
                else:
                    print(f"❌ Unknown voice: {new_voice}")
                continue
            
            if not text:
                continue
            
            # Process and speak
            processed = reader.process_for_tts(text)
            print(f"Processed: {processed}")
            
            audio_file = reader.generate_speech(processed)
            if audio_file and reader.play_audio(audio_file):
                print("🔊 Playing...")
            else:
                print("❌ Failed to generate/play audio")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye!")


def main():
    print("🚀 GROQ PLAYAI TTS TESTER")
    print("=" * 80)
    
    # Check for API key
    if not os.environ.get('GROQ_API_KEY'):
        print("❌ GROQ_API_KEY not found in environment")
        print("\nTo use Groq PlayAI TTS:")
        print("1. Get an API key from https://console.groq.com/keys")
        print("2. Set it: export GROQ_API_KEY='your-api-key-here'")
        print("3. Run this script again")
        return
    
    # Check for Groq library
    try:
        import groq
        print("✅ Groq library installed")
    except ImportError:
        print("❌ Groq library not installed")
        print("Install with: pip install groq")
        return
    
    print("\nSelect test mode:")
    print("1. Test voice samples (recommended)")
    print("2. Test hook integration")
    print("3. Interactive mode")
    print("4. All tests")
    
    try:
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == '1' or choice == '4':
            selected_voice = test_voice_samples()
            if selected_voice:
                print(f"\n\n🎉 Voice selection complete: {selected_voice}")
        
        if choice == '2' or choice == '4':
            test_hook_integration()
        
        if choice == '3':
            interactive_test()
        
    except KeyboardInterrupt:
        print("\n\nTest cancelled")
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n\n📝 NEXT STEPS:")
    print("-" * 60)
    print("1. Set your preferred voice:")
    print("   export QUICKHOOKS_TTS_VOICE='Samantha-PlayAI'")
    print("\n2. Enable TTS:")
    print("   export QUICKHOOKS_TTS_ENABLED=true")
    print("\n3. Deploy the hook:")
    print("   cp hooks/groq_playai_tts_reader.py ~/.claude/hooks/")
    print("\n4. Update Claude settings to use groq_playai_tts_reader.py")


if __name__ == "__main__":
    main()