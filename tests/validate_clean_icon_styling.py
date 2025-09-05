"""
Programmatic validation of clean icon styling for save and plus buttons across themes.

Tests the clean icon styling system without requiring a GUI, validating that
the styling generates proper CSS for all improved themes.
"""

import sys
import os

# Add the ghostman source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

def test_clean_icon_styling():
    """Test clean icon styling across all improved themes."""
    try:
        from ghostman.src.ui.themes.improved_preset_themes import get_improved_preset_themes
        from ghostman.src.ui.themes.icon_styling import IconStyleManager
        
        print("Clean Icon Styling Validation")
        print("=" * 50)
        
        improved_themes = get_improved_preset_themes()
        print(f"Testing clean icon styling across {len(improved_themes)} improved themes...\n")
        
        test_results = []
        
        for theme_name, color_system in improved_themes.items():
            print(f"Testing theme: {theme_name}")
            print("-" * 30)
            
            # Test different icon types
            icon_types = ["save", "plus", "normal", "close"]
            
            theme_results = {"theme": theme_name, "tests": {}}
            
            for icon_type in icon_types:
                try:
                    # Generate clean icon style CSS
                    css = IconStyleManager.get_clean_icon_style(color_system, icon_type, 16)
                    
                    # Validate CSS contains expected elements
                    css_valid = (
                        "QPushButton" in css and
                        "QToolButton" in css and
                        "background-color:" in css and
                        "color:" in css and
                        "border:" in css and
                        "/* No box-shadow, no gradients, no special effects */" in css
                    )
                    
                    # Check for clean hover/active states
                    hover_clean = (
                        ":hover" in css and
                        "/* Clean hover - just background change */" in css
                    )
                    
                    active_clean = (
                        ":pressed" in css and
                        "/* Clean pressed state - no special effects */" in css
                    )
                    
                    result = {
                        "css_generated": True,
                        "css_valid": css_valid,
                        "hover_clean": hover_clean,
                        "active_clean": active_clean,
                        "css_length": len(css)
                    }
                    
                    theme_results["tests"][icon_type] = result
                    
                    status = "✓ PASS" if all([css_valid, hover_clean, active_clean]) else "✗ FAIL"
                    print(f"  {icon_type:>8} icons: {status}")
                    
                except Exception as e:
                    theme_results["tests"][icon_type] = {
                        "css_generated": False,
                        "error": str(e)
                    }
                    print(f"  {icon_type:>8} icons: ✗ ERROR - {e}")
            
            test_results.append(theme_results)
            print()
        
        # Summary
        print("Summary")
        print("=" * 50)
        
        total_tests = len(improved_themes) * 4  # 4 icon types per theme
        passed_tests = 0
        
        for result in test_results:
            theme_passed = 0
            theme_total = 0
            
            for icon_type, test_result in result["tests"].items():
                theme_total += 1
                if (test_result.get("css_generated", False) and 
                    test_result.get("css_valid", False) and 
                    test_result.get("hover_clean", False) and 
                    test_result.get("active_clean", False)):
                    theme_passed += 1
                    passed_tests += 1
            
            status = "✓ PASS" if theme_passed == theme_total else "✗ PARTIAL"
            print(f"{result['theme']:>25}: {theme_passed}/{theme_total} {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! Clean icon styling system is working correctly.")
            return True
        else:
            print(f"\n⚠️ {total_tests - passed_tests} tests failed. Review the issues above.")
            return False
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this from the Ghostman directory")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def test_theme_integration():
    """Test integration with theme manager."""
    try:
        from ghostman.src.ui.themes.theme_manager import get_theme_manager
        
        print("\nTheme Manager Integration Test")
        print("=" * 50)
        
        theme_manager = get_theme_manager()
        print(f"Theme manager loaded: {type(theme_manager).__name__}")
        print(f"Current theme: {theme_manager.current_theme_name}")
        
        # Test integration methods exist
        methods_to_test = [
            'apply_clean_icon_styling',
            'apply_save_button_styling', 
            'apply_plus_button_styling'
        ]
        
        for method_name in methods_to_test:
            if hasattr(theme_manager, method_name):
                print(f"✓ {method_name} method available")
            else:
                print(f"✗ {method_name} method missing")
                return False
        
        print("✓ All integration methods available")
        return True
        
    except Exception as e:
        print(f"Theme manager integration test failed: {e}")
        return False


def test_color_contrast():
    """Test that save and plus buttons have adequate contrast."""
    try:
        from ghostman.src.ui.themes.improved_preset_themes import get_improved_preset_themes
        from ghostman.src.ui.themes.icon_styling import IconStyleManager
        
        print("\nColor Contrast Validation")
        print("=" * 50)
        
        improved_themes = get_improved_preset_themes()
        contrast_results = []
        
        for theme_name, color_system in improved_themes.items():
            # Test save button contrast
            save_contrast = IconStyleManager._calculate_contrast(
                color_system.status_success, color_system.background_secondary
            )
            
            # Test plus button contrast  
            plus_contrast = IconStyleManager._calculate_contrast(
                color_system.primary, color_system.background_secondary
            )
            
            # WCAG AA requires 4.5:1 for normal text, 3:1 for large text
            # Icons are typically considered large elements
            save_ok = save_contrast >= 3.0
            plus_ok = plus_contrast >= 3.0
            
            contrast_results.append({
                "theme": theme_name,
                "save_contrast": save_contrast,
                "plus_contrast": plus_contrast,
                "save_ok": save_ok,
                "plus_ok": plus_ok
            })
            
            save_status = "✓" if save_ok else "✗"
            plus_status = "✓" if plus_ok else "✗"
            
            print(f"{theme_name:>25}: Save {save_contrast:.1f}:1 {save_status} | Plus {plus_contrast:.1f}:1 {plus_status}")
        
        # Summary
        total_themes = len(contrast_results)
        good_save = sum(1 for r in contrast_results if r["save_ok"])
        good_plus = sum(1 for r in contrast_results if r["plus_ok"])
        
        print(f"\nContrast Summary:")
        print(f"Save button contrast: {good_save}/{total_themes} themes have adequate contrast")
        print(f"Plus button contrast: {good_plus}/{total_themes} themes have adequate contrast")
        
        return good_save == total_themes and good_plus == total_themes
        
    except Exception as e:
        print(f"Color contrast test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("Clean Icon Styling System Validation")
    print("=" * 60)
    print("Testing clean icon styling for save and plus buttons")
    print("across all redesigned themes...\n")
    
    # Run tests
    test1_passed = test_clean_icon_styling()
    test2_passed = test_theme_integration() 
    test3_passed = test_color_contrast()
    
    print("\n" + "=" * 60)
    print("Final Results:")
    print(f"✓ Clean Icon CSS Generation: {'PASS' if test1_passed else 'FAIL'}")
    print(f"✓ Theme Manager Integration: {'PASS' if test2_passed else 'FAIL'}")
    print(f"✓ Color Contrast Validation: {'PASS' if test3_passed else 'FAIL'}")
    
    if all([test1_passed, test2_passed, test3_passed]):
        print("\n🎉 All validation tests passed!")
        print("The clean icon styling system is ready for use.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)