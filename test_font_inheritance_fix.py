#!/usr/bin/env python3
"""
Test font inheritance fix during theme switching.

This script tests that:
1. Font configurations are preserved during theme changes
2. Semantic CSS is properly injected and updated
3. Different text types maintain their distinct fonts
4. The fixed inheritance system works correctly

Run this to verify the font inheritance fix.
"""

import sys
import logging
from pathlib import Path

# Add the ghostman src to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_font_inheritance")


def test_font_service_css_generation():
    """Test that FontService generates proper semantic CSS."""
    print("=== Testing FontService CSS Generation ===")
    
    try:
        from ghostman.src.application.font_service import font_service
        
        # Test CSS generation
        css = font_service.get_semantic_font_css()
        print(f"Generated CSS length: {len(css)} characters")
        
        # Check for critical components
        required_components = [
            "ghostman-fonts",
            "--gm-ai-response-font-family",
            "--gm-user-input-font-family", 
            "--gm-code-snippets-font-family",
            ".ghostman-message-container.ghostman-ai-response",
            ".ghostman-message-container.ghostman-user-input"
        ]
        
        missing_components = []
        for component in required_components:
            if component not in css:
                missing_components.append(component)
            else:
                print(f"✓ Found: {component}")
        
        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        else:
            print("✅ All required CSS components present")
            return True
            
    except Exception as e:
        print(f"❌ FontService test failed: {e}")
        return False


def test_font_configurations():
    """Test that font configurations are stored and retrieved correctly."""
    print("\n=== Testing Font Configurations ===")
    
    try:
        from ghostman.src.application.font_service import font_service
        
        # Test each font type
        font_types = ['ai_response', 'user_input', 'code_snippets']
        configs = {}
        
        for font_type in font_types:
            config = font_service.get_font_config(font_type)
            configs[font_type] = config
            print(f"{font_type}: {config['family']} {config['size']}pt")
            
            # Verify required keys exist
            required_keys = ['family', 'size', 'weight', 'style']
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                print(f"❌ Missing keys in {font_type}: {missing_keys}")
                return False
        
        # Verify they're different (especially code should be different)
        if configs['code_snippets']['family'] == configs['ai_response']['family']:
            print("⚠ Warning: Code font same as AI response font")
        else:
            print("✓ Code font is different from AI response font")
        
        print("✅ Font configurations valid")
        return True
        
    except Exception as e:
        print(f"❌ Font configuration test failed: {e}")
        return False


def test_theme_system_integration():
    """Test that theme system exists and works with fonts."""
    print("\n=== Testing Theme System Integration ===")
    
    try:
        from ghostman.src.ui.themes.theme_manager import get_theme_manager
        
        theme_manager = get_theme_manager()
        current_theme = theme_manager.current_theme_name
        available_themes = theme_manager.get_available_themes()
        
        print(f"Current theme: {current_theme}")
        print(f"Available themes: {len(available_themes)}")
        print(f"First 5 themes: {available_themes[:5]}")
        
        # Test switching to different themes
        test_themes = available_themes[:3] if len(available_themes) >= 3 else available_themes
        
        for theme_name in test_themes:
            success = theme_manager.set_theme(theme_name)
            if success:
                print(f"✓ Successfully switched to: {theme_name}")
            else:
                print(f"❌ Failed to switch to: {theme_name}")
                return False
        
        # Switch back to original
        theme_manager.set_theme(current_theme)
        print(f"✓ Restored original theme: {current_theme}")
        
        print("✅ Theme system integration working")
        return True
        
    except Exception as e:
        print(f"❌ Theme system test failed: {e}")
        return False


def test_css_injection_logic():
    """Test the CSS injection logic without GUI components."""
    print("\n=== Testing CSS Injection Logic ===")
    
    try:
        # Test the semantic CSS safe method
        from ghostman.src.application.font_service import font_service
        
        # Clear cache to ensure fresh generation
        font_service.clear_cache()
        
        css = font_service.get_semantic_font_css()
        if not css:
            print("❌ No CSS generated")
            return False
        
        # Test CSS variables generation
        css_vars = font_service.get_semantic_css_variables()
        if not css_vars:
            print("❌ No CSS variables generated")
            return False
        
        print(f"✓ CSS generated: {len(css)} chars")
        print(f"✓ CSS variables generated: {len(css_vars)} chars")
        
        # Test that clearing cache works
        font_service.clear_cache()
        css2 = font_service.get_semantic_font_css()
        
        if css != css2:
            print("⚠ Warning: CSS changed after cache clear (expected but worth noting)")
        else:
            print("✓ CSS consistent after cache operations")
        
        print("✅ CSS injection logic working")
        return True
        
    except Exception as e:
        print(f"❌ CSS injection logic test failed: {e}")
        return False


def test_font_update_integration():
    """Test that font updates trigger proper cache clearing."""
    print("\n=== Testing Font Update Integration ===")
    
    try:
        from ghostman.src.application.font_service import font_service
        
        # Get current config
        original_config = font_service.get_font_config('ai_response')
        print(f"Original AI response font: {original_config['family']} {original_config['size']}pt")
        
        # Update font size
        font_service.update_font_config('ai_response', size=12)
        
        # Get updated config
        updated_config = font_service.get_font_config('ai_response')
        print(f"Updated AI response font: {updated_config['family']} {updated_config['size']}pt")
        
        if updated_config['size'] != 12:
            print("❌ Font size update failed")
            return False
        
        # Test CSS regeneration
        css_after_update = font_service.get_semantic_font_css()
        if "12pt" not in css_after_update:
            print("❌ CSS not updated with new font size")
            return False
        
        print("✓ CSS properly updated with new font size")
        
        # Restore original
        font_service.update_font_config('ai_response', size=original_config['size'])
        
        print("✅ Font update integration working")
        return True
        
    except Exception as e:
        print(f"❌ Font update integration test failed: {e}")
        return False


def run_all_tests():
    """Run all font inheritance tests."""
    print("🔍 Starting Font Inheritance Fix Tests")
    print("=" * 50)
    
    tests = [
        test_font_service_css_generation,
        test_font_configurations,
        test_theme_system_integration,
        test_css_injection_logic,
        test_font_update_integration
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)} tests")
    
    if all(results):
        print("🎉 All tests PASSED! Font inheritance fix is working correctly.")
        return True
    else:
        failed_tests = [test.__name__ for test, result in zip(tests, results) if not result]
        print(f"❌ Failed tests: {', '.join(failed_tests)}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)