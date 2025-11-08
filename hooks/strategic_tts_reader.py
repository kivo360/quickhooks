#!/usr/bin/env python3
"""
Strategic Text-to-Speech Hook for Claude Code

This hook intelligently processes Claude's responses by:
- Reading regular text content
- Summarizing code blocks instead of reading them verbatim
- Condensing tables to their key information
- Using Groq's TTS API for natural speech output
"""

import json
import os
import re
import sys
import subprocess
import tempfile
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Try to import Groq client
try:
    from groq import Groq
except ImportError:
    # If not installed, we'll handle it gracefully
    Groq = None

@dataclass
class ProcessedContent:
    """Holds processed content ready for TTS"""
    text: str
    has_code: bool
    has_tables: bool
    code_summary: Optional[str] = None
    table_summary: Optional[str] = None


class StrategicTTSReader:
    """Intelligently processes and reads Claude Code responses"""
    
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.groq_client = None
        
        if self.groq_api_key and Groq:
            self.groq_client = Groq(api_key=self.groq_api_key)
        
        # Patterns for content detection
        self.code_block_pattern = r'```[\s\S]*?```'
        self.inline_code_pattern = r'`[^`]+`'
        self.table_pattern = r'\|[^\n]+\|[\s\S]*?\n(?:\|[^\n]+\|(?:\n|$))+'
        
        # Audio player command (macOS uses afplay, Linux uses aplay)
        self.audio_player = self._detect_audio_player()
    
    def _detect_audio_player(self) -> Optional[str]:
        """Detect available audio player on the system"""
        if sys.platform == "darwin":  # macOS
            return "afplay"
        elif sys.platform.startswith("linux"):
            # Check for various Linux audio players
            for player in ["aplay", "paplay", "mpg123", "play"]:
                if subprocess.run(["which", player], capture_output=True).returncode == 0:
                    return player
        return None
    
    def process_content(self, content: str) -> ProcessedContent:
        """Process content for TTS, summarizing code and tables"""
        original_content = content
        processed_text = content
        code_summary = None
        table_summary = None
        
        # Process code blocks
        code_blocks = re.findall(self.code_block_pattern, content, re.MULTILINE)
        if code_blocks:
            code_summary = self._summarize_code_blocks(code_blocks)
            # Replace code blocks with brief mentions
            for i, block in enumerate(code_blocks):
                # Extract language if specified
                lang_match = re.match(r'```(\w+)', block)
                lang = lang_match.group(1) if lang_match else "code"
                
                replacement = f"[{lang} code block {i+1}]"
                processed_text = processed_text.replace(block, replacement, 1)
        
        # Process inline code
        inline_codes = re.findall(self.inline_code_pattern, processed_text)
        for code in inline_codes:
            # Keep short inline code, replace long ones
            if len(code) > 50:
                processed_text = processed_text.replace(code, "[inline code]", 1)
        
        # Process tables
        tables = re.findall(self.table_pattern, processed_text, re.MULTILINE)
        if tables:
            table_summary = self._summarize_tables(tables)
            # Replace tables with brief mentions
            for i, table in enumerate(tables):
                replacement = f"[table {i+1}]"
                processed_text = processed_text.replace(table, replacement, 1)
        
        # Build final text with summaries
        final_text = processed_text
        
        if code_summary:
            final_text += f"\n\nCode summary: {code_summary}"
        
        if table_summary:
            final_text += f"\n\nTable summary: {table_summary}"
        
        # Clean up excessive whitespace
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        
        return ProcessedContent(
            text=final_text,
            has_code=bool(code_blocks),
            has_tables=bool(tables),
            code_summary=code_summary,
            table_summary=table_summary
        )
    
    def _summarize_code_blocks(self, code_blocks: List[str]) -> str:
        """Create a brief summary of code blocks"""
        summaries = []
        
        for block in code_blocks:
            # Extract language
            lang_match = re.match(r'```(\w+)', block)
            language = lang_match.group(1) if lang_match else "unknown"
            
            # Count lines
            lines = block.count('\n') - 1  # Subtract for the ``` markers
            
            # Detect key patterns
            patterns = []
            if 'function' in block or 'def ' in block:
                patterns.append("functions")
            if 'class ' in block:
                patterns.append("classes")
            if 'import ' in block or 'from ' in block or 'require' in block:
                patterns.append("imports")
            if 'test' in block.lower():
                patterns.append("tests")
            
            summary = f"{language} code with {lines} lines"
            if patterns:
                summary += f" containing {', '.join(patterns)}"
            
            summaries.append(summary)
        
        if len(summaries) == 1:
            return summaries[0]
        else:
            return f"{len(summaries)} code blocks: " + "; ".join(summaries)
    
    def _summarize_tables(self, tables: List[str]) -> str:
        """Create a brief summary of tables"""
        summaries = []
        
        for table in tables:
            lines = table.strip().split('\n')
            if len(lines) >= 2:
                # Extract headers
                headers = [h.strip() for h in lines[0].split('|') if h.strip()]
                rows = len(lines) - 2  # Subtract header and separator
                
                summary = f"table with {len(headers)} columns ({', '.join(headers[:3])}"
                if len(headers) > 3:
                    summary += "..."
                summary += f") and {rows} rows"
                
                summaries.append(summary)
        
        if len(summaries) == 1:
            return summaries[0]
        else:
            return f"{len(summaries)} tables: " + "; ".join(summaries)
    
    def text_to_speech(self, text: str) -> Optional[str]:
        """Convert text to speech using Groq API"""
        if not self.groq_client:
            return None
        
        try:
            # Use Groq's TTS API
            # Note: As of my knowledge, Groq's TTS might be in beta or have specific requirements
            # This is a placeholder for the actual API call
            response = self.groq_client.audio.speech.create(
                model="whisper-large-v3",  # or appropriate TTS model
                input=text,
                voice="nova",  # or appropriate voice option
                response_format="mp3"
            )
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
                
        except Exception as e:
            print(f"TTS Error: {e}", file=sys.stderr)
            return None
    
    def play_audio(self, audio_file: str):
        """Play audio file using system audio player"""
        if not self.audio_player:
            return
        
        try:
            subprocess.run([self.audio_player, audio_file], check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to play audio with {self.audio_player}", file=sys.stderr)
        finally:
            # Clean up temporary file
            try:
                os.unlink(audio_file)
            except:
                pass
    
    def should_read_response(self, hook_input: Dict) -> bool:
        """Determine if this response should be read aloud"""
        # Only read responses from certain tools
        tool_name = hook_input.get('tool_name', '')
        
        # Skip reading for certain tools that generate too much output
        skip_tools = ['Read', 'Grep', 'LS', 'Glob']
        if tool_name in skip_tools:
            return False
        
        # Read responses that are likely to be informative
        read_tools = ['Task', 'WebSearch', 'WebFetch']
        if tool_name in read_tools:
            return True
        
        # For other tools, check if the response seems substantial
        # (This is a PostToolUse hook, so we'd need to see the response)
        return True
    
    def run(self, hook_input: Dict) -> Dict:
        """Main hook execution"""
        # This hook runs after tool use, so we look for responses
        # In a PostToolUse context, we might need to capture Claude's response differently
        
        # For now, we'll assume this runs on Claude's text responses
        # In practice, this might need to be adapted based on how responses are captured
        
        # Check if we should read this response
        if not self.should_read_response(hook_input):
            return {
                'allowed': True,
                'modified': False,
                'message': 'TTS skipped for this tool'
            }
        
        # Get the response text (this would need to be adapted to actual hook context)
        response_text = hook_input.get('response', '')
        if not response_text:
            # Try to get from tool output
            tool_output = hook_input.get('tool_output', '')
            if isinstance(tool_output, dict):
                response_text = json.dumps(tool_output, indent=2)
            else:
                response_text = str(tool_output)
        
        if not response_text or len(response_text) < 10:
            return {
                'allowed': True,
                'modified': False,
                'message': 'No substantial content to read'
            }
        
        # Process content
        processed = self.process_content(response_text)
        
        # Convert to speech
        if self.groq_client and self.audio_player:
            audio_file = self.text_to_speech(processed.text)
            if audio_file:
                # Play audio in background so we don't block
                subprocess.Popen([sys.executable, __file__, "--play", audio_file])
        
        return {
            'allowed': True,
            'modified': False,
            'message': f'TTS processed: {len(processed.text)} chars'
        }


def main():
    """Main entry point for the hook"""
    # Handle command line audio playback
    if len(sys.argv) > 2 and sys.argv[1] == "--play":
        audio_file = sys.argv[2]
        reader = StrategicTTSReader()
        reader.play_audio(audio_file)
        return
    
    # Normal hook operation
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({
            'allowed': True,
            'modified': False,
            'error': 'Invalid JSON input'
        }))
        return
    
    reader = StrategicTTSReader()
    result = reader.run(input_data)
    print(json.dumps(result))


if __name__ == '__main__':
    main()