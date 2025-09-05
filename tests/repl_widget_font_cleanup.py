#!/usr/bin/env python3
"""
Script to clean up font methods in REPL widget.
"""

import re

# Read the file
with open('ghostman/src/presentation/widgets/repl_widget.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the entire refresh_fonts method and its leftover code
pattern = r'def refresh_fonts\(self\):.*?(?=\n    def |\nclass |\Z)'
replacement = '''def refresh_fonts(self):
        """No-op - using fixed fonts (Tahoma for text, Courier for code)."""
        logger.info("🔤 Font refresh called - using default fonts (Tahoma/Courier)")
    '''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Replace _update_existing_font_formatting method
pattern = r'def _update_existing_font_formatting\(self\):.*?(?=\n    def |\nclass |\Z)'
replacement = '''def _update_existing_font_formatting(self):
        """No-op - using fixed fonts."""
        pass
    '''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Replace _update_existing_content_fonts method  
pattern = r'def _update_existing_content_fonts\(self\):.*?(?=\n    def |\nclass |\Z)'
replacement = '''def _update_existing_content_fonts(self):
        """No-op - using fixed fonts."""
        pass
    '''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('ghostman/src/presentation/widgets/repl_widget.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Font methods cleaned up successfully")