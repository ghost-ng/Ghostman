#!/usr/bin/env python3
"""
Debug the Pygments syntax highlighting integration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

def test_pygments_directly():
    """Test Pygments highlighting directly."""
    print("🔍 Testing Pygments Integration")
    print("=" * 50)
    
    # Test 1: Check if Pygments is available
    try:
        import pygments
        from pygments.lexers import get_lexer_by_name
        from pygments.token import Token
        print("✅ Pygments imported successfully")
        print(f"   Version: {pygments.__version__}")
    except ImportError as e:
        print(f"❌ Pygments import failed: {e}")
        return False
    
    # Test 2: Test lexer creation
    try:
        lexer = get_lexer_by_name('python')
        print("✅ Python lexer created successfully")
        print(f"   Name: {lexer.name}")
        print(f"   Aliases: {lexer.aliases}")
    except Exception as e:
        print(f"❌ Lexer creation failed: {e}")
        return False
    
    # Test 3: Test tokenization
    test_code = '''def count_lines(filepath):
    """Count the number of lines in a text file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return len(f.readlines())

# Example usage
if __name__ == "__main__":
    path = "example.txt"
    try:
        print(count_lines(path))
    except FileNotFoundError:
        print(f"File not found: {path}")'''
    
    try:
        tokens = list(lexer.get_tokens(test_code))
        print("✅ Code tokenization successful")
        print(f"   Generated {len(tokens)} tokens")
        
        # Show first few tokens
        print("   Sample tokens:")
        for i, (token_type, value) in enumerate(tokens[:10]):
            if value.strip():
                print(f"     {token_type}: '{value.strip()}'")
    except Exception as e:
        print(f"❌ Tokenization failed: {e}")
        return False
    
    return True

def test_highlighter_class():
    """Test our PygmentsSyntaxHighlighter class."""
    print("\n🔍 Testing PygmentsSyntaxHighlighter Class")
    print("=" * 50)
    
    try:
        from ghostman.src.presentation.widgets.pygments_syntax_highlighter import PygmentsSyntaxHighlighter
        print("✅ PygmentsSyntaxHighlighter imported successfully")
    except ImportError as e:
        print(f"❌ PygmentsSyntaxHighlighter import failed: {e}")
        return False
    
    try:
        # Test supported languages
        languages = PygmentsSyntaxHighlighter.get_supported_languages()
        print(f"✅ Found {len(languages)} supported languages")
        
        # Show some example languages
        print("   Example languages:")
        for name, aliases, filenames, mimetypes in languages[:10]:
            if aliases:
                print(f"     {name} ({aliases[0]})")
    except Exception as e:
        print(f"❌ Language enumeration failed: {e}")
        return False
    
    # Test language detection
    test_codes = {
        'python': '''def hello_world():
    print("Hello, World!")
    return 42''',
        'javascript': '''function helloWorld() {
    console.log("Hello, World!");
    return 42;
}''',
        'json': '''{"name": "test", "version": "1.0.0", "active": true}'''
    }
    
    print("\n   Testing language detection:")
    for expected_lang, code in test_codes.items():
        try:
            detected = PygmentsSyntaxHighlighter.detect_language(code)
            print(f"     {expected_lang}: detected as '{detected}' ✅" if detected != 'text' else f"     {expected_lang}: detected as '{detected}' ⚠️")
        except Exception as e:
            print(f"     {expected_lang}: detection failed - {e} ❌")
    
    return True

def test_widget_integration():
    """Test the widget integration."""
    print("\n🔍 Testing Widget Integration")
    print("=" * 50)
    
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QTextDocument
    
    app = QApplication([])
    
    try:
        from ghostman.src.presentation.widgets.pygments_syntax_highlighter import PygmentsSyntaxHighlighter
        
        # Create a test document
        document = QTextDocument()
        document.setPlainText('''def greet(name):
    """Greet someone by name.""" 
    return f"Hello, {name}!"

print(greet("World"))''')
        
        # Test theme colors
        theme_colors = {
            'keyword': '#569cd6',   # Blue
            'string': '#ce9178',    # Orange
            'comment': '#6a9955',   # Green
            'function': '#dcdcaa',  # Yellow
            'number': '#b5cea8',    # Light green
            'builtin': '#4ec9b0',   # Cyan
        }
        
        # Create highlighter
        highlighter = PygmentsSyntaxHighlighter(document, 'python', theme_colors=theme_colors)
        print("✅ PygmentsSyntaxHighlighter created successfully")
        print(f"   Language: {highlighter.language}")
        print(f"   Lexer: {highlighter.lexer.name}")
        print(f"   Token formats: {len(highlighter.token_formats)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Widget integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Pygments Debug Test Suite")
    print("=" * 70)
    
    success_count = 0
    total_tests = 3
    
    if test_pygments_directly():
        success_count += 1
    
    if test_highlighter_class():
        success_count += 1
    
    if test_widget_integration():
        success_count += 1
    
    print("\n" + "=" * 70)
    print(f"🏁 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Pygments integration should be working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return success_count == total_tests

if __name__ == "__main__":
    main()