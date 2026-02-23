"""
Universal Pygments-based syntax highlighter for PyQt6.
Supports 500+ languages without hardcoded patterns.
"""

from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt
import logging
from typing import Dict, Optional, Any

try:
    import pygments
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, guess_lexer, get_all_lexers
    from pygments.token import Token
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    logging.warning("Pygments not available - syntax highlighting will be limited")

logger = logging.getLogger('specter.pygments_highlighter')


class PygmentsSyntaxHighlighter(QSyntaxHighlighter):
    """
    Universal syntax highlighter using Pygments for 500+ language support.
    Automatically adapts to theme colors without hardcoded patterns.
    """
    
    # Map Pygments token types to semantic categories
    TOKEN_MAPPING = {
        Token.Keyword: 'keyword',
        Token.Keyword.Namespace: 'keyword',
        Token.Keyword.Type: 'builtin',
        Token.Keyword.Constant: 'builtin',
        
        Token.Name.Builtin: 'builtin',
        Token.Name.Builtin.Pseudo: 'builtin',
        Token.Name.Class: 'class',
        Token.Name.Function: 'function',
        Token.Name.Decorator: 'decorator',
        Token.Name.Variable: 'variable',
        Token.Name.Constant: 'constant',
        Token.Name.Entity: 'entity',
        Token.Name.Attribute: 'attribute',
        Token.Name.Tag: 'tag',
        Token.Name.Label: 'label',
        
        Token.String: 'string',
        Token.String.Single: 'string',
        Token.String.Double: 'string',
        Token.String.Backtick: 'string',
        Token.String.Doc: 'docstring',
        Token.String.Interpol: 'string',
        Token.String.Escape: 'escape',
        Token.String.Regex: 'regex',
        
        Token.Number: 'number',
        Token.Number.Integer: 'number',
        Token.Number.Float: 'number',
        Token.Number.Hex: 'number',
        Token.Number.Oct: 'number',
        Token.Number.Bin: 'number',
        
        Token.Operator: 'operator',
        Token.Operator.Word: 'keyword',
        
        Token.Comment: 'comment',
        Token.Comment.Single: 'comment',
        Token.Comment.Multiline: 'comment',
        Token.Comment.Special: 'comment',
        Token.Comment.Preproc: 'preprocessor',
        
        Token.Generic.Deleted: 'diff_deleted',
        Token.Generic.Inserted: 'diff_inserted',
        Token.Generic.Heading: 'heading',
        Token.Generic.Subheading: 'subheading',
        Token.Generic.Strong: 'strong',
        Token.Generic.Emph: 'emphasis',
        
        Token.Error: 'error',
    }
    
    def __init__(self, document, language: str = None, code: str = None, theme_colors: Dict[str, str] = None):
        """
        Initialize the Pygments syntax highlighter.
        
        Args:
            document: QTextDocument to highlight
            language: Programming language name (e.g., 'python', 'javascript')
            code: Optional code sample for language detection
            theme_colors: Theme color dictionary for styling
        """
        super().__init__(document)
        
        if not PYGMENTS_AVAILABLE:
            logger.warning("Pygments not available - highlighting disabled")
            return
            
        self.language = language or 'text'
        self.theme_colors = theme_colors or self._get_default_colors()
        self.lexer = self._get_or_detect_lexer(language, code)
        self.token_formats = self._create_token_formats()
        
        logger.debug(f"Initialized Pygments highlighter for language: {self.lexer.name}")
    
    def _get_default_colors(self) -> Dict[str, str]:
        """Get default color scheme if no theme provided."""
        # Import the universal color adapter if available
        try:
            from .universal_syntax_colors import UniversalSyntaxColorAdapter
            adapter = UniversalSyntaxColorAdapter()
            # Get colors for a default dark theme
            default_theme = {
                'bg_primary': '#1e1e1e',
                'bg_tertiary': '#2d2d2d',
                'text_primary': '#d4d4d4',
            }
            return adapter.get_syntax_colors(default_theme)
        except ImportError:
            # Fallback to VS Code dark theme colors
            return {
                'keyword': '#569cd6',      # Blue
                'string': '#ce9178',       # Orange/brown
                'comment': '#6a9955',      # Green
                'function': '#dcdcaa',     # Yellow
                'number': '#b5cea8',       # Light green
                'builtin': '#4ec9b0',      # Cyan
                'operator': '#d4d4d4',     # Light gray
                'class': '#4ec9b0',        # Cyan
                'variable': '#9cdcfe',     # Light blue
                'constant': '#4fc1ff',     # Bright blue
                'decorator': '#ffd700',    # Gold
                'docstring': '#6a9955',    # Green
                'preprocessor': '#c586c0', # Purple
                'error': '#f48771',        # Red
            }
    
    def _get_or_detect_lexer(self, language: str = None, code: str = None):
        """
        Get appropriate lexer for the language or detect from code.
        
        Args:
            language: Language name if known
            code: Code sample for detection
            
        Returns:
            Pygments lexer instance
        """
        lexer = None
        
        # Try to get lexer by language name
        if language:
            try:
                # Handle common aliases and normalize language names
                language_map = {
                    'js': 'javascript',
                    'ts': 'typescript', 
                    'py': 'python',
                    'rb': 'ruby',
                    'yml': 'yaml',
                    'sh': 'bash',
                    'shell': 'bash',
                    'dockerfile': 'docker',
                    'golang': 'go',
                    'rs': 'rust',
                    'pl': 'perl',
                    'cs': 'csharp',
                    'c++': 'cpp',
                    'c#': 'csharp',
                    'powershell': 'ps1',
                    'make': 'makefile',
                    'docker': 'dockerfile',
                }
                normalized_lang = language_map.get(language.lower(), language.lower())
                lexer = get_lexer_by_name(normalized_lang, stripall=True)
                logger.debug(f"✅ Got lexer for language: {normalized_lang} -> {lexer.name}")
            except ClassNotFound:
                logger.warning(f"❌ No lexer found for language: '{language}' (normalized: '{normalized_lang}')")
        
        # Try to detect from code if no lexer yet
        if not lexer and code:
            try:
                lexer = guess_lexer(code)
                logger.debug(f"Detected language: {lexer.name}")
            except Exception as e:
                logger.debug(f"Failed to detect language: {e}")
        
        # Fallback to plain text
        if not lexer:
            try:
                lexer = get_lexer_by_name('text')
            except:
                # Ultimate fallback - create a basic lexer
                from pygments.lexer import Lexer
                
                class PlainTextLexer(Lexer):
                    name = 'PlainText'
                    aliases = ['text']
                    filenames = ['*.txt']
                    
                    def get_tokens(self, text):
                        yield 0, Token.Text, text
                
                lexer = PlainTextLexer()
        
        return lexer
    
    def _create_token_formats(self) -> Dict[Any, QTextCharFormat]:
        """
        Create QTextCharFormat objects for each token type.
        
        Returns:
            Dictionary mapping token types to format objects
        """
        formats = {}
        
        # Create formats for each semantic category
        for token_type, category in self.TOKEN_MAPPING.items():
            format_obj = QTextCharFormat()
            
            # Get color for this category
            color = self.theme_colors.get(category)
            if color:
                format_obj.setForeground(QColor(color))
            
            # Apply special formatting
            if category in ['keyword', 'builtin']:
                format_obj.setFontWeight(QFont.Weight.Bold)
            elif category == 'comment' or category == 'docstring':
                format_obj.setFontItalic(True)
            elif category in ['strong', 'heading']:
                format_obj.setFontWeight(QFont.Weight.Bold)
            elif category in ['emphasis']:
                format_obj.setFontItalic(True)
            elif category == 'error':
                format_obj.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
                if color:
                    format_obj.setUnderlineColor(QColor(color))
            
            formats[token_type] = format_obj
        
        return formats
    
    def highlightBlock(self, text: str):
        """
        Apply syntax highlighting to a block of text using Pygments.
        
        Args:
            text: Text block to highlight
        """
        if not PYGMENTS_AVAILABLE or not self.lexer:
            return
        
        try:
            # Get tokens from Pygments
            tokens = list(self.lexer.get_tokens(text))
            
            # Apply formatting for each token
            index = 0
            for token_type, value in tokens:
                length = len(value)
                
                # Find the best matching format
                format_obj = self._find_format_for_token(token_type)
                
                if format_obj:
                    self.setFormat(index, length, format_obj)
                
                index += length
                
        except Exception as e:
            logger.debug(f"Highlighting failed for block: {e}")
    
    def _find_format_for_token(self, token_type) -> Optional[QTextCharFormat]:
        """
        Find the best matching format for a token type.
        
        Args:
            token_type: Pygments token type
            
        Returns:
            QTextCharFormat object or None
        """
        # Direct match
        if token_type in self.token_formats:
            return self.token_formats[token_type]
        
        # Try parent token types
        # Token types are hierarchical (e.g., Token.Name.Function -> Token.Name -> Token)
        current = token_type
        while current != Token:
            current = current.parent
            if current in self.token_formats:
                return self.token_formats[current]
        
        return None
    
    def update_theme_colors(self, theme_colors: Dict[str, str]):
        """
        Update the color scheme when theme changes.
        
        Args:
            theme_colors: New theme color dictionary
        """
        self.theme_colors = theme_colors
        self.token_formats = self._create_token_formats()
        self.rehighlight()  # Re-apply highlighting with new colors
    
    def set_language(self, language: str, code: str = None):
        """
        Change the highlighting language.
        
        Args:
            language: New language name
            code: Optional code for language detection
        """
        self.language = language
        self.lexer = self._get_or_detect_lexer(language, code)
        self.rehighlight()  # Re-apply highlighting for new language
    
    @staticmethod
    def get_supported_languages() -> list:
        """
        Get list of all supported languages.
        
        Returns:
            List of (name, aliases, filenames, mimetypes) tuples
        """
        if not PYGMENTS_AVAILABLE:
            return []
        
        return list(get_all_lexers())
    
    @staticmethod
    def detect_language(code: str) -> str:
        """
        Detect the programming language from code.
        
        Args:
            code: Code sample
            
        Returns:
            Detected language name or 'text'
        """
        if not PYGMENTS_AVAILABLE:
            return 'text'
        
        try:
            lexer = guess_lexer(code)
            return lexer.aliases[0] if lexer.aliases else lexer.name.lower()
        except:
            return 'text'