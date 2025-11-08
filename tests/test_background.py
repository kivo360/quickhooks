#!/usr/bin/env python3
"""Test background processing directly"""

import sys
import os
import json
sys.path.append('hooks')

from context_portal_memory import EnhancedContextPortalMemoryManager
import time

def test_background_processing():
    """Test if background processing works"""
    print("Initializing memory manager...")
    manager = EnhancedContextPortalMemoryManager()
    
    print("Starting background processing...")
    manager.start_background_processing()
    
    print("Storing context entry...")
    entry_id = manager.store_enhanced_context_entry(
        tool_name="Edit",
        command="test command",
        context='{"tool": "Edit", "file_path": "test.py", "operation": "implement architecture"}',
        session_id="background_test",
        file_path="test.py"
    )
    
    print(f"Entry ID: {entry_id}")
    print("Waiting for background processing...")
    time.sleep(10)
    
    print("Checking results...")
    return True

if __name__ == "__main__":
    os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY', '')
    test_background_processing()