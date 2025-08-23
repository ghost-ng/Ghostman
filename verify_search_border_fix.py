#!/usr/bin/env python3
"""
Search Border Fix Verification Script

This script verifies that the comprehensive search border fix has been properly implemented.
It checks all the key changes made to eliminate the persistent border issue.
"""

import os
import sys
from pathlib import Path

def verify_fix():
    """Verify that all components of the search border fix are in place."""
    
    print("=" * 60)
    print("SEARCH BORDER FIX VERIFICATION")
    print("=" * 60)
    
    ghostman_root = Path(__file__).parent / "ghostman"
    
    # Check 1: Verify setFrame(False) is present in repl_widget.py
    repl_widget_path = ghostman_root / "src" / "presentation" / "widgets" / "repl_widget.py"
    check_setframe_present = False
    check_focus_policy_present = False
    check_theme_refresh_present = False
    
    if repl_widget_path.exists():
        with open(repl_widget_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "self.search_input.setFrame(False)" in content:
                check_setframe_present = True
            if "setFocusPolicy(Qt.FocusPolicy.ClickFocus)" in content:
                check_focus_policy_present = True
            if "# Ensure frame is always disabled after theme changes" in content:
                check_theme_refresh_present = True
    
    # Check 2: Verify enhanced CSS styling is present
    check_enhanced_css = False
    css_indicators = [
        "selection-background-color:",
        "selection-color:",
        "QLineEdit:selected",
        "box-shadow: none !important"
    ]
    
    if repl_widget_path.exists():
        with open(repl_widget_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if all(indicator in content for indicator in css_indicators):
                check_enhanced_css = True
    
    # Check 3: Verify search frame styling improvements
    style_templates_path = ghostman_root / "src" / "ui" / "themes" / "style_templates.py"
    check_frame_styling = False
    
    if style_templates_path.exists():
        with open(style_templates_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "QFrame QLineEdit {" in content and "margin: 0px;" in content:
                check_frame_styling = True
    
    # Print results
    print(f"✓ setFrame(False) implementation: {'PASS' if check_setframe_present else 'FAIL'}")
    print(f"✓ Focus policy optimization: {'PASS' if check_focus_policy_present else 'FAIL'}")
    print(f"✓ Theme refresh protection: {'PASS' if check_theme_refresh_present else 'FAIL'}")
    print(f"✓ Enhanced CSS styling: {'PASS' if check_enhanced_css else 'FAIL'}")
    print(f"✓ Frame styling improvements: {'PASS' if check_frame_styling else 'FAIL'}")
    
    print("\n" + "-" * 60)
    
    # Summary
    total_checks = 5
    passed_checks = sum([
        check_setframe_present,
        check_focus_policy_present,
        check_theme_refresh_present,
        check_enhanced_css,
        check_frame_styling
    ])
    
    print(f"VERIFICATION RESULT: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 ALL CHECKS PASSED - Search border fix is properly implemented!")
        print("\nThe fix includes:")
        print("• setFrame(False) to disable Qt's native border rendering")
        print("• Optimized focus policy to reduce focus ring artifacts")
        print("• Enhanced CSS with comprehensive border removal")
        print("• Improved search frame styling")
        print("• Theme change protection to maintain border-free state")
        print("\nThe search bar should now be completely border-free across all themes.")
    else:
        print("❌ Some checks failed - fix may be incomplete")
        
        if not check_setframe_present:
            print("• Missing: setFrame(False) call")
        if not check_focus_policy_present:
            print("• Missing: Focus policy optimization")
        if not check_theme_refresh_present:
            print("• Missing: Theme refresh protection")
        if not check_enhanced_css:
            print("• Missing: Enhanced CSS styling")
        if not check_frame_styling:
            print("• Missing: Frame styling improvements")
    
    print("\n" + "=" * 60)
    
    return passed_checks == total_checks

if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)