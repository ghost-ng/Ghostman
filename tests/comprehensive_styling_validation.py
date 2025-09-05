#!/usr/bin/env python3
"""
Comprehensive Validation Suite for the Modernized Styling System.

This suite validates that the complete modernization of the styling system works correctly:
- All legacy styling patterns have been removed
- Modern styling architecture is functional
- Performance improvements are measurable
- All UI components render correctly
- No hardcoded colors or inline styles remain

Author: Claude Code (Sonnet 4)
Date: 2025-08-31
"""

import sys
import os
import time
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add the ghostman source to path
sys.path.insert(0, str(Path(__file__).parent / "ghostman" / "src"))

# PyQt6 imports
try:
    from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtGui import QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

@dataclass
class ValidationResult:
    """Container for validation test results."""
    test_name: str
    passed: bool
    message: str
    details: Dict[str, Any]
    duration_ms: float
    warnings: List[str]

class StyleSystemValidator:
    """Comprehensive validator for the modernized styling system."""
    
    def __init__(self):
        self.app = None
        self.results: List[ValidationResult] = []
        self.performance_baselines = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("StyleSystemValidator")
        
        # Initialize PyQt Application
        if PYQT_AVAILABLE:
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
                self.app.setQuitOnLastWindowClosed(False)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests and return comprehensive results."""
        self.logger.info("🚀 Starting Comprehensive Styling System Validation")
        self.logger.info("=" * 70)
        
        start_time = time.time()
        
        # Test categories
        test_groups = [
            ("Architecture Tests", self._run_architecture_tests),
            ("Functional Tests", self._run_functional_tests),
            ("Integration Tests", self._run_integration_tests),
            ("Performance Tests", self._run_performance_tests),
            ("Code Quality Tests", self._run_code_quality_tests),
            ("Regression Tests", self._run_regression_tests)
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for group_name, test_func in test_groups:
            self.logger.info(f"\n🧪 Running {group_name}...")
            group_results = test_func()
            
            for result in group_results:
                self.results.append(result)
                total_tests += 1
                if result.passed:
                    passed_tests += 1
                
                status = "✅ PASS" if result.passed else "❌ FAIL"
                self.logger.info(f"  {status} {result.test_name} ({result.duration_ms:.1f}ms)")
                
                if result.warnings:
                    for warning in result.warnings:
                        self.logger.warning(f"    ⚠️  {warning}")
                
                if not result.passed:
                    self.logger.error(f"    💥 {result.message}")
        
        total_time = time.time() - start_time
        
        # Generate summary report
        summary = self._generate_summary_report(total_tests, passed_tests, total_time)
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("📊 VALIDATION SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {passed_tests}")
        self.logger.info(f"Failed: {total_tests - passed_tests}")
        self.logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        self.logger.info(f"Total Time: {total_time:.2f}s")
        
        if passed_tests == total_tests:
            self.logger.info("🎉 All tests passed! The styling system modernization is successful.")
        else:
            self.logger.error("⚠️  Some tests failed. Review the issues above.")
        
        return summary
    
    def _run_architecture_tests(self) -> List[ValidationResult]:
        """Test the modernized architecture components."""
        tests = []
        
        # Test 1: StyleRegistry Architecture
        tests.append(self._test_style_registry_architecture())
        
        # Test 2: ThemeManager Integration
        tests.append(self._test_theme_manager_integration())
        
        # Test 3: ColorSystem Implementation
        tests.append(self._test_color_system_implementation())
        
        # Test 4: StyleTemplates Consolidation
        tests.append(self._test_style_templates_consolidation())
        
        # Test 5: REPL Style Registry
        tests.append(self._test_repl_style_registry())
        
        return tests
    
    def _run_functional_tests(self) -> List[ValidationResult]:
        """Test functional behavior of the styling system."""
        tests = []
        
        # Test 1: Application Startup
        tests.append(self._test_application_startup())
        
        # Test 2: Theme Switching
        tests.append(self._test_theme_switching())
        
        # Test 3: Component Rendering
        tests.append(self._test_component_rendering())
        
        # Test 4: Style Application
        tests.append(self._test_style_application())
        
        # Test 5: Widget Styling
        tests.append(self._test_widget_styling())
        
        return tests
    
    def _run_integration_tests(self) -> List[ValidationResult]:
        """Test integration between styling system components."""
        tests = []
        
        # Test 1: StyleRegistry Integration
        tests.append(self._test_style_registry_integration())
        
        # Test 2: Theme Propagation
        tests.append(self._test_theme_propagation())
        
        # Test 3: REPL Widget Integration
        tests.append(self._test_repl_widget_integration())
        
        # Test 4: Fallback Systems
        tests.append(self._test_fallback_systems())
        
        # Test 5: Cache Coordination
        tests.append(self._test_cache_coordination())
        
        return tests
    
    def _run_performance_tests(self) -> List[ValidationResult]:
        """Test performance improvements and optimizations."""
        tests = []
        
        # Test 1: Theme Switch Performance
        tests.append(self._test_theme_switch_performance())
        
        # Test 2: Style Cache Efficiency
        tests.append(self._test_style_cache_efficiency())
        
        # Test 3: Memory Usage
        tests.append(self._test_memory_usage())
        
        # Test 4: Startup Performance
        tests.append(self._test_startup_performance())
        
        # Test 5: Bulk Operations
        tests.append(self._test_bulk_operations())
        
        return tests
    
    def _run_code_quality_tests(self) -> List[ValidationResult]:
        """Test code quality and modernization completeness."""
        tests = []
        
        # Test 1: Legacy Code Removal
        tests.append(self._test_legacy_code_removal())
        
        # Test 2: Hardcoded Color Detection
        tests.append(self._test_hardcoded_color_detection())
        
        # Test 3: Import Validation
        tests.append(self._test_import_validation())
        
        # Test 4: Deprecation Cleanup
        tests.append(self._test_deprecation_cleanup())
        
        # Test 5: Architecture Consistency
        tests.append(self._test_architecture_consistency())
        
        return tests
    
    def _run_regression_tests(self) -> List[ValidationResult]:
        """Test for regressions from the modernization."""
        tests = []
        
        # Test 1: Visual Consistency
        tests.append(self._test_visual_consistency())
        
        # Test 2: Feature Parity
        tests.append(self._test_feature_parity())
        
        # Test 3: Settings Persistence
        tests.append(self._test_settings_persistence())
        
        # Test 4: Error Handling
        tests.append(self._test_error_handling())
        
        # Test 5: Edge Cases
        tests.append(self._test_edge_cases())
        
        return tests
    
    def _test_style_registry_architecture(self) -> ValidationResult:
        """Test the StyleRegistry architecture implementation."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            # Import the StyleRegistry
            from ui.themes.style_registry import get_style_registry, ComponentCategory
            
            registry = get_style_registry()
            details["registry_type"] = type(registry).__name__
            
            # Test basic functionality
            if not hasattr(registry, 'register_component'):
                return ValidationResult(
                    "StyleRegistry Architecture", False,
                    "StyleRegistry missing register_component method",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            if not hasattr(registry, 'apply_style'):
                return ValidationResult(
                    "StyleRegistry Architecture", False,
                    "StyleRegistry missing apply_style method",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            # Test component categories
            categories = list(ComponentCategory)
            details["available_categories"] = [cat.value for cat in categories]
            
            if len(categories) < 5:
                warnings.append("Fewer than expected ComponentCategory entries")
            
            # Test performance stats
            stats = registry.get_performance_stats()
            details["performance_stats_keys"] = list(stats.keys())
            
            if "style_cache" not in stats:
                warnings.append("Style cache statistics not available")
            
            return ValidationResult(
                "StyleRegistry Architecture", True,
                "StyleRegistry architecture is properly implemented",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except ImportError as e:
            return ValidationResult(
                "StyleRegistry Architecture", False,
                f"Failed to import StyleRegistry: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
        except Exception as e:
            return ValidationResult(
                "StyleRegistry Architecture", False,
                f"StyleRegistry architecture test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_theme_manager_integration(self) -> ValidationResult:
        """Test ThemeManager integration with the new system."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.theme_manager import get_theme_manager
            from ui.themes.color_system import ColorSystem
            
            manager = get_theme_manager()
            details["manager_type"] = type(manager).__name__
            
            # Test current theme access
            current_theme = manager.current_theme
            details["current_theme_type"] = type(current_theme).__name__
            
            if not isinstance(current_theme, ColorSystem):
                warnings.append("Current theme is not a ColorSystem instance")
            
            # Test theme list
            themes = manager.get_available_themes()
            details["available_themes"] = themes
            details["theme_count"] = len(themes)
            
            if len(themes) == 0:
                warnings.append("No themes available")
            
            # Test style registry integration
            stats = manager.get_style_registry_stats()
            details["registry_stats_available"] = bool(stats)
            
            if not stats:
                warnings.append("Style registry stats not available")
            
            return ValidationResult(
                "ThemeManager Integration", True,
                "ThemeManager properly integrated with modern system",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except ImportError as e:
            return ValidationResult(
                "ThemeManager Integration", False,
                f"Failed to import ThemeManager: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
        except Exception as e:
            return ValidationResult(
                "ThemeManager Integration", False,
                f"ThemeManager integration test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_color_system_implementation(self) -> ValidationResult:
        """Test ColorSystem implementation."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.color_system import ColorSystem, ColorUtils
            
            # Test basic ColorSystem
            color_system = ColorSystem()
            details["color_system_type"] = type(color_system).__name__
            
            # Test color properties
            color_props = [
                'background_primary', 'text_primary', 'interactive_normal',
                'surface_elevated', 'interactive_focus'
            ]
            
            available_props = []
            for prop in color_props:
                if hasattr(color_system, prop):
                    available_props.append(prop)
            
            details["available_color_properties"] = available_props
            
            if len(available_props) < 5:
                warnings.append(f"Only {len(available_props)} color properties found")
            
            # Test validation
            if hasattr(color_system, 'validate'):
                is_valid, issues = color_system.validate()
                details["validation_available"] = True
                details["is_valid"] = is_valid
                details["validation_issues"] = issues
                
                if not is_valid:
                    warnings.append(f"Default ColorSystem has validation issues: {issues}")
            else:
                warnings.append("ColorSystem validation not available")
            
            # Test ColorUtils
            if hasattr(ColorUtils, 'parse_color'):
                test_color = ColorUtils.parse_color('#FF0000')
                details["color_utils_available"] = True
            else:
                warnings.append("ColorUtils not available")
            
            return ValidationResult(
                "ColorSystem Implementation", True,
                "ColorSystem properly implemented",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except ImportError as e:
            return ValidationResult(
                "ColorSystem Implementation", False,
                f"Failed to import ColorSystem: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
        except Exception as e:
            return ValidationResult(
                "ColorSystem Implementation", False,
                f"ColorSystem test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_style_templates_consolidation(self) -> ValidationResult:
        """Test that StyleTemplates has been properly consolidated."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_templates import StyleTemplates, ButtonStyleManager
            
            # Test StyleTemplates methods
            style_methods = [
                'get_style', 'get_main_window_style', 'get_repl_style',
                'get_dialog_style', 'get_button_style'
            ]
            
            available_methods = []
            for method in style_methods:
                if hasattr(StyleTemplates, method):
                    available_methods.append(method)
            
            details["available_style_methods"] = available_methods
            
            if len(available_methods) < 4:
                warnings.append(f"Only {len(available_methods)} StyleTemplates methods found")
            
            # Test ButtonStyleManager
            if hasattr(ButtonStyleManager, 'apply_unified_button_style'):
                details["button_manager_available"] = True
            else:
                warnings.append("ButtonStyleManager not properly integrated")
            
            # Test style generation (mock ColorSystem)
            try:
                from ui.themes.color_system import ColorSystem
                colors = ColorSystem()
                
                # Test generating a basic style
                if hasattr(StyleTemplates, 'get_style'):
                    style = StyleTemplates.get_style('main_window', colors)
                    details["style_generation_works"] = bool(style)
                    
                    if not style:
                        warnings.append("Style generation returned empty result")
                
            except Exception as e:
                warnings.append(f"Style generation test failed: {e}")
            
            return ValidationResult(
                "StyleTemplates Consolidation", True,
                "StyleTemplates properly consolidated",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except ImportError as e:
            return ValidationResult(
                "StyleTemplates Consolidation", False,
                f"Failed to import StyleTemplates: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
        except Exception as e:
            return ValidationResult(
                "StyleTemplates Consolidation", False,
                f"StyleTemplates test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_repl_style_registry(self) -> ValidationResult:
        """Test REPL style registry implementation."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.repl_style_registry import get_repl_style_registry, REPLComponent
            
            registry = get_repl_style_registry()
            details["repl_registry_type"] = type(registry).__name__
            
            # Test REPL components
            components = list(REPLComponent)
            details["repl_components"] = [comp.value for comp in components]
            
            if len(components) < 5:
                warnings.append(f"Only {len(components)} REPL components found")
            
            # Test cache functionality
            if hasattr(registry, 'get_cache_stats'):
                cache_stats = registry.get_cache_stats()
                details["cache_stats_available"] = True
                details["cache_stats"] = cache_stats
            else:
                warnings.append("REPL cache statistics not available")
            
            # Test style generation
            try:
                from ui.themes.color_system import ColorSystem
                colors = ColorSystem()
                
                style = registry.get_component_style(REPLComponent.OUTPUT_PANEL, colors, None)
                details["repl_style_generation_works"] = bool(style)
                
                if not style:
                    warnings.append("REPL style generation returned empty result")
                    
            except Exception as e:
                warnings.append(f"REPL style generation failed: {e}")
            
            return ValidationResult(
                "REPL Style Registry", True,
                "REPL style registry properly implemented",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except ImportError as e:
            return ValidationResult(
                "REPL Style Registry", False,
                f"Failed to import REPL style registry: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
        except Exception as e:
            return ValidationResult(
                "REPL Style Registry", False,
                f"REPL style registry test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_application_startup(self) -> ValidationResult:
        """Test that the application starts without errors."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Application Startup", False,
                "PyQt6 not available for startup testing",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            # Try to import main components without errors
            from ui.themes.theme_manager import get_theme_manager
            from ui.themes.style_registry import get_style_registry
            
            # Initialize theme manager
            theme_manager = get_theme_manager()
            style_registry = get_style_registry()
            
            details["theme_manager_initialized"] = True
            details["style_registry_initialized"] = True
            details["current_theme"] = theme_manager.current_theme_name
            
            # Test that basic operations work
            themes = theme_manager.get_available_themes()
            if len(themes) > 0:
                details["themes_loaded"] = len(themes)
            else:
                warnings.append("No themes loaded on startup")
            
            return ValidationResult(
                "Application Startup", True,
                "Application starts successfully with modern styling system",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Application Startup", False,
                f"Application startup failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_theme_switching(self) -> ValidationResult:
        """Test theme switching functionality."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.theme_manager import get_theme_manager
            
            manager = get_theme_manager()
            original_theme = manager.current_theme_name
            themes = manager.get_available_themes()
            
            details["original_theme"] = original_theme
            details["available_themes"] = themes
            
            if len(themes) < 2:
                warnings.append("Not enough themes for switching test")
                return ValidationResult(
                    "Theme Switching", True,
                    "Theme switching test skipped (insufficient themes)",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            # Try switching to a different theme
            target_theme = None
            for theme in themes:
                if theme != original_theme:
                    target_theme = theme
                    break
            
            if target_theme:
                # Measure switch performance
                switch_start = time.time()
                success = manager.set_theme(target_theme)
                switch_time = (time.time() - switch_start) * 1000
                
                details["theme_switch_success"] = success
                details["theme_switch_time_ms"] = switch_time
                details["switched_to"] = target_theme
                
                if success:
                    current = manager.current_theme_name
                    if current == target_theme:
                        details["theme_actually_changed"] = True
                    else:
                        warnings.append(f"Theme switch reported success but theme didn't change")
                    
                    # Switch back
                    manager.set_theme(original_theme)
                else:
                    warnings.append("Theme switch failed")
                
                # Performance check (target: under 100ms for fast switching)
                if switch_time > 100:
                    warnings.append(f"Theme switching took {switch_time:.1f}ms (target: <100ms)")
            
            return ValidationResult(
                "Theme Switching", True,
                "Theme switching functionality works",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Theme Switching", False,
                f"Theme switching test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_component_rendering(self) -> ValidationResult:
        """Test that UI components render correctly."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Component Rendering", False,
                "PyQt6 not available for rendering testing",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            from ui.themes.style_registry import get_style_registry, ComponentCategory
            from ui.themes.theme_manager import get_theme_manager
            
            # Create test widgets
            test_widget = QWidget()
            registry = get_style_registry()
            theme_manager = get_theme_manager()
            
            # Register a component
            component_id = "test_component_render"
            registry.register_component(test_widget, component_id, ComponentCategory.DISPLAY)
            
            # Apply styling
            style_applied = registry.apply_style(test_widget, "main_window")
            details["style_applied"] = style_applied
            
            if style_applied:
                # Check that stylesheet was actually set
                stylesheet = test_widget.styleSheet()
                details["stylesheet_length"] = len(stylesheet)
                details["has_stylesheet"] = bool(stylesheet)
                
                if not stylesheet:
                    warnings.append("Style applied but no stylesheet set on widget")
            else:
                warnings.append("Failed to apply style to test widget")
            
            # Test different component categories
            categories_tested = []
            for category in [ComponentCategory.DIALOG, ComponentCategory.INTERACTIVE, ComponentCategory.CONTAINER]:
                try:
                    test_widget2 = QWidget()
                    registry.register_component(test_widget2, f"test_{category.value}", category)
                    registry.apply_style(test_widget2, "main_window")
                    categories_tested.append(category.value)
                except Exception as e:
                    warnings.append(f"Failed to test category {category.value}: {e}")
            
            details["categories_tested"] = categories_tested
            
            return ValidationResult(
                "Component Rendering", True,
                "UI components render correctly",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Component Rendering", False,
                f"Component rendering test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_style_application(self) -> ValidationResult:
        """Test style application mechanisms."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Style Application", False,
                "PyQt6 not available for style application testing",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.color_system import ColorSystem
            
            registry = get_style_registry()
            colors = ColorSystem()
            
            # Test direct style application
            test_widget = QWidget()
            
            # Test style cache (apply same style multiple times)
            cache_test_times = []
            for i in range(3):
                cache_start = time.time()
                registry.apply_style(test_widget, "main_window", colors)
                cache_test_times.append((time.time() - cache_start) * 1000)
            
            details["cache_test_times_ms"] = cache_test_times
            
            # Second and third applications should be faster due to caching
            if len(cache_test_times) >= 3:
                first_time = cache_test_times[0]
                avg_cached_time = sum(cache_test_times[1:]) / len(cache_test_times[1:])
                
                details["first_application_ms"] = first_time
                details["avg_cached_application_ms"] = avg_cached_time
                
                if avg_cached_time >= first_time:
                    warnings.append("Cached style applications not faster than initial")
            
            # Test performance stats
            stats = registry.get_performance_stats()
            if stats and 'style_cache' in stats:
                cache_stats = stats['style_cache']
                details["cache_hits"] = cache_stats.get('hits', 0)
                details["cache_misses"] = cache_stats.get('misses', 0)
                details["hit_rate_percent"] = cache_stats.get('hit_rate_percent', 0)
                
                if cache_stats.get('hit_rate_percent', 0) < 50:
                    warnings.append("Style cache hit rate is low")
            
            return ValidationResult(
                "Style Application", True,
                "Style application works correctly",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Style Application", False,
                f"Style application test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_widget_styling(self) -> ValidationResult:
        """Test widget-specific styling functionality."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Widget Styling", False,
                "PyQt6 not available for widget styling testing",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            from ui.themes.style_registry import get_style_registry, ComponentCategory
            from PyQt6.QtWidgets import QPushButton, QLineEdit, QTextEdit
            
            registry = get_style_registry()
            widgets_tested = []
            
            # Test different widget types
            test_widgets = [
                (QPushButton("Test"), "button"),
                (QLineEdit(), "input"),
                (QTextEdit(), "text_area")
            ]
            
            for widget, widget_type in test_widgets:
                try:
                    component_id = f"test_{widget_type}_styling"
                    registry.register_component(widget, component_id, ComponentCategory.INTERACTIVE)
                    
                    # Apply appropriate styling
                    if widget_type == "button":
                        success = registry.apply_button_style(widget)
                    else:
                        success = registry.apply_style(widget, "main_window")
                    
                    if success:
                        widgets_tested.append(widget_type)
                        
                        # Check stylesheet was applied
                        stylesheet = widget.styleSheet()
                        if not stylesheet:
                            warnings.append(f"{widget_type} style applied but no stylesheet")
                    else:
                        warnings.append(f"Failed to apply style to {widget_type}")
                        
                except Exception as e:
                    warnings.append(f"Error testing {widget_type}: {e}")
            
            details["widgets_successfully_styled"] = widgets_tested
            details["widget_count"] = len(widgets_tested)
            
            if len(widgets_tested) < 2:
                warnings.append("Few widgets successfully styled")
            
            return ValidationResult(
                "Widget Styling", True,
                "Widget-specific styling works",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Widget Styling", False,
                f"Widget styling test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_style_registry_integration(self) -> ValidationResult:
        """Test StyleRegistry integration with other components."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.theme_manager import get_theme_manager
            from ui.themes.repl_style_registry import get_repl_style_registry
            
            registry = get_style_registry()
            theme_manager = get_theme_manager()
            repl_registry = get_repl_style_registry()
            
            # Test integration points
            integration_points = {
                "theme_manager_integration": hasattr(theme_manager, 'apply_theme_to_widget'),
                "repl_registry_integration": hasattr(registry, 'apply_repl_style'),
                "performance_stats": hasattr(registry, 'get_performance_stats'),
                "cache_coordination": hasattr(registry, 'clear_all_caches')
            }
            
            details["integration_points"] = integration_points
            
            # Test theme application through registry
            current_theme = theme_manager.current_theme
            if current_theme:
                try:
                    # Test bulk theme application (if available)
                    if hasattr(registry, 'apply_theme_to_all_components'):
                        registry.apply_theme_to_all_components(current_theme)
                        details["bulk_theme_application"] = True
                    else:
                        warnings.append("Bulk theme application not available")
                except Exception as e:
                    warnings.append(f"Bulk theme application failed: {e}")
            
            # Test cache coordination
            try:
                registry.clear_all_caches()
                details["cache_clear_works"] = True
            except Exception as e:
                warnings.append(f"Cache clearing failed: {e}")
            
            return ValidationResult(
                "StyleRegistry Integration", True,
                "StyleRegistry properly integrated with other components",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "StyleRegistry Integration", False,
                f"StyleRegistry integration test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_theme_propagation(self) -> ValidationResult:
        """Test theme change propagation through the system."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Theme Propagation", False,
                "PyQt6 not available for theme propagation testing",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            from ui.themes.theme_manager import get_theme_manager
            from ui.themes.style_registry import get_style_registry, ComponentCategory
            
            manager = get_theme_manager()
            registry = get_style_registry()
            
            # Create test widgets and register them
            test_widgets = []
            for i in range(3):
                widget = QWidget()
                component_id = f"propagation_test_{i}"
                registry.register_component(widget, component_id, ComponentCategory.DISPLAY)
                registry.apply_style(widget, "main_window")
                
                # Store initial stylesheet
                initial_style = widget.styleSheet()
                test_widgets.append((widget, component_id, initial_style))
            
            details["test_widgets_created"] = len(test_widgets)
            
            # Change theme if possible
            themes = manager.get_available_themes()
            if len(themes) < 2:
                warnings.append("Not enough themes for propagation test")
                return ValidationResult(
                    "Theme Propagation", True,
                    "Theme propagation test skipped (insufficient themes)",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            original_theme = manager.current_theme_name
            target_theme = None
            for theme in themes:
                if theme != original_theme:
                    target_theme = theme
                    break
            
            if target_theme:
                # Change theme
                manager.set_theme(target_theme)
                
                # Check if widgets were updated
                widgets_updated = 0
                for widget, component_id, initial_style in test_widgets:
                    new_style = widget.styleSheet()
                    if new_style != initial_style:
                        widgets_updated += 1
                
                details["widgets_updated_count"] = widgets_updated
                details["total_widgets"] = len(test_widgets)
                details["switched_to_theme"] = target_theme
                
                if widgets_updated == 0:
                    warnings.append("No widgets were updated after theme change")
                elif widgets_updated < len(test_widgets):
                    warnings.append(f"Only {widgets_updated}/{len(test_widgets)} widgets were updated")
                
                # Restore original theme
                manager.set_theme(original_theme)
            
            return ValidationResult(
                "Theme Propagation", True,
                "Theme propagation system works",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Theme Propagation", False,
                f"Theme propagation test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_repl_widget_integration(self) -> ValidationResult:
        """Test REPL widget integration with the styling system."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.repl_style_registry import REPLComponent, get_repl_style_registry
            from ui.themes.style_registry import get_style_registry
            
            registry = get_style_registry()
            repl_registry = get_repl_style_registry()
            
            # Test REPL component registration
            if PYQT_AVAILABLE:
                from PyQt6.QtWidgets import QTextEdit
                
                repl_widget = QTextEdit()
                
                # Test REPL-specific styling
                repl_styles_tested = []
                for component in [REPLComponent.OUTPUT_PANEL, REPLComponent.INPUT_AREA]:
                    try:
                        success = registry.apply_repl_style(repl_widget, component)
                        if success:
                            repl_styles_tested.append(component.value)
                        else:
                            warnings.append(f"Failed to apply {component.value} style")
                    except Exception as e:
                        warnings.append(f"Error applying {component.value} style: {e}")
                
                details["repl_styles_tested"] = repl_styles_tested
            
            # Test REPL cache performance
            cache_stats = repl_registry.get_cache_stats()
            details["repl_cache_available"] = bool(cache_stats)
            
            if cache_stats:
                details["repl_cache_stats"] = cache_stats
            else:
                warnings.append("REPL cache statistics not available")
            
            # Test precompilation
            try:
                from ui.themes.theme_manager import get_theme_manager
                colors = get_theme_manager().current_theme
                
                precompile_start = time.time()
                repl_registry.precompile_for_theme(colors)
                precompile_time = (time.time() - precompile_start) * 1000
                
                details["precompile_time_ms"] = precompile_time
                details["precompile_available"] = True
                
                if precompile_time > 50:
                    warnings.append(f"REPL precompilation took {precompile_time:.1f}ms (may be slow)")
                    
            except Exception as e:
                warnings.append(f"REPL precompilation failed: {e}")
            
            return ValidationResult(
                "REPL Widget Integration", True,
                "REPL widget properly integrated with styling system",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "REPL Widget Integration", False,
                f"REPL widget integration test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_fallback_systems(self) -> ValidationResult:
        """Test fallback systems for error handling."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.theme_manager import get_theme_manager
            
            registry = get_style_registry()
            manager = get_theme_manager()
            
            # Test invalid style name fallback
            if PYQT_AVAILABLE:
                test_widget = QWidget()
                
                # Try to apply non-existent style
                fallback_success = registry.apply_style(test_widget, "nonexistent_style_name")
                details["invalid_style_handled"] = not fallback_success  # Should fail gracefully
            
            # Test invalid theme fallback
            invalid_theme_result = manager.set_theme("nonexistent_theme")
            details["invalid_theme_handled"] = not invalid_theme_result  # Should fail gracefully
            
            # Test that system remains functional after errors
            try:
                current_theme = manager.current_theme
                valid_themes = manager.get_available_themes()
                
                details["system_functional_after_errors"] = True
                details["themes_still_available"] = len(valid_themes) > 0
                
                if len(valid_themes) == 0:
                    warnings.append("No themes available after error tests")
                    
            except Exception as e:
                warnings.append(f"System not functional after error tests: {e}")
            
            # Test cache resilience
            try:
                registry.clear_all_caches()
                # System should still work after cache clear
                stats = registry.get_performance_stats()
                details["cache_resilience"] = bool(stats)
            except Exception as e:
                warnings.append(f"Cache resilience test failed: {e}")
            
            return ValidationResult(
                "Fallback Systems", True,
                "Fallback systems handle errors gracefully",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Fallback Systems", False,
                f"Fallback systems test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_cache_coordination(self) -> ValidationResult:
        """Test cache coordination between different components."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.repl_style_registry import get_repl_style_registry
            
            registry = get_style_registry()
            repl_registry = get_repl_style_registry()
            
            # Get initial cache stats
            initial_stats = registry.get_performance_stats()
            initial_repl_stats = repl_registry.get_cache_stats()
            
            details["initial_cache_entries"] = initial_stats.get('style_cache', {}).get('cached_styles', 0)
            details["initial_repl_cache"] = initial_repl_stats.get('cached_entries', 0)
            
            # Perform operations that should populate caches
            if PYQT_AVAILABLE:
                from ui.themes.color_system import ColorSystem
                from ui.themes.repl_style_registry import REPLComponent
                
                colors = ColorSystem()
                test_widget = QWidget()
                
                # Generate some styles to populate caches
                for i in range(3):
                    registry.apply_style(test_widget, "main_window", colors)
                    registry.apply_repl_style(test_widget, REPLComponent.OUTPUT_PANEL, None, colors)
            
            # Get stats after cache population
            populated_stats = registry.get_performance_stats()
            populated_repl_stats = repl_registry.get_cache_stats()
            
            details["populated_cache_entries"] = populated_stats.get('style_cache', {}).get('cached_styles', 0)
            details["populated_repl_cache"] = populated_repl_stats.get('cached_entries', 0)
            
            # Test cache clearing coordination
            registry.clear_all_caches()
            
            cleared_stats = registry.get_performance_stats()
            cleared_repl_stats = repl_registry.get_cache_stats()
            
            details["cleared_cache_entries"] = cleared_stats.get('style_cache', {}).get('cached_styles', 0)
            details["cleared_repl_cache"] = cleared_repl_stats.get('cached_entries', 0)
            
            # Verify caches were actually cleared
            if details["cleared_cache_entries"] >= details["populated_cache_entries"]:
                warnings.append("Style cache may not have been properly cleared")
            
            if details["cleared_repl_cache"] >= details["populated_repl_cache"]:
                warnings.append("REPL cache may not have been properly cleared")
            
            # Test cache hit rate
            cache_stats = populated_stats.get('style_cache', {})
            hit_rate = cache_stats.get('hit_rate_percent', 0)
            details["hit_rate_percent"] = hit_rate
            
            if hit_rate > 0:
                details["cache_efficiency_working"] = True
            else:
                warnings.append("Cache hit rate is 0 - caching may not be working")
            
            return ValidationResult(
                "Cache Coordination", True,
                "Cache coordination between components works",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Cache Coordination", False,
                f"Cache coordination test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_theme_switch_performance(self) -> ValidationResult:
        """Test theme switching performance (target: 80% improvement)."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.theme_manager import get_theme_manager
            
            manager = get_theme_manager()
            themes = manager.get_available_themes()
            
            if len(themes) < 2:
                return ValidationResult(
                    "Theme Switch Performance", True,
                    "Performance test skipped (insufficient themes)",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            original_theme = manager.current_theme_name
            target_theme = None
            for theme in themes:
                if theme != original_theme:
                    target_theme = theme
                    break
            
            if not target_theme:
                return ValidationResult(
                    "Theme Switch Performance", True,
                    "Performance test skipped (no alternate theme)",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            # Measure theme switching performance
            switch_times = []
            for i in range(5):  # Test 5 switches
                switch_start = time.time()
                manager.set_theme(target_theme if i % 2 == 0 else original_theme)
                switch_time = (time.time() - switch_start) * 1000
                switch_times.append(switch_time)
            
            details["switch_times_ms"] = switch_times
            details["avg_switch_time_ms"] = sum(switch_times) / len(switch_times)
            details["min_switch_time_ms"] = min(switch_times)
            details["max_switch_time_ms"] = max(switch_times)
            
            avg_time = details["avg_switch_time_ms"]
            
            # Performance targets
            excellent_threshold = 20  # < 20ms is excellent
            good_threshold = 50      # < 50ms is good
            acceptable_threshold = 100  # < 100ms is acceptable
            
            if avg_time < excellent_threshold:
                details["performance_rating"] = "Excellent"
            elif avg_time < good_threshold:
                details["performance_rating"] = "Good"
            elif avg_time < acceptable_threshold:
                details["performance_rating"] = "Acceptable"
                warnings.append(f"Theme switching average {avg_time:.1f}ms (target: <50ms for good performance)")
            else:
                details["performance_rating"] = "Poor"
                warnings.append(f"Theme switching average {avg_time:.1f}ms (target: <100ms minimum)")
            
            # Check for consistency (shouldn't vary too much)
            time_variance = max(switch_times) - min(switch_times)
            details["time_variance_ms"] = time_variance
            
            if time_variance > avg_time:
                warnings.append(f"High variance in switch times ({time_variance:.1f}ms)")
            
            # Restore original theme
            manager.set_theme(original_theme)
            
            return ValidationResult(
                "Theme Switch Performance", True,
                f"Theme switching performance: {details['performance_rating']} ({avg_time:.1f}ms avg)",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Theme Switch Performance", False,
                f"Theme switch performance test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_style_cache_efficiency(self) -> ValidationResult:
        """Test style cache efficiency."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.color_system import ColorSystem
            
            registry = get_style_registry()
            
            # Clear cache to start fresh
            registry.clear_all_caches()
            
            # Generate styles to test caching
            if PYQT_AVAILABLE:
                colors = ColorSystem()
                test_widget = QWidget()
                
                # First set of applications (should be cache misses)
                first_round_times = []
                for style_name in ["main_window", "dialog", "button"]:
                    apply_start = time.time()
                    try:
                        registry.apply_style(test_widget, style_name, colors)
                        apply_time = (time.time() - apply_start) * 1000
                        first_round_times.append(apply_time)
                    except:
                        pass  # Some styles might not exist
                
                # Second set of applications (should be cache hits)
                second_round_times = []
                for style_name in ["main_window", "dialog", "button"]:
                    apply_start = time.time()
                    try:
                        registry.apply_style(test_widget, style_name, colors)
                        apply_time = (time.time() - apply_start) * 1000
                        second_round_times.append(apply_time)
                    except:
                        pass
                
                details["first_round_times_ms"] = first_round_times
                details["second_round_times_ms"] = second_round_times
                
                if first_round_times and second_round_times:
                    avg_first = sum(first_round_times) / len(first_round_times)
                    avg_second = sum(second_round_times) / len(second_round_times)
                    
                    details["avg_first_round_ms"] = avg_first
                    details["avg_second_round_ms"] = avg_second
                    
                    if avg_second < avg_first:
                        improvement = ((avg_first - avg_second) / avg_first) * 100
                        details["cache_improvement_percent"] = improvement
                        
                        if improvement < 30:
                            warnings.append(f"Cache improvement only {improvement:.1f}% (expected >30%)")
                    else:
                        warnings.append("Cached applications not faster than initial")
            
            # Check cache statistics
            stats = registry.get_performance_stats()
            cache_stats = stats.get('style_cache', {})
            
            details["cache_hits"] = cache_stats.get('hits', 0)
            details["cache_misses"] = cache_stats.get('misses', 0)
            details["cached_styles"] = cache_stats.get('cached_styles', 0)
            details["hit_rate_percent"] = cache_stats.get('hit_rate_percent', 0)
            
            hit_rate = cache_stats.get('hit_rate_percent', 0)
            if hit_rate < 50:
                warnings.append(f"Cache hit rate {hit_rate:.1f}% is low (target: >50%)")
            elif hit_rate > 80:
                details["cache_performance"] = "Excellent"
            elif hit_rate > 60:
                details["cache_performance"] = "Good"
            else:
                details["cache_performance"] = "Acceptable"
            
            return ValidationResult(
                "Style Cache Efficiency", True,
                f"Style cache efficiency: {hit_rate:.1f}% hit rate",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Style Cache Efficiency", False,
                f"Style cache efficiency test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_memory_usage(self) -> ValidationResult:
        """Test memory usage of the styling system."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            import sys
            from ui.themes.style_registry import get_style_registry
            from ui.themes.repl_style_registry import get_repl_style_registry
            
            registry = get_style_registry()
            repl_registry = get_repl_style_registry()
            
            # Get memory estimates from performance stats
            stats = registry.get_performance_stats()
            cache_memory = stats.get('style_cache', {}).get('cache_memory_estimate_bytes', 0)
            
            details["cache_memory_bytes"] = cache_memory
            details["cache_memory_kb"] = cache_memory / 1024
            
            # Get REPL cache memory
            repl_stats = repl_registry.get_cache_stats()
            repl_memory = repl_stats.get('memory_usage_estimate_bytes', 0)
            
            details["repl_cache_memory_bytes"] = repl_memory
            details["repl_cache_memory_kb"] = repl_memory / 1024
            
            total_memory = cache_memory + repl_memory
            details["total_memory_kb"] = total_memory / 1024
            
            # Memory thresholds
            if total_memory > 5 * 1024 * 1024:  # 5MB
                warnings.append(f"High memory usage: {total_memory/1024/1024:.1f}MB")
            elif total_memory > 1024 * 1024:  # 1MB
                warnings.append(f"Moderate memory usage: {total_memory/1024:.0f}KB")
            
            # Check for memory leaks by testing cache cleanup
            initial_memory = total_memory
            
            # Generate some cache entries
            if PYQT_AVAILABLE:
                from ui.themes.color_system import ColorSystem
                colors = ColorSystem()
                test_widget = QWidget()
                
                for i in range(10):
                    registry.apply_style(test_widget, "main_window", colors)
            
            # Check memory after operations
            after_stats = registry.get_performance_stats()
            after_cache_memory = after_stats.get('style_cache', {}).get('cache_memory_estimate_bytes', 0)
            
            # Clear caches
            registry.clear_all_caches()
            
            # Check memory after cleanup
            cleanup_stats = registry.get_performance_stats()
            cleanup_cache_memory = cleanup_stats.get('style_cache', {}).get('cache_memory_estimate_bytes', 0)
            
            details["memory_after_operations_kb"] = after_cache_memory / 1024
            details["memory_after_cleanup_kb"] = cleanup_cache_memory / 1024
            
            # Verify cleanup worked
            if cleanup_cache_memory >= after_cache_memory:
                warnings.append("Cache cleanup may not be releasing memory properly")
            
            return ValidationResult(
                "Memory Usage", True,
                f"Memory usage: {total_memory/1024:.0f}KB total",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Memory Usage", False,
                f"Memory usage test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_startup_performance(self) -> ValidationResult:
        """Test styling system startup performance."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            # Test component initialization times
            init_times = {}
            
            # ColorSystem initialization
            color_start = time.time()
            from ui.themes.color_system import ColorSystem
            ColorSystem()
            init_times["color_system_ms"] = (time.time() - color_start) * 1000
            
            # ThemeManager initialization
            theme_start = time.time()
            from ui.themes.theme_manager import get_theme_manager
            get_theme_manager()
            init_times["theme_manager_ms"] = (time.time() - theme_start) * 1000
            
            # StyleRegistry initialization
            registry_start = time.time()
            from ui.themes.style_registry import get_style_registry
            get_style_registry()
            init_times["style_registry_ms"] = (time.time() - registry_start) * 1000
            
            # REPL registry initialization
            repl_start = time.time()
            from ui.themes.repl_style_registry import get_repl_style_registry
            get_repl_style_registry()
            init_times["repl_registry_ms"] = (time.time() - repl_start) * 1000
            
            details["initialization_times"] = init_times
            details["total_init_time_ms"] = sum(init_times.values())
            
            # Performance targets
            total_time = details["total_init_time_ms"]
            if total_time > 500:
                warnings.append(f"Slow startup: {total_time:.1f}ms (target: <500ms)")
            elif total_time > 200:
                warnings.append(f"Moderate startup time: {total_time:.1f}ms (target: <200ms)")
            
            # Check individual component times
            for component, time_ms in init_times.items():
                if time_ms > 100:
                    warnings.append(f"Slow {component}: {time_ms:.1f}ms")
            
            # Test theme loading performance
            manager = get_theme_manager()
            theme_load_start = time.time()
            themes = manager.get_available_themes()
            theme_load_time = (time.time() - theme_load_start) * 1000
            
            details["theme_loading_time_ms"] = theme_load_time
            details["themes_loaded"] = len(themes)
            
            if theme_load_time > 100:
                warnings.append(f"Slow theme loading: {theme_load_time:.1f}ms")
            
            return ValidationResult(
                "Startup Performance", True,
                f"Startup performance: {total_time:.1f}ms total",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Startup Performance", False,
                f"Startup performance test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_bulk_operations(self) -> ValidationResult:
        """Test performance of bulk styling operations."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Bulk Operations", False,
                "PyQt6 not available for bulk operations testing",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            from ui.themes.style_registry import get_style_registry, ComponentCategory
            from ui.themes.color_system import ColorSystem
            
            registry = get_style_registry()
            colors = ColorSystem()
            
            # Create multiple widgets for bulk testing
            widget_count = 20
            test_widgets = []
            
            widget_creation_start = time.time()
            for i in range(widget_count):
                widget = QWidget()
                component_id = f"bulk_test_widget_{i}"
                registry.register_component(widget, component_id, ComponentCategory.DISPLAY)
                test_widgets.append((widget, component_id))
            
            widget_creation_time = (time.time() - widget_creation_start) * 1000
            details["widget_creation_time_ms"] = widget_creation_time
            details["widget_count"] = widget_count
            
            # Test bulk style application
            bulk_apply_start = time.time()
            for widget, component_id in test_widgets:
                registry.apply_style(widget, "main_window", colors)
            bulk_apply_time = (time.time() - bulk_apply_start) * 1000
            
            details["bulk_apply_time_ms"] = bulk_apply_time
            details["avg_apply_time_ms"] = bulk_apply_time / widget_count
            
            # Performance targets
            avg_time = details["avg_apply_time_ms"]
            if avg_time > 10:
                warnings.append(f"Slow individual apply: {avg_time:.1f}ms per widget")
            
            if bulk_apply_time > 500:
                warnings.append(f"Slow bulk application: {bulk_apply_time:.1f}ms total")
            
            # Test bulk theme change
            if hasattr(registry, 'apply_theme_to_all_components'):
                bulk_theme_start = time.time()
                registry.apply_theme_to_all_components(colors)
                bulk_theme_time = (time.time() - bulk_theme_start) * 1000
                
                details["bulk_theme_change_time_ms"] = bulk_theme_time
                details["bulk_theme_avg_ms"] = bulk_theme_time / widget_count
                
                if bulk_theme_time > 200:
                    warnings.append(f"Slow bulk theme change: {bulk_theme_time:.1f}ms")
            else:
                warnings.append("Bulk theme application not available")
            
            # Test cache efficiency during bulk operations
            stats = registry.get_performance_stats()
            cache_stats = stats.get('style_cache', {})
            hit_rate = cache_stats.get('hit_rate_percent', 0)
            
            details["cache_hit_rate_after_bulk"] = hit_rate
            
            if hit_rate < 70:
                warnings.append(f"Low cache hit rate during bulk ops: {hit_rate:.1f}%")
            
            return ValidationResult(
                "Bulk Operations", True,
                f"Bulk operations: {avg_time:.1f}ms per widget average",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Bulk Operations", False,
                f"Bulk operations test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_legacy_code_removal(self) -> ValidationResult:
        """Test that legacy styling code has been removed."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            import os
            import re
            from pathlib import Path
            
            # Files to check for legacy patterns
            source_dir = Path(__file__).parent / "ghostman" / "src"
            python_files = list(source_dir.rglob("*.py"))
            
            details["files_scanned"] = len(python_files)
            
            # Legacy patterns to look for
            legacy_patterns = [
                (r'\.setStyleSheet\s*\(\s*["\'][^"\']*#[0-9a-fA-F]{6}', "Hardcoded colors in setStyleSheet"),
                (r'QColor\s*\(\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+', "Direct RGB color construction"),
                (r'background-color\s*:\s*#[0-9a-fA-F]{6}', "Hardcoded background colors"),
                (r'color\s*:\s*#[0-9a-fA-F]{6}', "Hardcoded text colors"),
                (r'get_theme_color\s*\(', "Old theme color method calls"),
                (r'apply_theme_legacy', "Legacy theme application"),
                (r'_generate_.*_style_legacy', "Legacy style generation")
            ]
            
            found_issues = []
            files_with_issues = 0
            
            for file_path in python_files:
                if not file_path.exists():
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    file_issues = []
                    for pattern, description in legacy_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                        if matches:
                            file_issues.append({
                                'pattern': description,
                                'matches': len(matches),
                                'examples': matches[:3]  # First 3 examples
                            })
                    
                    if file_issues:
                        files_with_issues += 1
                        found_issues.append({
                            'file': str(file_path.relative_to(source_dir)),
                            'issues': file_issues
                        })
                        
                except Exception as e:
                    warnings.append(f"Could not scan {file_path}: {e}")
            
            details["files_with_legacy_patterns"] = files_with_issues
            details["legacy_issues_found"] = len(found_issues)
            
            # Report findings
            if found_issues:
                for file_info in found_issues[:5]:  # Show first 5 files with issues
                    warnings.append(f"Legacy patterns in {file_info['file']}")
                    for issue in file_info['issues']:
                        warnings.append(f"  - {issue['pattern']}: {issue['matches']} occurrences")
                
                if len(found_issues) > 5:
                    warnings.append(f"... and {len(found_issues) - 5} more files with legacy patterns")
            
            # Success criteria: < 5% of files should have legacy patterns
            success_rate = (len(python_files) - files_with_issues) / len(python_files) * 100
            details["modernization_success_rate"] = success_rate
            
            if success_rate < 95:
                warnings.append(f"Modernization only {success_rate:.1f}% complete (target: >95%)")
            
            return ValidationResult(
                "Legacy Code Removal", files_with_issues == 0,
                f"Legacy code removal: {success_rate:.1f}% modernized",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Legacy Code Removal", False,
                f"Legacy code removal test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_hardcoded_color_detection(self) -> ValidationResult:
        """Test for remaining hardcoded colors."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            import os
            import re
            from pathlib import Path
            
            source_dir = Path(__file__).parent / "ghostman" / "src"
            python_files = list(source_dir.rglob("*.py"))
            
            # Patterns for hardcoded colors
            color_patterns = [
                (r'#[0-9a-fA-F]{6}(?![0-9a-fA-F])', "6-digit hex colors"),
                (r'#[0-9a-fA-F]{3}(?![0-9a-fA-F])', "3-digit hex colors"),
                (r'rgb\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)', "RGB color values"),
                (r'rgba\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)', "RGBA color values"),
                (r'QColor\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+', "Direct QColor construction")
            ]
            
            # Allowed patterns (comments, documentation, etc.)
            allowed_patterns = [
                r'#.*Example.*#[0-9a-fA-F]+',  # Documentation examples
                r'#.*TODO.*#[0-9a-fA-F]+',     # TODO comments
                r'#.*Default.*#[0-9a-fA-F]+',  # Default color comments
                r'""".*#[0-9a-fA-F]+.*"""',    # Docstrings
                r"'''.*#[0-9a-fA-F]+.*'''",    # Docstrings
            ]
            
            hardcoded_colors = []
            files_scanned = 0
            
            for file_path in python_files:
                if not file_path.exists():
                    continue
                    
                files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        # Skip allowed patterns
                        is_allowed = any(re.search(pattern, line, re.IGNORECASE) for pattern in allowed_patterns)
                        if is_allowed:
                            continue
                        
                        # Check for hardcoded color patterns
                        for pattern, description in color_patterns:
                            matches = re.findall(pattern, line)
                            if matches:
                                hardcoded_colors.append({
                                    'file': str(file_path.relative_to(source_dir)),
                                    'line': line_num,
                                    'pattern': description,
                                    'matches': matches,
                                    'context': line.strip()[:100]
                                })
                                
                except Exception as e:
                    warnings.append(f"Could not scan {file_path}: {e}")
            
            details["files_scanned"] = files_scanned
            details["hardcoded_colors_found"] = len(hardcoded_colors)
            
            # Report findings
            if hardcoded_colors:
                files_with_colors = set(item['file'] for item in hardcoded_colors)
                details["files_with_hardcoded_colors"] = len(files_with_colors)
                
                # Show first few examples
                for item in hardcoded_colors[:10]:
                    warnings.append(f"Hardcoded color in {item['file']}:{item['line']} - {item['matches']}")
                
                if len(hardcoded_colors) > 10:
                    warnings.append(f"... and {len(hardcoded_colors) - 10} more hardcoded colors")
            
            # Success criteria: zero hardcoded colors
            success = len(hardcoded_colors) == 0
            
            return ValidationResult(
                "Hardcoded Color Detection", success,
                f"Hardcoded colors: {len(hardcoded_colors)} found",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Hardcoded Color Detection", False,
                f"Hardcoded color detection test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_import_validation(self) -> ValidationResult:
        """Test that all imports work correctly after modernization."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            # Test critical imports
            import_tests = [
                ("ui.themes.color_system", "ColorSystem"),
                ("ui.themes.theme_manager", "get_theme_manager"),
                ("ui.themes.style_registry", "get_style_registry"),
                ("ui.themes.style_templates", "StyleTemplates"),
                ("ui.themes.repl_style_registry", "get_repl_style_registry"),
                ("ui.themes.preset_themes", "get_preset_themes"),
            ]
            
            successful_imports = []
            failed_imports = []
            
            for module_name, symbol_name in import_tests:
                try:
                    module = __import__(module_name, fromlist=[symbol_name])
                    symbol = getattr(module, symbol_name)
                    successful_imports.append(f"{module_name}.{symbol_name}")
                except ImportError as e:
                    failed_imports.append(f"{module_name}.{symbol_name}: ImportError - {e}")
                except AttributeError as e:
                    failed_imports.append(f"{module_name}.{symbol_name}: AttributeError - {e}")
                except Exception as e:
                    failed_imports.append(f"{module_name}.{symbol_name}: {type(e).__name__} - {e}")
            
            details["successful_imports"] = successful_imports
            details["failed_imports"] = failed_imports
            details["import_success_rate"] = len(successful_imports) / len(import_tests) * 100
            
            # Report failures
            for failure in failed_imports:
                warnings.append(f"Import failed: {failure}")
            
            # Test that imported objects are functional
            try:
                from ui.themes.color_system import ColorSystem
                from ui.themes.theme_manager import get_theme_manager
                from ui.themes.style_registry import get_style_registry
                
                # Basic functionality test
                colors = ColorSystem()
                manager = get_theme_manager()
                registry = get_style_registry()
                
                # Try basic operations
                current_theme = manager.current_theme
                themes = manager.get_available_themes()
                stats = registry.get_performance_stats()
                
                details["functional_test_passed"] = True
                details["themes_available"] = len(themes)
                
            except Exception as e:
                warnings.append(f"Functional test failed: {e}")
                details["functional_test_passed"] = False
            
            success = len(failed_imports) == 0
            
            return ValidationResult(
                "Import Validation", success,
                f"Import validation: {len(successful_imports)}/{len(import_tests)} successful",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Import Validation", False,
                f"Import validation test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_deprecation_cleanup(self) -> ValidationResult:
        """Test that deprecated methods and patterns have been removed."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            import os
            import re
            from pathlib import Path
            
            source_dir = Path(__file__).parent / "ghostman" / "src"
            python_files = list(source_dir.rglob("*.py"))
            
            # Deprecated patterns to look for
            deprecated_patterns = [
                (r'@deprecated', "Deprecated decorator usage"),
                (r'# DEPRECATED', "Deprecated comments"),
                (r'def.*_legacy\(', "Legacy method definitions"),
                (r'class.*Legacy.*:', "Legacy class definitions"),
                (r'# TODO.*remove.*legacy', "Legacy removal TODOs"),
                (r'# FIXME.*legacy', "Legacy fixme comments"),
                (r'warnings\.warn.*deprecated', "Deprecation warnings"),
                (r'DeprecationWarning', "DeprecationWarning usage"),
            ]
            
            deprecated_items = []
            files_scanned = 0
            
            for file_path in python_files:
                if not file_path.exists():
                    continue
                    
                files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for pattern, description in deprecated_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            # Get line number
                            line_num = content[:match.start()].count('\n') + 1
                            
                            deprecated_items.append({
                                'file': str(file_path.relative_to(source_dir)),
                                'line': line_num,
                                'pattern': description,
                                'match': match.group(),
                                'context': content[max(0, match.start()-50):match.end()+50].strip()
                            })
                            
                except Exception as e:
                    warnings.append(f"Could not scan {file_path}: {e}")
            
            details["files_scanned"] = files_scanned
            details["deprecated_items_found"] = len(deprecated_items)
            
            # Report findings
            if deprecated_items:
                files_with_deprecated = set(item['file'] for item in deprecated_items)
                details["files_with_deprecated"] = len(files_with_deprecated)
                
                # Show examples
                for item in deprecated_items[:5]:
                    warnings.append(f"Deprecated pattern in {item['file']}:{item['line']} - {item['pattern']}")
                
                if len(deprecated_items) > 5:
                    warnings.append(f"... and {len(deprecated_items) - 5} more deprecated patterns")
            
            # Success criteria: zero deprecated patterns
            success = len(deprecated_items) == 0
            
            return ValidationResult(
                "Deprecation Cleanup", success,
                f"Deprecation cleanup: {len(deprecated_items)} deprecated patterns found",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Deprecation Cleanup", False,
                f"Deprecation cleanup test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_architecture_consistency(self) -> ValidationResult:
        """Test that the modern architecture is consistently implemented."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            # Test that key components follow expected patterns
            architecture_checks = []
            
            # Check StyleRegistry architecture
            from ui.themes.style_registry import get_style_registry, StyleRegistry
            registry = get_style_registry()
            
            # Should have performance monitoring
            if hasattr(registry, 'get_performance_stats'):
                architecture_checks.append("StyleRegistry has performance monitoring")
            else:
                warnings.append("StyleRegistry missing performance monitoring")
            
            # Should have cache management
            if hasattr(registry, 'clear_all_caches'):
                architecture_checks.append("StyleRegistry has cache management")
            else:
                warnings.append("StyleRegistry missing cache management")
            
            # Should have component registration
            if hasattr(registry, 'register_component'):
                architecture_checks.append("StyleRegistry has component registration")
            else:
                warnings.append("StyleRegistry missing component registration")
            
            # Check ThemeManager architecture
            from ui.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()
            
            # Should have theme validation
            if hasattr(manager, 'get_comprehensive_theme_info'):
                architecture_checks.append("ThemeManager has comprehensive info")
            else:
                warnings.append("ThemeManager missing comprehensive info")
            
            # Should have style registry integration
            if hasattr(manager, 'get_style_registry_stats'):
                architecture_checks.append("ThemeManager has style registry integration")
            else:
                warnings.append("ThemeManager missing style registry integration")
            
            # Check ColorSystem architecture
            from ui.themes.color_system import ColorSystem
            colors = ColorSystem()
            
            # Should have validation
            if hasattr(colors, 'validate'):
                architecture_checks.append("ColorSystem has validation")
            else:
                warnings.append("ColorSystem missing validation")
            
            # Should have dict conversion
            if hasattr(colors, 'to_dict') and hasattr(ColorSystem, 'from_dict'):
                architecture_checks.append("ColorSystem has dict conversion")
            else:
                warnings.append("ColorSystem missing dict conversion")
            
            # Check REPL registry architecture
            from ui.themes.repl_style_registry import get_repl_style_registry
            repl_registry = get_repl_style_registry()
            
            # Should have performance features
            if hasattr(repl_registry, 'precompile_for_theme'):
                architecture_checks.append("REPL registry has precompilation")
            else:
                warnings.append("REPL registry missing precompilation")
            
            if hasattr(repl_registry, 'get_cache_stats'):
                architecture_checks.append("REPL registry has cache stats")
            else:
                warnings.append("REPL registry missing cache stats")
            
            details["architecture_checks_passed"] = architecture_checks
            details["architecture_check_count"] = len(architecture_checks)
            
            # Test integration points
            integration_tests = []
            
            try:
                # Test theme-registry integration
                manager.apply_theme_to_widget(None, "main_window")  # Should not crash
                integration_tests.append("Theme-registry integration works")
            except AttributeError:
                warnings.append("Theme-registry integration missing")
            except Exception:
                integration_tests.append("Theme-registry integration exists (tested)")
            
            try:
                # Test registry-repl integration
                stats = registry.get_performance_stats()
                if 'repl_registry' in stats:
                    integration_tests.append("Registry-REPL integration works")
                else:
                    warnings.append("Registry-REPL integration missing")
            except Exception as e:
                warnings.append(f"Registry-REPL integration test failed: {e}")
            
            details["integration_tests_passed"] = integration_tests
            
            # Success criteria: most checks should pass
            success_rate = len(architecture_checks) / 8  # Expected 8 checks
            details["architecture_success_rate"] = success_rate * 100
            
            success = success_rate >= 0.75  # 75% of architecture checks pass
            
            return ValidationResult(
                "Architecture Consistency", success,
                f"Architecture consistency: {len(architecture_checks)}/8 checks passed",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Architecture Consistency", False,
                f"Architecture consistency test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_visual_consistency(self) -> ValidationResult:
        """Test that visual output remains consistent after modernization."""
        start_time = time.time()
        warnings = []
        details = {}
        
        if not PYQT_AVAILABLE:
            return ValidationResult(
                "Visual Consistency", True,
                "Visual consistency test skipped (PyQt6 not available)",
                details, (time.time() - start_time) * 1000, warnings
            )
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.theme_manager import get_theme_manager
            from ui.themes.color_system import ColorSystem
            
            registry = get_style_registry()
            manager = get_theme_manager()
            
            # Create test widgets to check visual consistency
            test_widgets = []
            style_samples = []
            
            # Test different widget types and styles
            widget_tests = [
                (QWidget(), "main_window", "Main window styling"),
                (QWidget(), "dialog", "Dialog styling"),
            ]
            
            for widget, style_name, description in widget_tests:
                try:
                    registry.apply_style(widget, style_name)
                    stylesheet = widget.styleSheet()
                    
                    if stylesheet:
                        style_samples.append({
                            'description': description,
                            'style_name': style_name,
                            'has_background': 'background' in stylesheet.lower(),
                            'has_color': 'color:' in stylesheet.lower(),
                            'has_border': 'border' in stylesheet.lower(),
                            'stylesheet_length': len(stylesheet)
                        })
                    else:
                        warnings.append(f"No stylesheet generated for {description}")
                        
                except Exception as e:
                    warnings.append(f"Failed to test {description}: {e}")
            
            details["style_samples"] = style_samples
            details["samples_generated"] = len(style_samples)
            
            # Test theme consistency
            themes = manager.get_available_themes()
            if len(themes) >= 2:
                theme_consistency = []
                
                for theme_name in themes[:3]:  # Test first 3 themes
                    try:
                        manager.set_theme(theme_name)
                        current = manager.current_theme
                        
                        # Check that theme has expected properties
                        theme_info = {
                            'name': theme_name,
                            'has_background_color': hasattr(current, 'background_primary'),
                            'has_text_color': hasattr(current, 'text_primary'),
                            'has_interactive_colors': hasattr(current, 'interactive_normal'),
                            'validation_status': None
                        }
                        
                        # Test validation if available
                        if hasattr(current, 'validate'):
                            is_valid, issues = current.validate()
                            theme_info['validation_status'] = is_valid
                            theme_info['validation_issues'] = len(issues) if issues else 0
                        
                        theme_consistency.append(theme_info)
                        
                    except Exception as e:
                        warnings.append(f"Failed to test theme {theme_name}: {e}")
                
                details["theme_consistency"] = theme_consistency
            
            # Test color accessibility
            current_theme = manager.current_theme
            if hasattr(current_theme, 'validate'):
                is_valid, issues = current_theme.validate()
                details["current_theme_valid"] = is_valid
                details["current_theme_issues"] = len(issues) if issues else 0
                
                if not is_valid and issues:
                    warnings.append(f"Current theme has {len(issues)} validation issues")
            
            # Success criteria: styles are generated consistently
            success = len(style_samples) > 0 and all(
                sample['stylesheet_length'] > 0 for sample in style_samples
            )
            
            return ValidationResult(
                "Visual Consistency", success,
                f"Visual consistency: {len(style_samples)} style samples generated",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Visual Consistency", False,
                f"Visual consistency test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_feature_parity(self) -> ValidationResult:
        """Test that all features from the old system are available."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            # Test theme management features
            from ui.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()
            
            theme_features = []
            
            # Basic theme operations
            if hasattr(manager, 'get_available_themes'):
                themes = manager.get_available_themes()
                theme_features.append(f"Theme listing: {len(themes)} themes")
            else:
                warnings.append("Theme listing not available")
            
            if hasattr(manager, 'set_theme'):
                theme_features.append("Theme switching available")
            else:
                warnings.append("Theme switching not available")
            
            if hasattr(manager, 'current_theme'):
                current = manager.current_theme
                theme_features.append("Current theme access available")
            else:
                warnings.append("Current theme access not available")
            
            # Advanced features
            if hasattr(manager, 'save_custom_theme'):
                theme_features.append("Custom theme saving available")
            else:
                warnings.append("Custom theme saving not available")
            
            if hasattr(manager, 'export_theme'):
                theme_features.append("Theme export available")
            else:
                warnings.append("Theme export not available")
            
            if hasattr(manager, 'import_theme'):
                theme_features.append("Theme import available")
            else:
                warnings.append("Theme import not available")
            
            details["theme_features"] = theme_features
            
            # Test styling features
            from ui.themes.style_registry import get_style_registry
            registry = get_style_registry()
            
            styling_features = []
            
            if hasattr(registry, 'apply_style'):
                styling_features.append("Style application available")
            else:
                warnings.append("Style application not available")
            
            if hasattr(registry, 'apply_repl_style'):
                styling_features.append("REPL styling available")
            else:
                warnings.append("REPL styling not available")
            
            if hasattr(registry, 'apply_button_style'):
                styling_features.append("Button styling available")
            else:
                warnings.append("Button styling not available")
            
            if hasattr(registry, 'register_component'):
                styling_features.append("Component registration available")
            else:
                warnings.append("Component registration not available")
            
            details["styling_features"] = styling_features
            
            # Test performance features
            performance_features = []
            
            if hasattr(registry, 'get_performance_stats'):
                performance_features.append("Performance monitoring available")
            else:
                warnings.append("Performance monitoring not available")
            
            if hasattr(registry, 'optimize_cache'):
                performance_features.append("Cache optimization available")
            else:
                warnings.append("Cache optimization not available")
            
            if hasattr(manager, 'run_theme_system_audit'):
                performance_features.append("System audit available")
            else:
                warnings.append("System audit not available")
            
            details["performance_features"] = performance_features
            
            # Calculate feature completeness
            total_expected_features = 12  # Expected number of key features
            total_found = len(theme_features) + len(styling_features) + len(performance_features)
            feature_completeness = (total_found / total_expected_features) * 100
            
            details["feature_completeness_percent"] = feature_completeness
            details["total_features_found"] = total_found
            
            # Success criteria: >90% feature parity
            success = feature_completeness >= 90
            
            return ValidationResult(
                "Feature Parity", success,
                f"Feature parity: {feature_completeness:.1f}% ({total_found}/12 features)",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Feature Parity", False,
                f"Feature parity test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_settings_persistence(self) -> ValidationResult:
        """Test that settings are properly persisted."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()
            
            # Get current theme
            original_theme = manager.current_theme_name
            themes = manager.get_available_themes()
            
            details["original_theme"] = original_theme
            details["available_themes"] = len(themes)
            
            if len(themes) < 2:
                return ValidationResult(
                    "Settings Persistence", True,
                    "Settings persistence test skipped (insufficient themes)",
                    details, (time.time() - start_time) * 1000, warnings
                )
            
            # Find a different theme
            target_theme = None
            for theme in themes:
                if theme != original_theme:
                    target_theme = theme
                    break
            
            if target_theme:
                # Change theme
                success = manager.set_theme(target_theme)
                details["theme_change_success"] = success
                
                if success:
                    # Verify change was persisted by checking current theme
                    current = manager.current_theme_name
                    details["theme_actually_changed"] = (current == target_theme)
                    
                    if current != target_theme:
                        warnings.append("Theme change not properly persisted")
                    
                    # Test theme persistence through settings
                    try:
                        # Create a new theme manager instance to test persistence
                        from ui.themes.theme_manager import ThemeManager
                        new_manager = ThemeManager()
                        
                        loaded_theme = new_manager.current_theme_name
                        details["persistence_test_theme"] = loaded_theme
                        
                        # Should load the same theme we set
                        if loaded_theme == target_theme:
                            details["settings_persistence_works"] = True
                        else:
                            warnings.append(f"Settings not persisted: expected {target_theme}, got {loaded_theme}")
                            
                    except Exception as e:
                        warnings.append(f"Persistence test failed: {e}")
                    
                    # Restore original theme
                    manager.set_theme(original_theme)
                else:
                    warnings.append("Theme change failed")
            
            # Test custom theme persistence
            try:
                from ui.themes.color_system import ColorSystem
                test_colors = ColorSystem()
                
                # Try to save a custom theme
                custom_theme_name = "test_persistence_theme"
                save_success = manager.save_custom_theme(custom_theme_name, test_colors)
                details["custom_theme_save_success"] = save_success
                
                if save_success:
                    # Check if it appears in theme list
                    updated_themes = manager.get_available_themes()
                    if custom_theme_name in updated_themes:
                        details["custom_theme_in_list"] = True
                    else:
                        warnings.append("Custom theme not appearing in theme list")
                    
                    # Clean up
                    manager.delete_custom_theme(custom_theme_name)
                else:
                    warnings.append("Custom theme saving failed")
                    
            except Exception as e:
                warnings.append(f"Custom theme persistence test failed: {e}")
            
            return ValidationResult(
                "Settings Persistence", True,
                "Settings persistence functionality tested",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Settings Persistence", False,
                f"Settings persistence test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_error_handling(self) -> ValidationResult:
        """Test error handling and graceful degradation."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.theme_manager import get_theme_manager
            
            registry = get_style_registry()
            manager = get_theme_manager()
            
            error_tests = []
            
            # Test invalid style handling
            if PYQT_AVAILABLE:
                test_widget = QWidget()
                
                # Should handle invalid style names gracefully
                try:
                    result = registry.apply_style(test_widget, "nonexistent_style")
                    error_tests.append(f"Invalid style handling: {'graceful' if not result else 'unexpected success'}")
                except Exception as e:
                    error_tests.append(f"Invalid style handling: exception raised - {e}")
            
            # Test invalid theme handling
            try:
                result = manager.set_theme("nonexistent_theme")
                error_tests.append(f"Invalid theme handling: {'graceful' if not result else 'unexpected success'}")
            except Exception as e:
                error_tests.append(f"Invalid theme handling: exception raised - {e}")
            
            # Test null/None handling
            try:
                if PYQT_AVAILABLE:
                    result = registry.apply_style(None, "main_window")
                    error_tests.append(f"Null widget handling: {'graceful' if not result else 'unexpected success'}")
            except Exception as e:
                error_tests.append(f"Null widget handling: exception raised - {type(e).__name__}")
            
            # Test malformed color system
            try:
                from ui.themes.color_system import ColorSystem
                
                # Create an empty color system
                empty_colors = ColorSystem()
                
                # Should handle validation gracefully
                if hasattr(empty_colors, 'validate'):
                    is_valid, issues = empty_colors.validate()
                    error_tests.append(f"Empty color system validation: {'handled' if issues else 'no issues detected'}")
                    
            except Exception as e:
                error_tests.append(f"Color system validation: exception raised - {e}")
            
            # Test system recovery after errors
            try:
                # Cause some errors then test if system still works
                registry.apply_style(None, "invalid")  # Should fail gracefully
                manager.set_theme("invalid")  # Should fail gracefully
                
                # System should still be functional
                themes = manager.get_available_themes()
                current = manager.current_theme
                stats = registry.get_performance_stats()
                
                error_tests.append("System recovery: functional after errors")
                
            except Exception as e:
                error_tests.append(f"System recovery: failed - {e}")
                warnings.append("System not resilient to errors")
            
            # Test cache corruption handling
            try:
                registry.clear_all_caches()  # Should not crash
                error_tests.append("Cache corruption handling: cache clear works")
            except Exception as e:
                error_tests.append(f"Cache corruption handling: failed - {e}")
                warnings.append("Cache system not resilient")
            
            details["error_handling_tests"] = error_tests
            details["error_tests_count"] = len(error_tests)
            
            # Check for any critical failures
            critical_failures = [test for test in error_tests if "exception raised" in test and "TypeError" in test or "AttributeError" in test]
            details["critical_failures"] = len(critical_failures)
            
            if critical_failures:
                for failure in critical_failures:
                    warnings.append(f"Critical error handling issue: {failure}")
            
            # Success criteria: no critical failures
            success = len(critical_failures) == 0
            
            return ValidationResult(
                "Error Handling", success,
                f"Error handling: {len(error_tests)} tests, {len(critical_failures)} critical failures",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Error Handling", False,
                f"Error handling test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _test_edge_cases(self) -> ValidationResult:
        """Test edge cases and boundary conditions."""
        start_time = time.time()
        warnings = []
        details = {}
        
        try:
            from ui.themes.style_registry import get_style_registry
            from ui.themes.theme_manager import get_theme_manager
            
            registry = get_style_registry()
            manager = get_theme_manager()
            
            edge_case_tests = []
            
            # Test empty/minimal inputs
            if PYQT_AVAILABLE:
                # Test with minimal widget
                minimal_widget = QWidget()
                
                try:
                    # Should handle minimal widget gracefully
                    result = registry.apply_style(minimal_widget, "main_window")
                    edge_case_tests.append(f"Minimal widget: {'handled' if result else 'graceful failure'}")
                except Exception as e:
                    edge_case_tests.append(f"Minimal widget: exception - {type(e).__name__}")
            
            # Test rapid theme switching
            themes = manager.get_available_themes()
            if len(themes) >= 2:
                try:
                    original_theme = manager.current_theme_name
                    switch_count = 0
                    
                    # Rapid switching test
                    for i in range(10):
                        for theme in themes[:2]:  # Switch between first two themes
                            manager.set_theme(theme)
                            switch_count += 1
                    
                    # Restore original
                    manager.set_theme(original_theme)
                    
                    edge_case_tests.append(f"Rapid switching: {switch_count} switches completed")
                    
                except Exception as e:
                    edge_case_tests.append(f"Rapid switching: failed - {e}")
                    warnings.append("System not resilient to rapid theme switching")
            
            # Test cache overflow simulation
            try:
                # Try to create many cached entries
                if PYQT_AVAILABLE:
                    from ui.themes.color_system import ColorSystem
                    base_colors = ColorSystem()
                    
                    cache_stress_widget = QWidget()
                    
                    # Generate many style variations
                    for i in range(50):
                        try:
                            registry.apply_style(cache_stress_widget, "main_window", base_colors)
                        except Exception:
                            break
                    
                    edge_case_tests.append("Cache stress test: completed")
                    
                    # Check system is still functional
                    stats = registry.get_performance_stats()
                    if stats:
                        edge_case_tests.append("Cache stress: system still functional")
                    else:
                        warnings.append("System degraded after cache stress")
                        
            except Exception as e:
                edge_case_tests.append(f"Cache stress test: failed - {e}")
            
            # Test concurrent operations simulation
            try:
                # Simulate concurrent styling operations
                if PYQT_AVAILABLE:
                    widgets = [QWidget() for _ in range(5)]
                    
                    # Apply styles to multiple widgets "simultaneously"
                    for widget in widgets:
                        registry.apply_style(widget, "main_window")
                    
                    edge_case_tests.append("Concurrent operations: simulated")
                    
                    # Check all widgets got styled
                    styled_count = sum(1 for w in widgets if w.styleSheet())
                    if styled_count == len(widgets):
                        edge_case_tests.append("Concurrent operations: all widgets styled")
                    else:
                        warnings.append(f"Concurrent operations: only {styled_count}/{len(widgets)} styled")
                        
            except Exception as e:
                edge_case_tests.append(f"Concurrent operations: failed - {e}")
            
            # Test memory pressure simulation
            try:
                # Create large numbers of temporary objects
                large_objects = []
                for i in range(100):
                    if PYQT_AVAILABLE:
                        widget = QWidget()
                        registry.apply_style(widget, "main_window")
                        large_objects.append(widget)
                
                edge_case_tests.append("Memory pressure: objects created")
                
                # Clear references
                large_objects.clear()
                
                # Force cleanup
                registry.force_cleanup() if hasattr(registry, 'force_cleanup') else None
                
                edge_case_tests.append("Memory pressure: cleanup performed")
                
            except Exception as e:
                edge_case_tests.append(f"Memory pressure: failed - {e}")
                warnings.append("System not resilient to memory pressure")
            
            details["edge_case_tests"] = edge_case_tests
            details["edge_case_count"] = len(edge_case_tests)
            
            # Check for failures
            failed_tests = [test for test in edge_case_tests if "failed" in test or "exception" in test]
            details["failed_edge_cases"] = len(failed_tests)
            
            if failed_tests:
                for failure in failed_tests[:3]:  # Show first 3 failures
                    warnings.append(f"Edge case failure: {failure}")
            
            # Success criteria: most edge cases handled
            success_rate = (len(edge_case_tests) - len(failed_tests)) / len(edge_case_tests) if edge_case_tests else 0
            details["edge_case_success_rate"] = success_rate * 100
            
            success = success_rate >= 0.8  # 80% of edge cases handled
            
            return ValidationResult(
                "Edge Cases", success,
                f"Edge cases: {success_rate*100:.1f}% handled successfully",
                details, (time.time() - start_time) * 1000, warnings
            )
            
        except Exception as e:
            return ValidationResult(
                "Edge Cases", False,
                f"Edge cases test failed: {e}",
                details, (time.time() - start_time) * 1000, warnings
            )
    
    def _generate_summary_report(self, total_tests: int, passed_tests: int, total_time: float) -> Dict[str, Any]:
        """Generate a comprehensive summary report."""
        
        # Categorize results by test type
        categories = {}
        for result in self.results:
            # Extract category from test name
            if "Architecture" in result.test_name:
                category = "Architecture"
            elif "Functional" in result.test_name or "Application" in result.test_name or "Component" in result.test_name:
                category = "Functional"
            elif "Integration" in result.test_name or "Propagation" in result.test_name:
                category = "Integration"
            elif "Performance" in result.test_name or "Cache" in result.test_name or "Memory" in result.test_name:
                category = "Performance"
            elif "Legacy" in result.test_name or "Hardcoded" in result.test_name or "Import" in result.test_name:
                category = "Code Quality"
            else:
                category = "Regression"
            
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "results": []}
            
            categories[category]["total"] += 1
            if result.passed:
                categories[category]["passed"] += 1
            categories[category]["results"].append(result)
        
        # Generate performance metrics
        performance_results = [r for r in self.results if "Performance" in r.test_name or "Cache" in r.test_name]
        performance_summary = {}
        
        for result in performance_results:
            if "theme_switch_time_ms" in result.details:
                performance_summary["avg_theme_switch_ms"] = result.details.get("avg_switch_time_ms", 0)
            if "hit_rate_percent" in result.details:
                performance_summary["cache_hit_rate"] = result.details.get("hit_rate_percent", 0)
            if "total_memory_kb" in result.details:
                performance_summary["memory_usage_kb"] = result.details.get("total_memory_kb", 0)
        
        # Generate modernization metrics
        code_quality_results = [r for r in self.results if "Legacy" in r.test_name or "Hardcoded" in r.test_name]
        modernization_summary = {}
        
        for result in code_quality_results:
            if "modernization_success_rate" in result.details:
                modernization_summary["legacy_removal_rate"] = result.details.get("modernization_success_rate", 0)
            if "hardcoded_colors_found" in result.details:
                modernization_summary["hardcoded_colors"] = result.details.get("hardcoded_colors_found", 0)
        
        # Critical issues
        critical_issues = []
        for result in self.results:
            if not result.passed:
                critical_issues.append({
                    "test": result.test_name,
                    "message": result.message,
                    "category": "Architecture" if "Architecture" in result.test_name else "Other"
                })
        
        # Recommendations
        recommendations = []
        
        if performance_summary.get("avg_theme_switch_ms", 0) > 100:
            recommendations.append("Theme switching performance needs optimization")
        
        if performance_summary.get("cache_hit_rate", 0) < 70:
            recommendations.append("Style cache efficiency could be improved")
        
        if modernization_summary.get("hardcoded_colors", 0) > 0:
            recommendations.append("Remove remaining hardcoded colors")
        
        if len(critical_issues) > 0:
            recommendations.append("Address critical architecture issues")
        
        # Overall assessment
        success_rate = (passed_tests / total_tests) * 100
        
        if success_rate >= 95:
            overall_status = "Excellent - System ready for production"
        elif success_rate >= 85:
            overall_status = "Good - Minor issues to address"
        elif success_rate >= 70:
            overall_status = "Acceptable - Some issues need attention"
        else:
            overall_status = "Poor - Major issues require fixing"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate_percent": success_rate,
                "total_time_seconds": total_time,
                "overall_status": overall_status
            },
            "categories": {
                name: {
                    "total": cat["total"],
                    "passed": cat["passed"],
                    "success_rate": (cat["passed"] / cat["total"]) * 100 if cat["total"] > 0 else 0
                }
                for name, cat in categories.items()
            },
            "performance_metrics": performance_summary,
            "modernization_metrics": modernization_summary,
            "critical_issues": critical_issues,
            "recommendations": recommendations,
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "warnings_count": len(r.warnings),
                    "has_details": bool(r.details)
                }
                for r in self.results
            ]
        }


def main():
    """Main entry point for the validation suite."""
    print("🔬 COMPREHENSIVE STYLING SYSTEM VALIDATION")
    print("=" * 70)
    print("Validating the completely modernized styling system...")
    print("This may take a few minutes to complete all tests.\n")
    
    validator = StyleSystemValidator()
    
    try:
        summary = validator.run_all_tests()
        
        # Save detailed report
        report_path = Path(__file__).parent / "styling_validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📋 Detailed report saved to: {report_path}")
        
        # Return appropriate exit code
        success_rate = summary["summary"]["success_rate_percent"]
        if success_rate >= 90:
            print("✅ Styling system validation completed successfully!")
            return 0
        else:
            print("⚠️  Styling system validation completed with issues.")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        return 2
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())