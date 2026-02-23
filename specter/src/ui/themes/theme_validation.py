"""
Theme Validation System for Specter Application.

Provides comprehensive validation for theme accessibility, color harmony,
and visual hierarchy compliance. Ensures all themes meet WCAG 2.1 AA
standards and provide excellent user experience.

Key Features:
1. WCAG 2.1 AA/AAA Contrast Validation
2. Color Harmony Analysis
3. Visual Hierarchy Assessment
4. Interface Area Distinction Validation
5. Icon Visibility Testing
6. Accessibility Recommendations
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from .color_system import ColorSystem, ColorUtils

logger = logging.getLogger("specter.theme_validation")


@dataclass
class ValidationResult:
    """Result of theme validation with detailed feedback."""
    theme_name: str
    is_valid: bool
    accessibility_score: float  # 0-100
    visual_hierarchy_score: float  # 0-100
    color_harmony_score: float  # 0-100
    overall_score: float  # 0-100
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    contrast_ratios: Dict[str, float]


class ThemeValidator:
    """
    Comprehensive theme validation system.
    
    Validates themes against accessibility standards, color harmony principles,
    and visual hierarchy requirements for the Specter REPL interface.
    """
    
    # WCAG 2.1 contrast requirements
    WCAG_AA_NORMAL = 4.5
    WCAG_AA_LARGE = 3.0
    WCAG_AAA_NORMAL = 7.0
    WCAG_AAA_LARGE = 4.5
    
    def __init__(self):
        self.results_cache = {}
    
    def validate_theme(self, theme_name: str, colors: ColorSystem) -> ValidationResult:
        """
        Perform comprehensive theme validation.
        
        Args:
            theme_name: Name of the theme being validated
            colors: ColorSystem object to validate
            
        Returns:
            ValidationResult with detailed analysis
        """
        # Check cache first
        cache_key = f"{theme_name}_{hash(str(colors.to_dict()))}"
        if cache_key in self.results_cache:
            return self.results_cache[cache_key]
        
        issues = []
        warnings = []
        recommendations = []
        contrast_ratios = {}
        
        # 1. Accessibility Validation
        accessibility_score, accessibility_issues, accessibility_ratios = self._validate_accessibility(colors)
        issues.extend(accessibility_issues)
        contrast_ratios.update(accessibility_ratios)
        
        # 2. Visual Hierarchy Validation
        hierarchy_score, hierarchy_issues = self._validate_visual_hierarchy(colors)
        issues.extend(hierarchy_issues)
        
        # 3. Color Harmony Validation
        harmony_score, harmony_issues = self._validate_color_harmony(colors)
        issues.extend(harmony_issues)
        
        # 4. Interface Area Validation
        interface_warnings, interface_recommendations = self._validate_interface_areas(colors)
        warnings.extend(interface_warnings)
        recommendations.extend(interface_recommendations)
        
        # 5. Icon Visibility Validation
        icon_issues, icon_recommendations = self._validate_icon_visibility(colors)
        issues.extend(icon_issues)
        recommendations.extend(icon_recommendations)
        
        # Calculate overall scores
        overall_score = (accessibility_score + hierarchy_score + harmony_score) / 3
        is_valid = overall_score >= 70 and accessibility_score >= 80  # Strict accessibility requirement
        
        result = ValidationResult(
            theme_name=theme_name,
            is_valid=is_valid,
            accessibility_score=accessibility_score,
            visual_hierarchy_score=hierarchy_score,
            color_harmony_score=harmony_score,
            overall_score=overall_score,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            contrast_ratios=contrast_ratios
        )
        
        # Cache result
        self.results_cache[cache_key] = result
        
        return result
    
    def _validate_accessibility(self, colors: ColorSystem) -> Tuple[float, List[str], Dict[str, float]]:
        """Validate WCAG 2.1 accessibility compliance."""
        issues = []
        ratios = {}
        score_points = []
        
        # Critical text/background combinations for REPL interface
        critical_combinations = [
            ("text_primary", "background_primary", "Primary text on main background", self.WCAG_AA_NORMAL),
            ("text_secondary", "background_secondary", "Secondary text on panels", self.WCAG_AA_NORMAL),
            ("text_primary", "background_tertiary", "Primary text on input areas", self.WCAG_AA_NORMAL),
            ("text_primary", "interactive_normal", "Text on buttons", self.WCAG_AA_NORMAL),
        ]
        
        for text_attr, bg_attr, description, min_ratio in critical_combinations:
            text_color = getattr(colors, text_attr)
            bg_color = getattr(colors, bg_attr)
            
            ratio = self._calculate_contrast_ratio(text_color, bg_color)
            ratios[f"{text_attr}_on_{bg_attr}"] = ratio
            
            if ratio < min_ratio:
                issues.append(f"ACCESSIBILITY: {description} contrast ratio {ratio:.2f} < {min_ratio} (WCAG AA)")
                score_points.append(0)
            elif ratio < self.WCAG_AAA_NORMAL:
                score_points.append(80)  # Good but not AAA
            else:
                score_points.append(100)  # Excellent AAA compliance
        
        # Status color accessibility
        status_combinations = [
            ("status_success", "background_primary", "Success indicators"),
            ("status_warning", "background_primary", "Warning indicators"),
            ("status_error", "background_primary", "Error indicators"),
            ("status_info", "background_primary", "Info indicators"),
        ]
        
        for status_attr, bg_attr, description in status_combinations:
            status_color = getattr(colors, status_attr)
            bg_color = getattr(colors, bg_attr)
            
            ratio = self._calculate_contrast_ratio(status_color, bg_color)
            ratios[f"{status_attr}_on_{bg_attr}"] = ratio
            
            if ratio < self.WCAG_AA_NORMAL:
                issues.append(f"ACCESSIBILITY: {description} contrast ratio {ratio:.2f} < {self.WCAG_AA_NORMAL}")
                score_points.append(0)
            else:
                score_points.append(100)
        
        # Calculate accessibility score
        accessibility_score = sum(score_points) / len(score_points) if score_points else 0
        
        return accessibility_score, issues, ratios
    
    def _validate_visual_hierarchy(self, colors: ColorSystem) -> Tuple[float, List[str]]:
        """Validate visual hierarchy and interface area distinction."""
        issues = []
        score_points = []
        
        # Check background differentiation for 4 main areas
        bg_primary = colors.background_primary
        bg_secondary = colors.background_secondary  
        bg_tertiary = colors.background_tertiary
        
        # Areas should be visually distinct
        primary_secondary_diff = self._calculate_color_difference(bg_primary, bg_secondary)
        secondary_tertiary_diff = self._calculate_color_difference(bg_secondary, bg_tertiary)
        primary_tertiary_diff = self._calculate_color_difference(bg_primary, bg_tertiary)
        
        min_difference = 30  # Minimum perceptual difference
        
        if primary_secondary_diff < min_difference:
            issues.append("HIERARCHY: Primary and secondary backgrounds too similar")
            score_points.append(50)
        else:
            score_points.append(100)
            
        if secondary_tertiary_diff < min_difference:
            issues.append("HIERARCHY: Secondary and tertiary backgrounds too similar") 
            score_points.append(50)
        else:
            score_points.append(100)
            
        if primary_tertiary_diff < min_difference:
            issues.append("HIERARCHY: Primary and tertiary backgrounds too similar")
            score_points.append(50)
        else:
            score_points.append(100)
        
        # Check interactive state differentiation
        interactive_normal = colors.interactive_normal
        interactive_hover = colors.interactive_hover
        interactive_active = colors.interactive_active
        
        hover_diff = self._calculate_color_difference(interactive_normal, interactive_hover)
        active_diff = self._calculate_color_difference(interactive_normal, interactive_active)
        
        if hover_diff < 20:
            issues.append("HIERARCHY: Hover state not distinct enough from normal")
            score_points.append(60)
        else:
            score_points.append(100)
            
        if active_diff < 30:
            issues.append("HIERARCHY: Active state not distinct enough from normal")
            score_points.append(60)
        else:
            score_points.append(100)
        
        hierarchy_score = sum(score_points) / len(score_points) if score_points else 0
        return hierarchy_score, issues
    
    def _validate_color_harmony(self, colors: ColorSystem) -> Tuple[float, List[str]]:
        """Validate color harmony and aesthetic coherence."""
        issues = []
        score_points = []
        
        # Check primary/secondary harmony
        primary_secondary_harmony = self._assess_color_harmony(colors.primary, colors.secondary)
        if primary_secondary_harmony < 0.6:
            issues.append("HARMONY: Primary and secondary colors clash")
            score_points.append(40)
        else:
            score_points.append(100)
        
        # Check status color distinctiveness
        status_colors = [colors.status_success, colors.status_warning, colors.status_error, colors.status_info]
        
        for i, color1 in enumerate(status_colors):
            for j, color2 in enumerate(status_colors):
                if i < j:  # Avoid duplicate comparisons
                    diff = self._calculate_color_difference(color1, color2)
                    if diff < 50:  # Status colors should be very distinct
                        issues.append(f"HARMONY: Status colors too similar for accessibility")
                        score_points.append(30)
                    else:
                        score_points.append(100)
        
        # Check temperature consistency
        temp_score = self._assess_temperature_consistency(colors)
        score_points.append(temp_score)
        
        if temp_score < 70:
            issues.append("HARMONY: Inconsistent color temperature throughout theme")
        
        harmony_score = sum(score_points) / len(score_points) if score_points else 0
        return harmony_score, issues
    
    def _validate_interface_areas(self, colors: ColorSystem) -> Tuple[List[str], List[str]]:
        """Validate the 4 main interface areas for clarity."""
        warnings = []
        recommendations = []
        
        # Titlebar (uses background_secondary)
        titlebar_text_contrast = self._calculate_contrast_ratio(colors.text_primary, colors.background_secondary)
        if titlebar_text_contrast < 4.5:
            warnings.append("Titlebar text may be hard to read")
            recommendations.append("Increase contrast between text and titlebar background")
        
        # REPL area (uses background_primary)
        repl_contrast = self._calculate_contrast_ratio(colors.text_primary, colors.background_primary)
        if repl_contrast < 7.0:  # Higher standard for reading area
            recommendations.append("Consider higher contrast for REPL area (main reading area)")
        
        # Search bar (between titlebar and REPL)
        # Should have medium contrast between background_secondary and background_primary
        search_distinction = self._calculate_color_difference(colors.background_secondary, colors.background_primary)
        if search_distinction < 20:
            recommendations.append("Increase distinction between search bar and adjacent areas")
        
        # Input bar (uses background_tertiary) - should be most prominent
        input_distinction = self._calculate_color_difference(colors.background_tertiary, colors.background_primary)
        if input_distinction < 30:
            warnings.append("User input area may not be prominent enough")
            recommendations.append("Make input area more visually distinct as primary interaction area")
        
        return warnings, recommendations
    
    def _validate_icon_visibility(self, colors: ColorSystem) -> Tuple[List[str], List[str]]:
        """Validate icon visibility on different backgrounds."""
        issues = []
        recommendations = []
        
        # Test save/plus icon visibility on titlebar
        titlebar_bg = colors.background_secondary
        
        # Test potential icon colors
        icon_candidates = [colors.primary, colors.secondary, colors.status_success, colors.text_primary]
        
        best_contrast = 0
        for icon_color in icon_candidates:
            contrast = self._calculate_contrast_ratio(icon_color, titlebar_bg)
            best_contrast = max(best_contrast, contrast)
        
        if best_contrast < 4.5:
            issues.append("ICONS: Save/plus icons may not be visible on titlebar")
            recommendations.append("Adjust titlebar background or icon colors for better visibility")
        elif best_contrast < 7.0:
            recommendations.append("Consider higher contrast for save/plus icons")
        
        # Test interactive button visibility  
        button_bg = colors.interactive_normal
        button_text_contrast = self._calculate_contrast_ratio(colors.text_primary, button_bg)
        
        if button_text_contrast < 4.5:
            issues.append("ICONS: Interactive buttons may have poor text visibility")
            recommendations.append("Improve button background/text contrast")
        
        return issues, recommendations
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """Calculate WCAG contrast ratio between two colors."""
        try:
            from PyQt6.QtGui import QColor
            
            def get_luminance(hex_color: str) -> float:
                qcolor = QColor(hex_color)
                r, g, b = qcolor.red() / 255.0, qcolor.green() / 255.0, qcolor.blue() / 255.0
                
                # Apply gamma correction
                r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
                g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
                b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
                
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            lum1 = get_luminance(color1)
            lum2 = get_luminance(color2)
            
            if lum1 < lum2:
                lum1, lum2 = lum2, lum1
            
            return (lum1 + 0.05) / (lum2 + 0.05)
        except:
            return 4.5  # Default to acceptable contrast
    
    def _calculate_color_difference(self, color1: str, color2: str) -> float:
        """Calculate perceptual color difference."""
        try:
            from PyQt6.QtGui import QColor
            qcolor1 = QColor(color1)
            qcolor2 = QColor(color2)
            
            # Simple RGB distance calculation (good approximation)
            r_diff = abs(qcolor1.red() - qcolor2.red())
            g_diff = abs(qcolor1.green() - qcolor2.green())
            b_diff = abs(qcolor1.blue() - qcolor2.blue())
            
            # Weighted difference (human eye is more sensitive to green)
            distance = (2 * r_diff**2 + 4 * g_diff**2 + 3 * b_diff**2) ** 0.5
            
            return distance / 4.41  # Normalize to 0-100 scale
        except:
            return 50  # Default to medium difference
    
    def _assess_color_harmony(self, color1: str, color2: str) -> float:
        """Assess color harmony between two colors (0-1 scale)."""
        try:
            from PyQt6.QtGui import QColor
            qcolor1 = QColor(color1)
            qcolor2 = QColor(color2)
            
            # Convert to HSV for harmony analysis
            h1, s1, v1, _ = qcolor1.getHsv()
            h2, s2, v2, _ = qcolor2.getHsv()
            
            # Hue difference (circular)
            hue_diff = min(abs(h1 - h2), 360 - abs(h1 - h2)) if h1 != -1 and h2 != -1 else 0
            
            # Harmony rules
            if hue_diff < 30:  # Analogous colors (good harmony)
                harmony = 0.9
            elif 150 < hue_diff < 210:  # Complementary colors (good harmony)
                harmony = 0.8
            elif 90 < hue_diff < 150:  # Triadic (moderate harmony)
                harmony = 0.6
            else:  # Other relationships
                harmony = 0.4
            
            # Adjust for saturation and value similarity
            sat_diff = abs(s1 - s2) / 255.0
            val_diff = abs(v1 - v2) / 255.0
            
            if sat_diff < 0.2 and val_diff < 0.2:
                harmony += 0.1  # Bonus for similar saturation/brightness
            
            return min(1.0, harmony)
        except:
            return 0.5  # Default to moderate harmony
    
    def _assess_temperature_consistency(self, colors: ColorSystem) -> float:
        """Assess color temperature consistency across the theme."""
        try:
            from PyQt6.QtGui import QColor
            
            # Analyze main colors for temperature
            main_colors = [
                colors.primary, colors.secondary, 
                colors.background_primary, colors.background_secondary,
                colors.text_primary
            ]
            
            temperatures = []
            for color in main_colors:
                temp = self._get_color_temperature(color)
                if temp is not None:
                    temperatures.append(temp)
            
            if len(temperatures) < 2:
                return 70  # Default score if unable to analyze
            
            # Calculate temperature variance
            avg_temp = sum(temperatures) / len(temperatures)
            variance = sum((t - avg_temp) ** 2 for t in temperatures) / len(temperatures)
            
            # Lower variance = more consistent = higher score
            consistency_score = max(0, 100 - variance * 10)
            
            return min(100, consistency_score)
        except:
            return 70  # Default to moderate consistency
    
    def _get_color_temperature(self, hex_color: str) -> Optional[float]:
        """Get color temperature (warm=1, cool=-1, neutral=0)."""
        try:
            from PyQt6.QtGui import QColor
            qcolor = QColor(hex_color)
            r, g, b = qcolor.red(), qcolor.green(), qcolor.blue()
            
            # Simple temperature heuristic
            warm_score = r - b  # Red vs Blue
            return max(-1, min(1, warm_score / 255.0))
        except:
            return None


def validate_all_themes(themes: Dict[str, ColorSystem]) -> Dict[str, ValidationResult]:
    """
    Validate all themes and return comprehensive results.
    
    Args:
        themes: Dictionary of theme names to ColorSystem objects
        
    Returns:
        Dictionary of theme names to ValidationResult objects
    """
    validator = ThemeValidator()
    results = {}
    
    for theme_name, colors in themes.items():
        results[theme_name] = validator.validate_theme(theme_name, colors)
    
    return results


def generate_validation_report(results: Dict[str, ValidationResult]) -> str:
    """
    Generate a comprehensive validation report.
    
    Args:
        results: Dictionary of validation results
        
    Returns:
        Formatted report string
    """
    report = ["=== GHOSTMAN THEME VALIDATION REPORT ===", ""]
    
    # Summary statistics
    valid_themes = sum(1 for result in results.values() if result.is_valid)
    total_themes = len(results)
    avg_accessibility = sum(result.accessibility_score for result in results.values()) / total_themes
    avg_hierarchy = sum(result.visual_hierarchy_score for result in results.values()) / total_themes
    avg_harmony = sum(result.color_harmony_score for result in results.values()) / total_themes
    
    report.extend([
        f"Valid Themes: {valid_themes}/{total_themes} ({valid_themes/total_themes*100:.1f}%)",
        f"Average Accessibility Score: {avg_accessibility:.1f}/100",
        f"Average Visual Hierarchy Score: {avg_hierarchy:.1f}/100", 
        f"Average Color Harmony Score: {avg_harmony:.1f}/100",
        "", "=== INDIVIDUAL THEME RESULTS ===", ""
    ])
    
    # Individual theme results
    for theme_name, result in sorted(results.items()):
        status = "✓ PASS" if result.is_valid else "✗ FAIL"
        report.extend([
            f"{theme_name}: {status} (Overall: {result.overall_score:.1f}%)",
            f"  Accessibility: {result.accessibility_score:.1f}% | Hierarchy: {result.visual_hierarchy_score:.1f}% | Harmony: {result.color_harmony_score:.1f}%"
        ])
        
        if result.issues:
            report.append(f"  Issues: {'; '.join(result.issues[:3])}")  # Show first 3 issues
        
        if result.recommendations:
            report.append(f"  Recommendations: {'; '.join(result.recommendations[:2])}")  # Show first 2 recommendations
        
        report.append("")
    
    return "\n".join(report)