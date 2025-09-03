#!/usr/bin/env python3
"""
Full integration test for font inheritance during theme switching.

This test simulates the full flow:
1. Load font configurations
2. Generate semantic CSS
3. Switch themes
4. Verify fonts are preserved
5. Update font settings
6. Verify CSS is regenerated

Run this to test the complete font inheritance fix.
"""

import sys
import logging
from pathlib import Path

# Add the ghostman src to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("integration_test")


def test_full_theme_switching_workflow():
    """Test the complete theme switching workflow with fonts."""
    print("🔄 Testing Complete Theme Switching Workflow")
    print("=" * 60)
    
    try:
        from ghostman.src.application.font_service import font_service
        from ghostman.src.ui.themes.theme_manager import get_theme_manager
        
        # Step 1: Get initial state
        theme_manager = get_theme_manager()
        original_theme = theme_manager.current_theme_name
        
        initial_ai_config = font_service.get_font_config('ai_response')
        initial_code_config = font_service.get_font_config('code_snippets')
        
        print(f"✓ Initial state loaded")
        print(f"  Theme: {original_theme}")
        print(f"  AI Response Font: {initial_ai_config['family']} {initial_ai_config['size']}pt")
        print(f"  Code Font: {initial_code_config['family']} {initial_code_config['size']}pt")
        
        # Step 2: Generate initial CSS
        initial_css = font_service.get_semantic_font_css()
        css_length = len(initial_css)
        print(f"✓ Initial CSS generated: {css_length} characters")
        
        # Verify CSS contains font families
        if initial_ai_config['family'] not in initial_css:
            raise Exception(f"AI font {initial_ai_config['family']} not found in CSS")
        if initial_code_config['family'] not in initial_css:
            raise Exception(f"Code font {initial_code_config['family']} not found in CSS")
        print(f"✓ CSS contains correct font families")
        
        # Step 3: Switch themes multiple times
        test_themes = ['arctic_white', 'cyberpunk', 'dark_matrix']
        available_themes = theme_manager.get_available_themes()
        test_themes = [t for t in test_themes if t in available_themes]
        
        for theme_name in test_themes:
            print(f"\n🎨 Testing theme: {theme_name}")
            
            # Switch theme
            success = theme_manager.set_theme(theme_name)
            if not success:
                raise Exception(f"Failed to switch to theme {theme_name}")
            
            # Verify fonts are still correct after theme switch
            ai_config_after = font_service.get_font_config('ai_response')
            code_config_after = font_service.get_font_config('code_snippets')
            
            if ai_config_after['family'] != initial_ai_config['family']:
                raise Exception(f"AI font changed from {initial_ai_config['family']} to {ai_config_after['family']}")
            if code_config_after['family'] != initial_code_config['family']:
                raise Exception(f"Code font changed from {initial_code_config['family']} to {code_config_after['family']}")
            
            # Generate CSS for this theme
            theme_css = font_service.get_semantic_font_css()
            
            # Verify CSS still contains font families
            if ai_config_after['family'] not in theme_css:
                raise Exception(f"AI font {ai_config_after['family']} not found in CSS after theme switch")
            if code_config_after['family'] not in theme_css:
                raise Exception(f"Code font {code_config_after['family']} not found in CSS after theme switch")
            
            print(f"  ✓ Fonts preserved after theme switch")
            print(f"  ✓ CSS updated correctly ({len(theme_css)} chars)")
        
        # Step 4: Test font updates
        print(f"\n🔧 Testing font configuration updates")
        
        # Update AI response font size
        new_size = 14
        font_service.update_font_config('ai_response', size=new_size)
        
        updated_ai_config = font_service.get_font_config('ai_response')
        if updated_ai_config['size'] != new_size:
            raise Exception(f"Font size not updated: expected {new_size}, got {updated_ai_config['size']}")
        
        # Verify CSS reflects the change
        updated_css = font_service.get_semantic_font_css()
        if f"{new_size}pt" not in updated_css:
            raise Exception(f"Updated font size {new_size}pt not found in CSS")
        
        print(f"  ✓ Font size updated to {new_size}pt")
        print(f"  ✓ CSS reflects font size change")
        
        # Step 5: Test theme switch with updated fonts
        print(f"\n🎨 Testing theme switch with updated fonts")
        
        final_theme = 'cyber' if 'cyber' in available_themes else available_themes[0]
        theme_manager.set_theme(final_theme)
        
        final_ai_config = font_service.get_font_config('ai_response')
        if final_ai_config['size'] != new_size:
            raise Exception(f"Font size lost after theme switch: expected {new_size}, got {final_ai_config['size']}")
        
        final_css = font_service.get_semantic_font_css()
        if f"{new_size}pt" not in final_css:
            raise Exception(f"Font size lost in CSS after theme switch")
        
        print(f"  ✓ Font settings preserved through theme switch")
        print(f"  ✓ Final theme: {final_theme}")
        
        # Step 6: Restore original state
        print(f"\n🔄 Restoring original state")
        
        theme_manager.set_theme(original_theme)
        font_service.update_font_config('ai_response', size=initial_ai_config['size'])
        
        restored_theme = theme_manager.current_theme_name
        restored_config = font_service.get_font_config('ai_response')
        
        if restored_theme != original_theme:
            raise Exception(f"Failed to restore theme: expected {original_theme}, got {restored_theme}")
        if restored_config['size'] != initial_ai_config['size']:
            raise Exception(f"Failed to restore font size: expected {initial_ai_config['size']}, got {restored_config['size']}")
        
        print(f"  ✓ Original state restored")
        
        print(f"\n🎉 INTEGRATION TEST PASSED!")
        print(f"✓ Fonts are properly preserved during theme switching")
        print(f"✓ CSS is correctly regenerated with font changes")  
        print(f"✓ Theme system and font system work together correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_css_injection_simulation():
    """Simulate CSS injection process that would happen in REPL widget."""
    print("\n" + "=" * 60)
    print("🧪 Testing CSS Injection Simulation")
    
    try:
        from ghostman.src.application.font_service import font_service
        
        # Simulate getting CSS for injection
        css = font_service.get_semantic_font_css()
        
        # Check CSS structure
        required_parts = [
            ":root {",  # CSS variables
            "--gm-ai-response-font-family:",
            "--gm-code-snippets-font-family:",
            "@layer ghostman-fonts {",  # CSS layer
            ".ghostman-message-container.ghostman-ai-response",
            "font-family: var(--gm-ai-response-font-family) !important;",
            "font-family: var(--gm-code-snippets-font-family) !important;"
        ]
        
        missing_parts = [part for part in required_parts if part not in css]
        if missing_parts:
            raise Exception(f"Missing CSS parts: {missing_parts}")
        
        print("✓ CSS structure is correct for injection")
        print(f"✓ CSS ready for QTextEdit document injection ({len(css)} chars)")
        
        # Test cache clearing behavior
        font_service.clear_cache()
        css2 = font_service.get_semantic_font_css()
        
        if len(css2) == 0:
            raise Exception("CSS generation failed after cache clear")
        
        print("✓ CSS regeneration after cache clear works")
        
        # Test that font updates trigger new CSS
        original_ai_config = font_service.get_font_config('ai_response')
        font_service.update_font_config('ai_response', size=15)
        
        css_after_update = font_service.get_semantic_font_css()
        if "15pt" not in css_after_update:
            raise Exception("CSS not updated after font configuration change")
        
        # Restore
        font_service.update_font_config('ai_response', size=original_ai_config['size'])
        
        print("✓ CSS updates correctly when font settings change")
        
        return True
        
    except Exception as e:
        print(f"❌ CSS injection simulation failed: {e}")
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Full Integration Tests for Font Inheritance Fix")
    
    tests = [
        test_full_theme_switching_workflow,
        test_css_injection_simulation
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Integration Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)} tests")
    
    if all(results):
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("The font inheritance fix is working correctly end-to-end.")
        return True
    else:
        failed_tests = [test.__name__ for test, result in zip(tests, results) if not result]
        print(f"❌ Failed tests: {', '.join(failed_tests)}")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)