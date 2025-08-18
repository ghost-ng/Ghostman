# Color Variable Reference

Complete mapping of the 24 color variables in the Ghostman theme system, including their purpose, affected UI elements, and usage examples.

## Quick Reference Table

| Variable | Category | Default Value | Purpose |
|----------|----------|---------------|---------|
| `primary` | Primary | `#4CAF50` | Main brand color, primary buttons |
| `primary_hover` | Primary | `#45a049` | Primary button hover state |
| `secondary` | Primary | `#2196F3` | Secondary accent, selections |
| `secondary_hover` | Primary | `#1976D2` | Secondary element hover state |
| `background_primary` | Background | `#1a1a1a` | Main app background |
| `background_secondary` | Background | `#2a2a2a` | Panels, dialogs, containers |
| `background_tertiary` | Background | `#3a3a3a` | Cards, elevated surfaces |
| `background_overlay` | Background | `#000000cc` | Modal overlays (with alpha) |
| `text_primary` | Text | `#ffffff` | Primary text (high contrast) |
| `text_secondary` | Text | `#cccccc` | Secondary text (medium contrast) |
| `text_tertiary` | Text | `#888888` | Tertiary text (low contrast) |
| `text_disabled` | Text | `#555555` | Disabled text |
| `interactive_normal` | Interactive | `#4a4a4a` | Buttons, inputs (normal state) |
| `interactive_hover` | Interactive | `#5a5a5a` | Interactive elements on hover |
| `interactive_active` | Interactive | `#6a6a6a` | Interactive elements when pressed |
| `interactive_disabled` | Interactive | `#333333` | Disabled interactive elements |
| `status_success` | Status | `#4CAF50` | Success messages, positive states |
| `status_warning` | Status | `#FF9800` | Warning messages, caution states |
| `status_error` | Status | `#F44336` | Error messages, negative states |
| `status_info` | Status | `#2196F3` | Info messages, neutral states |
| `border_primary` | Border | `#444444` | Main borders, outlines |
| `border_secondary` | Border | `#333333` | Secondary borders, subtle lines |
| `border_focus` | Border | `#4CAF50` | Focus indicators, active borders |
| `separator` | Border | `#2a2a2a` | Separators, dividers |

## Detailed Variable Documentation

### Primary Colors (4 variables)

#### `primary`
- **Purpose**: Main brand color used throughout the application
- **UI Elements**:
  - Primary action buttons (Apply, Save, Submit)
  - Progress bar fill
  - Selected/active states
  - Focus rings on important elements
  - Brand accents and highlights
- **Usage Example**: Apply button background, loading progress
- **Accessibility**: Should have good contrast against background colors
- **Relationship**: Works with `primary_hover` for interactive states

#### `primary_hover`
- **Purpose**: Hover state for primary colored elements
- **UI Elements**:
  - Primary button hover states
  - Interactive primary elements on mouseover
  - Highlighted menu items
- **Usage Example**: When user hovers over Apply button
- **Design Note**: Typically 10-20% darker or lighter than `primary`
- **Accessibility**: Must maintain contrast ratios when transitioning

#### `secondary`
- **Purpose**: Secondary accent color for supporting elements
- **UI Elements**:
  - Selection highlights
  - Secondary action buttons
  - Tab active indicators
  - Link colors
  - Combo box selections
- **Usage Example**: Selected items in lists, secondary buttons
- **Relationship**: Complements `primary` without competing

#### `secondary_hover`
- **Purpose**: Hover state for secondary colored elements
- **UI Elements**:
  - Secondary button hover states
  - Tab hover indicators
  - Link hover effects
- **Usage Example**: When user hovers over secondary buttons
- **Design Note**: Should maintain visual hierarchy below `primary_hover`

### Background Colors (4 variables)

#### `background_primary`
- **Purpose**: Main application background
- **UI Elements**:
  - Main window background
  - Primary content areas
  - Base layer for all content
- **Usage Example**: The main Ghostman window background
- **Accessibility**: Base for text contrast calculations
- **Performance**: Applied to large areas, keep performant

#### `background_secondary`
- **Purpose**: Secondary panels and containers
- **UI Elements**:
  - Dialog backgrounds
  - Panel containers
  - REPL panel background
  - Side panels and toolbars
  - Menu backgrounds
- **Usage Example**: Settings dialog background, conversation browser
- **Design Note**: Should be visually distinct from primary background

#### `background_tertiary`
- **Purpose**: Elevated surfaces and cards
- **UI Elements**:
  - Input field backgrounds
  - Card containers
  - Elevated panels
  - Dropdown content areas
  - Title frames
- **Usage Example**: Text input backgrounds, elevated content cards
- **Visual Hierarchy**: Creates depth perception in the interface

#### `background_overlay`
- **Purpose**: Modal overlays and backdrops
- **UI Elements**:
  - Modal dialog backdrops
  - Overlay screens
  - Loading overlays
  - Popup backgrounds
- **Usage Example**: Dark overlay behind modal dialogs
- **Technical Note**: Usually includes alpha channel for transparency
- **Format**: Supports both hex (#000000cc) and rgba formats

### Text Colors (4 variables)

#### `text_primary`
- **Purpose**: Primary text with highest contrast
- **UI Elements**:
  - Main headings
  - Primary content text
  - Important labels
  - Button text on primary backgrounds
- **Usage Example**: Main conversation text, primary headings
- **Accessibility**: Must meet WCAG AA contrast requirements (4.5:1)
- **Hierarchy**: Highest visual priority in text

#### `text_secondary`
- **Purpose**: Secondary text with medium contrast
- **UI Elements**:
  - Subheadings
  - Supporting text
  - Captions
  - Metadata text
  - Secondary information
- **Usage Example**: Conversation timestamps, secondary labels
- **Accessibility**: Should still be readable but less prominent
- **Contrast**: Lower contrast than primary but still accessible

#### `text_tertiary`
- **Purpose**: Tertiary text with lower contrast
- **UI Elements**:
  - Placeholder text
  - Helper text
  - Footnotes
  - Muted information
  - Status text
- **Usage Example**: Input placeholder text, help text
- **Design Note**: Used for supplementary information
- **Accessibility**: Minimum readable contrast levels

#### `text_disabled`
- **Purpose**: Disabled or inactive text
- **UI Elements**:
  - Disabled form labels
  - Inactive menu items
  - Greyed-out text
  - Unavailable options
- **Usage Example**: Disabled button text, inactive menu items
- **UX Note**: Clearly indicates non-interactive state
- **Accessibility**: May not meet full contrast requirements (intentionally)

### Interactive Elements (4 variables)

#### `interactive_normal`
- **Purpose**: Normal state for interactive elements
- **UI Elements**:
  - Button backgrounds
  - Input field borders
  - Clickable elements
  - Tool buttons
  - Interactive panels
- **Usage Example**: Secondary button background, input border
- **User Experience**: Clearly indicates clickable elements

#### `interactive_hover`
- **Purpose**: Hover state for interactive elements
- **UI Elements**:
  - Button hover backgrounds
  - Hover effects on interactive elements
  - Menu item hovers
  - Clickable area highlights
- **Usage Example**: Button background when mouse hovers over it
- **Animation**: Often used in smooth transitions
- **Feedback**: Provides immediate visual feedback for interactivity

#### `interactive_active`
- **Purpose**: Active/pressed state for interactive elements
- **UI Elements**:
  - Button pressed states
  - Active/selected interactive elements
  - Click feedback
  - Currently pressed controls
- **Usage Example**: Button appearance while being clicked
- **UX Note**: Provides tactile feedback for interactions
- **Duration**: Usually brief, during click/tap events

#### `interactive_disabled`
- **Purpose**: Disabled interactive elements
- **UI Elements**:
  - Disabled buttons
  - Inactive form controls
  - Greyed-out interactive elements
  - Unavailable tools
- **Usage Example**: Disabled save button when form is invalid
- **Accessibility**: Should clearly indicate non-interactive state
- **Contrast**: Deliberately lower contrast to show disabled state

### Status Colors (4 variables)

#### `status_success`
- **Purpose**: Success states and positive feedback
- **UI Elements**:
  - Success messages
  - Positive notifications
  - Completion indicators
  - Valid form states
  - Confirmation dialogs
- **Usage Example**: "Theme saved successfully" message
- **Psychology**: Green color conveys success and completion
- **Consistency**: Should match user expectations for success

#### `status_warning`
- **Purpose**: Warning states and caution indicators
- **UI Elements**:
  - Warning messages
  - Caution notifications
  - Validation warnings
  - Non-critical alerts
  - Search result highlights
- **Usage Example**: "Theme has validation issues" warning
- **Psychology**: Orange/yellow conveys caution without alarm
- **UX Note**: Indicates attention needed but not critical

#### `status_error`
- **Purpose**: Error states and negative feedback
- **UI Elements**:
  - Error messages
  - Critical notifications
  - Failed operations
  - Invalid form states
  - Critical alerts
- **Usage Example**: "Failed to save theme" error message
- **Psychology**: Red color universally indicates errors
- **Accessibility**: Don't rely solely on color for error indication

#### `status_info`
- **Purpose**: Informational states and neutral feedback
- **UI Elements**:
  - Info messages
  - Neutral notifications
  - Help text
  - Informational dialogs
  - Tips and hints
- **Usage Example**: "Theme validation: Checking..." info message
- **Psychology**: Blue typically conveys information and trust
- **Balance**: Neutral emotional tone

### Borders & Separators (4 variables)

#### `border_primary`
- **Purpose**: Main borders and outlines
- **UI Elements**:
  - Input field borders
  - Panel outlines
  - Card borders
  - Container edges
  - Dialog borders
- **Usage Example**: Text input field border, dialog outline
- **Visual Structure**: Defines component boundaries
- **Hierarchy**: Primary visual separation

#### `border_secondary`
- **Purpose**: Secondary borders and subtle lines
- **UI Elements**:
  - Secondary panel borders
  - Subtle dividers
  - Inner component borders
  - Less prominent outlines
- **Usage Example**: Inner panel borders, subtle dividers
- **Visual Weight**: Less prominent than primary borders
- **Layering**: Used for secondary visual separation

#### `border_focus`
- **Purpose**: Focus indicators and active borders
- **UI Elements**:
  - Focused input fields
  - Active element outlines
  - Keyboard navigation indicators
  - Selected element borders
- **Usage Example**: Blue border around focused text input
- **Accessibility**: Critical for keyboard navigation users
- **Animation**: Often used with transitions for smooth focus changes

#### `separator`
- **Purpose**: Separators, dividers, and subtle lines
- **UI Elements**:
  - Menu separators
  - Content dividers
  - Section breaks
  - Subtle line elements
  - List item dividers
- **Usage Example**: Horizontal line between menu sections
- **Visual Function**: Organizes content without strong visual weight
- **Subtlety**: Should be noticeable but not distracting

## Color Relationships and Hierarchy

### Contrast Relationships
```
High Contrast:
- text_primary on background_primary
- text_primary on background_secondary

Medium Contrast:
- text_secondary on background_primary
- text_secondary on background_secondary

Low Contrast:
- text_tertiary on background_primary
- separator on background_primary
```

### Interactive State Progression
```
Normal → Hover → Active → Disabled
interactive_normal → interactive_hover → interactive_active → interactive_disabled
primary → primary_hover → (interactive_active) → interactive_disabled
```

### Background Layering
```
Base Layer: background_primary
Container Layer: background_secondary
Elevated Layer: background_tertiary
Overlay Layer: background_overlay (with transparency)
```

## Usage Guidelines

### Semantic Consistency
- Always use colors for their intended semantic purpose
- Don't use `status_error` for non-error elements
- Keep `primary` colors for primary actions only

### Accessibility Requirements
- Maintain minimum 4.5:1 contrast for normal text
- Maintain minimum 3:1 contrast for large text
- Ensure focus indicators are clearly visible
- Don't rely solely on color to convey information

### Performance Considerations
- Background colors affect large areas - keep them performant
- Minimize style recalculations when changing themes
- Use CSS variables when possible for better performance

### Testing Checklist
- [ ] Test with all 10 preset themes
- [ ] Verify contrast ratios meet WCAG standards
- [ ] Check focus indicators are visible
- [ ] Ensure disabled states are clearly indicated
- [ ] Test with both light and dark themes
- [ ] Validate interactive state transitions
- [ ] Confirm status colors match user expectations

## Common Patterns

### Button Styling Pattern
```css
QPushButton {
    background-color: {interactive_normal};
    color: {text_primary};
    border: 1px solid {border_primary};
}
QPushButton:hover {
    background-color: {interactive_hover};
    border-color: {border_focus};
}
QPushButton:pressed {
    background-color: {interactive_active};
}
QPushButton:disabled {
    background-color: {interactive_disabled};
    color: {text_disabled};
}
```

### Input Field Pattern
```css
QLineEdit {
    background-color: {background_tertiary};
    color: {text_primary};
    border: 1px solid {border_primary};
}
QLineEdit:focus {
    border-color: {border_focus};
}
QLineEdit:disabled {
    background-color: {interactive_disabled};
    color: {text_disabled};
}
```

### Status Message Pattern
```css
.success { color: {status_success}; }
.warning { color: {status_warning}; }
.error { color: {status_error}; }
.info { color: {status_info}; }
```