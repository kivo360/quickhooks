#!/usr/bin/env python3
"""
Groq PlayAI Text-to-Speech Hook for Claude Code

Uses Groq's playai-tts model for high-quality voice synthesis.
Intelligently processes Claude's responses before speaking them.
"""

import json
import os
import re
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional
import hashlib

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False


class GroqPlayAITTSReader:
    """Strategic TTS reader using Groq's PlayAI TTS"""
    
    # Available PlayAI voices (from API error message)
    VOICES = [
        "Aaliyah-PlayAI",
        "Adelaide-PlayAI",
        "Angelo-PlayAI",
        "Arista-PlayAI",
        "Atlas-PlayAI",
        "Basil-PlayAI",
        "Briggs-PlayAI",
        "Calum-PlayAI",
        "Celeste-PlayAI",
        "Cheyenne-PlayAI",
        "Chip-PlayAI",
        "Cillian-PlayAI",
        "Deedee-PlayAI",
        "Eleanor-PlayAI",
        "Fritz-PlayAI",
        "Gail-PlayAI",
        "Indigo-PlayAI",
        "Jennifer-PlayAI",
        "Judy-PlayAI",
        "Mamaw-PlayAI",
        "Mason-PlayAI",
        "Mikail-PlayAI",
        "Mitch-PlayAI",
        "Nia-PlayAI",
        "Quinn-PlayAI",
        "Ruby-PlayAI",
        "Thunder-PlayAI"
    ]
    
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.enabled = os.environ.get('QUICKHOOKS_TTS_ENABLED', 'false').lower() == 'true'
        self.voice = os.environ.get('QUICKHOOKS_TTS_VOICE', 'Aaliyah-PlayAI')
        self.cache_dir = Path.home() / '.quickhooks' / 'tts_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate voice
        if self.voice not in self.VOICES:
            print(f"Warning: Voice '{self.voice}' not found. Using Samantha-PlayAI", file=sys.stderr)
            self.voice = 'Samantha-PlayAI'
        
        self.client = None
        if HAS_GROQ and self.groq_api_key and self.enabled:
            self.client = Groq(api_key=self.groq_api_key)
        
        # Audio player detection
        self.audio_player = self._detect_audio_player()
        
        # Content patterns
        self.patterns = {
            'code_block': re.compile(r'```(?P<lang>\w*)\n?(?P<code>[\s\S]*?)```', re.MULTILINE),
            'inline_code': re.compile(r'`([^`]+)`'),
            'table': re.compile(r'(\|[^\n]+\|\n)+(\|[-:| ]+\|\n)(\|[^\n]+\|\n)+', re.MULTILINE),
            'url': re.compile(r'https?://[^\s\)]+'),
            'file_path': re.compile(r'(?:^|\s)(/[\w.-]+)+(?:/[\w.-]+)?(?:\.\w+)?'),
            'command': re.compile(r'^\$\s+(.+)$', re.MULTILINE)
        }
    
    def _detect_audio_player(self) -> Optional[str]:
        """Detect system audio player"""
        if sys.platform == "darwin":
            return "afplay"
        elif sys.platform.startswith("linux"):
            for player in ["paplay", "aplay", "play", "cvlc"]:
                try:
                    result = subprocess.run(["which", player], capture_output=True, text=True)
                    if result.returncode == 0:
                        return player
                except:
                    continue
        elif sys.platform == "win32":
            return "powershell"
        return None
    
    def process_for_tts(self, content: str) -> str:
        """Process content for optimal TTS"""
        if not content or len(content.strip()) < 10:
            return ""
        
        processed = content
        
        # Handle code blocks
        for match in self.patterns['code_block'].finditer(content):
            lang = match.group('lang') or 'code'
            code = match.group('code')
            lines = len(code.strip().split('\n'))
            
            # Detect what's in the code
            characteristics = []
            if lang.lower() in ['python', 'py']:
                if 'def ' in code:
                    func_count = code.count('def ')
                    characteristics.append(f"{func_count} function{'s' if func_count > 1 else ''}")
                if 'class ' in code:
                    class_count = code.count('class ')
                    characteristics.append(f"{class_count} class{'es' if class_count > 1 else ''}")
            elif lang.lower() in ['javascript', 'js', 'typescript', 'ts']:
                if 'function' in code or '=>' in code:
                    characteristics.append("functions")
                if 'class ' in code:
                    characteristics.append("classes")
            
            summary = f"{lang} code block with {lines} lines"
            if characteristics:
                summary += f", containing {', '.join(characteristics)}"
            
            processed = processed.replace(match.group(0), f"[{summary}]", 1)
        
        # Clean inline code
        processed = self.patterns['inline_code'].sub(r'\1', processed)
        
        # Summarize tables
        for match in self.patterns['table'].finditer(processed):
            table = match.group(0)
            lines = table.strip().split('\n')
            if len(lines) >= 3:
                headers = [h.strip() for h in lines[0].split('|') if h.strip()]
                rows = len([l for l in lines[2:] if l.strip()])
                summary = f"table with {len(headers)} columns"
                if len(headers) <= 3:
                    summary += f" ({', '.join(headers)})"
                summary += f" and {rows} rows"
                processed = processed.replace(table, f"[{summary}]", 1)
        
        # Simplify URLs
        processed = self.patterns['url'].sub('[link]', processed)
        
        # Simplify file paths
        def simplify_path(match):
            path = match.group(0).strip()
            filename = path.split('/')[-1]
            return f"file {filename}"
        processed = self.patterns['file_path'].sub(simplify_path, processed)
        
        # Clean commands
        processed = self.patterns['command'].sub(r'command: \1', processed)
        
        # Remove markdown formatting
        processed = re.sub(r'#{1,6}\s*', '', processed)  # Headers
        processed = processed.replace('**', '').replace('__', '')  # Bold
        processed = processed.replace('*', '').replace('_', '')  # Italic
        processed = processed.replace('>', '')  # Quotes
        processed = processed.replace('|', ' ')  # Table remnants
        
        # Normalize whitespace
        processed = re.sub(r'\n{3,}', '\n\n', processed)
        processed = re.sub(r' {2,}', ' ', processed)
        
        # Limit length (PlayAI has limits)
        max_length = 800  # Conservative limit for PlayAI
        if len(processed) > max_length:
            processed = processed[:max_length-20] + "... (message truncated)"
        
        return processed.strip()
    
    def generate_speech(self, text: str) -> Optional[Path]:
        """Generate speech using Groq PlayAI TTS"""
        if not self.client or not text:
            return None
        
        # Create cache key
        cache_key = hashlib.md5(f"{text}:{self.voice}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.wav"
        
        # Check cache (24 hour expiry)
        if cache_file.exists() and cache_file.stat().st_mtime > time.time() - 86400:
            return cache_file
        
        try:
            # Generate speech using Groq PlayAI TTS
            response = self.client.audio.speech.create(
                model="playai-tts",
                voice=self.voice,
                response_format="wav",
                input=text
            )
            
            # Save to cache file
            response.write_to_file(str(cache_file))
            return cache_file
            
        except Exception as e:
            print(f"TTS generation error: {e}", file=sys.stderr)
            return None
    
    def play_audio(self, audio_file: Path) -> bool:
        """Play audio file using system player"""
        if not self.audio_player or not audio_file.exists():
            return False
        
        try:
            if sys.platform == "win32" and self.audio_player == "powershell":
                cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync()"]
            else:
                cmd = [self.audio_player, str(audio_file)]
            
            # Play in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
            
        except Exception as e:
            print(f"Audio playback error: {e}", file=sys.stderr)
            return False
    
    def should_read(self, hook_input: Dict) -> bool:
        """Determine if content should be read"""
        if not self.enabled or not self.client:
            return False
        
        tool_name = hook_input.get('tool_name', '')
        
        # Skip tools with large outputs
        skip_tools = {'Read', 'Grep', 'LS', 'Glob', 'NotebookRead', 'MultiEdit'}
        if tool_name in skip_tools:
            return False
        
        # Check for quiet mode
        tool_input = hook_input.get('tool_input', {})
        if isinstance(tool_input, dict) and (tool_input.get('no_tts') or tool_input.get('quiet')):
            return False
        
        return True
    
    def extract_content(self, hook_input: Dict) -> Optional[str]:
        """Extract readable content from hook input"""
        # Try different locations where content might be
        content = None
        
        # Check for direct response
        if 'response' in hook_input:
            content = str(hook_input['response'])
        
        # Check tool output
        elif 'tool_output' in hook_input:
            output = hook_input['tool_output']
            if isinstance(output, dict):
                if 'content' in output:
                    content = str(output['content'])
                elif 'message' in output:
                    content = str(output['message'])
                elif 'text' in output:
                    content = str(output['text'])
                else:
                    content = json.dumps(output, indent=2)
            else:
                content = str(output)
        
        # Check for message
        elif 'message' in hook_input:
            content = str(hook_input['message'])
        
        return content
    
    def run(self, hook_input: Dict) -> Dict:
        """Main hook execution"""
        # Check if we should read
        if not self.should_read(hook_input):
            return {
                'allowed': True,
                'modified': False,
                'message': 'TTS disabled or skipped'
            }
        
        # Extract content
        content = self.extract_content(hook_input)
        if not content or len(content) < 20:
            return {
                'allowed': True,
                'modified': False,
                'message': 'No substantial content'
            }
        
        # Process for TTS
        processed = self.process_for_tts(content)
        if not processed:
            return {
                'allowed': True,
                'modified': False,
                'message': 'Content processed but nothing to speak'
            }
        
        # Generate speech
        audio_file = self.generate_speech(processed)
        if audio_file:
            # Play audio
            if self.play_audio(audio_file):
                return {
                    'allowed': True,
                    'modified': False,
                    'message': f'TTS: Playing {len(processed)} chars with {self.voice}'
                }
            else:
                return {
                    'allowed': True,
                    'modified': False,
                    'message': 'TTS: Generated but playback failed'
                }
        
        return {
            'allowed': True,
            'modified': False,
            'message': 'TTS: Generation failed'
        }


def main():
    """Hook entry point"""
    # Read input
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({
            'allowed': True,
            'modified': False,
            'error': 'Invalid JSON input'
        }))
        return
    
    # Check dependencies
    if not HAS_GROQ:
        print(json.dumps({
            'allowed': True,
            'modified': False,
            'message': 'Groq library not installed'
        }))
        return
    
    # Process with TTS reader
    reader = GroqPlayAITTSReader()
    result = reader.run(input_data)
    
    # Output result
    print(json.dumps(result))


if __name__ == '__main__':
    main()