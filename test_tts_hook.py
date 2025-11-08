#!/usr/bin/env python3
"""
Test the Smart TTS Reader hook
"""

import json
import subprocess
import os
from pathlib import Path


def test_hook(hook_input):
    """Test the hook with given input"""
    hook_path = Path(__file__).parent / "hooks" / "smart_tts_reader.py"
    
    # Convert input to JSON
    input_json = json.dumps(hook_input)
    
    # Run the hook
    result = subprocess.run(
        ["python", str(hook_path)],
        input=input_json,
        capture_output=True,
        text=True
    )
    
    print(f"Input: {json.dumps(hook_input, indent=2)}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Errors: {result.stderr}")
    print("-" * 60)
    
    return json.loads(result.stdout) if result.stdout else None


def main():
    """Run tests"""
    print("Testing Smart TTS Reader Hook")
    print("=" * 60)
    
    # Enable TTS for testing
    os.environ['QUICKHOOKS_TTS_ENABLED'] = 'true'
    
    # Test 1: Simple response
    print("\nTest 1: Simple text response")
    test_hook({
        "tool_name": "Task",
        "tool_output": {
            "content": "I've completed the task successfully. The code has been updated."
        }
    })
    
    # Test 2: Response with code
    print("\nTest 2: Response with code block")
    test_hook({
        "tool_name": "Task",
        "tool_output": {
            "message": """I've created the function:
            
```python
def calculate_sum(a, b):
    return a + b
```

This function adds two numbers together."""
        }
    })
    
    # Test 3: Response with table
    print("\nTest 3: Response with table")
    test_hook({
        "tool_name": "WebSearch",
        "response": """Here are the search results:

| Site | Description | Relevance |
|------|-------------|-----------|
| Stack Overflow | Q&A site | High |
| GitHub | Code hosting | Medium |
| Docs | Official docs | High |

Found 3 relevant results."""
    })
    
    # Test 4: Skip large output tools
    print("\nTest 4: Skip Read tool (large output)")
    test_hook({
        "tool_name": "Read",
        "tool_output": {
            "content": "This is a very long file content that should not be read aloud..."
        }
    })
    
    # Test 5: Respect quiet mode
    print("\nTest 5: Quiet mode")
    test_hook({
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo 'test'",
            "quiet": True
        },
        "tool_output": {
            "content": "This should not be spoken due to quiet mode"
        }
    })
    
    # Test 6: Complex mixed content
    print("\nTest 6: Complex mixed content")
    test_hook({
        "tool_name": "Task",
        "message": """I've analyzed your code at `/Users/dev/project/main.py`:

```javascript
async function fetchData() {
    const response = await fetch('https://api.example.com/data');
    return response.json();
}
```

Performance metrics:
| Metric | Value |
|--------|-------|
| Speed | 250ms |
| Memory | 45MB |

Run with `node app.js` to test."""
    })
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("\nTo use in production:")
    print("1. Set QUICKHOOKS_TTS_ENABLED=true")
    print("2. Optional: Set QUICKHOOKS_TTS_VOICE_INDEX (e.g., 132 for Samantha)")
    print("3. Optional: Set QUICKHOOKS_TTS_RATE (default: 175)")
    print("4. Deploy with: quickhooks deploy all")


if __name__ == "__main__":
    main()