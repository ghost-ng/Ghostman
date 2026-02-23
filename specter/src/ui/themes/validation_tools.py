"""
Validation Tools for Preventing Legacy Styling Regression.

This module provides comprehensive validation tools to ensure the codebase
maintains modern styling practices and prevents regression to legacy patterns.

Key Features:
- Pre-commit hooks for style validation
- Continuous integration checks
- Real-time development warnings
- Automated code quality metrics
- Legacy pattern prevention guards
"""

import logging
import ast
import re
import sys
from typing import Dict, List, Tuple, Optional, Set, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import json

logger = logging.getLogger("specter.validation_tools")


class ValidationLevel(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Must be fixed, prevents commit/build
    WARNING = "warning"  # Should be fixed, but doesn't block
    INFO = "info"        # Informational, suggests improvement
    SUGGESTION = "suggestion"  # Optional improvement


@dataclass
class ValidationIssue:
    """Represents a validation issue found in code."""
    level: ValidationLevel
    rule_id: str
    message: str
    file_path: str
    line_number: int
    column: int = 0
    code_snippet: str = ""
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False


class StyleValidationRules:
    """
    Comprehensive validation rules for modern styling practices.
    
    These rules prevent common anti-patterns and enforce best practices.
    """
    
    def __init__(self):
        self.rules = {
            'no_inline_setstylesheet': {
                'description': 'Prevent inline setStyleSheet() calls',
                'pattern': r'\.setStyleSheet\s*\(\s*[\'"][^\'"]*[\'"]',
                'level': ValidationLevel.ERROR,
                'message': 'Use StyleRegistry.apply_style() instead of inline setStyleSheet()',
                'suggested_fix': 'registry.apply_style(widget, "template_name")'
            },
            'no_hardcoded_colors': {
                'description': 'Prevent hardcoded color values',
                'pattern': r'(?:rgba?\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+|#[0-9a-fA-F]{3,8})',
                'level': ValidationLevel.WARNING,
                'message': 'Use theme colors instead of hardcoded values',
                'suggested_fix': 'Use colors.primary, colors.background_primary, etc.'
            },
            'no_css_concatenation': {
                'description': 'Prevent CSS string concatenation',
                'pattern': r'[\'"][^\'"]*\{[^}]*\}[^\'"]*[\'"].*?\+',
                'level': ValidationLevel.WARNING,
                'message': 'Use StyleTemplates instead of CSS string concatenation',
                'suggested_fix': 'StyleTemplates.get_style("template_name", colors)'
            },
            'require_component_registration': {
                'description': 'Ensure widgets are registered before styling',
                'pattern': r'(?:StyleRegistry|ComponentStyler).*?(?!register_component)',
                'level': ValidationLevel.INFO,
                'message': 'Consider registering component for lifecycle management',
                'suggested_fix': 'registry.register_component(widget, "component_id", category)'
            },
            'prefer_component_stylers': {
                'description': 'Prefer component stylers over generic templates',
                'pattern': r'apply_style.*?"(?:button|input|text)',
                'level': ValidationLevel.SUGGESTION,
                'message': 'Consider using specialized component stylers',
                'suggested_fix': 'Use ButtonStyler, InputFieldStyler, etc.'
            },
            'no_manual_color_calculation': {
                'description': 'Prevent manual color calculations',
                'pattern': r'QColor.*?\.(?:lighter|darker)\s*\(',
                'level': ValidationLevel.WARNING,
                'message': 'Use ColorUtils for color manipulations',
                'suggested_fix': 'ColorUtils.lighten(color, factor) or ColorUtils.darken(color, factor)'
            },
            'require_accessibility_check': {
                'description': 'Ensure accessibility validation for custom colors',
                'pattern': r'ColorSystem\s*\([^)]*\)',
                'level': ValidationLevel.INFO,
                'message': 'Remember to validate color accessibility with .validate()',
                'suggested_fix': 'is_valid, issues = color_system.validate()'
            }
        }
    
    def validate_code(self, content: str, file_path: str) -> List[ValidationIssue]:
        """
        Validate code content against all rules.
        
        Args:
            content: Source code content
            file_path: Path to the file being validated
            
        Returns:
            List of validation issues
        """
        issues = []
        lines = content.split('\n')
        
        for rule_id, rule_config in self.rules.items():
            pattern = rule_config['pattern']
            level = rule_config['level']
            message = rule_config['message']
            suggested_fix = rule_config.get('suggested_fix')
            
            for match in re.finditer(pattern, content, re.MULTILINE):
                line_num = content[:match.start()].count('\n') + 1
                column = match.start() - content.rfind('\n', 0, match.start()) - 1
                
                code_snippet = ""
                if 1 <= line_num <= len(lines):
                    code_snippet = lines[line_num - 1].strip()
                
                issue = ValidationIssue(
                    level=level,
                    rule_id=rule_id,
                    message=message,
                    file_path=file_path,
                    line_number=line_num,
                    column=max(0, column),
                    code_snippet=code_snippet,
                    suggested_fix=suggested_fix,
                    auto_fixable=self._is_auto_fixable(rule_id)
                )
                
                issues.append(issue)
        
        return issues
    
    def _is_auto_fixable(self, rule_id: str) -> bool:
        """Check if a rule violation can be automatically fixed."""
        auto_fixable_rules = {
            'no_inline_setstylesheet',
            'no_hardcoded_colors',
        }
        return rule_id in auto_fixable_rules


class CodeQualityAnalyzer:
    """
    Analyzes code quality metrics related to styling practices.
    """
    
    def __init__(self):
        self.metrics = {
            'legacy_pattern_density': 0.0,
            'modern_pattern_adoption': 0.0,
            'accessibility_compliance': 0.0,
            'performance_score': 0.0,
            'maintainability_score': 0.0
        }
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a file for styling quality metrics.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Dictionary of quality metrics
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {'error': str(e)}
        
        lines = content.split('\n')
        total_lines = len([line for line in lines if line.strip()])
        
        if total_lines == 0:
            return self.metrics.copy()
        
        # Analyze patterns
        legacy_patterns = self._count_legacy_patterns(content)
        modern_patterns = self._count_modern_patterns(content)
        accessibility_features = self._count_accessibility_features(content)
        
        # Calculate metrics
        legacy_density = sum(legacy_patterns.values()) / total_lines
        modern_adoption = sum(modern_patterns.values()) / max(1, sum(legacy_patterns.values()) + sum(modern_patterns.values()))
        accessibility_score = min(1.0, accessibility_features / max(1, sum(modern_patterns.values())))
        
        # Performance score (based on modern pattern usage)
        performance_indicators = modern_patterns.get('style_registry', 0) + modern_patterns.get('component_stylers', 0)
        performance_score = min(1.0, performance_indicators / max(1, total_lines / 50))
        
        # Maintainability score (inverse of complexity)
        complexity_indicators = (
            legacy_patterns.get('css_concatenation', 0) +
            legacy_patterns.get('manual_calculations', 0) +
            legacy_patterns.get('hardcoded_colors', 0)
        )
        maintainability_score = max(0.0, 1.0 - (complexity_indicators / total_lines))
        
        return {
            'legacy_pattern_density': legacy_density,
            'modern_pattern_adoption': modern_adoption,
            'accessibility_compliance': accessibility_score,
            'performance_score': performance_score,
            'maintainability_score': maintainability_score,
            'total_lines': total_lines,
            'legacy_patterns': legacy_patterns,
            'modern_patterns': modern_patterns,
            'accessibility_features': accessibility_features
        }
    
    def _count_legacy_patterns(self, content: str) -> Dict[str, int]:
        """Count legacy styling patterns in content."""
        patterns = {
            'inline_setstylesheet': len(re.findall(r'\.setStyleSheet\s*\(\s*[\'"][^\'"]*[\'"]', content)),
            'hardcoded_colors': len(re.findall(r'(?:rgba?\s*\(\s*\d+|#[0-9a-fA-F]{3,8})', content)),
            'css_concatenation': len(re.findall(r'[\'"][^\'"]*\{[^}]*\}[^\'"]*[\'"].*?\+', content)),
            'manual_calculations': len(re.findall(r'QColor.*?\.(?:lighter|darker)\s*\(', content))
        }
        return patterns
    
    def _count_modern_patterns(self, content: str) -> Dict[str, int]:
        """Count modern styling patterns in content."""
        patterns = {
            'style_registry': len(re.findall(r'(?:StyleRegistry|get_style_registry)', content)),
            'component_stylers': len(re.findall(r'(?:ButtonStyler|InputFieldStyler|REPLComponentStyler)', content)),
            'style_templates': len(re.findall(r'StyleTemplates\.get_style', content)),
            'color_utils': len(re.findall(r'ColorUtils\.(?:lighten|darken|blend)', content)),
            'theme_colors': len(re.findall(r'colors\.(?:primary|background|text)', content))
        }
        return patterns
    
    def _count_accessibility_features(self, content: str) -> int:
        """Count accessibility-related features in content."""
        features = 0
        
        # Check for contrast validation
        features += len(re.findall(r'validate_contrast|contrast_ratio', content))
        
        # Check for accessibility validation
        features += len(re.findall(r'\.validate\(\)|accessibility', content))
        
        # Check for semantic color usage
        features += len(re.findall(r'colors\.(?:status_|border_|text_)', content))
        
        return features


class DevelopmentGuards:
    """
    Real-time guards that warn developers about legacy pattern usage.
    """
    
    def __init__(self):
        self.enabled = True
        self.warning_threshold = ValidationLevel.WARNING
        self.suppress_rules: Set[str] = set()
    
    def check_setstylesheet_call(self, widget_name: str, style_content: str, 
                                 file_path: str, line_number: int) -> Optional[str]:
        """
        Guard against setStyleSheet() calls - can be used as a hook.
        
        Args:
            widget_name: Name of widget being styled
            style_content: CSS content being applied
            file_path: Source file path
            line_number: Line number
            
        Returns:
            Warning message if guard is triggered, None otherwise
        """
        if not self.enabled or 'no_inline_setstylesheet' in self.suppress_rules:
            return None
        
        # Check if this looks like an inline style
        if len(style_content) > 20 and ('{' in style_content or ';' in style_content):
            warning = (
                f"Legacy styling detected at {file_path}:{line_number}\n"
                f"Consider using StyleRegistry.apply_style({widget_name}, 'template_name') "
                f"instead of setStyleSheet()"
            )
            
            if self.warning_threshold in [ValidationLevel.WARNING, ValidationLevel.ERROR]:
                logger.warning(warning)
                return warning
        
        return None
    
    def check_color_usage(self, color_value: str, context: str, 
                         file_path: str, line_number: int) -> Optional[str]:
        """
        Guard against hardcoded color values.
        
        Args:
            color_value: Color value being used
            context: Context where color is used
            file_path: Source file path
            line_number: Line number
            
        Returns:
            Warning message if guard is triggered, None otherwise
        """
        if not self.enabled or 'no_hardcoded_colors' in self.suppress_rules:
            return None
        
        # Check for hardcoded color patterns
        if re.match(r'(?:rgba?\s*\(\s*\d+|#[0-9a-fA-F]{3,8})', color_value):
            warning = (
                f"Hardcoded color detected at {file_path}:{line_number}\n"
                f"Consider using theme colors: colors.primary, colors.background_primary, etc."
            )
            
            if self.warning_threshold in [ValidationLevel.WARNING, ValidationLevel.ERROR]:
                logger.warning(warning)
                return warning
        
        return None
    
    def suppress_rule(self, rule_id: str):
        """Temporarily suppress a validation rule."""
        self.suppress_rules.add(rule_id)
        logger.debug(f"Suppressed validation rule: {rule_id}")
    
    def enable_rule(self, rule_id: str):
        """Re-enable a previously suppressed validation rule."""
        self.suppress_rules.discard(rule_id)
        logger.debug(f"Re-enabled validation rule: {rule_id}")


class PreCommitHook:
    """
    Pre-commit hook for validating styling practices.
    """
    
    def __init__(self):
        self.validator = StyleValidationRules()
        self.analyzer = CodeQualityAnalyzer()
        self.fail_on_errors = True
        self.fail_on_warnings = False
    
    def validate_changes(self, changed_files: Optional[List[str]] = None) -> bool:
        """
        Validate changed files before commit.
        
        Args:
            changed_files: List of changed file paths (auto-detect if None)
            
        Returns:
            True if validation passes, False if commit should be blocked
        """
        if changed_files is None:
            changed_files = self._get_changed_files()
        
        # Filter for Python files
        python_files = [f for f in changed_files if f.endswith('.py')]
        
        if not python_files:
            return True
        
        total_errors = 0
        total_warnings = 0
        
        print("🎨 Validating styling practices...")
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Validate with rules
                issues = self.validator.validate_code(content, file_path)
                
                if issues:
                    print(f"\n📄 {file_path}:")
                    
                    for issue in issues:
                        icon = self._get_issue_icon(issue.level)
                        print(f"  {icon} Line {issue.line_number}: {issue.message}")
                        
                        if issue.code_snippet:
                            print(f"    Code: {issue.code_snippet}")
                        
                        if issue.suggested_fix:
                            print(f"    Fix:  {issue.suggested_fix}")
                        
                        if issue.level == ValidationLevel.ERROR:
                            total_errors += 1
                        elif issue.level == ValidationLevel.WARNING:
                            total_warnings += 1
                
                # Analyze quality metrics
                metrics = self.analyzer.analyze_file(Path(file_path))
                if 'error' not in metrics:
                    if metrics['legacy_pattern_density'] > 0.1:  # More than 10% legacy patterns
                        print(f"  ⚠️  High legacy pattern density: {metrics['legacy_pattern_density']:.1%}")
                        total_warnings += 1
            
            except Exception as e:
                print(f"  ❌ Error validating {file_path}: {e}")
                total_errors += 1
        
        # Summary
        if total_errors > 0 or total_warnings > 0:
            print(f"\n📊 Summary: {total_errors} errors, {total_warnings} warnings")
        
        # Determine if commit should be blocked
        should_block = (
            (self.fail_on_errors and total_errors > 0) or
            (self.fail_on_warnings and total_warnings > 0)
        )
        
        if should_block:
            print("❌ Commit blocked due to styling validation issues")
            print("💡 Run the migration tools or fix issues manually")
            return False
        else:
            print("✅ Styling validation passed")
            return True
    
    def _get_changed_files(self) -> List[str]:
        """Get list of changed files from git."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            logger.warning("Failed to get changed files from git")
            return []
    
    def _get_issue_icon(self, level: ValidationLevel) -> str:
        """Get emoji icon for validation level."""
        icons = {
            ValidationLevel.ERROR: "❌",
            ValidationLevel.WARNING: "⚠️",
            ValidationLevel.INFO: "ℹ️",
            ValidationLevel.SUGGESTION: "💡"
        }
        return icons.get(level, "❓")


class ContinuousIntegrationValidator:
    """
    Validation tools for CI/CD pipelines.
    """
    
    def __init__(self):
        self.validator = StyleValidationRules()
        self.analyzer = CodeQualityAnalyzer()
    
    def validate_project(self, project_root: Path) -> Dict[str, Any]:
        """
        Validate entire project for styling practices.
        
        Args:
            project_root: Root directory of project
            
        Returns:
            Comprehensive validation report
        """
        report = {
            'summary': {
                'total_files': 0,
                'files_with_issues': 0,
                'total_errors': 0,
                'total_warnings': 0,
                'overall_quality_score': 0.0
            },
            'files': {},
            'quality_metrics': {},
            'recommendations': []
        }
        
        python_files = list(project_root.rglob('*.py'))
        report['summary']['total_files'] = len(python_files)
        
        quality_scores = []
        
        for file_path in python_files:
            file_report = self._validate_single_file(file_path)
            
            if file_report['issues'] or file_report['quality_metrics']['legacy_pattern_density'] > 0:
                report['files'][str(file_path)] = file_report
                report['summary']['files_with_issues'] += 1
            
            # Count errors and warnings
            for issue in file_report['issues']:
                if issue.level == ValidationLevel.ERROR:
                    report['summary']['total_errors'] += 1
                elif issue.level == ValidationLevel.WARNING:
                    report['summary']['total_warnings'] += 1
            
            # Aggregate quality metrics
            quality_scores.append(file_report['quality_metrics']['maintainability_score'])
        
        # Calculate overall quality score
        if quality_scores:
            report['summary']['overall_quality_score'] = sum(quality_scores) / len(quality_scores)
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _validate_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single file and return detailed report."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                'error': str(e),
                'issues': [],
                'quality_metrics': {}
            }
        
        issues = self.validator.validate_code(content, str(file_path))
        quality_metrics = self.analyzer.analyze_file(file_path)
        
        return {
            'issues': issues,
            'quality_metrics': quality_metrics
        }
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        summary = report['summary']
        
        if summary['total_errors'] > 0:
            recommendations.append(
                f"Fix {summary['total_errors']} critical styling errors to improve code quality"
            )
        
        if summary['total_warnings'] > 10:
            recommendations.append(
                f"Address {summary['total_warnings']} styling warnings for better maintainability"
            )
        
        if summary['overall_quality_score'] < 0.7:
            recommendations.append(
                "Consider running automated migration to modernize styling patterns"
            )
        
        high_density_files = []
        for file_path, file_report in report['files'].items():
            if 'quality_metrics' in file_report:
                density = file_report['quality_metrics'].get('legacy_pattern_density', 0)
                if density > 0.2:  # More than 20% legacy patterns
                    high_density_files.append(file_path)
        
        if high_density_files:
            recommendations.append(
                f"Prioritize migration for {len(high_density_files)} files with high legacy pattern density"
            )
        
        return recommendations


# Global instances
_development_guards = None
_pre_commit_hook = None

def get_development_guards() -> DevelopmentGuards:
    """Get global development guards instance."""
    global _development_guards
    if _development_guards is None:
        _development_guards = DevelopmentGuards()
    return _development_guards

def get_pre_commit_hook() -> PreCommitHook:
    """Get global pre-commit hook instance."""
    global _pre_commit_hook
    if _pre_commit_hook is None:
        _pre_commit_hook = PreCommitHook()
    return _pre_commit_hook


# CLI interface for validation tools
def main():
    """CLI interface for running validation tools."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Specter Styling Validation Tools')
    parser.add_argument('--pre-commit', action='store_true', help='Run pre-commit validation')
    parser.add_argument('--validate-project', type=str, help='Validate entire project at path')
    parser.add_argument('--file', type=str, help='Validate specific file')
    parser.add_argument('--output', type=str, help='Output file for report')
    
    args = parser.parse_args()
    
    if args.pre_commit:
        hook = get_pre_commit_hook()
        success = hook.validate_changes()
        sys.exit(0 if success else 1)
    
    elif args.validate_project:
        validator = ContinuousIntegrationValidator()
        report = validator.validate_project(Path(args.validate_project))
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report saved to {args.output}")
        else:
            print(json.dumps(report, indent=2, default=str))
        
        # Exit with error code if there are errors
        sys.exit(1 if report['summary']['total_errors'] > 0 else 0)
    
    elif args.file:
        validator = StyleValidationRules()
        
        with open(args.file, 'r') as f:
            content = f.read()
        
        issues = validator.validate_code(content, args.file)
        
        for issue in issues:
            print(f"{issue.level.value.upper()}: Line {issue.line_number}: {issue.message}")
            if issue.suggested_fix:
                print(f"  Suggested fix: {issue.suggested_fix}")
        
        sys.exit(1 if any(i.level == ValidationLevel.ERROR for i in issues) else 0)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()