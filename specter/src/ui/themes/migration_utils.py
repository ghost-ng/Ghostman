"""
Migration Utilities for Legacy to Modern Styling Transition.

This module provides tools to safely transition from legacy setStyleSheet() patterns
to the modern styling architecture, with automated detection, conversion, and validation.

Key Features:
- Automated legacy pattern detection
- Safe CSS-to-modern-API conversion
- Backwards compatibility during migration
- Performance impact analysis
- Developer-friendly migration guides
"""

import logging
import re
import ast
import inspect
from typing import Dict, List, Tuple, Optional, Set, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("specter.migration_utils")


class LegacyPattern(Enum):
    """Types of legacy styling patterns found in code."""
    SET_STYLESHEET_INLINE = "setStyleSheet_inline"
    SET_STYLESHEET_VARIABLE = "setStyleSheet_variable"
    HARDCODED_RGBA = "hardcoded_rgba"
    CSS_STRING_CONCATENATION = "css_concatenation"
    MANUAL_COLOR_CALCULATION = "manual_color_calc"
    THEME_PROPERTY_ACCESS = "theme_property_access"


@dataclass
class LegacyPatternMatch:
    """Information about a found legacy pattern."""
    pattern_type: LegacyPattern
    file_path: str
    line_number: int
    code_snippet: str
    suggested_replacement: Optional[str] = None
    confidence_score: float = 0.0
    migration_complexity: str = "simple"  # simple, moderate, complex
    performance_impact: str = "low"  # low, medium, high
    breaking_changes: List[str] = field(default_factory=list)


class LegacyPatternDetector:
    """
    Automated detection of legacy styling patterns in Python code.
    
    Scans source files to identify manual setStyleSheet() calls, hardcoded
    colors, and other patterns that should be migrated to the modern system.
    """
    
    def __init__(self):
        self.patterns = {
            LegacyPattern.SET_STYLESHEET_INLINE: [
                r'\.setStyleSheet\s*\(\s*["\']([^"\']*)["\']',
                r'\.setStyleSheet\s*\(\s*f["\']([^"\']*)["\']',
            ],
            LegacyPattern.SET_STYLESHEET_VARIABLE: [
                r'\.setStyleSheet\s*\(\s*(\w+)\s*\)',
            ],
            LegacyPattern.HARDCODED_RGBA: [
                r'rgba?\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+.*?\)',
                r'#[0-9a-fA-F]{3,8}',
            ],
            LegacyPattern.CSS_STRING_CONCATENATION: [
                r'["\'][^"\']*\{\s*[^}]*\}\s*["\'].*?\+',
                r'f["\'][^"\']*\{.*?\}[^"\']*["\']',
            ],
            LegacyPattern.MANUAL_COLOR_CALCULATION: [
                r'QColor\s*\([^)]*\)\.name\s*\(\)',
                r'\.lighter\s*\(\s*\d*\s*\)',
                r'\.darker\s*\(\s*\d*\s*\)',
            ],
        }
        
        self.replacement_suggestions = {
            LegacyPattern.SET_STYLESHEET_INLINE: self._suggest_inline_replacement,
            LegacyPattern.SET_STYLESHEET_VARIABLE: self._suggest_variable_replacement,
            LegacyPattern.HARDCODED_RGBA: self._suggest_color_replacement,
            LegacyPattern.CSS_STRING_CONCATENATION: self._suggest_template_replacement,
            LegacyPattern.MANUAL_COLOR_CALCULATION: self._suggest_color_utils_replacement,
        }
    
    def scan_file(self, file_path: Path) -> List[LegacyPatternMatch]:
        """
        Scan a Python file for legacy styling patterns.
        
        Args:
            file_path: Path to the Python file to scan
            
        Returns:
            List of found legacy patterns
        """
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Scan for each pattern type
            for pattern_type, regexes in self.patterns.items():
                for regex in regexes:
                    for match in re.finditer(regex, content, re.MULTILINE | re.DOTALL):
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Get the full line for context
                        if 1 <= line_num <= len(lines):
                            code_snippet = lines[line_num - 1].strip()
                        else:
                            code_snippet = match.group(0)
                        
                        # Generate suggestion
                        suggestion = None
                        if pattern_type in self.replacement_suggestions:
                            suggestion = self.replacement_suggestions[pattern_type](
                                match.group(0), code_snippet
                            )
                        
                        pattern_match = LegacyPatternMatch(
                            pattern_type=pattern_type,
                            file_path=str(file_path),
                            line_number=line_num,
                            code_snippet=code_snippet,
                            suggested_replacement=suggestion,
                            confidence_score=self._calculate_confidence(pattern_type, match.group(0)),
                            migration_complexity=self._assess_complexity(pattern_type, code_snippet),
                            performance_impact=self._assess_performance_impact(pattern_type)
                        )
                        
                        matches.append(pattern_match)
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
        
        return matches
    
    def scan_directory(self, directory: Path, 
                      patterns: Optional[List[str]] = None) -> Dict[str, List[LegacyPatternMatch]]:
        """
        Scan a directory for legacy styling patterns.
        
        Args:
            directory: Directory to scan
            patterns: File patterns to include (default: ['*.py'])
            
        Returns:
            Dictionary mapping file paths to found patterns
        """
        if patterns is None:
            patterns = ['*.py']
        
        results = {}
        
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    matches = self.scan_file(file_path)
                    if matches:
                        results[str(file_path)] = matches
        
        return results
    
    def _suggest_inline_replacement(self, original: str, context: str) -> str:
        """Suggest replacement for inline setStyleSheet calls."""
        # Extract widget variable name from context
        widget_match = re.search(r'(\w+)\.setStyleSheet', context)
        widget_name = widget_match.group(1) if widget_match else 'widget'
        
        # Determine appropriate modern approach
        if 'button' in context.lower() or 'QPushButton' in context:
            return f"style_button({widget_name}, '{widget_name}_button').apply_style()"
        elif 'input' in context.lower() or 'QLineEdit' in context:
            return f"style_input({widget_name}, '{widget_name}_input').apply_style()"
        elif 'repl' in context.lower():
            return f"apply_repl_style_to_widget({widget_name}, REPLComponent.OUTPUT_PANEL, None, '{widget_name}_repl')"
        else:
            return f"apply_style_to_widget({widget_name}, 'main_window', '{widget_name}')"
    
    def _suggest_variable_replacement(self, original: str, context: str) -> str:
        """Suggest replacement for variable-based setStyleSheet calls."""
        widget_match = re.search(r'(\w+)\.setStyleSheet', context)
        widget_name = widget_match.group(1) if widget_match else 'widget'
        
        return f"# Replace style variable with: get_style_registry().apply_style({widget_name}, 'template_name')"
    
    def _suggest_color_replacement(self, original: str, context: str) -> str:
        """Suggest replacement for hardcoded colors."""
        return f"# Replace hardcoded color with theme color: colors.primary (or appropriate semantic color)"
    
    def _suggest_template_replacement(self, original: str, context: str) -> str:
        """Suggest replacement for CSS string concatenation."""
        return f"# Use StyleTemplates.get_style() or component styler instead of string concatenation"
    
    def _suggest_color_utils_replacement(self, original: str, context: str) -> str:
        """Suggest replacement for manual color calculations."""
        if '.lighter(' in original:
            return "# Use ColorUtils.lighten(color, factor) instead"
        elif '.darker(' in original:
            return "# Use ColorUtils.darken(color, factor) instead"
        else:
            return "# Use ColorUtils methods for color manipulation"
    
    def _calculate_confidence(self, pattern_type: LegacyPattern, match_text: str) -> float:
        """Calculate confidence score for pattern match."""
        base_confidence = {
            LegacyPattern.SET_STYLESHEET_INLINE: 0.9,
            LegacyPattern.SET_STYLESHEET_VARIABLE: 0.8,
            LegacyPattern.HARDCODED_RGBA: 0.7,
            LegacyPattern.CSS_STRING_CONCATENATION: 0.8,
            LegacyPattern.MANUAL_COLOR_CALCULATION: 0.9,
        }.get(pattern_type, 0.5)
        
        # Adjust based on context clues
        if 'setStyleSheet' in match_text:
            base_confidence += 0.1
        if 'rgba(' in match_text:
            base_confidence += 0.05
        if 'f"' in match_text or "f'" in match_text:
            base_confidence += 0.05
        
        return min(1.0, base_confidence)
    
    def _assess_complexity(self, pattern_type: LegacyPattern, code_snippet: str) -> str:
        """Assess migration complexity for a pattern."""
        if pattern_type == LegacyPattern.SET_STYLESHEET_INLINE:
            # Check if it's a simple single-property style
            if code_snippet.count(':') <= 2 and code_snippet.count(';') <= 2:
                return "simple"
            elif code_snippet.count('{') <= 1:
                return "moderate"
            else:
                return "complex"
        
        elif pattern_type == LegacyPattern.CSS_STRING_CONCATENATION:
            return "complex"  # Usually requires careful refactoring
        
        elif pattern_type == LegacyPattern.HARDCODED_RGBA:
            return "simple"  # Just replace with theme color
        
        else:
            return "moderate"
    
    def _assess_performance_impact(self, pattern_type: LegacyPattern) -> str:
        """Assess performance impact of migrating this pattern."""
        high_impact_patterns = [
            LegacyPattern.CSS_STRING_CONCATENATION,
            LegacyPattern.MANUAL_COLOR_CALCULATION
        ]
        
        medium_impact_patterns = [
            LegacyPattern.SET_STYLESHEET_INLINE,
            LegacyPattern.SET_STYLESHEET_VARIABLE
        ]
        
        if pattern_type in high_impact_patterns:
            return "high"  # Significant performance improvement expected
        elif pattern_type in medium_impact_patterns:
            return "medium"  # Moderate performance improvement
        else:
            return "low"  # Minor performance improvement


class MigrationConverter:
    """
    Automated conversion of legacy patterns to modern equivalents.
    
    Provides safe, incremental migration with backwards compatibility.
    """
    
    def __init__(self):
        self.conversion_rules = {}
        self.backup_enabled = True
        self.validation_enabled = True
    
    def convert_file(self, file_path: Path, 
                    patterns: Optional[List[LegacyPatternMatch]] = None,
                    dry_run: bool = True) -> Dict[str, Any]:
        """
        Convert legacy patterns in a file to modern equivalents.
        
        Args:
            file_path: Path to file to convert
            patterns: Specific patterns to convert (auto-detect if None)
            dry_run: If True, show what would be changed without modifying files
            
        Returns:
            Dictionary with conversion results and statistics
        """
        if patterns is None:
            detector = LegacyPatternDetector()
            patterns = detector.scan_file(file_path)
        
        if not patterns:
            return {"status": "no_patterns", "changes": 0}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                lines = original_content.split('\n')
            
            modified_lines = lines.copy()
            changes_made = 0
            conversion_log = []
            
            # Sort patterns by line number (descending) to avoid line number shifts
            patterns_sorted = sorted(patterns, key=lambda p: p.line_number, reverse=True)
            
            for pattern in patterns_sorted:
                if pattern.suggested_replacement:
                    line_idx = pattern.line_number - 1
                    if 0 <= line_idx < len(modified_lines):
                        original_line = modified_lines[line_idx]
                        
                        # Apply simple replacements for high-confidence patterns
                        if pattern.confidence_score >= 0.8 and pattern.migration_complexity == "simple":
                            if pattern.pattern_type == LegacyPattern.SET_STYLESHEET_INLINE:
                                # Add import if needed
                                self._add_modern_imports(modified_lines)
                                
                                # Replace the line
                                modified_lines[line_idx] = self._apply_indentation(
                                    pattern.suggested_replacement,
                                    original_line
                                )
                                changes_made += 1
                                
                                conversion_log.append({
                                    "line": pattern.line_number,
                                    "original": original_line.strip(),
                                    "replacement": pattern.suggested_replacement,
                                    "pattern_type": pattern.pattern_type.value
                                })
                        else:
                            # Add comment for manual review
                            comment = f"# TODO: Migrate legacy pattern - {pattern.suggested_replacement}"
                            modified_lines.insert(line_idx, self._apply_indentation(comment, original_line))
                            
                            conversion_log.append({
                                "line": pattern.line_number,
                                "action": "commented",
                                "suggestion": pattern.suggested_replacement,
                                "pattern_type": pattern.pattern_type.value
                            })
            
            result = {
                "status": "success",
                "changes": changes_made,
                "total_patterns": len(patterns),
                "conversion_log": conversion_log,
                "dry_run": dry_run
            }
            
            if not dry_run and changes_made > 0:
                # Create backup
                if self.backup_enabled:
                    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                    backup_path.write_text(original_content, encoding='utf-8')
                    result["backup_path"] = str(backup_path)
                
                # Write modified content
                modified_content = '\n'.join(modified_lines)
                file_path.write_text(modified_content, encoding='utf-8')
                result["file_modified"] = True
            else:
                result["file_modified"] = False
                if dry_run:
                    result["preview_content"] = '\n'.join(modified_lines)
            
            return result
            
        except Exception as e:
            logger.error(f"Error converting file {file_path}: {e}")
            return {"status": "error", "error": str(e)}
    
    def _add_modern_imports(self, lines: List[str]):
        """Add required imports for modern styling system."""
        import_lines = [
            "from specter.src.ui.themes.component_styler import style_button, style_input, apply_repl_style_to_widget",
            "from specter.src.ui.themes.style_registry import apply_style_to_widget",
            "from specter.src.ui.themes.repl_style_registry import REPLComponent"
        ]
        
        # Find where to insert imports (after existing imports)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                insert_idx = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
        
        # Check if imports already exist
        content = '\n'.join(lines)
        for import_line in import_lines:
            if import_line not in content:
                lines.insert(insert_idx, import_line)
                insert_idx += 1
    
    def _apply_indentation(self, new_line: str, reference_line: str) -> str:
        """Apply the same indentation as the reference line."""
        indent = len(reference_line) - len(reference_line.lstrip())
        return ' ' * indent + new_line.lstrip()


class MigrationValidator:
    """
    Validation utilities for ensuring migration safety and correctness.
    """
    
    @staticmethod
    def validate_conversion(original_file: Path, converted_file: Path) -> Dict[str, Any]:
        """
        Validate that a conversion maintains functionality.
        
        Args:
            original_file: Path to original file
            converted_file: Path to converted file
            
        Returns:
            Validation results
        """
        validation_results = {
            "syntax_valid": False,
            "imports_resolved": False,
            "style_calls_valid": False,
            "warnings": [],
            "errors": []
        }
        
        try:
            # Test syntax validity
            with open(converted_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                ast.parse(content)
                validation_results["syntax_valid"] = True
            except SyntaxError as e:
                validation_results["errors"].append(f"Syntax error: {e}")
            
            # Check for required imports
            required_imports = [
                'component_styler',
                'style_registry',
                'repl_style_registry'
            ]
            
            missing_imports = []
            for import_name in required_imports:
                if import_name not in content:
                    missing_imports.append(import_name)
            
            if not missing_imports:
                validation_results["imports_resolved"] = True
            else:
                validation_results["warnings"].append(f"Missing imports: {missing_imports}")
            
            # Look for potential issues in style calls
            style_call_patterns = [
                r'style_button\(',
                r'style_input\(',
                r'apply_style_to_widget\(',
                r'apply_repl_style_to_widget\('
            ]
            
            valid_calls = 0
            for pattern in style_call_patterns:
                matches = re.findall(pattern, content)
                valid_calls += len(matches)
            
            validation_results["style_calls_valid"] = valid_calls > 0
            validation_results["style_calls_found"] = valid_calls
            
        except Exception as e:
            validation_results["errors"].append(f"Validation error: {e}")
        
        return validation_results


class MigrationReporter:
    """
    Generates comprehensive migration reports and statistics.
    """
    
    def generate_report(self, scan_results: Dict[str, List[LegacyPatternMatch]], 
                       output_path: Optional[Path] = None) -> str:
        """
        Generate a comprehensive migration report.
        
        Args:
            scan_results: Results from scanning files
            output_path: Optional path to save report file
            
        Returns:
            Report content as string
        """
        total_patterns = sum(len(patterns) for patterns in scan_results.values())
        total_files = len(scan_results)
        
        # Count by pattern type
        pattern_counts = {}
        complexity_counts = {"simple": 0, "moderate": 0, "complex": 0}
        impact_counts = {"low": 0, "medium": 0, "high": 0}
        
        for patterns in scan_results.values():
            for pattern in patterns:
                pattern_counts[pattern.pattern_type] = pattern_counts.get(pattern.pattern_type, 0) + 1
                complexity_counts[pattern.migration_complexity] += 1
                impact_counts[pattern.performance_impact] += 1
        
        # Generate report
        report = f"""
# Specter Legacy Styling Migration Report

## Summary
- **Total files scanned**: {total_files}
- **Total legacy patterns found**: {total_patterns}
- **Estimated migration effort**: {self._estimate_effort(complexity_counts)} hours

## Pattern Breakdown
"""
        
        for pattern_type, count in pattern_counts.items():
            percentage = (count / total_patterns * 100) if total_patterns > 0 else 0
            report += f"- **{pattern_type.value}**: {count} occurrences ({percentage:.1f}%)\n"
        
        report += f"""
## Migration Complexity
- **Simple**: {complexity_counts['simple']} patterns (~5 minutes each)
- **Moderate**: {complexity_counts['moderate']} patterns (~15 minutes each)  
- **Complex**: {complexity_counts['complex']} patterns (~45 minutes each)

## Performance Impact
- **High impact**: {impact_counts['high']} patterns (significant improvement expected)
- **Medium impact**: {impact_counts['medium']} patterns (moderate improvement)
- **Low impact**: {impact_counts['low']} patterns (minor improvement)

## File Details
"""
        
        for file_path, patterns in scan_results.items():
            report += f"\n### {file_path}\n"
            report += f"- **Patterns found**: {len(patterns)}\n"
            
            for pattern in patterns[:5]:  # Show first 5 patterns
                report += f"  - Line {pattern.line_number}: {pattern.pattern_type.value} "
                report += f"({pattern.migration_complexity} complexity)\n"
            
            if len(patterns) > 5:
                report += f"  - ... and {len(patterns) - 5} more patterns\n"
        
        report += f"""
## Migration Strategy

### Phase 1: Simple Patterns (Automated)
- Replace inline setStyleSheet calls with component stylers
- Update hardcoded colors to use theme colors
- Estimated time: {complexity_counts['simple'] * 5 / 60:.1f} hours

### Phase 2: Moderate Patterns (Semi-automated)
- Convert variable-based stylesheets to templates
- Refactor CSS string concatenation
- Estimated time: {complexity_counts['moderate'] * 15 / 60:.1f} hours

### Phase 3: Complex Patterns (Manual)
- Redesign complex styling logic
- Create custom style templates
- Estimated time: {complexity_counts['complex'] * 45 / 60:.1f} hours

## Next Steps
1. Run automated migration for simple patterns
2. Review and test Phase 1 changes
3. Begin Phase 2 with manual oversight
4. Create custom templates for complex cases
5. Performance test after each phase

## Tools Available
- `LegacyPatternDetector`: Scan for patterns
- `MigrationConverter`: Automated conversion
- `MigrationValidator`: Validate changes
- Component stylers: Modern styling APIs
"""
        
        if output_path:
            output_path.write_text(report, encoding='utf-8')
            logger.info(f"Migration report saved to {output_path}")
        
        return report
    
    def _estimate_effort(self, complexity_counts: Dict[str, int]) -> float:
        """Estimate total migration effort in hours."""
        return (
            complexity_counts["simple"] * 5 +      # 5 minutes each
            complexity_counts["moderate"] * 15 +   # 15 minutes each
            complexity_counts["complex"] * 45      # 45 minutes each
        ) / 60  # Convert to hours


# Convenience functions for common migration tasks

def scan_for_legacy_patterns(directory: Path) -> Dict[str, List[LegacyPatternMatch]]:
    """Scan directory for legacy styling patterns."""
    detector = LegacyPatternDetector()
    return detector.scan_directory(directory)

def generate_migration_report(directory: Path, output_file: Optional[Path] = None) -> str:
    """Generate migration report for directory."""
    scan_results = scan_for_legacy_patterns(directory)
    reporter = MigrationReporter()
    return reporter.generate_report(scan_results, output_file)

def convert_file_safely(file_path: Path, dry_run: bool = True) -> Dict[str, Any]:
    """Safely convert a file from legacy to modern patterns."""
    converter = MigrationConverter()
    return converter.convert_file(file_path, dry_run=dry_run)