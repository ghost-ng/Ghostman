#!/usr/bin/env python3
"""
Search Result Count Contrast Analyzer for Ghostman Themes.

Analyzes all themes to calculate WCAG contrast ratios between search frame
background (background_tertiary) and search result count text (text_tertiary).
"""

import colorsys
import math
from typing import Dict, List, Tuple

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculate relative luminance of RGB color according to WCAG standards."""
    def linear_rgb(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
    
    r, g, b = rgb
    return 0.2126 * linear_rgb(r) + 0.7152 * linear_rgb(g) + 0.0722 * linear_rgb(b)

def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    try:
        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        
        lum1 = rgb_to_luminance(rgb1)
        lum2 = rgb_to_luminance(rgb2)
        
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    except:
        return 0.0

def get_best_text_color_for_background(bg_color: str, 
                                     candidate_colors: List[str]) -> Tuple[str, float]:
    """Find the best text color from candidates for the given background."""
    best_color = candidate_colors[0]
    best_ratio = 0.0
    
    for text_color in candidate_colors:
        ratio = calculate_contrast_ratio(bg_color, text_color)
        if ratio > best_ratio:
            best_ratio = ratio
            best_color = text_color
    
    return best_color, best_ratio

def analyze_all_themes():
    """Analyze contrast for all themes."""
    
    # Theme definitions extracted from preset_themes.py
    themes = {
        "dark_matrix": {
            "background_tertiary": "#2d2d2d",
            "text_tertiary": "#009929",
        },
        "midnight_blue": {
            "background_tertiary": "#1e2742",
            "text_tertiary": "#90caf9",
        },
        "forest_green": {
            "background_tertiary": "#2e4a33",
            "text_tertiary": "#a5d6a7",
        },
        "sunset_orange": {
            "background_tertiary": "#4a2c1a",
            "text_tertiary": "#ffcc80",
        },
        "royal_purple": {
            "background_tertiary": "#331a4a",
            "text_tertiary": "#ce93d8",
        },
        "arctic_white": {
            "background_tertiary": "#e9ecef",
            "text_tertiary": "#555555",
        },
        "cyberpunk": {
            "background_tertiary": "#16213e",
            "text_tertiary": "#00ffff",
        },
        "earth_tones": {
            "background_tertiary": "#4a3728",
            "text_tertiary": "#bcaaa4",
        },
        "ocean_deep": {
            "background_tertiary": "#21262d",
            "text_tertiary": "#80cbc4",
        },
        "lilac": {
            "background_tertiary": "#3a3040",
            "text_tertiary": "#d0c8d8",
        },
        "sunburst": {
            "background_tertiary": "#4a2f1c",
            "text_tertiary": "#ffcc80",
        },
        "forest": {
            "background_tertiary": "#2a4a26",
            "text_tertiary": "#a8cc9f",
        },
        "firefly": {
            "background_tertiary": "#242455",
            "text_tertiary": "#d2cfb4",
        },
        "mintly": {
            "background_tertiary": "#1a4040",
            "text_tertiary": "#80deea",
        },
        "ocean": {
            "background_tertiary": "#334155",
            "text_tertiary": "#B4C6D3",
        },
        "pulse": {
            "background_tertiary": "#2D2A4A",
            "text_tertiary": "#C8B9FF",
        },
        "solarized_light": {
            "background_tertiary": "#e3dcc6",
            "text_tertiary": "#405a63",
        },
        "solarized_dark": {
            "background_tertiary": "#0e4853",
            "text_tertiary": "#839496",
        },
        "dracula": {
            "background_tertiary": "#6272a4",
            "text_tertiary": "#d4d4cf",
        },
        "openai_like": {
            "background_tertiary": "#ececf1",
            "text_tertiary": "#4a5568",
        },
        "openui_like": {
            "background_tertiary": "#e8e8e8",
            "text_tertiary": "#777777",
        },
        "openwebui_like": {
            "background_tertiary": "#374151",
            "text_tertiary": "#9ca3af",
        },
        "moonlight": {
            "background_tertiary": "#334155",
            "text_tertiary": "#b8bcc8",
        },
        "fireswamp": {
            "background_tertiary": "#44403c",
            "text_tertiary": "#fdba74",
        },
        "cyber": {
            "background_tertiary": "#1e1e30",
            "text_tertiary": "#80e6ff",
        },
        "steampunk": {
            "background_tertiary": "#3d2f22",
            "text_tertiary": "#d4c0a1",
        },
    }
    
    results = []
    failing_themes = []
    
    print("=" * 80)
    print("GHOSTMAN SEARCH RESULT COUNT CONTRAST ANALYSIS")
    print("=" * 80)
    print(f"{'Theme':<20} {'Background':<10} {'Text':<10} {'Contrast':<10} {'WCAG Status'}")
    print("-" * 80)
    
    for theme_name, colors in themes.items():
        bg_color = colors["background_tertiary"]
        text_color = colors["text_tertiary"]
        
        ratio = calculate_contrast_ratio(bg_color, text_color)
        status = "PASS" if ratio >= 4.5 else "FAIL"
        
        if ratio < 4.5:
            failing_themes.append((theme_name, ratio))
        
        results.append({
            "theme": theme_name,
            "background": bg_color,
            "text": text_color,
            "ratio": ratio,
            "passes": ratio >= 4.5
        })
        
        print(f"{theme_name:<20} {bg_color:<10} {text_color:<10} {ratio:<10.2f} {status}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_themes = len(themes)
    failing_count = len(failing_themes)
    passing_count = total_themes - failing_count
    
    print(f"Total themes analyzed: {total_themes}")
    print(f"Themes passing WCAG AA (≥4.5): {passing_count} ({passing_count/total_themes*100:.1f}%)")
    print(f"Themes failing WCAG AA (<4.5): {failing_count} ({failing_count/total_themes*100:.1f}%)")
    
    if failing_themes:
        print(f"\nFailing themes (worst first):")
        failing_themes.sort(key=lambda x: x[1])  # Sort by ratio, lowest first
        for theme_name, ratio in failing_themes:
            print(f"  • {theme_name}: {ratio:.2f} contrast ratio")
    
    # Test optimal colors for each failing theme
    print("\n" + "=" * 80)
    print("OPTIMAL COLOR RECOMMENDATIONS")
    print("=" * 80)
    
    # Common high-contrast text colors to test
    candidate_colors = [
        "#ffffff",  # Pure white
        "#000000",  # Pure black
        "#f8f8f2",  # Near white
        "#2d2d2d",  # Dark gray
        "#e6e6e6",  # Light gray
        "#333333",  # Medium dark gray
    ]
    
    for theme_name, colors in themes.items():
        bg_color = colors["background_tertiary"]
        current_text = colors["text_tertiary"]
        current_ratio = calculate_contrast_ratio(bg_color, current_text)
        
        if current_ratio < 4.5:
            best_color, best_ratio = get_best_text_color_for_background(bg_color, candidate_colors)
            improvement = best_ratio - current_ratio
            
            print(f"\n{theme_name.upper()}:")
            print(f"  Background: {bg_color}")
            print(f"  Current text: {current_text} (ratio: {current_ratio:.2f}) ❌")
            print(f"  Optimal text: {best_color} (ratio: {best_ratio:.2f}) ✅")
            print(f"  Improvement: +{improvement:.2f}")
    
    return results

if __name__ == "__main__":
    analyze_all_themes()