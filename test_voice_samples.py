#!/usr/bin/env python3
"""
Test different voices to find the best ones for TTS
"""

import pyttsx3
import time

def test_voices():
    """Test and categorize available voices"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # Sample text for testing
    test_text = "Hello! I've analyzed your code and found three issues. The main function has a memory leak, and the API endpoint needs authentication. Would you like me to fix these problems?"
    
    # Categorize voices
    english_voices = []
    high_quality_voices = []
    natural_voices = []
    
    print(f"Total voices available: {len(voices)}\n")
    
    # Find English voices and categorize
    for i, voice in enumerate(voices):
        if 'en-' in voice.id.lower() or 'english' in voice.name.lower():
            english_voices.append((i, voice))
            
            # Check for high-quality indicators
            if any(name in voice.name.lower() for name in ['samantha', 'alex', 'karen', 'daniel', 'moira', 'tessa', 'fiona', 'victoria']):
                high_quality_voices.append((i, voice))
            
            # Natural sounding names (avoid robotic ones)
            if not any(robot in voice.name.lower() for robot in ['robot', 'zarvox', 'whisper', 'bells', 'bubbles', 'trinoids']):
                natural_voices.append((i, voice))
    
    # Print high-quality English voices
    print("🌟 HIGH-QUALITY ENGLISH VOICES:")
    print("-" * 60)
    for idx, voice in high_quality_voices:
        print(f"{idx}: {voice.name}")
        if 'com.apple.voice' in voice.id:
            quality = "Premium" if 'premium' in voice.id else "Compact"
            print(f"   Quality: {quality}")
        print(f"   ID: {voice.id}")
        print()
    
    # Test top recommendations
    print("\n🎯 TOP RECOMMENDATIONS FOR CLAUDE CODE TTS:")
    print("-" * 60)
    
    recommendations = [
        (132, "Samantha", "Clear American female voice - great for code"),
        (14, "Daniel", "British male voice - professional tone"),
        (82, "Karen", "Australian female voice - friendly"),
        (86, "Moira", "Irish female voice - pleasant accent"),
        (164, "Tessa", "South African female voice - clear pronunciation"),
        (171, "Rishi", "Indian English male voice - clear technical speech"),
    ]
    
    for idx, name, description in recommendations:
        if idx < len(voices):
            voice = voices[idx]
            if name.lower() in voice.name.lower():
                print(f"✅ {idx}: {voice.name}")
                print(f"   {description}")
                print(f"   ID: {voice.id}")
                
                # Test the voice
                engine.setProperty('voice', voice.id)
                engine.setProperty('rate', 175)
                print("   Testing... (listen for quality)")
                engine.say(f"This is {voice.name}. " + test_text)
                engine.runAndWait()
                time.sleep(1)
                print()
    
    # Find enhanced/premium voices
    print("\n💎 ENHANCED/PREMIUM VOICES (if available):")
    print("-" * 60)
    premium_found = False
    for i, voice in enumerate(voices):
        if 'premium' in voice.id.lower() or 'enhanced' in voice.id.lower():
            premium_found = True
            print(f"{i}: {voice.name}")
            print(f"   ID: {voice.id}")
    
    if not premium_found:
        print("No premium voices found. Consider downloading enhanced voices from:")
        print("- macOS: System Settings > Accessibility > Spoken Content > Voices")
        print("- Click 'Manage Voices...' to download premium options")
    
    # Alternative high-quality voices
    print("\n🎭 ALTERNATIVE CHARACTER VOICES (fun but clear):")
    print("-" * 60)
    
    character_voices = {
        "Albert": "Friendly male voice",
        "Agnes": "Gentle female voice",
        "Alex": "Clear American voice (if available)",
        "Vicki": "Efficient female voice",
        "Victoria": "Professional female voice",
        "Tom": "Reliable male voice"
    }
    
    for i, voice in enumerate(voices):
        for char_name, desc in character_voices.items():
            if char_name.lower() in voice.name.lower():
                print(f"{i}: {voice.name} - {desc}")
                break
    
    return high_quality_voices, recommendations


def test_speech_rates():
    """Test different speech rates"""
    engine = pyttsx3.init()
    
    # Use Samantha
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[132].id)
    
    test_text = "The code analysis is complete. Found 3 issues that need attention."
    
    print("\n🎚️  TESTING SPEECH RATES:")
    print("-" * 60)
    
    rates = [
        (150, "Slow and clear"),
        (175, "Default - balanced"),
        (200, "Slightly faster"),
        (225, "Fast but clear"),
        (250, "Very fast")
    ]
    
    for rate, description in rates:
        print(f"\nRate {rate} - {description}")
        engine.setProperty('rate', rate)
        engine.say(test_text)
        engine.runAndWait()
        time.sleep(1)


def main():
    print("🔊 QUICKHOOKS TTS VOICE EXPLORER")
    print("=" * 80)
    print("This will test different voices to help you find the best one.")
    print("Listen carefully to each voice sample.\n")
    
    # Get voice recommendations
    high_quality, recommendations = test_voices()
    
    # Test speech rates
    print("\nPress Enter to test different speech rates...")
    try:
        input()
        test_speech_rates()
    except:
        pass
    
    print("\n" + "=" * 80)
    print("📝 CONFIGURATION RECOMMENDATIONS:")
    print("-" * 60)
    print("Add to your shell profile (.bashrc/.zshrc):\n")
    print("# High-quality voices:")
    print("export QUICKHOOKS_TTS_VOICE_INDEX=132  # Samantha (US)")
    print("# export QUICKHOOKS_TTS_VOICE_INDEX=14   # Daniel (UK)")
    print("# export QUICKHOOKS_TTS_VOICE_INDEX=82   # Karen (AU)")
    print("# export QUICKHOOKS_TTS_VOICE_INDEX=86   # Moira (IE)")
    print("\n# Speech rate:")
    print("export QUICKHOOKS_TTS_RATE=175  # Default")
    print("# export QUICKHOOKS_TTS_RATE=200  # Faster")
    print("\n# Enable TTS:")
    print("export QUICKHOOKS_TTS_ENABLED=true")
    
    print("\n💡 TIP: Download premium voices from System Settings > Accessibility")
    print("   > Spoken Content > Manage Voices for even better quality!")


if __name__ == "__main__":
    main()