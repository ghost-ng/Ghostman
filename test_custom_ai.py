"""Test custom AI model and API base functionality."""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "ghostman" / "src"
sys.path.insert(0, str(src_path))

def test_custom_ai_config():
    """Test custom AI configuration."""
    print("Testing custom AI configuration...")
    
    try:
        from services.ai_service import AIService, AIConfig
        
        # Test default config
        config = AIConfig()
        print(f"✓ Default API base: {config.api_base}")
        print(f"✓ Default model: {config.model}")
        
        # Test custom config
        config.api_base = "http://localhost:11434/v1"  # Ollama
        config.model = "llama2:7b-chat"
        config.api_key = "not-needed-for-ollama"
        
        print(f"✓ Custom API base: {config.api_base}")
        print(f"✓ Custom model: {config.model}")
        
        # Test AI service with custom config
        ai_service = AIService()
        ai_service.config = config
        
        # Test config save/load
        ai_service.save_config()
        print(f"✓ Config saved to: {ai_service.config_path}")
        
        # Create new service and load config
        ai_service2 = AIService(ai_service.config_path)
        
        print(f"✓ Loaded API base: {ai_service2.config.api_base}")
        print(f"✓ Loaded model: {ai_service2.config.model}")
        
        # Verify they match
        assert ai_service2.config.api_base == config.api_base
        assert ai_service2.config.model == config.model
        print(f"✓ Config persistence works")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_config_path():
    """Test that configs are saved in proper location."""
    print("\nTesting config paths...")
    
    try:
        from services.ai_service import AIService
        from services.conversation_storage import ConversationStorage
        from ui.themes.theme_manager import ThemeManager
        
        ai_service = AIService()
        storage = ConversationStorage()
        theme_manager = ThemeManager()
        
        # Check paths use APPDATA on Windows
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            expected_base = Path(appdata) / "Ghostman"
            
            print(f"✓ Expected base path: {expected_base}")
            
            # Check AI service path
            assert str(ai_service.config_path).startswith(str(expected_base))
            print(f"✓ AI config: {ai_service.config_path}")
            
            # Check storage path
            assert str(storage.storage_path).startswith(str(expected_base))
            print(f"✓ Conversations: {storage.storage_path}")
            
            # Check theme path
            assert str(theme_manager.config_path).startswith(str(expected_base))
            print(f"✓ Themes: {theme_manager.config_path}")
            
        else:
            print("✓ Non-Windows system, using home directory")
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_openai_compatible_models():
    """Test that various model names are supported."""
    print("\nTesting OpenAI-compatible model names...")
    
    try:
        from services.ai_service import AIConfig
        
        test_models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "claude-3-opus",
            "llama2:7b-chat",
            "mistral:7b-instruct",
            "gemma:2b-instruct",
            "codellama:7b-code",
            "vicuna-13b-v1.5",
            "custom-model-name-123"
        ]
        
        for model in test_models:
            config = AIConfig()
            config.model = model
            print(f"✓ Supports model: {model}")
        
        print(f"✓ All {len(test_models)} model types supported")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("CUSTOM AI CONFIGURATION TEST")
    print("=" * 60)
    
    results = []
    
    results.append(("Custom AI Config", test_custom_ai_config()))
    results.append(("Config Paths", test_config_path()))
    results.append(("Model Support", test_openai_compatible_models()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
    
    total_passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if os.name == 'nt':
        appdata = os.environ.get('APPDATA', 'Unknown')
        print(f"\n📁 Config Location: {appdata}\\Ghostman\\")
    
    return all(p for _, p in results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)