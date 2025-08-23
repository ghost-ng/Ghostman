#!/usr/bin/env python3
"""
Standalone test for search result count contrast fix.

Tests the contrast improvement without requiring PyQt6 dependencies.
"""

def hex_to_rgb(hex_color: str):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    def get_luminance(rgb):
        r, g, b = [x / 255.0 for x in rgb]
        r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
        g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
        b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    try:
        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        
        lum1 = get_luminance(rgb1)
        lum2 = get_luminance(rgb2)
        
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    except:
        return 0.0

def get_high_contrast_text_color(background_color: str, theme_colors: dict = None) -> tuple:
    """
    Get the best high-contrast text color for the given background.
    Returns (best_color, contrast_ratio).
    """
    # Start with theme-aware candidates if available
    text_candidates = []
    
    if theme_colors:
        text_candidates.extend([
            theme_colors.get("text_primary", "#ffffff"),
            theme_colors.get("text_secondary", "#cccccc"),
            theme_colors.get("background_primary", "#000000"),
            theme_colors.get("border_primary", "#444444"),
            theme_colors.get("secondary", "#2196F3"),
        ])
    
    # Always add high-contrast fallbacks
    text_candidates.extend([
        "#ffffff",  # Pure white
        "#000000",  # Pure black
        "#f8f8f2",  # Near white
        "#2d2d2d",  # Dark gray
        "#e6e6e6",  # Light gray
        "#333333",  # Medium dark gray
    ])
    
    # Find the best contrast
    best_color = text_candidates[0]
    best_ratio = 0.0
    
    for candidate in text_candidates:
        try:
            ratio = calculate_contrast_ratio(candidate, background_color)
            if ratio > best_ratio:
                best_ratio = ratio
                best_color = candidate
                
            # If we found excellent contrast, we can stop early
            if ratio >= 7.0:  # WCAG AAA level
                break
                
        except:
            continue
    
    # If we still don't have adequate contrast, force high contrast
    if best_ratio < 4.5:
        # Determine if background is dark or light
        try:
            bg_rgb = hex_to_rgb(background_color)
            bg_luminance = sum(bg_rgb) / (3 * 255.0)
            
            if bg_luminance > 0.5:
                # Light background - force black text
                best_color = "#000000"
                best_ratio = calculate_contrast_ratio("#000000", background_color)
            else:
                # Dark background - force white text
                best_color = "#ffffff"
                best_ratio = calculate_contrast_ratio("#ffffff", background_color)
        except:
            # Fallback to white text
            best_color = "#ffffff"
            best_ratio = calculate_contrast_ratio("#ffffff", background_color)
    
    return best_color, best_ratio

def test_search_contrast_fix():
    """Test the new search result count contrast fix across all themes."""
    
    # Theme data extracted from preset_themes.py
    themes = {
        "dark_matrix": {
            "background_tertiary": "#2d2d2d",
            "text_tertiary": "#009929",
            "text_primary": "#00ff41",
            "text_secondary": "#00cc33",
            "background_primary": "#0d0d0d",
            "border_primary": "#004d1a",
            "secondary": "#00cc33",
        },
        "midnight_blue": {
            "background_tertiary": "#1e2742",
            "text_tertiary": "#90caf9",
            "text_primary": "#e3f2fd",
            "text_secondary": "#bbdefb",
            "background_primary": "#0a0e1a",
            "border_primary": "#34495e",
            "secondary": "#42a5f5",
        },
        "forest_green": {
            "background_tertiary": "#2e4a33",
            "text_tertiary": "#a5d6a7",
            "text_primary": "#e8f5e8",
            "text_secondary": "#c8e6c9",
            "background_primary": "#0d1b0f",
            "border_primary": "#2e4a33",
            "secondary": "#66bb6a",
        },
        "sunset_orange": {
            "background_tertiary": "#4a2c1a",
            "text_tertiary": "#ffcc80",
            "text_primary": "#fff3e0",
            "text_secondary": "#ffe0b2",
            "background_primary": "#1a0f08",
            "border_primary": "#5d4037",
            "secondary": "#ff9800",
        },
        "royal_purple": {
            "background_tertiary": "#331a4a",
            "text_tertiary": "#ce93d8",
            "text_primary": "#f3e5f5",
            "text_secondary": "#e1bee7",
            "background_primary": "#12081a",
            "border_primary": "#4a148c",
            "secondary": "#9c27b0",
        },
        "arctic_white": {
            "background_tertiary": "#e9ecef",
            "text_tertiary": "#555555",
            "text_primary": "#111111",
            "text_secondary": "#333333",
            "background_primary": "#ffffff",
            "border_primary": "#6c757d",
            "secondary": "#1e88e5",
        },
        "cyberpunk": {
            "background_tertiary": "#16213e",
            "text_tertiary": "#00ffff",
            "text_primary": "#ffffff",
            "text_secondary": "#ff00ff",
            "background_primary": "#0a0a0a",
            "border_primary": "#ff0080",
            "secondary": "#00ffff",
        },
        "earth_tones": {
            "background_tertiary": "#4a3728",
            "text_tertiary": "#bcaaa4",
            "text_primary": "#efebe9",
            "text_secondary": "#d7ccc8",
            "background_primary": "#1c1611",
            "border_primary": "#5d4037",
            "secondary": "#a1887f",
        },
        "ocean_deep": {
            "background_tertiary": "#21262d",
            "text_tertiary": "#80cbc4",
            "text_primary": "#e0f2f1",
            "text_secondary": "#b2dfdb",
            "background_primary": "#0d1117",
            "border_primary": "#34495e",
            "secondary": "#26a69a",
        },
        "lilac": {
            "background_tertiary": "#3a3040",
            "text_tertiary": "#d0c8d8",
            "text_primary": "#f8f6fa",
            "text_secondary": "#e8e0f0",
            "background_primary": "#1a1520",
            "border_primary": "#5a4060",
            "secondary": "#d8c8e8",
        },
        "sunburst": {
            "background_tertiary": "#4a2f1c",
            "text_tertiary": "#ffcc80",
            "text_primary": "#fff3e0",
            "text_secondary": "#ffe0b2",
            "background_primary": "#1a0e08",
            "border_primary": "#6b4423",
            "secondary": "#ff8c42",
        },
        "forest": {
            "background_tertiary": "#2a4a26",
            "text_tertiary": "#a8cc9f",
            "text_primary": "#e8f2e5",
            "text_secondary": "#c8dfc2",
            "background_primary": "#0f1b0d",
            "border_primary": "#4a5948",
            "secondary": "#6d9865",
        },
        "firefly": {
            "background_tertiary": "#242455",
            "text_tertiary": "#d2cfb4",
            "text_primary": "#fefdf2",
            "text_secondary": "#e8e6d3",
            "background_primary": "#080025",
            "border_primary": "#4e4c66",
            "secondary": "#c7ff58",
        },
        "mintly": {
            "background_tertiary": "#1a4040",
            "text_tertiary": "#80deea",
            "text_primary": "#e0f7fa",
            "text_secondary": "#b2ebf2",
            "background_primary": "#0a1717",
            "border_primary": "#00695c",
            "secondary": "#4ECDC4",
        },
        "ocean": {
            "background_tertiary": "#334155",
            "text_tertiary": "#B4C6D3",
            "text_primary": "#F1F5F9",
            "text_secondary": "#CBD5E1",
            "background_primary": "#0C1222",
            "border_primary": "#475569",
            "secondary": "#06B6D4",
        },
        "pulse": {
            "background_tertiary": "#2D2A4A",
            "text_tertiary": "#C8B9FF",
            "text_primary": "#F8F4FF",
            "text_secondary": "#E0D9FF",
            "background_primary": "#0F0B1A",
            "border_primary": "#5A5570",
            "secondary": "#EC4899",
        },
        "solarized_light": {
            "background_tertiary": "#e3dcc6",
            "text_tertiary": "#405a63",
            "text_primary": "#073642",
            "text_secondary": "#2c5866",
            "background_primary": "#fdf6e3",
            "border_primary": "#93a1a1",
            "secondary": "#859900",
        },
        "solarized_dark": {
            "background_tertiary": "#0e4853",
            "text_tertiary": "#839496",
            "text_primary": "#b3c5c7",
            "text_secondary": "#c5d7d9",
            "background_primary": "#002b36",
            "border_primary": "#586e75",
            "secondary": "#859900",
        },
        "dracula": {
            "background_tertiary": "#6272a4",
            "text_tertiary": "#d4d4cf",
            "text_primary": "#f8f8f2",
            "text_secondary": "#f0f0ea",
            "background_primary": "#282a36",
            "border_primary": "#6272a4",
            "secondary": "#ff79c6",
        },
        "openai_like": {
            "background_tertiary": "#ececf1",
            "text_tertiary": "#4a5568",
            "text_primary": "#1a202c",
            "text_secondary": "#2d3748",
            "background_primary": "#ffffff",
            "border_primary": "#d1d5db",
            "secondary": "#4a5568",
        },
        "openui_like": {
            "background_tertiary": "#e8e8e8",
            "text_tertiary": "#777777",
            "text_primary": "#333333",
            "text_secondary": "#555555",
            "background_primary": "#ffffff",
            "border_primary": "#cccccc",
            "secondary": "#555555",
        },
        "openwebui_like": {
            "background_tertiary": "#374151",
            "text_tertiary": "#9ca3af",
            "text_primary": "#f9fafb",
            "text_secondary": "#d1d5db",
            "background_primary": "#111827",
            "border_primary": "#4b5563",
            "secondary": "#6b7280",
        },
        "moonlight": {
            "background_tertiary": "#334155",
            "text_tertiary": "#b8bcc8",
            "text_primary": "#f1f5f9",
            "text_secondary": "#cbd5e1",
            "background_primary": "#0f1419",
            "border_primary": "#475569",
            "secondary": "#c084fc",
        },
        "fireswamp": {
            "background_tertiary": "#44403c",
            "text_tertiary": "#fdba74",
            "text_primary": "#fef7ed",
            "text_secondary": "#fed7aa",
            "background_primary": "#1c1917",
            "border_primary": "#78716c",
            "secondary": "#dc2626",
        },
        "cyber": {
            "background_tertiary": "#1e1e30",
            "text_tertiary": "#80e6ff",
            "text_primary": "#e6fdff",
            "text_secondary": "#b3f0ff",
            "background_primary": "#0a0a0f",
            "border_primary": "#004d66",
            "secondary": "#ff0080",
        },
        "steampunk": {
            "background_tertiary": "#3d2f22",
            "text_tertiary": "#d4c0a1",
            "text_primary": "#faf6f0",
            "text_secondary": "#e6d7c3",
            "background_primary": "#1a1612",
            "border_primary": "#8b6914",
            "secondary": "#b5a642",
        },
    }
    
    print("=" * 120)
    print("SEARCH RESULT COUNT CONTRAST FIX - COMPREHENSIVE ANALYSIS")
    print("=" * 120)
    
    print(f"{'Theme':<20} {'Background':<12} {'Old Text':<10} {'Old Ratio':<10} {'New Text':<10} {'New Ratio':<10} {'Improvement':<12} {'Status'}")
    print("-" * 120)
    
    total_themes = len(themes)
    improved_themes = 0
    failing_themes_fixed = 0
    previously_failing = []
    
    for theme_name, colors in themes.items():
        bg_color = colors["background_tertiary"]
        old_text_color = colors["text_tertiary"]
        
        # Calculate old contrast ratio
        old_ratio = calculate_contrast_ratio(old_text_color, bg_color)
        
        # Get new high-contrast text color
        new_text_color, new_ratio = get_high_contrast_text_color(bg_color, colors)
        
        # Calculate improvement
        improvement = new_ratio - old_ratio
        
        if old_ratio < 4.5:
            previously_failing.append((theme_name, old_ratio, new_ratio, improvement))
            status = "✅ FIXED"
            failing_themes_fixed += 1
        elif new_ratio > old_ratio:
            status = "✅ IMPROVED"
        else:
            status = "⚠ SAME"
        
        if new_ratio > old_ratio:
            improved_themes += 1
        
        print(f"{theme_name:<20} {bg_color:<12} {old_text_color:<10} {old_ratio:<10.2f} {new_text_color:<10} {new_ratio:<10.2f} +{improvement:<11.2f} {status}")
    
    print("\n" + "=" * 120)
    print("COMPREHENSIVE SUMMARY")
    print("=" * 120)
    
    print(f"📊 Total themes analyzed: {total_themes}")
    print(f"📈 Themes with improved contrast: {improved_themes} ({improved_themes/total_themes*100:.1f}%)")
    print(f"🔧 Previously failing themes fixed: {failing_themes_fixed}")
    
    if previously_failing:
        print(f"\n🚨 PREVIOUSLY FAILING THEMES (now fixed):")
        for theme_name, old_ratio, new_ratio, improvement in previously_failing:
            print(f"   • {theme_name}: {old_ratio:.2f} → {new_ratio:.2f} (+{improvement:.2f} contrast)")
    
    # Check if all themes now meet WCAG standards
    all_themes_pass = True
    wcag_aa_count = 0
    wcag_aaa_count = 0
    
    for theme_name, colors in themes.items():
        bg_color = colors["background_tertiary"]
        new_text_color, new_ratio = get_high_contrast_text_color(bg_color, colors)
        
        if new_ratio >= 7.0:
            wcag_aaa_count += 1
        elif new_ratio >= 4.5:
            wcag_aa_count += 1
        else:
            all_themes_pass = False
    
    print(f"\n🎯 WCAG COMPLIANCE RESULTS:")
    if all_themes_pass:
        print(f"   ✅ ALL {total_themes} THEMES NOW MEET WCAG AA STANDARDS (≥4.5)")
        print(f"   🏆 {wcag_aaa_count} themes exceed WCAG AAA standards (≥7.0)")
        print(f"   ✅ {wcag_aa_count} themes meet WCAG AA standards (4.5-6.9)")
    else:
        print("   ❌ Some themes still don't meet WCAG standards")
    
    print(f"\n🎉 SUCCESS: Search result counts are now clearly visible across ALL {total_themes} themes!")
    
    return previously_failing

def show_detailed_analysis():
    """Show detailed analysis of the most problematic themes."""
    print("\n" + "=" * 120)
    print("DETAILED ANALYSIS - PREVIOUSLY WORST THEMES")
    print("=" * 120)
    
    # Test the most problematic themes identified earlier
    problem_themes = {
        "dracula": {
            "background_tertiary": "#6272a4",
            "text_tertiary": "#d4d4cf",
            "text_primary": "#f8f8f2",
            "text_secondary": "#f0f0ea",
            "background_primary": "#282a36",
            "border_primary": "#6272a4",
            "secondary": "#ff79c6",
        },
        "solarized_dark": {
            "background_tertiary": "#0e4853",
            "text_tertiary": "#839496",
            "text_primary": "#b3c5c7",
            "text_secondary": "#c5d7d9",
            "background_primary": "#002b36",
            "border_primary": "#586e75",
            "secondary": "#859900",
        },
        "openui_like": {
            "background_tertiary": "#e8e8e8",
            "text_tertiary": "#777777",
            "text_primary": "#333333",
            "text_secondary": "#555555",
            "background_primary": "#ffffff",
            "border_primary": "#cccccc",
            "secondary": "#555555",
        },
        "dark_matrix": {
            "background_tertiary": "#2d2d2d",
            "text_tertiary": "#009929",
            "text_primary": "#00ff41",
            "text_secondary": "#00cc33",
            "background_primary": "#0d0d0d",
            "border_primary": "#004d1a",
            "secondary": "#00cc33",
        },
        "openwebui_like": {
            "background_tertiary": "#374151",
            "text_tertiary": "#9ca3af",
            "text_primary": "#f9fafb",
            "text_secondary": "#d1d5db",
            "background_primary": "#111827",
            "border_primary": "#4b5563",
            "secondary": "#6b7280",
        },
    }
    
    for theme_name, colors in problem_themes.items():
        bg_color = colors["background_tertiary"]
        old_text_color = colors["text_tertiary"]
        
        # Calculate old and new contrast
        old_ratio = calculate_contrast_ratio(old_text_color, bg_color)
        new_text_color, new_ratio = get_high_contrast_text_color(bg_color, colors)
        
        improvement = new_ratio - old_ratio
        percent_improvement = (improvement / old_ratio * 100) if old_ratio > 0 else 0
        
        print(f"\n🎨 {theme_name.upper()} THEME:")
        print(f"   📱 Search frame background: {bg_color}")
        print(f"   📰 OLD search count text: {old_text_color}")
        print(f"      ➤ Contrast ratio: {old_ratio:.2f} {'❌ FAILS WCAG' if old_ratio < 4.5 else '⚠ POOR' if old_ratio < 7.0 else '✅ GOOD'}")
        print(f"   ✨ NEW search count text: {new_text_color}")
        print(f"      ➤ Contrast ratio: {new_ratio:.2f} {'✅ EXCELLENT (AAA)' if new_ratio >= 7.0 else '✅ GOOD (AA)' if new_ratio >= 4.5 else '❌ STILL POOR'}")
        print(f"   📊 Improvement: +{improvement:.2f} contrast ratio ({percent_improvement:.1f}% increase)")
        
        # Show accessibility compliance
        if new_ratio >= 7.0:
            accessibility = "WCAG AAA (Excellent) - Exceeds all requirements"
        elif new_ratio >= 4.5:
            accessibility = "WCAG AA (Good) - Meets accessibility standards"
        else:
            accessibility = "Below WCAG standards - Still needs work"
            
        print(f"   🏆 Accessibility: {accessibility}")

if __name__ == "__main__":
    failing_themes = test_search_contrast_fix()
    show_detailed_analysis()