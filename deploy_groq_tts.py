#!/usr/bin/env python3
"""
Deploy Groq PlayAI TTS hook to Claude Code
"""

import json
import shutil
from pathlib import Path

def deploy_groq_tts():
    """Deploy the Groq PlayAI TTS hook"""
    
    # Paths
    source_hook = Path(__file__).parent / "hooks" / "groq_playai_tts_reader.py"
    target_hook = Path.home() / ".claude" / "hooks" / "groq_playai_tts_reader.py"
    settings_file = Path.home() / ".claude" / "settings.json"
    
    print("🚀 DEPLOYING GROQ PLAYAI TTS HOOK")
    print("=" * 60)
    
    # Check source exists
    if not source_hook.exists():
        print(f"❌ Source hook not found: {source_hook}")
        return False
    
    # Copy hook file
    print(f"📁 Copying hook to {target_hook}")
    target_hook.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_hook, target_hook)
    target_hook.chmod(0o755)
    print("✅ Hook copied")
    
    # Update settings
    print("\n📝 Updating Claude settings...")
    
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        print(f"❌ Settings file not found: {settings_file}")
        return False
    
    # Find and update TTS hook
    updated = False
    for config in settings.get("hooks", {}).get("PostToolUse", []):
        if "tools" in config and isinstance(config.get("hooks"), list):
            for hook in config["hooks"]:
                if "smart_tts_reader.py" in hook.get("command", ""):
                    # Update to use Groq TTS
                    old_command = hook["command"]
                    hook["command"] = str(target_hook)
                    print(f"✅ Updated hook command:")
                    print(f"   From: {old_command}")
                    print(f"   To:   {hook['command']}")
                    updated = True
                    break
    
    if not updated:
        # Add new hook config
        tts_config = {
            "tools": ["Task", "WebSearch", "WebFetch", "Bash", "Edit", "Write"],
            "hooks": [{
                "command": str(target_hook),
                "timeout": 10,
                "type": "command"
            }]
        }
        settings.setdefault("hooks", {}).setdefault("PostToolUse", []).append(tts_config)
        print("✅ Added new TTS hook configuration")
    
    # Write settings back
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print("\n✅ Deployment complete!")
    
    # Check environment
    print("\n🔍 Environment check:")
    import os
    
    if os.environ.get('GROQ_API_KEY'):
        print("✅ GROQ_API_KEY is set")
    else:
        print("❌ GROQ_API_KEY not found - set it with:")
        print("   export GROQ_API_KEY='your-api-key-here'")
    
    if os.environ.get('QUICKHOOKS_TTS_ENABLED', '').lower() == 'true':
        print("✅ TTS is enabled")
    else:
        print("⚠️  TTS is not enabled - enable with:")
        print("   export QUICKHOOKS_TTS_ENABLED=true")
    
    voice = os.environ.get('QUICKHOOKS_TTS_VOICE', 'Samantha-PlayAI')
    print(f"🎤 Current voice: {voice}")
    
    print("\n📋 Quick test command:")
    print("   python test_groq_playai_tts.py")
    
    return True


if __name__ == "__main__":
    import sys
    
    # Check for Groq library
    try:
        import groq
    except ImportError:
        print("❌ Groq library not installed")
        print("Install with: pip install groq")
        sys.exit(1)
    
    success = deploy_groq_tts()
    sys.exit(0 if success else 1)