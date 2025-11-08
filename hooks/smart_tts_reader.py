#!/usr/bin/env python3
"""
Smart Text-to-Speech Hook for Claude Code

This hook intelligently reads Claude's responses aloud by:
- Summarizing code blocks instead of reading them verbatim
- Condensing tables to key information
- Cleaning up technical content for better speech
- Using local TTS for instant feedback

To use:
1. Set environment variable QUICKHOOKS_TTS_ENABLED=true to enable
2. Optional: QUICKHOOKS_TTS_VOICE_INDEX=132 (for Samantha on macOS)
3. Optional: QUICKHOOKS_TTS_RATE=175 (speech rate)
"""

import json
import os
import re
import sys
import subprocess
import threading
from typing import Dict, Optional

# Try to import TTS library
try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False


class SmartTTSReader:
    """Intelligently processes and reads Claude Code responses"""
    
    def __init__(self):
        self.enabled = os.environ.get('QUICKHOOKS_TTS_ENABLED', 'false').lower() == 'true'
        self.voice_index = int(os.environ.get('QUICKHOOKS_TTS_VOICE_INDEX', '132'))  # Samantha
        self.speech_rate = int(os.environ.get('QUICKHOOKS_TTS_RATE', '175'))
        
        self.engine = None
        if HAS_TTS and self.enabled:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', self.speech_rate)
                self.engine.setProperty('volume', 0.9)
                
                # Set voice if available
                voices = self.engine.getProperty('voices')
                if 0 <= self.voice_index < len(voices):
                    self.engine.setProperty('voice', voices[self.voice_index].id)
            except Exception as e:
                print(f"TTS init error: {e}", file=sys.stderr)
                self.engine = None
        
        # Content patterns
        self.code_block_pattern = re.compile(r'```(?P<lang>\w*)\n?(?P<code>[\s\S]*?)```', re.MULTILINE)
        self.inline_code_pattern = re.compile(r'`([^`]+)`')
        self.table_pattern = re.compile(r'(\|[^\n]+\|\n)+(\|[-:| ]+\|\n)(\|[^\n]+\|\n)+', re.MULTILINE)
        self.url_pattern = re.compile(r'https?://[^\s\)]+')
        self.file_path_pattern = re.compile(r'(?:^|\s)(/[\w.-]+)+(?:/[\w.-]+)?(?:\.\w+)?')
        self.command_pattern = re.compile(r'^\$\s+(.+)$', re.MULTILINE)
    
    def should_read(self, hook_input: Dict) -> bool:
        """Determine if this content should be read"""
        if not self.enabled or not self.engine:
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
    
    def summarize_code_block(self, lang: str, code: str) -> str:
        """Create a brief summary of code block"""
        lines = code.strip().split('\n')
        line_count = len(lines)
        
        # Detect content type
        characteristics = []
        
        if lang.lower() in ['python', 'py']:
            if any('def ' in line for line in lines):
                func_count = sum(1 for line in lines if line.strip().startswith('def '))
                if func_count == 1:
                    characteristics.append("a function")
                else:
                    characteristics.append(f"{func_count} functions")
            if any('class ' in line for line in lines):
                class_count = sum(1 for line in lines if line.strip().startswith('class '))
                if class_count == 1:
                    characteristics.append("a class")
                else:
                    characteristics.append(f"{class_count} classes")
        
        elif lang.lower() in ['javascript', 'js', 'typescript', 'ts']:
            if any('function ' in line or '=>' in line for line in lines):
                characteristics.append("functions")
            if any('class ' in line for line in lines):
                characteristics.append("classes")
        
        elif lang.lower() in ['bash', 'sh', 'shell']:
            characteristics.append("shell commands")
        
        # Build natural summary
        summary = f"{lang or 'code'} block with {line_count} lines"
        if characteristics:
            summary += f" containing {', '.join(characteristics)}"
        
        return f"[{summary}]"
    
    def summarize_table(self, table_text: str) -> str:
        """Create natural summary of table"""
        lines = table_text.strip().split('\n')
        if len(lines) < 3:
            return "[small table]"
        
        # Extract headers
        headers = [h.strip() for h in lines[0].split('|') if h.strip()]
        data_rows = len([l for l in lines[2:] if l.strip()])
        
        # Create natural description
        if len(headers) <= 3:
            summary = f"table with columns {', '.join(headers)} and {data_rows} rows"
        else:
            summary = f"table with {len(headers)} columns and {data_rows} rows"
        
        return f"[{summary}]"
    
    def process_text(self, text: str) -> str:
        """Process text for natural speech"""
        if not text or len(text.strip()) < 10:
            return ""
        
        processed = text
        
        # Replace code blocks with summaries
        for match in self.code_block_pattern.finditer(text):
            lang = match.group('lang')
            code = match.group('code')
            summary = self.summarize_code_block(lang, code)
            processed = processed.replace(match.group(0), summary, 1)
        
        # Clean inline code (remove backticks)
        processed = self.inline_code_pattern.sub(r'\1', processed)
        
        # Replace tables with summaries
        for match in self.table_pattern.finditer(processed):
            table = match.group(0)
            summary = self.summarize_table(table)
            processed = processed.replace(table, summary, 1)
        
        # Simplify URLs
        processed = self.url_pattern.sub('[link]', processed)
        
        # Simplify file paths
        def simplify_path(match):
            path = match.group(0).strip()
            filename = path.split('/')[-1]
            return f"file {filename}"
        
        processed = self.file_path_pattern.sub(simplify_path, processed)
        
        # Clean commands
        processed = self.command_pattern.sub(r'command: \1', processed)
        
        # Remove markdown formatting
        processed = processed.replace('```', '')
        processed = re.sub(r'#{1,6}\s*', '', processed)  # Headers
        processed = processed.replace('**', '').replace('__', '')  # Bold
        processed = processed.replace('*', '').replace('_', '')  # Italic
        processed = processed.replace('>', '')  # Quotes
        processed = processed.replace('|', ' ')  # Table remnants
        
        # Clean up whitespace
        processed = re.sub(r'\n{3,}', '\n\n', processed)
        processed = re.sub(r' {2,}', ' ', processed)
        
        # Truncate if too long
        max_length = 1000  # Reasonable length for TTS
        if len(processed) > max_length:
            processed = processed[:max_length-20] + "... (truncated)"
        
        return processed.strip()
    
    def speak_async(self, text: str):
        """Speak text in background thread"""
        if not self.engine or not text:
            return
        
        def speak():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"TTS speak error: {e}", file=sys.stderr)
        
        # Run in background so we don't block
        thread = threading.Thread(target=speak, daemon=True)
        thread.start()
    
    def extract_content(self, hook_input: Dict) -> Optional[str]:
        """Extract readable content from hook input"""
        # For PostToolUse hooks, we need to look at the response
        # This is simplified - actual implementation would depend on hook context
        
        # Try different locations where content might be
        content = None
        
        # Check for direct response
        if 'response' in hook_input:
            content = str(hook_input['response'])
        
        # Check tool output
        elif 'tool_output' in hook_input:
            output = hook_input['tool_output']
            if isinstance(output, dict):
                # Look for common content keys
                if 'content' in output:
                    content = str(output['content'])
                elif 'message' in output:
                    content = str(output['message'])
                elif 'text' in output:
                    content = str(output['text'])
                else:
                    # Convert dict to readable format
                    content = json.dumps(output, indent=2)
            else:
                content = str(output)
        
        # Check for message
        elif 'message' in hook_input:
            content = str(hook_input['message'])
        
        return content
    
    def run(self, hook_input: Dict) -> Dict:
        """Main hook execution"""
        # Quick validation
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
                'message': 'No substantial content to read'
            }
        
        # Process for speech
        processed = self.process_text(content)
        if not processed:
            return {
                'allowed': True,
                'modified': False,
                'message': 'Content processed but nothing to speak'
            }
        
        # Speak in background
        self.speak_async(processed)
        
        return {
            'allowed': True,
            'modified': False,
            'message': f'TTS: Speaking {len(processed)} chars'
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
    
    # Check if TTS is available
    if not HAS_TTS:
        print(json.dumps({
            'allowed': True,
            'modified': False,
            'message': 'TTS not available (install pyttsx3)'
        }))
        return
    
    # Process with TTS reader
    reader = SmartTTSReader()
    result = reader.run(input_data)
    
    # Output result
    print(json.dumps(result))


if __name__ == '__main__':
    main()