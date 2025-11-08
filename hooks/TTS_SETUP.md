# Smart TTS Reader Hook Setup

## Overview

The Smart TTS Reader hook intelligently reads Claude Code's responses aloud, making it easier to multitask or consume information while working on other things. It:

- ✅ Summarizes code blocks instead of reading them verbatim
- ✅ Condenses tables to key information
- ✅ Cleans up technical content for natural speech
- ✅ Skips tools with large outputs (Read, Grep, etc.)
- ✅ Respects quiet mode settings

## Installation

### 1. Install Dependencies

```bash
# Install the text-to-speech library
pip install pyttsx3

# On macOS, this uses the built-in voices
# On Linux, you may need: sudo apt-get install espeak
# On Windows, it uses SAPI5
```

### 2. Deploy the Hook

The hook has already been deployed to:
- `/Users/kevinhill/.claude/hooks/smart_tts_reader.py`

And configured in Claude Code settings for these tools:
- Task
- WebSearch
- WebFetch
- Bash
- Edit
- Write

### 3. Enable TTS

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# Enable TTS for Claude Code
export QUICKHOOKS_TTS_ENABLED=true

# Optional: Set voice (macOS)
# List voices: python -c "import pyttsx3; e=pyttsx3.init(); print([(i,v.name) for i,v in enumerate(e.getProperty('voices'))])"
export QUICKHOOKS_TTS_VOICE_INDEX=132  # Samantha on macOS

# Optional: Adjust speech rate (default: 175)
export QUICKHOOKS_TTS_RATE=200  # Faster
# export QUICKHOOKS_TTS_RATE=150  # Slower
```

## Usage

Once enabled, Claude Code will automatically speak:

1. **Task completions** - Summaries of work done
2. **Web search results** - Key findings
3. **Code explanations** - With code blocks summarized
4. **Error messages** - Cleaned up for clarity
5. **Command outputs** - Important results

### Examples of What You'll Hear

#### Original Response:
```
I've updated your function:

```python
def process_data(items):
    results = []
    for item in items:
        if validate(item):
            results.append(transform(item))
    return results
```

The function now includes validation.
```

#### What TTS Says:
"I've updated your function: [python block with 6 lines containing a function]. The function now includes validation."

#### Table Example:
```
Results:
| Test | Status | Time |
|------|--------|------|
| Unit | Passed | 0.5s |
| Integration | Failed | 2.1s |
```

#### What TTS Says:
"Results: [table with columns Test, Status, Time and 2 rows]"

## Customization

### Disable for Specific Commands

Add `quiet` or `no_tts` to tool input:

```python
# In your code
{"command": "long-running-command", "quiet": true}
```

### Change Which Tools Trigger TTS

Edit `/Users/kevinhill/.claude/settings.json` and modify the `tools` array in the TTS hook configuration.

### Adjust Processing Rules

Edit `/Users/kevinhill/.claude/hooks/smart_tts_reader.py` to customize:
- Code summarization logic
- Table processing
- URL/path simplification
- Maximum text length

## Troubleshooting

### No Sound

1. Check TTS is enabled:
   ```bash
   echo $QUICKHOOKS_TTS_ENABLED  # Should print "true"
   ```

2. Test TTS directly:
   ```bash
   python -c "import pyttsx3; e=pyttsx3.init(); e.say('Testing'); e.runAndWait()"
   ```

### Wrong Voice

List available voices:
```bash
python test_tts_simple.py --list-voices
```

Then set the index of your preferred voice.

### Performance Issues

- TTS runs in a background thread, so it shouldn't block Claude Code
- If needed, reduce the speech rate or disable for certain tools

## Advanced: Groq TTS Integration

The repository includes `groq_tts_reader.py` for cloud-based TTS using Groq's API. To use:

1. Get API key from https://console.groq.com/keys
2. Set `export GROQ_API_KEY=your_key`
3. Replace `smart_tts_reader.py` with `groq_tts_reader.py` in settings

This provides more natural voices but requires internet connection and API calls.