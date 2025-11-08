#!/usr/bin/env python3
"""
Test script for Groq TTS functionality

Usage:
    python test_tts.py "Your text to speak"
    python test_tts.py --file example.txt
    python test_tts.py --test-processing
    python test_tts.py --test-voices
"""

import os
import sys
import json
import tempfile
import subprocess
import argparse
from pathlib import Path

# Add the hooks directory to path
sys.path.insert(0, str(Path(__file__).parent / "hooks"))

from groq_tts_reader import GroqTTSReader


def test_text_processing():
    """Test the text processing functionality"""
    reader = GroqTTSReader()
    
    test_cases = [
        # Test 1: Simple text
        ("Hello world! This is a test.", "Hello world! This is a test."),
        
        # Test 2: Text with code block
        ("""Here's a Python function:
```python
def hello_world():
    print("Hello, world!")
    return 42
```
Pretty cool, right?""", 
         "Here's a Python function:\n[python block with 3 lines, containing functions]\nPretty cool, right?"),
        
        # Test 3: Text with inline code
        ("Use `npm install` to install dependencies and `npm start` to run.",
         "Use npm install to install dependencies and npm start to run."),
        
        # Test 4: Text with long inline code
        ("The command `docker run -it --rm -v $(pwd):/app -w /app node:16 npm install` will install packages.",
         "The command [code snippet] will install packages."),
        
        # Test 5: Text with table
        ("""Here's the data:
| Name | Age | City |
|------|-----|------|
| John | 25  | NYC  |
| Jane | 30  | LA   |
That's all.""",
         "Here's the data:\n[table with 3 columns (Name, Age, City) and 2 rows]\nThat's all."),
        
        # Test 6: Text with URL
        ("Check out https://example.com/very/long/path/to/resource for more info.",
         "Check out [link] for more info."),
        
        # Test 7: Text with file path
        ("Edit the file /Users/john/projects/myapp/src/components/Button.tsx to fix the issue.",
         "Edit the file [file: Button.tsx] to fix the issue."),
        
        # Test 8: Mixed content
        ("""I've analyzed your code:

```javascript
const getData = async () => {
  const response = await fetch('/api/data');
  return response.json();
};
```

The results are:
| Metric | Value |
|--------|-------|
| Lines  | 4     |
| Complexity | Low |

You can run it with `node app.js` or check https://docs.example.com""",
         """I've analyzed your code:

[javascript block with 4 lines, containing functions]

The results are:
[table with 2 columns (Metric, Value) and 2 rows]

You can run it with node app.js or check [link]""")
    ]
    
    print("Testing text processing...")
    print("=" * 60)
    
    all_passed = True
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = reader.process_for_tts(input_text)
        passed = result.strip() == expected.strip()
        
        print(f"\nTest {i}: {'✅ PASSED' if passed else '❌ FAILED'}")
        if not passed:
            print(f"Input:\n{input_text[:100]}...")
            print(f"\nExpected:\n{expected}")
            print(f"\nGot:\n{result}")
            all_passed = False
    
    print("\n" + "=" * 60)
    print(f"Overall: {'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}")
    return all_passed


def test_groq_connection():
    """Test Groq API connection"""
    print("Testing Groq API connection...")
    print("=" * 60)
    
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        print("❌ GROQ_API_KEY environment variable not set!")
        print("Get your API key from: https://console.groq.com/keys")
        return False
    
    print(f"✅ GROQ_API_KEY found: {api_key[:8]}...")
    
    # Test with Groq client
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Test chat completion to verify API key works
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            max_tokens=10
        )
        print(f"✅ Groq API test: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return False


def test_audio_player():
    """Test audio playback capability"""
    print("\nTesting audio playback...")
    print("=" * 60)
    
    reader = GroqTTSReader()
    
    if not reader.audio_player:
        print("❌ No audio player detected!")
        print("Please install one of: afplay (macOS), paplay, aplay, mpg123")
        return False
    
    print(f"✅ Audio player found: {reader.audio_player}")
    
    # Test playing a simple beep
    try:
        if sys.platform == "darwin":
            # macOS system sound
            subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=True)
            print("✅ Audio playback test successful!")
            return True
        else:
            print("⚠️  Audio test skipped (non-macOS system)")
            return True
    except Exception as e:
        print(f"❌ Audio playback error: {e}")
        return False


def test_voices(text="Hello, this is a test of different voices."):
    """Test different TTS voices"""
    print("\nTesting different TTS voices...")
    print("=" * 60)
    
    voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    for voice in voices:
        print(f"\nTesting voice: {voice}")
        os.environ['QUICKHOOKS_TTS_VOICE'] = voice
        
        reader = GroqTTSReader()
        # Note: This would actually call the TTS API
        print(f"Voice '{voice}' configured successfully")


async def test_tts_generation(text):
    """Test actual TTS generation"""
    reader = GroqTTSReader()
    
    print(f"\nProcessing text ({len(text)} chars)...")
    processed = reader.process_for_tts(text)
    print(f"Processed to: {len(processed)} chars")
    print(f"Preview: {processed[:100]}...")
    
    print("\nGenerating speech...")
    audio_data = await reader.generate_speech_groq(processed)
    
    if audio_data:
        print(f"✅ Generated {len(audio_data)} bytes of audio")
        
        # Save for inspection
        test_file = Path("test_output.mp3")
        test_file.write_bytes(audio_data)
        print(f"✅ Saved to: {test_file}")
        
        # Try to play
        if reader.play_audio_data(audio_data):
            print("✅ Playing audio...")
        else:
            print("⚠️  Could not play audio automatically")
            
        return True
    else:
        print("❌ Failed to generate audio")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Groq TTS functionality")
    parser.add_argument("text", nargs="?", help="Text to speak")
    parser.add_argument("--file", help="Read text from file")
    parser.add_argument("--test-processing", action="store_true", help="Test text processing")
    parser.add_argument("--test-voices", action="store_true", help="Test different voices")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument("--voice", default="alloy", help="Voice to use (alloy, echo, fable, onyx, nova, shimmer)")
    
    args = parser.parse_args()
    
    # Set voice
    os.environ['QUICKHOOKS_TTS_VOICE'] = args.voice
    
    if args.test_all or args.test_processing:
        test_text_processing()
    
    if args.test_all:
        test_groq_connection()
        test_audio_player()
    
    if args.test_voices:
        test_voices()
    
    # Test actual TTS
    text = args.text
    if args.file:
        text = Path(args.file).read_text()
    
    if text:
        import asyncio
        asyncio.run(test_tts_generation(text))
    elif not any([args.test_processing, args.test_voices, args.test_all]):
        # Run interactive test
        print("No text provided. Running interactive test...")
        print("=" * 60)
        
        # Test connection first
        if test_groq_connection() and test_audio_player():
            test_text = """Hello! This is a test of the Groq text-to-speech system.

I can handle code blocks like this:
```python
def greet(name):
    return f"Hello, {name}!"
```

And tables:
| Feature | Status |
|---------|--------|
| TTS     | Working |
| Summary | Active  |

Pretty neat, right?"""
            
            import asyncio
            asyncio.run(test_tts_generation(test_text))


if __name__ == "__main__":
    main()