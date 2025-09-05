# Implementation Guide: Modern Styling Architecture

## Quick Start Guide

This guide provides step-by-step instructions for implementing the modern styling architecture in your development workflow.

## 1. Setting Up the Modern System

### Import the New Architecture
```python
# Core styling components
from ghostman.src.ui.themes.style_registry import get_style_registry, apply_style_to_widget, ComponentCategory
from ghostman.src.ui.themes.component_styler import style_button, style_input, style_repl_component
from ghostman.src.ui.themes.repl_style_registry import REPLComponent, StyleConfig, apply_repl_style_to_widget

# Performance optimization
from ghostman.src.ui.themes.performance_optimizer import get_performance_optimizer, optimize_for_startup

# Validation and migration
from ghostman.src.ui.themes.migration_utils import scan_for_legacy_patterns, convert_file_safely
from ghostman.src.ui.themes.validation_tools import get_development_guards
```

### Initialize at Application Startup
```python
def initialize_modern_styling():
    """Initialize the modern styling system at application startup."""
    
    # Optimize for startup performance
    optimize_for_startup()
    
    # Enable development guards (optional, for development)
    guards = get_development_guards()
    guards.enabled = True  # Warns about legacy pattern usage
    
    # Pre-compile styles for current theme
    optimizer = get_performance_optimizer()
    from ghostman.src.ui.themes.theme_manager import get_theme_manager
    current_theme = get_theme_manager().current_theme
    optimizer.optimize_for_theme(current_theme)
    
    logger.info("Modern styling system initialized")

# Call during application startup
initialize_modern_styling()
```

## 2. Migration Patterns

### Pattern 1: Simple Button Styling

**Before (Legacy)**:
```python
self.submit_button.setStyleSheet(f"""
    QPushButton {{
        background-color: {colors.primary};
        color: {colors.text_primary};
        border: 1px solid {colors.border_primary};
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {colors.primary_hover};
    }}
""")
```

**After (Modern)**:
```python
style_button(self.submit_button, "submit_button") \
    .make_primary() \
    .apply_style()
```

### Pattern 2: Input Field with Validation

**Before (Legacy)**:
```python
error_style = f"""
    QLineEdit {{
        background-color: {colors.background_tertiary};
        border: 2px solid {colors.status_error};
        color: {colors.text_primary};
        padding: 4px;
        border-radius: 4px;
    }}
"""
if has_error:
    self.email_input.setStyleSheet(error_style)
else:
    self.email_input.setStyleSheet(normal_style)
```

**After (Modern)**:
```python
styler = style_input(self.email_input, "email_input")
if has_error:
    styler.show_error("Invalid email format")
else:
    styler.clear_validation()
styler.apply_style()
```

### Pattern 3: REPL Component Styling

**Before (Legacy)**:
```python
opacity = 0.9
self.output_panel.setStyleSheet(f"""
    QTextBrowser {{
        background-color: rgba({bg_r}, {bg_g}, {bg_b}, {opacity});
        color: {colors.text_primary};
        border: 1px solid {colors.border_primary};
        border-radius: 4px;
        padding: 8px;
        font-size: 12px;
    }}
""")
```

**After (Modern)**:
```python
apply_repl_style_to_widget(
    self.output_panel,
    REPLComponent.OUTPUT_BROWSER,
    StyleConfig(opacity=0.9),
    "repl_output_panel"
)
```

### Pattern 4: Complex Dialog Styling

**Before (Legacy)**:
```python
dialog_style = f"""
    QDialog {{
        background-color: {colors.background_primary};
        color: {colors.text_primary};
    }}
    QGroupBox {{
        color: {colors.text_primary};
        border: 1px solid {colors.border_primary};
        border-radius: 5px;
        margin-top: 10px;
        font-weight: bold;
    }}
    /* ... many more CSS rules ... */
"""
self.setStyleSheet(dialog_style)
```

**After (Modern)**:
```python
registry = get_style_registry()
registry.register_component(self, "settings_dialog", ComponentCategory.DIALOG)
registry.apply_style(self, "settings_dialog")
```

## 3. Component Lifecycle Management

### Register Components for Automatic Management
```python
class MyDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        # Register with style registry for automatic lifecycle management
        registry = get_style_registry()
        registry.register_component(self, "my_dialog", ComponentCategory.DIALOG)
        
        # Components will be automatically styled on theme changes
        # and cleaned up when dialog is destroyed
    
    def customize_appearance(self):
        # Apply custom styling after registration
        registry = get_style_registry()
        registry.apply_style(self, "custom_dialog_template")
```

### Automatic Theme Updates
```python
# When theme changes, all registered components update automatically
theme_manager = get_theme_manager()
theme_manager.set_theme("new_theme_name")
# All registered components automatically update to new theme
```

## 4. Performance Optimization Patterns

### Pre-compile Styles for Critical Components
```python
def optimize_for_repl():
    """Optimize styling for REPL components - call when REPL is created."""
    
    optimizer = get_performance_optimizer()
    theme_manager = get_theme_manager()
    
    # Pre-compile common REPL styles
    results = optimizer.optimize_for_theme(theme_manager.current_theme)
    logger.info(f"REPL optimization: {results['precompiled_styles']} styles ready")
```

### Monitor Performance
```python
@performance_monitor  # Decorator automatically measures timing
def apply_complex_styling():
    """Apply styling to many components."""
    for widget in self.widgets:
        apply_style_to_widget(widget, "widget_template")

# Performance is automatically tracked and reported
```

### Cache Management
```python
# Get performance statistics
optimizer = get_performance_optimizer()
stats = optimizer.get_performance_report()
print(f"Cache hit rate: {stats['adaptive_cache']['hit_rate_percent']}%")

# Clear caches during development
if DEBUG_MODE:
    optimizer.cache.clear()
```

## 5. Validation and Quality Assurance

### Development-Time Validation
```python
# Enable real-time validation during development
guards = get_development_guards()
guards.enabled = True
guards.warning_threshold = ValidationLevel.WARNING

# Validation automatically warns about legacy patterns:
# WARNING: Legacy styling detected at file.py:42
# Consider using StyleRegistry.apply_style(widget, 'template_name')
```

### Pre-commit Hook Setup
```bash
# Add to your .git/hooks/pre-commit
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from ghostman.src.ui.themes.validation_tools import get_pre_commit_hook

hook = get_pre_commit_hook()
success = hook.validate_changes()
sys.exit(0 if success else 1)
```

### CI/CD Integration
```yaml
# .github/workflows/style-validation.yml
name: Style Validation
on: [push, pull_request]
jobs:
  validate-styling:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Validate Styling Practices
      run: |
        python -m ghostman.src.ui.themes.validation_tools \
          --validate-project ghostman/src \
          --output style_report.json
    - name: Upload Report
      uses: actions/upload-artifact@v2
      with:
        name: style-report
        path: style_report.json
```

## 6. Migration Workflow

### Step 1: Assess Current State
```python
from ghostman.src.ui.themes.migration_utils import generate_migration_report

# Scan entire project
project_root = Path("ghostman/src")
report = generate_migration_report(project_root, Path("migration_report.md"))

print(f"Found {report.count('legacy patterns')} patterns to migrate")
```

### Step 2: Safe File Conversion
```python
# Always dry run first to see what would change
result = convert_file_safely(Path("my_widget.py"), dry_run=True)
print(f"Would make {result['changes']} changes")
print("Preview:", result.get('preview_content', 'N/A')[:200])

# Apply changes after review
if input("Apply changes? (y/n): ").lower() == 'y':
    result = convert_file_safely(Path("my_widget.py"), dry_run=False)
    print(f"Applied {result['changes']} changes")
```

### Step 3: Validate Changes
```python
from ghostman.src.ui.themes.validation_tools import StyleValidationRules

validator = StyleValidationRules()
with open("converted_file.py", 'r') as f:
    content = f.read()

issues = validator.validate_code(content, "converted_file.py")
for issue in issues:
    print(f"{issue.level.value}: {issue.message}")
```

## 7. Custom Style Templates

### Create Custom Templates
```python
# Register custom style generator
registry = get_style_registry()

def my_custom_style(colors):
    return f"""
    QWidget {{
        background-color: {colors.background_secondary};
        border: 2px solid {colors.primary};
        border-radius: 8px;
        padding: 12px;
    }}
    """

registry.register_custom_style_generator("my_custom_template", my_custom_style)

# Use custom template
registry.apply_style(my_widget, "my_custom_template")
```

### Extend Component Stylers
```python
class CustomButtonStyler(ButtonStyler):
    def make_special_action(self):
        """Custom styling for special action buttons."""
        return self.set_variant("special").set_size("large")
    
    def apply_style(self, colors=None):
        # Custom logic before applying
        if self.variant == "special":
            # Apply special custom styling
            custom_colors = colors or get_theme_manager().current_theme
            special_style = self._generate_special_style(custom_colors)
            self.widget.setStyleSheet(special_style)
            return True
        else:
            return super().apply_style(colors)
```

## 8. Debugging and Troubleshooting

### Performance Debugging
```python
# Get detailed performance metrics
optimizer = get_performance_optimizer()
report = optimizer.get_performance_report()

print("Theme Switching:")
print(f"  Average time: {report['theme_switching']['average_switch_time_ms']:.1f}ms")
print(f"  Performance improvement: {report['theme_switching']['performance_improvement_percent']:.1f}%")

print("Cache Performance:")
print(f"  Hit rate: {report['adaptive_cache']['hit_rate_percent']:.1f}%")
print(f"  Memory usage: {report['adaptive_cache']['memory_usage_kb']:.1f}KB")
```

### Style Registry Debugging
```python
registry = get_style_registry()
stats = registry.get_performance_stats()

print("Style Registry:")
print(f"  Registered components: {stats['registered_components']}")
print(f"  Cache hit rate: {stats['style_cache']['hit_rate_percent']:.1f}%")
print(f"  REPL registry hit rate: {stats['repl_registry']['hit_rate_percent']:.1f}%")
```

### Common Issues and Solutions

**Issue**: Styles not applying after theme change
**Solution**: Ensure component is registered with style registry
```python
# Register component for automatic theme updates
registry.register_component(widget, "my_widget", ComponentCategory.DISPLAY)
```

**Issue**: Performance slower than expected
**Solution**: Check cache hit rates and pre-compile styles
```python
# Pre-compile styles for better performance
optimizer.optimize_for_theme(current_theme)
```

**Issue**: Legacy validation warnings
**Solution**: Use migration utilities to modernize code
```python
# Scan and convert legacy patterns
patterns = scan_for_legacy_patterns(Path("."))
convert_file_safely(Path("problem_file.py"))
```

## 9. Best Practices

### 1. Always Register Components
```python
# Good: Component gets automatic theme updates and cleanup
registry.register_component(widget, "unique_id", category)
registry.apply_style(widget, "template")

# Avoid: Manual styling without registration
widget.setStyleSheet("...")  # No automatic updates
```

### 2. Use Semantic Stylers
```python
# Good: Clear intent and type safety
style_button(save_btn, "save_button").make_primary().apply_style()

# Avoid: Generic styling
apply_style_to_widget(save_btn, "generic_template")
```

### 3. Leverage Performance Optimization
```python
# Good: Pre-compile frequently used styles
optimizer.optimize_for_theme(theme)

# Good: Use REPL registry for REPL components
apply_repl_style_to_widget(widget, REPLComponent.OUTPUT_PANEL)
```

### 4. Enable Validation
```python
# Enable during development
guards.enabled = True

# Use pre-commit hooks
# Install validation in CI/CD
```

This implementation guide provides everything needed to successfully adopt the modern styling architecture. Start with small components, validate changes, and gradually migrate larger systems using the provided tools and patterns.