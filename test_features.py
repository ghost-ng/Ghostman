"""Quick test to verify what features are working."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "ghostman" / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test all imports work."""
    print("Testing imports...")
    try:
        from app.application import GhostmanApplication
        print("✓ Application imports")
        
        from ui.components.settings_dialog import SettingsDialog
        print("✓ Settings dialog imports")
        
        from services.ai_service import AIService
        print("✓ AI service imports")
        
        from services.conversation_storage import ConversationStorage
        print("✓ Conversation storage imports")
        
        from ui.themes.theme_manager import ThemeManager
        print("✓ Theme manager imports")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_theme_manager():
    """Test theme manager functionality."""
    print("\nTesting theme manager...")
    try:
        from ui.themes.theme_manager import ThemeManager
        
        tm = ThemeManager()
        
        # Test getting themes
        themes = tm.get_all_builtin_themes()
        print(f"✓ Found {len(themes)} built-in themes: {list(themes.keys())}")
        
        # Test theme switching
        tm.apply_theme("dark")
        print(f"✓ Applied dark theme")
        
        tm.apply_theme("light")
        print(f"✓ Applied light theme")
        
        # Test stylesheet generation
        style = tm.get_stylesheet("general")
        print(f"✓ Generated stylesheet ({len(style)} chars)")
        
        return True
    except Exception as e:
        print(f"✗ Theme manager error: {e}")
        return False

def test_ai_config():
    """Test AI configuration."""
    print("\nTesting AI configuration...")
    try:
        from services.ai_service import AIService, AIConfig
        
        config = AIConfig()
        print(f"✓ Default AI config created")
        print(f"  - Model: {config.model}")
        print(f"  - Max tokens: {config.max_tokens}")
        print(f"  - Temperature: {config.temperature}")
        
        # Check if API key is configured
        if config.api_key:
            print(f"✓ API key is configured")
        else:
            print(f"⚠ No API key configured (expected for first run)")
        
        return True
    except Exception as e:
        print(f"✗ AI config error: {e}")
        return False

def test_conversation_storage():
    """Test conversation storage."""
    print("\nTesting conversation storage...")
    try:
        from services.conversation_storage import ConversationStorage
        from services.models import SimpleMessage
        
        storage = ConversationStorage()
        
        # Create test messages
        messages = [
            SimpleMessage("Hello AI", True),
            SimpleMessage("Hello! How can I help?", False),
            SimpleMessage("What's the weather?", True),
            SimpleMessage("I can't check weather, but I can help with other things!", False)
        ]
        
        # Save conversation
        session_id = storage.save_conversation(messages, "test_session")
        print(f"✓ Saved conversation with ID: {session_id}")
        
        # Load conversation
        loaded = storage.load_conversation(session_id)
        print(f"✓ Loaded {len(loaded)} messages")
        
        # List conversations
        convos = storage.list_conversations()
        print(f"✓ Found {len(convos)} saved conversations")
        
        # Clean up test
        storage.delete_conversation(session_id)
        print(f"✓ Deleted test conversation")
        
        return True
    except Exception as e:
        print(f"✗ Storage error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("GHOSTMAN FEATURE TEST")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Theme Manager", test_theme_manager()))
    results.append(("AI Configuration", test_ai_config()))
    results.append(("Conversation Storage", test_conversation_storage()))
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    return all(p for _, p in results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)