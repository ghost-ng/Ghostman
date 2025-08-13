#!/usr/bin/env python3
"""
Test script to verify font refresh functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

from ghostman.src.application.font_service import font_service
from ghostman.src.infrastructure.storage.settings_manager import settings

def test_font_refresh():
    """Test font refresh functionality."""
    print("=== Testing Font Refresh ===\n")
    
    # Test 1: Check initial font settings
    print("1. Initial font settings:")
    ai_config = font_service.get_font_config('ai_response')
    user_config = font_service.get_font_config('user_input')
    print(f"   AI Response: {ai_config}")
    print(f"   User Input: {user_config}")
    
    # Test 2: Update AI response font
    print("\n2. Updating AI response font to Arial 16pt bold:")
    font_service.update_font_config('ai_response', 
                                   family='Arial', 
                                   size=16, 
                                   weight='bold')
    
    updated_ai_config = font_service.get_font_config('ai_response')
    print(f"   Updated AI Response: {updated_ai_config}")
    
    # Test 3: Update user input font
    print("\n3. Updating user input font to Courier New 12pt italic:")
    font_service.update_font_config('user_input',
                                   family='Courier New',
                                   size=12,
                                   style='italic')
    
    updated_user_config = font_service.get_font_config('user_input')
    print(f"   Updated User Input: {updated_user_config}")
    
    # Test 4: Generate new CSS
    print("\n4. Generated CSS with new fonts:")
    ai_css = font_service.get_css_font_style('ai_response')
    user_css = font_service.get_css_font_style('user_input')
    print(f"   AI CSS: {ai_css}")
    print(f"   User CSS: {user_css}")
    
    # Test 5: Verify settings were saved
    print("\n5. Verifying settings were saved:")
    saved_ai = settings.get('fonts.ai_response')
    saved_user = settings.get('fonts.user_input')
    print(f"   Saved AI settings: {saved_ai}")
    print(f"   Saved User settings: {saved_user}")
    
    # Test 6: Reset to defaults
    print("\n6. Resetting to defaults:")
    font_service.update_font_config('ai_response',
                                   family='Segoe UI',
                                   size=11,
                                   weight='normal',
                                   style='normal')
    font_service.update_font_config('user_input',
                                   family='Consolas',
                                   size=10,
                                   weight='normal',
                                   style='normal')
    
    final_ai = font_service.get_font_config('ai_response')
    final_user = font_service.get_font_config('user_input')
    print(f"   Reset AI: {final_ai}")
    print(f"   Reset User: {final_user}")
    
    print("\n=== Font Refresh Test Complete ===")

if __name__ == "__main__":
    test_font_refresh()