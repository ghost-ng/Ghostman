# Theme User Guide

A practical guide for users to create, customize, and manage themes in Ghostman.

## Quick Start

### Using Preset Themes

1. **Open Theme Settings**: Right-click tray icon → Settings → Appearance
2. **Choose Theme**: Select from 27 preset themes in the dropdown
3. **Preview**: Enable "Live Updates" to see changes in real-time
4. **Apply**: Click "Apply" to save your selection

### Popular Preset Themes

| Theme | Style | Best For |
|-------|-------|----------|
| **OpenAI Like** | Clean light | Professional, day work |
| **Dracula** | Purple dark | Developer environments |
| **Matrix** | Bright green on black | Terminal/coding aesthetic |
| **Arctic White** | High contrast light | Bright environments |
| **Cyberpunk** | Neon accents | Gaming, futuristic feel |
| **Forest Green** | Natural greens | Relaxed, nature-inspired |
| **Ocean Deep** | Blue-greens | Calm, focused work |

## Creating Custom Themes

### Method 1: Modify Existing Theme

1. Select a preset theme as your starting point
2. Navigate through color category tabs:
   - **Primary Colors**: Main brand colors and accents
   - **Backgrounds**: Window, panel, and surface colors
   - **Text Colors**: Text hierarchy and readability
   - **Interactive**: Button and control states
   - **Status Colors**: Success, warning, error, info
   - **Borders**: Lines, focus indicators, separators

3. Click any color preview to open the color picker
4. See instant preview with "Live Updates" enabled
5. Use undo buttons (↶) to revert individual changes

### Method 2: Import Theme

1. Click "Import Theme" button
2. Select a `.json` theme file
3. The theme appears in your custom themes list
4. Apply it from the preset dropdown

## Saving and Sharing Themes

### Save Custom Theme
1. After customizing colors, enter a name
2. Click "Save Custom Theme"
3. Theme appears in preset dropdown as "Custom: [Name]"
4. Stored in: `%APPDATA%/Ghostman/themes/custom/`

### Export Theme
1. Configure your desired theme
2. Enter export name (optional)
3. Click "Export Theme"
4. Choose save location for `.json` file
5. Share file with other users

## Theme Validation

### Understanding Validation Status

- **✅ All Valid**: Perfect theme, meets accessibility standards
- **⚠️ Issues Found**: Some problems detected, still usable
- **❌ Invalid**: Serious issues, may affect usability

### Common Issues and Fixes

#### Low Contrast Warnings
**Problem**: Text hard to read against background
**Fix**: Choose darker text on light backgrounds, or lighter text on dark backgrounds

#### Invalid Colors
**Problem**: Broken color codes
**Fix**: Use the color picker instead of typing hex codes

#### Missing Colors
**Problem**: Required color not defined
**Fix**: Reset problematic color and choose a new one

## Accessibility Guidelines

### For Better Usability

1. **High Contrast**: Ensure text is clearly readable
2. **Focus Indicators**: Keep blue focus borders visible
3. **Status Colors**: Use standard colors (green=good, red=error, etc.)
4. **Test Both Modes**: Try your theme in day and night lighting

### WCAG Compliance

The theme system automatically checks for:
- **WCAG AA**: 4.5:1 contrast ratio for normal text
- **WCAG AAA**: 7.0:1 contrast ratio (ideal)
- **Color Blindness**: Ensures essential information isn't color-dependent

## Tips and Best Practices

### For Theme Creators

1. **Start with Presets**: Modify existing themes rather than starting from scratch
2. **Use Live Preview**: Keep "Live Updates" on to see changes immediately
3. **Check All Areas**: Preview theme in different parts of the application
4. **Save Frequently**: Save your work as custom theme to prevent loss
5. **Export Backups**: Keep `.json` files of your favorite themes

### For Daily Use

1. **Lighting Matters**: Dark themes for low light, light themes for bright environments
2. **Time of Day**: Consider switching themes based on time (dark evening, light day)
3. **Eye Strain**: If you experience strain, try themes with softer contrasts
4. **Personal Preference**: Ultimately, choose what feels comfortable for you

## Troubleshooting

### Theme Not Applying
1. Ensure "Apply" button was clicked
2. Try restarting the application
3. Check if custom theme file is corrupted
4. Reset to a working preset theme

### Colors Look Wrong
1. Check your monitor's color settings
2. Verify theme validation shows no errors
3. Try a different preset theme to compare
4. Reset individual colors using undo buttons

### Performance Issues
1. Disable "Live Updates" during editing
2. Apply theme only when finished editing
3. Clear custom theme cache in settings
4. Restart application if themes load slowly

## Getting Help

- **Validation Messages**: Hover over warning icons for specific issues
- **Reset Options**: Use "Reset All" to return to working state
- **Community**: Share theme files with other users for help
- **Logs**: Check application logs for detailed error information

## File Locations

- **Custom Themes**: `%APPDATA%/Ghostman/themes/custom/`
- **Settings**: `%APPDATA%/Ghostman/settings.json`
- **Logs**: `%APPDATA%/Ghostman/logs/`

Themes are stored as JSON files and can be shared between installations and users.