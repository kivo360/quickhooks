#!/usr/bin/env python3
"""
Simple TTS test using pyttsx3 for local TTS (no API needed)

This helps test the text processing and audio playback before using Groq API.

Install: pip install pyttsx3
"""

import sys
import argparse
import re
from pathlib import Path

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False
    print("Warning: pyttsx3 not installed. Install with: pip install pyttsx3")


class SimpleTTSProcessor:
    """Simple TTS processor for testing"""
    
    def __init__(self):
        self.engine = None
        if HAS_PYTTSX3:
            self.engine = pyttsx3.init()
            # Configure voice settings
            self.engine.setProperty('rate', 175)    # Speed of speech
            self.engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
    
    def process_text(self, text):
        """Process text for TTS - same logic as main hook"""
        # Handle code blocks
        code_pattern = r'```[\w]*\n?([\s\S]*?)```'
        code_blocks = list(re.finditer(code_pattern, text))
        
        for i, match in enumerate(code_blocks):
            code = match.group(1)
            lines = len(code.strip().split('\n'))
            
            # Detect language from the fence
            lang_match = re.match(r'```(\w+)', match.group(0))
            lang = lang_match.group(1) if lang_match else "code"
            
            replacement = f"[{lang} code block with {lines} lines]"
            text = text.replace(match.group(0), replacement)
        
        # Handle inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Handle tables
        table_pattern = r'\|[^\n]+\|[\s\S]*?\n(?:\|[^\n]+\|(?:\n|$))+'
        tables = list(re.finditer(table_pattern, text, re.MULTILINE))
        
        for i, match in enumerate(tables):
            table_text = match.group(0)
            lines = table_text.strip().split('\n')
            if len(lines) >= 2:
                headers = [h.strip() for h in lines[0].split('|') if h.strip()]
                rows = len(lines) - 2
                replacement = f"[table with {len(headers)} columns and {rows} rows]"
                text = text.replace(table_text, replacement)
        
        # Clean up URLs
        text = re.sub(r'https?://[^\s]+', '[link]', text)
        
        # Clean up file paths
        text = re.sub(r'/[\w/.-]+\.\w+', '[file]', text)
        
        # Remove special markdown characters
        text = text.replace('#', '').replace('*', '').replace('_', '')
        text = text.replace('>', '').replace('|', ' ')
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def speak(self, text):
        """Speak the text using pyttsx3"""
        if not self.engine:
            print("TTS engine not available. Would have spoken:")
            print("-" * 40)
            print(text)
            print("-" * 40)
            return
        
        print("Speaking:")
        print("-" * 40)
        print(text)
        print("-" * 40)
        
        self.engine.say(text)
        self.engine.runAndWait()
    
    def list_voices(self):
        """List available voices"""
        if not self.engine:
            print("TTS engine not available")
            return
        
        voices = self.engine.getProperty('voices')
        print(f"Available voices ({len(voices)}):")
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name} - {voice.id}")
    
    def set_voice(self, voice_index):
        """Set voice by index"""
        if not self.engine:
            return
        
        voices = self.engine.getProperty('voices')
        if 0 <= voice_index < len(voices):
            self.engine.setProperty('voice', voices[voice_index].id)
            print(f"Set voice to: {voices[voice_index].name}")


def test_examples():
    """Test with various example texts"""
    examples = [
        # Simple text
        "Hello world! This is a test of the text to speech system.",
        
        # Text with code
        """Here's how to define a function in Python:
```python
def greet(name):
    print(f"Hello, {name}!")
    return True
```
Pretty simple, right?""",
        
        # Text with inline code
        "To install, run `npm install` and then `npm start` to begin.",
        
        # Text with table
        """Here are the results:
| Test | Result | Time |
|------|--------|------|
| Unit | Passed | 0.5s |
| Integration | Passed | 2.1s |
| E2E | Failed | 10.3s |

One test failed.""",
        
        # Mixed content
        """I've analyzed your code at `/Users/john/project/src/main.py`:

```python
def process_data(data):
    # Complex processing here
    results = []
    for item in data:
        results.append(transform(item))
    return results
```

Check the docs at https://example.com/api/docs for more info.

The performance metrics:
| Metric | Value |
|--------|-------|
| Speed | 95ms |
| Memory | 12MB |

Use `python main.py --optimize` to improve performance."""
    ]
    
    processor = SimpleTTSProcessor()
    
    for i, example in enumerate(examples, 1):
        print(f"\n{'='*60}")
        print(f"Example {i}:")
        print(f"{'='*60}")
        print("Original:")
        print(example)
        print("\nProcessed:")
        processed = processor.process_text(example)
        print(processed)
        
        input(f"\nPress Enter to speak example {i}...")
        processor.speak(processed)


def main():
    parser = argparse.ArgumentParser(description="Test TTS processing and playback")
    parser.add_argument("text", nargs="?", help="Text to speak")
    parser.add_argument("--file", help="Read text from file")
    parser.add_argument("--examples", action="store_true", help="Run example tests")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    parser.add_argument("--voice", type=int, help="Voice index to use")
    parser.add_argument("--rate", type=int, default=175, help="Speech rate (default: 175)")
    
    args = parser.parse_args()
    
    processor = SimpleTTSProcessor()
    
    if args.list_voices:
        processor.list_voices()
        return
    
    if args.voice is not None:
        processor.set_voice(args.voice)
    
    if args.rate and processor.engine:
        processor.engine.setProperty('rate', args.rate)
    
    if args.examples:
        test_examples()
        return
    
    # Process provided text
    text = args.text
    if args.file:
        text = Path(args.file).read_text()
    
    if text:
        processed = processor.process_text(text)
        print("Original text:")
        print("-" * 40)
        print(text)
        print("\nProcessed text:")
        print("-" * 40)
        print(processed)
        print("-" * 40)
        
        processor.speak(processed)
    else:
        print("No text provided. Use --help for options.")


if __name__ == "__main__":
    main()