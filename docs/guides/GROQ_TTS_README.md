# Groq PlayAI TTS Hook for Claude Code

## Overview

The Groq PlayAI TTS hook provides high-quality text-to-speech functionality using Groq's PlayAI TTS model. It intelligently processes Claude's responses before speaking them, making it perfect for hands-free operation or accessibility.

## Features

- 🎙️ **High-quality voices**: 50+ natural-sounding PlayAI voices
- 🧠 **Smart processing**: Summarizes code blocks and tables
- 💾 **Caching**: 24-hour cache to reduce API calls
- 🔇 **Selective reading**: Skips large outputs and respects quiet mode
- 🎵 **Background playback**: Non-blocking audio playback

## Quick Start

### 1. Get Groq API Key

1. Go to https://console.groq.com/keys
2. Create a new API key
3. Set it in your environment:
   ```bash
   export GROQ_API_KEY='gsk_your_api_key_here'
   ```

### 2. Install Dependencies

```bash
pip install groq
```

### 3. Test Voices

```bash
# Test different voices and features
python test_groq_playai_tts.py
```

### 4. Deploy

```bash
# Automatic deployment
python deploy_groq_tts.py

# Or manual deployment
cp hooks/groq_playai_tts_reader.py ~/.claude/hooks/
```

### 5. Configure

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# Enable TTS
export QUICKHOOKS_TTS_ENABLED=true

# Set your preferred voice (default: Samantha-PlayAI)
export QUICKHOOKS_TTS_VOICE='Emma-PlayAI'

# Required: Your Groq API key
export GROQ_API_KEY='gsk_your_api_key_here'
```

## Available Voices

### Recommended Voices

- **Samantha-PlayAI**: Clear American female (default)
- **Emma-PlayAI**: Natural female voice
- **Daniel-PlayAI**: British male voice
- **Olivia-PlayAI**: Friendly female voice
- **Michael-PlayAI**: Clear male voice

### All Available Voices

Run `python test_groq_playai_tts.py` to hear samples of all 50+ voices.

## Usage Examples

### What Gets Spoken

1. **Task completions**: Summary of work done
2. **Code explanations**: With code blocks summarized
3. **Error messages**: Cleaned for clarity
4. **Search results**: Key findings
5. **Command outputs**: Important results

### Example Transformations

#### Code Block
**Original:**
```python
def process_data(items):
    results = []
    for item in items:
        if validate(item):
            results.append(transform(item))
    return results
```

**Spoken as:** "[python code block with 6 lines containing a function]"

#### Table
**Original:**
| Test | Status | Time |
|------|--------|------|
| Unit | Passed | 0.5s |
| Int  | Failed | 2.1s |

**Spoken as:** "[table with columns Test, Status, Time and 2 rows]"

## Advanced Configuration

### Environment Variables

- `GROQ_API_KEY`: Your Groq API key (required)
- `QUICKHOOKS_TTS_ENABLED`: Enable/disable TTS (default: false)
- `QUICKHOOKS_TTS_VOICE`: Voice selection (default: Samantha-PlayAI)

### Customize Processing

Edit `~/.claude/hooks/groq_playai_tts_reader.py` to modify:
- Code summarization logic
- Table processing rules
- Maximum text length (default: 800 chars)
- Tools that trigger TTS

### Disable for Specific Commands

Add `quiet` or `no_tts` to tool inputs:
```json
{"command": "long-running-test", "quiet": true}
```

## Troubleshooting

### No Sound

1. Check API key is set:
   ```bash
   echo $GROQ_API_KEY
   ```

2. Check TTS is enabled:
   ```bash
   echo $QUICKHOOKS_TTS_ENABLED  # Should be "true"
   ```

3. Test Groq connection:
   ```bash
   python -c "from groq import Groq; print(Groq().models.list())"
   ```

### API Errors

- **Rate limits**: Groq has rate limits; caching helps reduce calls
- **Invalid voice**: Check voice name matches exactly (case-sensitive)
- **Network issues**: Ensure internet connection is stable

### Performance

- Audio generation typically takes 1-2 seconds
- Cached responses play instantly
- Background playback doesn't block Claude

## Cost Considerations

- Groq PlayAI TTS pricing: Check https://groq.com/pricing
- Caching reduces API calls significantly
- Average message ~200-400 characters after processing

## Comparison with Local TTS

| Feature | Groq PlayAI | Local (pyttsx3) |
|---------|-------------|-----------------|
| Voice Quality | Excellent | Good |
| Voice Selection | 50+ voices | System dependent |
| Internet Required | Yes | No |
| API Cost | Per character | Free |
| Latency | 1-2 seconds | Instant |
| Platform Support | All | Platform specific |

## Support

For issues or improvements:
1. Check this README
2. Run test script: `python test_groq_playai_tts.py`
3. Check hook logs in Claude Code output
4. Review API status at https://console.groq.com