#!/usr/bin/env python3
"""
Universal Theme Compatibility Test

Tests the enhanced code snippet widget system across all 39 themes 
to validate:
1. HTML artifact elimination 
2. Copy button functionality
3. Universal color accessibility
4. Theme adaptation quality

Run this script to validate that all improvements work correctly.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QScrollArea, QLabel, QComboBox, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import logging

# Import the components we're testing
try:
    from ghostman.src.presentation.widgets.mixed_content_display import MixedContentDisplay
    from ghostman.src.presentation.widgets.embedded_code_widget import EmbeddedCodeSnippetWidget
    from ghostman.src.presentation.widgets.universal_syntax_colors import get_universal_syntax_colors, get_theme_compatibility_info
    from ghostman.src.ui.themes.preset_themes import get_preset_themes
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import components: {e}")
    COMPONENTS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('theme_compatibility_test')


class ThemeCompatibilityTester(QMainWindow):
    """Test interface for validating theme compatibility."""
    
    def __init__(self):
        super().__init__()
        self.themes = get_preset_themes() if COMPONENTS_AVAILABLE else {}
        self.current_theme = None
        self.test_results = {}
        
        self.setWindowTitle("Universal Theme Compatibility Tester")
        self.setGeometry(100, 100, 1200, 800)
        
        self._setup_ui()
        self._load_test_content()
        
        # Start with first theme
        if self.themes:
            first_theme = list(self.themes.keys())[0]
            self.theme_selector.setCurrentText(first_theme)
            self.change_theme(first_theme)
    
    def _setup_ui(self):
        """Setup the test interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # Test content area
        self.content_display = MixedContentDisplay() if COMPONENTS_AVAILABLE else QLabel("Components not available")
        layout.addWidget(self.content_display)
        
        # Results panel
        self.results_label = QLabel("Select a theme to see compatibility results")
        self.results_label.setWordWrap(True)
        self.results_label.setMaximumHeight(150)
        layout.addWidget(self.results_label)
    
    def _create_control_panel(self):
        """Create the control panel with theme selector and test buttons."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        # Theme selector
        layout.addWidget(QLabel("Theme:"))
        self.theme_selector = QComboBox()
        if self.themes:
            self.theme_selector.addItems(self.themes.keys())
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        layout.addWidget(self.theme_selector)
        
        # Test buttons
        test_html_btn = QPushButton("Test HTML Parsing")
        test_html_btn.clicked.connect(self.test_html_parsing)
        layout.addWidget(test_html_btn)
        
        test_copy_btn = QPushButton("Test Copy Function")
        test_copy_btn.clicked.connect(self.test_copy_functionality)
        layout.addWidget(test_copy_btn)
        
        test_all_btn = QPushButton("Test All Themes")
        test_all_btn.clicked.connect(self.test_all_themes)
        layout.addWidget(test_all_btn)
        
        layout.addStretch()
        
        return panel
    
    def _load_test_content(self):
        """Load test content including problematic HTML that caused artifacts."""
        if not COMPONENTS_AVAILABLE:
            return
            
        # Sample content with various code blocks that previously caused issues
        test_html = '''
        <p>Here's some Python code that previously caused HTML artifacts:</p>
        
        <div style="background-color: #094352; border: 1px solid #073642; border-radius: 8px; margin: 6px 0;">
            <div style="background-color: #073642; padding: 12px 16px; border-bottom: 1px solid #073642;">
                <span style="color: #839496; font-weight: 600;">PYTHON</span>
            </div>
            <pre style="margin: 0; padding: 16px; background-color: #094352; color: #839496;"><span style="color: #859900;">def</span> fibonacci(n):
    <span style="color: #586e75;"># Generate Fibonacci sequence</span>
    <span style="color: #859900;">if</span> n <= <span style="color: #d33682;">0</span>:
        <span style="color: #859900;">return</span> []
    <span style="color: #859900;">elif</span> n == <span style="color: #d33682;">1</span>:
        <span style="color: #859900;">return</span> [<span style="color: #d33682;">0</span>]
    
    fib = [<span style="color: #d33682;">0</span>, <span style="color: #d33682;">1</span>]
    <span style="color: #859900;">for</span> i <span style="color: #859900;">in</span> range(<span style="color: #d33682;">2</span>, n):
        fib.append(fib[i<span style="color: #d33682;">-1</span>] + fib[i<span style="color: #d33682;">-2</span>])
    
    <span style="color: #859900;">return</span> fib</pre>
        </div></div>
        
        <p>And here's some JavaScript that also caused issues:</p>
        
        <div style="background-color: #2d2d2d; border: 1px solid #404040; border-radius: 8px; margin: 6px 0;">
            <pre style="margin: 0; padding: 16px; background-color: #2d2d2d; color: #f0f0f0;"><span style="color: #569cd6;">function</span> fetchUserData(userId) {
    <span style="color: #6a9955;">// Async function to fetch user data</span>
    <span style="color: #569cd6;">return</span> <span style="color: #569cd6;">new</span> Promise(<span style="color: #569cd6;">async</span> (resolve, reject) => {
        <span style="color: #569cd6;">try</span> {
            <span style="color: #569cd6;">const</span> response = <span style="color: #569cd6;">await</span> fetch(<span style="color: #ce9178;">`/api/users/</span><span style="color: #9cdcfe;">${userId}</span><span style="color: #ce9178;">`</span>);
            <span style="color: #569cd6;">const</span> data = <span style="color: #569cd6;">await</span> response.json();
            resolve(data);
        } <span style="color: #569cd6;">catch</span> (error) {
            reject(error);
        }
    });
}</pre>
        </div></div><br>
        
        <p>The HTML artifacts like &quot;</div></div><br>&quot; should now be eliminated.</p>
        '''
        
        # Add this problematic HTML to test the fixes
        self.content_display.add_html_content(test_html)
        
    def change_theme(self, theme_name: str):
        """Change to a specific theme and update all components."""
        if not COMPONENTS_AVAILABLE or theme_name not in self.themes:
            return
            
        self.current_theme = self.themes[theme_name]
        logger.info(f"Changing to theme: {theme_name}")
        
        # Convert theme colors to dictionary format expected by components
        theme_colors = {
            'bg_primary': self.current_theme.background_primary,
            'bg_secondary': self.current_theme.background_secondary, 
            'bg_tertiary': self.current_theme.background_tertiary,
            'text_primary': self.current_theme.text_primary,
            'text_secondary': self.current_theme.text_secondary,
            'border': self.current_theme.border_primary,
            'interactive': self.current_theme.interactive_normal,
            'interactive_hover': self.current_theme.interactive_hover,
            'background_primary': self.current_theme.background_primary,
            'background_secondary': self.current_theme.background_secondary,
            'background_tertiary': self.current_theme.background_tertiary,
            'primary': self.current_theme.primary,
        }\n        \n        # Update content display\n        self.content_display.set_theme_colors(theme_colors)\n        \n        # Test universal colors and display results\n        self._test_theme_compatibility(theme_name, theme_colors)\n        \n    def _test_theme_compatibility(self, theme_name: str, theme_colors: dict):\n        \"\"\"Test theme compatibility and display results.\"\"\"\n        try:\n            # Get compatibility info\n            compat_info = get_theme_compatibility_info(theme_colors)\n            \n            # Test syntax colors\n            syntax_colors = get_universal_syntax_colors(theme_colors)\n            \n            # Compile results\n            results = [\n                f\"Theme: {theme_name}\",\n                f\"Type: {'Dark' if compat_info['is_dark_theme'] else 'Light'}\",\n                f\"Background Luminance: {compat_info['background_luminance']:.3f}\",\n                f\"WCAG AA Compliant: {'✅ Yes' if compat_info['wcag_aa_compliant'] else '❌ No'}\",\n                \"\",\n                \"Contrast Ratios:\",\n            ]\n            \n            for element, ratio in compat_info['contrast_ratios'].items():\n                status = \"✅\" if ratio >= 4.5 else \"⚠️\" if ratio >= 3.0 else \"❌\"\n                results.append(f\"  {element}: {ratio:.2f} {status}\")\n                \n            # Store results\n            self.test_results[theme_name] = {\n                'compatible': compat_info['wcag_aa_compliant'],\n                'contrast_ratios': compat_info['contrast_ratios'],\n                'is_dark': compat_info['is_dark_theme'],\n                'bg_luminance': compat_info['background_luminance']\n            }\n            \n            # Display results\n            self.results_label.setText(\"\\n\".join(results))\n            \n        except Exception as e:\n            logger.error(f\"Theme compatibility test failed: {e}\")\n            self.results_label.setText(f\"Test failed: {e}\")\n    \n    def test_html_parsing(self):\n        \"\"\"Test HTML parsing for artifact elimination.\"\"\"\n        if not COMPONENTS_AVAILABLE:\n            return\n            \n        logger.info(\"Testing HTML parsing...\")\n        \n        # Clear and reload test content\n        self.content_display.clear()\n        self._load_test_content()\n        \n        # The test content includes problematic HTML that should now be parsed correctly\n        self.results_label.setText(\"HTML parsing test completed. Check console for detailed logs.\")\n    \n    def test_copy_functionality(self):\n        \"\"\"Test copy button functionality.\"\"\"\n        if not COMPONENTS_AVAILABLE:\n            return\n            \n        logger.info(\"Testing copy functionality...\")\n        \n        # Add a simple code snippet to test copy\n        test_code = '''def test_function():\n    print(\"Testing copy functionality\")\n    return True'''\n        \n        self.content_display.add_code_snippet(test_code, \"python\")\n        self.results_label.setText(\"Copy functionality test added. Hover over code block and click copy button to test.\")\n    \n    def test_all_themes(self):\n        \"\"\"Test compatibility across all themes.\"\"\"\n        if not COMPONENTS_AVAILABLE:\n            return\n            \n        logger.info(\"Testing all themes...\")\n        \n        compatible_themes = []\n        incompatible_themes = []\n        \n        for theme_name in self.themes.keys():\n            self.change_theme(theme_name)\n            QApplication.processEvents()  # Allow UI to update\n            \n            if theme_name in self.test_results:\n                if self.test_results[theme_name]['compatible']:\n                    compatible_themes.append(theme_name)\n                else:\n                    incompatible_themes.append(theme_name)\n        \n        # Display summary\n        summary = [\n            f\"Compatibility Test Summary:\",\n            f\"✅ Compatible: {len(compatible_themes)}/{len(self.themes)}\",\n            f\"❌ Needs adjustment: {len(incompatible_themes)}\",\n            \"\",\n        ]\n        \n        if incompatible_themes:\n            summary.append(\"Themes needing contrast adjustment:\")\n            for theme in incompatible_themes[:5]:  # Show first 5\n                summary.append(f\"  • {theme}\")\n            if len(incompatible_themes) > 5:\n                summary.append(f\"  ... and {len(incompatible_themes) - 5} more\")\n        \n        self.results_label.setText(\"\\n\".join(summary))\n        \n        # Log detailed results\n        logger.info(f\"Theme compatibility test completed:\")\n        logger.info(f\"Compatible: {compatible_themes}\")\n        logger.info(f\"Incompatible: {incompatible_themes}\")\n\n\ndef main():\n    \"\"\"Main test function.\"\"\"\n    app = QApplication(sys.argv)\n    \n    if not COMPONENTS_AVAILABLE:\n        print(\"Error: Required components not available. Please check imports.\")\n        return 1\n    \n    print(\"Universal Theme Compatibility Tester\")\n    print(\"====================================\")\n    print(f\"Testing {len(get_preset_themes())} themes for:\")\n    print(\"1. HTML artifact elimination\")\n    print(\"2. Copy button functionality\")\n    print(\"3. Universal color accessibility\")\n    print(\"4. WCAG 2.1 AA compliance\")\n    print()\n    \n    tester = ThemeCompatibilityTester()\n    tester.show()\n    \n    return app.exec()\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())"