#!/usr/bin/env python3
"""
Automated TTS test - tests processing logic and generates sample output
"""

import sys
from pathlib import Path

# Add the hooks directory to path
sys.path.insert(0, str(Path(__file__).parent / "hooks"))

from groq_tts_reader import GroqTTSReader


def test_text_processing():
    """Test text processing for various content types"""
    reader = GroqTTSReader()
    
    test_cases = [
        {
            "name": "Simple text",
            "input": "Hello world! This is a test.",
            "expected_contains": ["Hello world", "test"]
        },
        {
            "name": "Code block",
            "input": """Here's a function:
```python
def hello():
    print("Hello")
    return 42
```
Done!""",
            "expected_contains": ["Here's a function", "[python block with 3 lines", "Done!"]
        },
        {
            "name": "Table",
            "input": """Results:
| Name | Score |
|------|-------|
| Alice | 95 |
| Bob | 87 |

Great job!""",
            "expected_contains": ["Results", "[table with 2 columns", "2 rows", "Great job!"]
        },
        {
            "name": "Mixed content",
            "input": """I analyzed `/Users/john/project/main.py`:

```javascript
const app = async () => {
  await fetch('/api/data');
  console.log('Done');
};
```

Performance:
| Metric | Value |
|--------|-------|
| Speed | 100ms |
| Memory | 50MB |

Run with `node app.js` or check https://docs.example.com/api""",
            "expected_contains": [
                "analyzed", 
                "[file:", 
                "[javascript block", 
                "Performance",
                "[table",
                "Run with node app.js",
                "[link]"
            ]
        }
    ]
    
    print("Testing TTS Text Processing")
    print("=" * 60)
    
    all_passed = True
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("-" * 40)
        
        processed = reader.process_for_tts(test['input'])
        print(f"Input:\n{test['input'][:100]}{'...' if len(test['input']) > 100 else ''}")
        print(f"\nProcessed:\n{processed}")
        
        # Check expected content
        passed = all(expected in processed for expected in test['expected_contains'])
        
        if passed:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
            print("Missing:")
            for expected in test['expected_contains']:
                if expected not in processed:
                    print(f"  - {expected}")
            all_passed = False
    
    print("\n" + "=" * 60)
    print(f"Overall: {'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}")
    return all_passed


def test_code_summarization():
    """Test code block summarization"""
    reader = GroqTTSReader()
    
    print("\n\nTesting Code Summarization")
    print("=" * 60)
    
    # Test Python code
    python_code = """def process_data(items):
    results = []
    for item in items:
        if item.is_valid():
            results.append(transform(item))
    return results"""
    
    summary = reader._summarize_code_block("python", python_code)
    print(f"Python code summary: {summary}")
    
    # Test JavaScript code
    js_code = """class DataProcessor {
  constructor() {
    this.data = [];
  }
  
  async process() {
    const response = await fetch('/api/data');
    return response.json();
  }
}"""
    
    summary = reader._summarize_code_block("javascript", js_code)
    print(f"JavaScript code summary: {summary}")
    
    # Test shell commands
    shell_code = """#!/bin/bash
echo "Starting deployment..."
docker build -t myapp .
docker push myapp:latest
kubectl apply -f deploy.yaml"""
    
    summary = reader._summarize_code_block("bash", shell_code)
    print(f"Shell code summary: {summary}")


def test_table_summarization():
    """Test table summarization"""
    reader = GroqTTSReader()
    
    print("\n\nTesting Table Summarization")
    print("=" * 60)
    
    # Simple table
    table1 = """| Name | Age | City |
|------|-----|------|
| John | 25  | NYC  |
| Jane | 30  | LA   |"""
    
    summary = reader._summarize_table(table1)
    print(f"Simple table: {summary}")
    
    # Larger table
    table2 = """| Test | Status | Time | Memory | CPU |
|------|--------|------|--------|-----|
| Unit | Passed | 0.5s | 12MB | 5% |
| Integration | Passed | 2.1s | 45MB | 15% |
| E2E | Failed | 10.3s | 120MB | 85% |
| Performance | Passed | 30.2s | 200MB | 95% |"""
    
    summary = reader._summarize_table(table2)
    print(f"Large table: {summary}")


def generate_sample_outputs():
    """Generate sample TTS outputs for different scenarios"""
    reader = GroqTTSReader()
    
    print("\n\nSample TTS Outputs")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "Code Review Response",
            "text": """I've reviewed your pull request. Here are my findings:

The main changes look good. I noticed you refactored the authentication logic:

```python
def authenticate(user, password):
    # Hash password
    hashed = hash_password(password)
    
    # Check against database
    db_user = User.query.filter_by(username=user).first()
    if db_user and db_user.password == hashed:
        return generate_token(db_user)
    
    return None
```

Performance metrics:
| Metric | Before | After |
|--------|--------|-------|
| Login time | 250ms | 180ms |
| Memory | 45MB | 42MB |

Overall, this is a solid improvement. The code is cleaner and performs better.

One suggestion: consider adding rate limiting to prevent brute force attacks. You can check the security docs at https://owasp.org/www-project-top-ten/ for best practices."""
        },
        {
            "name": "Error Explanation",
            "text": """The error you're encountering is due to a missing dependency. Here's what's happening:

```bash
$ npm start
Error: Cannot find module 'express'
```

This means Express.js isn't installed. To fix this:

1. Run `npm install express`
2. Check your `package.json` file at `/project/package.json`
3. Ensure all dependencies are listed

Common causes:
| Issue | Solution |
|-------|----------|
| Missing package.json | Run npm init |
| Outdated lock file | Delete node_modules and reinstall |
| Wrong Node version | Use nvm to switch versions |

After fixing, your app should start successfully."""
        }
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 40)
        processed = reader.process_for_tts(scenario['text'])
        print(f"TTS Output ({len(processed)} chars):\n{processed}")


def main():
    """Run all tests"""
    print("QuickHooks TTS Testing Suite")
    print("=" * 80)
    
    # Run tests
    test_text_processing()
    test_code_summarization()
    test_table_summarization()
    generate_sample_outputs()
    
    print("\n" + "=" * 80)
    print("Testing complete! Review the outputs above.")
    print("\nNext steps:")
    print("1. Set GROQ_API_KEY environment variable")
    print("2. Test actual Groq TTS API with: python test_tts.py 'Your text here'")
    print("3. Deploy hook with: quickhooks deploy all")


if __name__ == "__main__":
    main()