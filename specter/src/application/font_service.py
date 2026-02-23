"""
Font Configuration Service for Specter.

Manages font settings for AI responses and user input with separate configurations.
"""

import logging
from typing import Dict, Any
from PyQt6.QtGui import QFont, QFontDatabase
from ..infrastructure.storage.settings_manager import settings

logger = logging.getLogger("specter.font_service")


class FontService:
    """Service to manage font configurations for different text types."""
    
    def __init__(self):
        """Initialize the font service."""
        self._font_cache = {}
        self._css_cache = {}  # Cache for CSS generation
        self._available_fonts = None
        self._monospace_fonts = None
        
    def get_available_fonts(self) -> list:
        """
        Get list of available system fonts.
        
        Returns:
            List of font family names available on the system
        """
        if self._available_fonts is None:
            try:
                # Use static method to get QFontDatabase instance
                font_families = QFontDatabase.families()
                self._available_fonts = sorted(font_families)
                logger.debug(f"Loaded {len(self._available_fonts)} available fonts")
            except Exception as e:
                logger.warning(f"Failed to load system fonts: {e}")
                # Fallback to common fonts
                self._available_fonts = [
                    'Arial', 'Calibri', 'Consolas', 'Courier New', 'Georgia',
                    'Helvetica', 'Impact', 'Lucida Console', 'Segoe UI', 'Tahoma',
                    'Times New Roman', 'Trebuchet MS', 'Verdana'
                ]
        
        return self._available_fonts
    
    def get_monospace_fonts(self) -> list:
        """
        Get list of available monospace fonts.
        
        Returns:
            List of monospace font family names
        """
        if self._monospace_fonts is None:
            try:
                # Use static method to get font families
                all_families = QFontDatabase.families()
                
                # Common monospace fonts (guaranteed to be monospace)
                known_monospace = [
                    'Consolas', 'Courier New', 'Courier', 'Monaco', 'Menlo',
                    'DejaVu Sans Mono', 'Liberation Mono', 'Lucida Console',
                    'Source Code Pro', 'Ubuntu Mono', 'Fira Code', 'JetBrains Mono',
                    'Roboto Mono', 'SF Mono', 'Cascadia Code', 'Cascadia Mono'
                ]
                
                # Filter known monospace fonts that are available
                monospace_fonts = []
                for font in known_monospace:
                    if font in all_families:
                        monospace_fonts.append(font)
                
                # Test remaining fonts for monospace characteristics
                for family in all_families:
                    if family not in monospace_fonts:
                        if self._is_monospace_font(family):
                            monospace_fonts.append(family)
                
                self._monospace_fonts = sorted(monospace_fonts)
                logger.debug(f"Found {len(self._monospace_fonts)} monospace fonts")
                
            except Exception as e:
                logger.warning(f"Failed to detect monospace fonts: {e}")
                # Fallback to guaranteed monospace fonts
                self._monospace_fonts = [
                    'Consolas', 'Courier New', 'Lucida Console', 'Monaco'
                ]
        
        return self._monospace_fonts
    
    def _is_monospace_font(self, family: str) -> bool:
        """
        Test if a font family is monospace by comparing character widths.
        
        Args:
            family: Font family name to test
            
        Returns:
            True if the font appears to be monospace
        """
        try:
            from PyQt6.QtGui import QFontMetrics
            font = QFont(family, 12)
            font_metrics = QFontMetrics(font)
            
            if font_metrics is None:
                return False
                
            # Test characters that should have same width in monospace fonts
            test_chars = ['i', 'l', 'W', 'M', '0', '1']
            widths = [font_metrics.horizontalAdvance(char) for char in test_chars]
            
            # In monospace fonts, all characters should have the same width
            # Allow small variations due to rounding/rendering differences
            max_width = max(widths)
            min_width = min(widths)
            
            # Consider monospace if width variation is less than 2 pixels
            is_mono = (max_width - min_width) <= 1
            
            if is_mono:
                logger.debug(f"Detected monospace font: {family}")
            
            return is_mono
            
        except Exception as e:
            logger.debug(f"Error testing font {family}: {e}")
            return False
    
    def get_font_config(self, font_type: str) -> Dict[str, Any]:
        """
        Get font configuration for a specific type.
        
        Args:
            font_type: 'ai_response', 'user_input', or 'code_snippets'
            
        Returns:
            Dictionary with font configuration
        """
        try:
            config = settings.get(f'fonts.{font_type}', {})
            
            # Ensure all required keys exist with defaults
            defaults = {
                'ai_response': {
                    'family': 'Segoe UI',
                    'size': 11,
                    'weight': 'normal',
                    'style': 'normal'
                },
                'user_input': {
                    'family': 'Consolas',
                    'size': 10,
                    'weight': 'normal',
                    'style': 'normal'
                },
                'code_snippets': {
                    'family': 'Consolas',
                    'size': 10,
                    'weight': 'normal',
                    'style': 'normal'
                }
            }
            
            default_config = defaults.get(font_type, defaults['ai_response'])
            
            # Merge with defaults
            for key, default_value in default_config.items():
                if key not in config:
                    config[key] = default_value
            
            logger.debug(f"Font config for {font_type}: {config}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to get font config for {font_type}: {e}")
            # Return safe defaults
            if font_type == 'user_input':
                return {'family': 'Consolas', 'size': 10, 'weight': 'normal', 'style': 'normal'}
            elif font_type == 'code_snippets':
                return {'family': 'Consolas', 'size': 10, 'weight': 'normal', 'style': 'normal'}
            else:
                return {'family': 'Segoe UI', 'size': 11, 'weight': 'normal', 'style': 'normal'}
    
    def create_qfont(self, font_type: str) -> QFont:
        """
        Create a QFont object for the specified font type.
        
        Args:
            font_type: 'ai_response', 'user_input', or 'code_snippets'
            
        Returns:
            QFont object configured with the settings
        """
        # Check cache first
        cache_key = font_type
        if cache_key in self._font_cache:
            cached_config, cached_font = self._font_cache[cache_key]
            current_config = self.get_font_config(font_type)
            
            # Return cached font if config hasn't changed
            if cached_config == current_config:
                return QFont(cached_font)  # Return a copy
        
        try:
            config = self.get_font_config(font_type)
            
            # Create QFont
            font = QFont()
            font.setFamily(config['family'])
            font.setPointSize(config['size'])
            
            # Set weight
            if config['weight'] == 'bold':
                font.setWeight(QFont.Weight.Bold)
            else:
                font.setWeight(QFont.Weight.Normal)
            
            # Set style
            if config['style'] == 'italic':
                font.setItalic(True)
            else:
                font.setItalic(False)
            
            # Ensure monospace hint for code fonts
            if font_type == 'code_snippets':
                font.setStyleHint(QFont.StyleHint.Monospace)
            
            # Cache the font
            self._font_cache[cache_key] = (config.copy(), QFont(font))
            
            logger.debug(f"Created QFont for {font_type}: {config}")
            return font
            
        except Exception as e:
            logger.error(f"Failed to create QFont for {font_type}: {e}")
            # Return system default font
            return QFont()
    
    def update_font_config(self, font_type: str, **config_updates):
        """
        Update font configuration for a specific type.
        
        Args:
            font_type: 'ai_response', 'user_input', or 'code_snippets'
            **config_updates: Font configuration updates (family, size, weight, style)
        """
        try:
            current_config = self.get_font_config(font_type)
            
            # Update with new values
            for key, value in config_updates.items():
                if key in ['family', 'size', 'weight', 'style']:
                    current_config[key] = value
                else:
                    logger.warning(f"Unknown font config key: {key}")
            
            # Validate font family
            if 'family' in config_updates:
                available_fonts = self.get_available_fonts()
                if current_config['family'] not in available_fonts:
                    logger.warning(f"Font family '{current_config['family']}' not available, keeping current")
                    current_config['family'] = self.get_font_config(font_type)['family']
            
            # Validate font size
            if 'size' in config_updates:
                size = current_config['size']
                if not isinstance(size, int) or size < 6 or size > 72:
                    logger.warning(f"Invalid font size {size}, using default")
                    if font_type == 'ai_response':
                        current_config['size'] = 11
                    else:  # user_input or code_snippets
                        current_config['size'] = 10
            
            # Save to settings
            settings.set(f'fonts.{font_type}', current_config)
            settings.save()
            
            # Clear all caches to force recreation with new settings
            if font_type in self._font_cache:
                del self._font_cache[font_type]
            self._css_cache.clear()  # Clear CSS cache when any font changes
            
            logger.info(f"Updated font config for {font_type}: {config_updates}")
            logger.debug("Cleared CSS cache due to font configuration change")
            
        except Exception as e:
            logger.error(f"Failed to update font config for {font_type}: {e}")
    
    def get_css_font_style(self, font_type: str) -> str:
        """
        Get CSS font style string for the specified font type.
        
        Args:
            font_type: 'ai_response', 'user_input', or 'code_snippets'
            
        Returns:
            CSS font style string
        """
        try:
            config = self.get_font_config(font_type)
            
            css_parts = []
            css_parts.append(f"font-family: '{config['family']}'")
            css_parts.append(f"font-size: {config['size']}pt")
            
            if config['weight'] == 'bold':
                css_parts.append("font-weight: bold")
            
            if config['style'] == 'italic':
                css_parts.append("font-style: italic")
            
            css_style = "; ".join(css_parts)
            logger.debug(f"Generated CSS for {font_type}: {css_style}")
            return css_style
            
        except Exception as e:
            logger.error(f"Failed to generate CSS for {font_type}: {e}")
            return "font-family: 'Segoe UI'; font-size: 11pt"
    
    def get_semantic_css_variables(self) -> str:
        """
        Generate CSS custom properties (variables) for semantic font targeting.
        
        Returns:
            CSS custom properties defining font variables for reliable targeting
        """
        try:
            ai_config = self.get_font_config('ai_response')
            user_config = self.get_font_config('user_input')
            code_config = self.get_font_config('code_snippets')
            
            css_vars = f"""
            :root {{
                /* AI Response Font Variables */
                --gm-ai-response-font-family: '{ai_config['family']}';
                --gm-ai-response-font-size: {ai_config['size']}pt;
                --gm-ai-response-font-weight: {ai_config['weight']};
                --gm-ai-response-font-style: {ai_config['style']};
                
                /* User Input Font Variables */
                --gm-user-input-font-family: '{user_config['family']}';
                --gm-user-input-font-size: {user_config['size']}pt;
                --gm-user-input-font-weight: {user_config['weight']};
                --gm-user-input-font-style: {user_config['style']};
                
                /* Code Snippets Font Variables */
                --gm-code-snippets-font-family: '{code_config['family']}';
                --gm-code-snippets-font-size: {code_config['size']}pt;
                --gm-code-snippets-font-weight: {code_config['weight']};
                --gm-code-snippets-font-style: {code_config['style']};
            }}
            """
            
            logger.debug("Generated semantic CSS variables for font targeting")
            return css_vars
            
        except Exception as e:
            logger.error(f"Failed to generate semantic CSS variables: {e}")
            return ":root { --gm-ai-response-font-family: 'Segoe UI'; --gm-ai-response-font-size: 11pt; }"
    
    def get_semantic_font_css(self) -> str:
        """
        Generate comprehensive CSS for semantic font targeting with high specificity.
        
        Returns:
            Complete CSS rules for reliable font application
        """
        try:
            variables_css = self.get_semantic_css_variables()
            
            targeting_css = """
            /* Specter Semantic Font Targeting - High Specificity Layer */
            @layer specter-fonts {
                /* AI Response Text Targeting */
                .specter-message-container.specter-ai-response .gm-text,
                .specter-message-container.specter-ai-response .gm-text p,
                .specter-message-container.specter-ai-response .gm-text span,
                .specter-message-container.specter-ai-response .gm-text div,
                .specter-message-container.specter-ai-response .gm-heading,
                .specter-message-container.specter-ai-response .gm-emphasis,
                .specter-message-container.specter-ai-response .gm-strong,
                .specter-message-container.specter-ai-response .gm-quote,
                .specter-message-container.specter-ai-response .gm-link {
                    font-family: var(--gm-ai-response-font-family) !important;
                    font-size: var(--gm-ai-response-font-size) !important;
                    font-weight: var(--gm-ai-response-font-weight) !important;
                    font-style: var(--gm-ai-response-font-style) !important;
                }
                
                /* User Input Text Targeting */
                .specter-message-container.specter-user-input .gm-text,
                .specter-message-container.specter-user-input .gm-text p,
                .specter-message-container.specter-user-input .gm-text span,
                .specter-message-container.specter-user-input .gm-text div,
                .specter-message-container.specter-user-input .gm-heading,
                .specter-message-container.specter-user-input .gm-emphasis,
                .specter-message-container.specter-user-input .gm-strong,
                .specter-message-container.specter-user-input .gm-quote,
                .specter-message-container.specter-user-input .gm-link {
                    font-family: var(--gm-user-input-font-family) !important;
                    font-size: var(--gm-user-input-font-size) !important;
                    font-weight: var(--gm-user-input-font-weight) !important;
                    font-style: var(--gm-user-input-font-style) !important;
                }
                
                /* Code Elements Targeting - Highest Priority */
                .specter-message-container .gm-code-inline,
                .specter-message-container .gm-code-block,
                .specter-message-container .gm-code-block code,
                .specter-message-container .gm-code-block pre,
                .specter-message-container .gm-code-block *,
                .specter-message-container code.gm-code-inline,
                .specter-message-container pre.gm-code-block,
                .specter-message-container pre.gm-code-block * {
                    font-family: var(--gm-code-snippets-font-family) !important;
                    font-size: var(--gm-code-snippets-font-size) !important;
                    font-weight: var(--gm-code-snippets-font-weight) !important;
                    font-style: var(--gm-code-snippets-font-style) !important;
                }
                
                /* Override any nested font inheritance */
                .specter-message-container.specter-ai-response .gm-text *:not(.gm-code-inline):not(.gm-code-block):not(code):not(pre) {
                    font-family: var(--gm-ai-response-font-family) !important;
                    font-size: var(--gm-ai-response-font-size) !important;
                }
                
                .specter-message-container.specter-user-input .gm-text *:not(.gm-code-inline):not(.gm-code-block):not(code):not(pre) {
                    font-family: var(--gm-user-input-font-family) !important;
                    font-size: var(--gm-user-input-font-size) !important;
                }
                
                /* Prevent theme overrides by using QTextEdit specificity */
                QTextEdit .specter-message-container.specter-ai-response .gm-text,
                QTextEdit .specter-message-container.specter-ai-response .gm-text * {
                    font-family: var(--gm-ai-response-font-family) !important;
                }
                
                QTextEdit .specter-message-container.specter-user-input .gm-text,
                QTextEdit .specter-message-container.specter-user-input .gm-text * {
                    font-family: var(--gm-user-input-font-family) !important;
                }
                
                QTextEdit .specter-message-container .gm-code-inline,
                QTextEdit .specter-message-container .gm-code-block,
                QTextEdit .specter-message-container .gm-code-block * {
                    font-family: var(--gm-code-snippets-font-family) !important;
                }
            }
            """
            
            complete_css = variables_css + targeting_css
            logger.debug("Generated complete semantic font CSS")
            return complete_css
            
        except Exception as e:
            logger.error(f"Failed to generate semantic font CSS: {e}")
            return self.get_semantic_css_variables()  # Fallback to just variables
    
    def clear_cache(self):
        """Clear all font and CSS caches to force recreation."""
        self._font_cache.clear()
        self._css_cache.clear()
        logger.debug("Font and CSS caches cleared")


# Global instance
font_service = FontService()