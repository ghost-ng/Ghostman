# Specter Setup Wizard - Design Document

## Overview
A standalone, theme-aware setup wizard for guiding new users through Specter configuration. The wizard features a landing page with two setup flows, each containing 3 carousel-style pages with placeholder content.

## Requirements Analysis

### Functional Requirements
- Standalone script that can be called as a module (`python -m specter.setup_wizard`)
- Theme-aware window integrating with existing `ThemeManager`
- Unattached window (independent of main application)
- Landing page with welcome content and two setup option buttons
- Each setup flow has 3 pages with carousel navigation
- Image placeholders with subtitle descriptions
- Side arrows for navigation between pages
- Professional, welcoming interface for new users

### Technical Requirements
- PyQt6-based (matching existing codebase)
- Integration with existing `ColorSystem` and `ThemeManager` 
- Self-contained window with no dependencies on main application
- Theme-responsive design with real-time theme switching support

## Interface Design

### Navigation Structure
```
Setup Wizard Landing
├── Quick Setup Flow
│   ├── Page 1: Basic AI Configuration
│   ├── Page 2: Interface Preferences  
│   └── Page 3: Quick Setup Complete
└── Advanced Setup Flow
    ├── Page 1: Custom AI Models & APIs
    ├── Page 2: Enterprise Features
    └── Page 3: Advanced Setup Complete
```

### Landing Page Layout
```
┌─────────────────────────────────────────────────────────────┐
│  [Specter Logo/Icon]     Setup Wizard                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Welcome Content Area                   │   │
│  │                                                     │   │
│  │  Welcome to Specter Setup                          │   │
│  │  Configure your AI assistant for optimal experience │   │
│  │                                                     │   │
│  │  [Welcome graphic/illustration placeholder]         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐ │
│  │   Quick Setup       │  │   Advanced Setup            │ │
│  │                     │  │                             │ │
│  │   Get started with  │  │   Full configuration with   │ │
│  │   recommended       │  │   custom AI models and     │ │
│  │   settings          │  │   enterprise features      │ │
│  │                     │  │                             │ │
│  │   [Continue →]      │  │   [Configure →]             │ │
│  └─────────────────────┘  └─────────────────────────────┘ │
│                                                             │
│                           [Skip Setup] [Exit]              │
└─────────────────────────────────────────────────────────────┘
```

### Carousel Page Layout
```
┌─────────────────────────────────────────────────────────────┐
│  ← Setup Flow Name                          Step X of 3     │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │           [Image/Graphic Placeholder]                   │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│              Step Title                                     │
│        Descriptive subtitle explaining this step           │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │              Configuration Content                      │ │
│  │              (Forms/Options/Info)                       │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│     ◀ Previous     ● ● ●     Next ▶     [Complete]        │
└─────────────────────────────────────────────────────────────┘
```

## Theme Integration

### ColorSystem Integration
The wizard will use Specter's existing theme system:

```python
class ThemedSetupWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._apply_theme)
        self._apply_theme()
    
    def _apply_theme(self):
        theme = self.theme_manager.current_theme
        self.setStyleSheet(f"""
            QWizard {{
                background-color: {theme.background_primary};
                color: {theme.text_primary};
            }}
            QPushButton {{
                background-color: {theme.interactive_normal};
                color: {theme.text_primary};
                border: 1px solid {theme.border_primary};
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {theme.interactive_hover};
            }}
        """)
```

### Theme-Aware Components
- **Primary Surfaces**: `background_primary` for main wizard background
- **Secondary Surfaces**: `background_secondary` for content areas
- **Interactive Elements**: `interactive_normal/hover/active` for buttons
- **Text Hierarchy**: `text_primary/secondary` for content
- **Borders**: `border_primary` for visual structure

## Technical Implementation

### Project Structure
```
specter/src/presentation/wizards/setup_wizard/
├── __init__.py
├── setup_wizard.py          # Main wizard class
├── pages/
│   ├── __init__.py
│   ├── landing_page.py      # Welcome page with two options
│   ├── quick_setup/         # Quick setup flow pages
│   │   ├── __init__.py
│   │   ├── basic_ai_config.py
│   │   ├── interface_prefs.py
│   │   └── quick_complete.py
│   └── advanced_setup/      # Advanced setup flow pages
│       ├── __init__.py
│       ├── custom_models.py
│       ├── enterprise_features.py
│       └── advanced_complete.py
├── components/
│   ├── __init__.py
│   ├── themed_wizard.py     # Base themed wizard class
│   ├── carousel_widget.py   # Image carousel component
│   └── option_card.py       # Landing page option cards
└── resources/
    ├── images/              # Placeholder images
    └── styles/              # Additional styling if needed
```

### Key Components

#### 1. ThemedSetupWizard (Base Class)
- Extends QWizard with theme integration
- Handles theme switching and real-time updates
- Manages navigation flow between pages

#### 2. LandingPage
- Welcome content with Specter branding
- Two option cards for setup flows
- Skip/Exit functionality

#### 3. CarouselPage (Base Class)
- Image placeholder area
- Title and subtitle content
- Navigation controls (Previous/Next arrows)
- Progress indicators (dots)

#### 4. OptionCard Widget
- Themed card component for setup options
- Hover effects and click handling
- Consistent styling with theme system

### Standalone Module Support
```python
# specter/src/presentation/wizards/setup_wizard/__main__.py
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from .setup_wizard import SetupWizard
    
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec())
```

### Integration Points
- **Theme System**: Uses existing `theme_manager` and `ColorSystem`
- **Settings**: Integrates with `settings_manager` for configuration persistence
- **Patterns**: Follows established patterns from `PKISetupWizard`
- **Styling**: Maintains consistency with `SettingsDialog` approach

## UX/UI Design Principles

### Navigation Flow
- **Clear Hierarchy**: Landing → Flow Selection → Step-by-Step Configuration
- **Progress Indicators**: Visual feedback on current step and completion
- **Escape Routes**: Skip Setup and proper cancellation handling
- **Smart Navigation**: Context-aware back/forward button states

### Visual Design
- **Professional Appearance**: Clean, modern design consistent with Specter
- **Theme Responsiveness**: Real-time theme switching support
- **Accessibility**: WCAG 2.1 AA compliance through ColorSystem
- **Placeholder Structure**: Easy content replacement for future updates

### Content Strategy
- **Welcoming Tone**: Professional but friendly introduction
- **Clear Options**: Distinct quick vs advanced setup paths
- **Visual Learning**: Image placeholders for step-by-step guidance
- **Progressive Disclosure**: Information revealed as needed

## Placeholder Content Structure

### Landing Page
- **Welcome Title**: "Welcome to Specter Setup"
- **Description**: "Configure your AI assistant for optimal experience"
- **Quick Setup**: "Get started with recommended settings"
- **Advanced Setup**: "Full configuration with custom AI models and enterprise features"

### Quick Setup Flow
1. **Basic AI Configuration**: Select default AI model and basic settings
2. **Interface Preferences**: Choose theme, font size, and layout options  
3. **Quick Setup Complete**: Summary and start using Specter

### Advanced Setup Flow
1. **Custom AI Models & APIs**: Configure custom endpoints and authentication
2. **Enterprise Features**: PKI setup, advanced security, team settings
3. **Advanced Setup Complete**: Comprehensive configuration summary

## Future Enhancement Considerations

### Extensibility
- **Plugin System**: Support for additional setup flows
- **Dynamic Content**: Load setup steps from configuration files
- **Customization**: Organization-specific branding and content

### Analytics
- **Setup Completion**: Track which flows users prefer
- **Drop-off Points**: Identify where users abandon setup
- **Feature Adoption**: Monitor which features get configured

### Accessibility
- **Screen Reader Support**: Proper ARIA labels and navigation
- **Keyboard Navigation**: Full keyboard accessibility
- **High Contrast**: Enhanced visual accessibility options

## Implementation Timeline

### Phase 1: Core Structure (Current)
- [ ] Create project structure
- [ ] Implement base ThemedSetupWizard class
- [ ] Create LandingPage with option cards
- [ ] Basic theme integration

### Phase 2: Carousel Implementation
- [ ] Implement CarouselPage base class
- [ ] Create image placeholder system
- [ ] Add navigation controls and progress indicators
- [ ] Implement all 6 setup pages with placeholder content

### Phase 3: Polish and Integration
- [ ] Advanced theme integration and styling
- [ ] Settings persistence integration
- [ ] Testing across all available themes
- [ ] Standalone module packaging

## Technical Notes

### Theme Manager Integration
The wizard leverages the enhanced `ThemeManager` with its comprehensive theme refresh capabilities:
- Supports all 39+ available themes
- Real-time theme switching
- Border artifact elimination
- Font configuration integration

### PyQt6 Best Practices
- Signal-based communication for wizard completion
- Proper widget hierarchy for theme propagation
- Memory management and cleanup
- Cross-platform compatibility

This design document provides a comprehensive foundation for implementing a professional, theme-aware setup wizard that enhances the Specter user onboarding experience.