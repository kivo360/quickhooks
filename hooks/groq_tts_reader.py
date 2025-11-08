#!/usr/bin/env python3
"""
Groq Text-to-Speech Hook for Claude Code

This hook intelligently processes Claude's responses and reads them aloud using Groq's TTS.
It summarizes code blocks and tables for better audio experience.
"""

import json
import os
import re
import sys
import subprocess
import tempfile
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
import hashlib
import time

# Try imports
try:
    import httpx
except ImportError:
    httpx = None

try:
    from groq import Groq
except ImportError:
    Groq = None


class GroqTTSReader:
    """Strategic TTS reader using Groq's API"""
    
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.enable_tts = os.environ.get('QUICKHOOKS_TTS_ENABLED', 'true').lower() == 'true'
        self.tts_voice = os.environ.get('QUICKHOOKS_TTS_VOICE', 'alloy')  # OpenAI-compatible voices
        self.cache_dir = Path.home() / '.quickhooks' / 'tts_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio settings
        self.max_text_length = 4000  # Groq TTS limit
        self.audio_player = self._detect_audio_player()
        
        # Content patterns
        self.patterns = {
            'code_block': re.compile(r'```(?P<lang>\w*)\n(?P<code>[\s\S]*?)```', re.MULTILINE),
            'inline_code': re.compile(r'`([^`]+)`'),
            'table': re.compile(r'(\|[^\n]+\|\n)+(\|[-:| ]+\|\n)(\|[^\n]+\|\n)+', re.MULTILINE),
            'url': re.compile(r'https?://[^\s\)]+'),
            'file_path': re.compile(r'(?:^|\s)(?:/[\w.-]+)+(?:/[\w.-]+)?(?:\.\w+)?'),
            'command': re.compile(r'^\$\s+(.+)$', re.MULTILINE),
            'number_list': re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE),
            'bullet_list': re.compile(r'^[-*]\s+(.+)$', re.MULTILINE)
        }
    
    def _detect_audio_player(self) -> Optional[str]:
        """Detect system audio player"""
        if sys.platform == "darwin":
            return "afplay"
        elif sys.platform.startswith("linux"):
            for player in ["paplay", "aplay", "mpg123", "play", "cvlc"]:
                try:
                    result = subprocess.run(["which", player], capture_output=True, text=True)
                    if result.returncode == 0:
                        return player
                except:
                    continue
        elif sys.platform == "win32":
            # Windows can use PowerShell
            return "powershell"
        return None
    
    def _clean_for_speech(self, text: str) -> str:
        """Clean text for better speech synthesis"""
        # Replace URLs with "link"
        text = self.patterns['url'].sub('[link]', text)
        
        # Simplify file paths
        def simplify_path(match):
            path = match.group(0).strip()
            parts = path.split('/')
            if len(parts) > 3:
                return f"[file: {parts[-1]}]"
            return f"[file: {path}]"
        
        text = self.patterns['file_path'].sub(simplify_path, text)
        
        # Handle commands
        text = self.patterns['command'].sub(r'Command: \1', text)
        
        # Clean up special characters
        text = text.replace('```', '').replace('`', '')
        text = text.replace('|', ' ').replace('#', '')
        text = text.replace('*', '').replace('_', '')
        text = text.replace('>', ' ')
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _summarize_code_block(self, lang: str, code: str) -> str:
        """Create spoken summary of code block"""
        lines = code.strip().split('\n')
        line_count = len(lines)
        
        # Detect code characteristics
        characteristics = []
        
        # Language-specific detection
        if lang.lower() in ['python', 'py']:
            if any('def ' in line for line in lines):
                func_count = sum(1 for line in lines if line.strip().startswith('def '))
                characteristics.append(f"{func_count} function{'s' if func_count > 1 else ''}")
            if any('class ' in line for line in lines):
                class_count = sum(1 for line in lines if line.strip().startswith('class '))
                characteristics.append(f"{class_count} class{'es' if class_count > 1 else ''}")
            if any('import ' in line or 'from ' in line for line in lines):
                characteristics.append("imports")
                
        elif lang.lower() in ['javascript', 'js', 'typescript', 'ts']:
            if any('function ' in line or '=>' in line for line in lines):
                characteristics.append("functions")
            if any('class ' in line for line in lines):
                characteristics.append("classes")
            if any('import ' in line or 'require(' in line for line in lines):
                characteristics.append("imports")
                
        elif lang.lower() in ['bash', 'sh', 'shell']:
            characteristics.append("shell commands")
            
        # Build summary
        summary = f"{lang or 'code'} block with {line_count} lines"
        if characteristics:
            summary += f", containing {', '.join(characteristics)}"
            
        return f"[{summary}]"
    
    def _summarize_table(self, table_text: str) -> str:
        """Create spoken summary of table"""
        lines = table_text.strip().split('\n')
        if len(lines) < 3:  # Need at least header, separator, and one row
            return "[small table]"
        
        # Extract headers
        headers = [h.strip() for h in lines[0].split('|') if h.strip()]
        data_rows = len([l for l in lines[2:] if l.strip()])  # Skip header and separator
        
        summary = f"table with {len(headers)} columns"
        if headers and len(headers) <= 3:
            summary += f" ({', '.join(headers)})"
        summary += f" and {data_rows} rows"
        
        return f"[{summary}]"
    
    def process_for_tts(self, content: str) -> str:
        """Process content for optimal TTS"""
        if not content or len(content.strip()) < 10:
            return ""
        
        processed = content
        
        # Handle code blocks
        for match in self.patterns['code_block'].finditer(content):
            lang = match.group('lang')
            code = match.group('code')
            summary = self._summarize_code_block(lang, code)
            processed = processed.replace(match.group(0), summary, 1)
        
        # Handle inline code (only long ones)
        for match in self.patterns['inline_code'].finditer(processed):
            code = match.group(1)
            if len(code) > 30:
                processed = processed.replace(f"`{code}`", "[code snippet]", 1)
        
        # Handle tables
        for match in self.patterns['table'].finditer(processed):
            table = match.group(0)
            summary = self._summarize_table(table)
            processed = processed.replace(table, summary, 1)
        
        # Clean for speech
        processed = self._clean_for_speech(processed)
        
        # Truncate if too long
        if len(processed) > self.max_text_length:
            processed = processed[:self.max_text_length-20] + "... [truncated]"
        
        return processed
    
    async def generate_speech_groq(self, text: str) -> Optional[bytes]:
        """Generate speech using Groq API"""
        if not self.groq_api_key or not httpx:
            return None
        
        # Create cache key
        cache_key = hashlib.md5(f"{text}:{self.tts_voice}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.mp3"
        
        # Check cache
        if cache_file.exists() and cache_file.stat().st_mtime > time.time() - 86400:  # 24h cache
            return cache_file.read_bytes()
        
        try:
            # Note: Groq's TTS API endpoint might differ - this is based on OpenAI's format
            # You may need to adjust based on Groq's actual TTS API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1",  # or Groq's TTS model name
                        "input": text,
                        "voice": self.tts_voice,
                        "response_format": "mp3",
                        "speed": 1.0
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    audio_data = response.content
                    # Cache the result
                    cache_file.write_bytes(audio_data)
                    return audio_data
                else:
                    print(f"TTS API error: {response.status_code}", file=sys.stderr)
                    
        except Exception as e:
            print(f"TTS generation error: {e}", file=sys.stderr)
        
        return None
    
    def play_audio_data(self, audio_data: bytes) -> bool:
        """Play audio data using system player"""
        if not self.audio_player or not audio_data:
            return False
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            # Play audio based on platform
            if sys.platform == "win32" and self.audio_player == "powershell":
                cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{tmp_path}').PlaySync()"]
            else:
                cmd = [self.audio_player, tmp_path]
            
            # Run in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Clean up after a delay (give time to play)
            def cleanup():
                time.sleep(30)  # Adjust based on typical audio length
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
            import threading
            threading.Thread(target=cleanup, daemon=True).start()
            
            return True
            
        except Exception as e:
            print(f"Audio playback error: {e}", file=sys.stderr)
            return False
    
    def should_read_content(self, hook_input: Dict) -> bool:
        """Determine if content should be read"""
        tool_name = hook_input.get('tool_name', '')
        
        # Skip tools with typically large outputs
        skip_tools = {'Read', 'Grep', 'LS', 'Glob', 'NotebookRead'}
        if tool_name in skip_tools:
            return False
        
        # Skip if TTS is disabled
        if not self.enable_tts:
            return False
        
        # Check for user preference in input
        tool_input = hook_input.get('tool_input', {})
        if isinstance(tool_input, dict):
            if tool_input.get('no_tts') or tool_input.get('quiet'):
                return False
        
        return True
    
    async def process_hook(self, hook_input: Dict) -> Dict:
        """Process the hook asynchronously"""
        # Check if we should process
        if not self.should_read_content(hook_input):
            return {
                'allowed': True,
                'modified': False,
                'message': 'TTS skipped'
            }
        
        # Extract content to read
        # This would need adjustment based on actual hook context
        content = ""
        
        # Try to get from various possible locations
        if 'response' in hook_input:
            content = str(hook_input['response'])
        elif 'tool_output' in hook_input:
            output = hook_input['tool_output']
            if isinstance(output, dict) and 'content' in output:
                content = output['content']
            else:
                content = str(output)
        elif 'message' in hook_input:
            content = str(hook_input['message'])
        
        if not content or len(content) < 20:
            return {
                'allowed': True,
                'modified': False,
                'message': 'No content to read'
            }
        
        # Process content
        tts_text = self.process_for_tts(content)
        if not tts_text:
            return {
                'allowed': True,
                'modified': False,
                'message': 'Content processed but nothing to speak'
            }
        
        # Generate and play speech
        audio_data = await self.generate_speech_groq(tts_text)
        if audio_data:
            success = self.play_audio_data(audio_data)
            return {
                'allowed': True,
                'modified': False,
                'message': f'TTS {"playing" if success else "generated"}: {len(tts_text)} chars'
            }
        
        return {
            'allowed': True,
            'modified': False,
            'message': 'TTS generation failed'
        }


def main():
    """Hook entry point"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({
            'allowed': True,
            'modified': False,
            'error': 'Invalid JSON input'
        }))
        return
    
    reader = GroqTTSReader()
    
    # Run async processing
    try:
        result = asyncio.run(reader.process_hook(input_data))
    except Exception as e:
        result = {
            'allowed': True,
            'modified': False,
            'error': f'TTS processing error: {str(e)}'
        }
    
    print(json.dumps(result))


if __name__ == '__main__':
    main()