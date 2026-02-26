"""
Tab Conversation Manager for Specter.

Manages multiple conversation tabs with context switching and state isolation.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QHBoxLayout, QMenu, QStackedWidget
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QAction

# Import MixedContentDisplay for per-tab output widgets
from .mixed_content_display import MixedContentDisplay

logger = logging.getLogger("specter.tab_conversation_manager")


class ConversationTab:
    """Represents a single conversation tab with its state and UI button."""

    def __init__(self, tab_id: str, title: str = "New Conversation", theme_manager=None):
        self.tab_id = tab_id
        self.conversation_id: Optional[str] = None
        self.is_active = False
        self.is_modified = False
        self.button: Optional[QPushButton] = None

        # Each tab owns its own output display widget - NO MORE SHARED WIDGET!
        # Note: MixedContentDisplay doesn't accept theme_manager parameter
        # Theme will be applied via the global theme system
        self.output_display = MixedContentDisplay()
        self.output_display.setAcceptDrops(False)  # Let parent REPL handle file drops

        # Each tab owns its own file browser widget - per-tab file isolation
        from .file_browser_bar import FileBrowserBar
        self.file_browser = FileBrowserBar(theme_manager=theme_manager)
        self.file_browser.setVisible(False)  # Initially hidden

        # Per-tab state storage for sandboxing
        self.file_ids: List[str] = []  # Files associated with THIS tab
        self.file_browser_visible: bool = False  # File browser visibility state

        # Initialize title using the setter to ensure proper truncation
        self.set_title(title)
        
    def set_title(self, title: str):
        """Update tab title and button text with 25 character limit."""
        # Store full title
        self.full_title = title
        
        # Apply 25 character limit: if over 20, truncate to 17 + "..."
        if len(title) > 25:
            self.title = title[:22] + "..."
        elif len(title) > 20:
            self.title = title[:17] + "..."
        else:
            self.title = title
            
        if self.button:
            self.button.setText(self.title)
            self.button.setToolTip(self.full_title)  # Full title in tooltip
    
    def set_modified(self, modified: bool):
        """Mark tab as modified (unsaved changes)."""
        self.is_modified = modified
        # Could add visual indicator later (dot, color change, etc.)


class TabConversationManager(QObject):
    """Manages tabbed conversations with context switching."""
    
    # Signals
    tab_switched = pyqtSignal(str, str)  # old_tab_id, new_tab_id
    tab_created = pyqtSignal(str)   # tab_id
    tab_closed = pyqtSignal(str)    # tab_id
    conversation_context_switched = pyqtSignal(str)  # conversation_id (empty for new conversation)
    new_tab_requested = pyqtSignal()
    
    def __init__(self, parent_repl_widget, tab_frame: QFrame, tab_layout: QHBoxLayout, output_container_layout=None, create_initial_tab: bool = True):
        super().__init__()
        self.parent_repl = parent_repl_widget
        self.tab_frame = tab_frame
        self.tab_layout = tab_layout

        # Tab management
        self.tabs: Dict[str, ConversationTab] = {}
        self.active_tab_id: Optional[str] = None
        self.tab_order: List[str] = []

        # Stacked widget to hold all tab output displays
        # Each tab's output_display will be added here and we'll switch between them
        self.output_stack = QStackedWidget()
        self.output_stack.setMinimumHeight(300)

        # Stacked widget to hold all tab file browsers
        # Each tab's file_browser will be added here and we'll switch between them
        self.file_browser_stack = QStackedWidget()
        self.file_browser_stack.setVisible(False)  # Initially hidden

        # NOTE: We create the QStackedWidget here but DON'T add it to the layout yet
        # The parent (REPLWidget) will add it in the correct position in its layout
        # This ensures proper ordering: tab_bar → title_bar → output_stack → input
        self.output_container_layout = output_container_layout

        # Initialize with first tab if requested
        if create_initial_tab:
            self._create_initial_tab()

        logger.info(f"TabConversationManager initialized (initial_tab={create_initial_tab})")
    
    def _create_initial_tab(self):
        """Create the initial default tab."""
        initial_id = f"tab-{str(uuid.uuid4())[:8]}"
        self.create_tab(initial_id, "New Conversation", activate=True)
    
    def create_tab(self, tab_id: str = None, title: str = "New Conversation", activate: bool = True) -> str:
        """Create a new conversation tab with max limit enforcement."""
        if not tab_id:
            tab_id = f"tab-{str(uuid.uuid4())[:8]}"

        # Check if tab already exists
        if tab_id in self.tabs:
            if activate:
                self.switch_to_tab(tab_id)
            return tab_id

        # Enforce tab limit (max 6 tabs)
        MAX_TABS = 6
        if len(self.tabs) >= MAX_TABS:
            logger.warning(f"Tab limit reached ({MAX_TABS} tabs). Cannot create more tabs.")
            # Optionally show a message to user
            if hasattr(self.parent_repl, 'append_output'):
                self.parent_repl.append_output(
                    f"⚠ Maximum {MAX_TABS} tabs allowed. Close a tab to create a new one.",
                    "warning"
                )
            return None
        
        # Create tab object
        logger.info(f"")
        logger.info(f"{'='*80}")
        logger.info(f"🆕 CREATING NEW TAB")
        logger.info(f"{'='*80}")
        logger.info(f"   Tab ID: {tab_id}")
        logger.info(f"   Title: {title}")
        logger.info(f"   Activate: {activate}")

        # Get theme_manager from parent REPL widget if available
        theme_manager = getattr(self.parent_repl, 'theme_manager', None)

        tab = ConversationTab(tab_id, title, theme_manager=theme_manager)
        logger.info(f"   ✅ Tab object created with its own output display widget")

        # Create tab button
        tab_button = QPushButton(title)
        tab_button.setObjectName(f"tab_button_{tab_id}")
        
        # Style the button and set size constraints
        self._style_tab_button(tab_button, active=False)
        
        # Ensure consistent sizing from creation
        tab_button.setSizePolicy(
            tab_button.sizePolicy().horizontalPolicy(),
            tab_button.sizePolicy().Policy.Fixed
        )
        
        # Connect button click
        tab_button.clicked.connect(lambda: self.switch_to_tab(tab_id))
        
        # Set up context menu
        tab_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_button.customContextMenuRequested.connect(
            lambda pos: self._show_tab_context_menu(tab_id, tab_button.mapToGlobal(pos))
        )
        
        # Store button reference
        tab.button = tab_button
        
        # Add to layout (before the stretch)
        insert_index = self.tab_layout.count() - 1  # Before stretch
        if insert_index < 0:
            insert_index = 0
        self.tab_layout.insertWidget(insert_index, tab_button)
        
        # Store tab
        self.tabs[tab_id] = tab
        self.tab_order.append(tab_id)

        # Add tab's output display widget to the stacked widget
        self.output_stack.addWidget(tab.output_display)
        logger.info(f"   📺 Added tab's output widget to QStackedWidget (index: {self.output_stack.count() - 1})")

        # Add tab's file browser widget to the file browser stacked widget
        self.file_browser_stack.addWidget(tab.file_browser)
        logger.info(f"   📁 Added tab's file browser to QStackedWidget (index: {self.file_browser_stack.count() - 1})")

        # Connect file browser signals to parent REPL widget
        if hasattr(self.parent_repl, '_connect_file_browser_signals'):
            self.parent_repl._connect_file_browser_signals(tab.file_browser)
            logger.debug(f"   ✅ Connected file browser signals for tab {tab_id[:8]}")

        # Activate if requested
        if activate:
            logger.info(f"   🔄 Activating new tab...")
            self.switch_to_tab(tab_id)

        logger.info(f"   ✅ Tab creation complete: {tab_id}")
        logger.info(f"   📢 Emitting tab_created signal...")
        logger.info(f"{'='*80}")
        logger.info(f"")

        self.tab_created.emit(tab_id)

        return tab_id
    
    def close_tab(self, tab_id: str) -> bool:
        """Close a conversation tab."""
        if tab_id not in self.tabs:
            return False

        # Don't close the last tab
        if len(self.tabs) <= 1:
            logger.debug("Cannot close the last tab")
            return False

        tab = self.tabs[tab_id]

        # Remove button from layout
        if tab.button:
            self.tab_layout.removeWidget(tab.button)
            tab.button.deleteLater()

        # Remove tab's output widget from stacked widget
        if tab.output_display:
            self.output_stack.removeWidget(tab.output_display)
            tab.output_display.deleteLater()
            logger.debug(f"Removed tab {tab_id[:8]}'s output widget from QStackedWidget")

        # Remove from tracking
        del self.tabs[tab_id]
        if tab_id in self.tab_order:
            self.tab_order.remove(tab_id)

        # Switch to another tab if this was active
        if self.active_tab_id == tab_id:
            # Find next tab to activate
            if self.tab_order:
                next_tab_id = self.tab_order[-1]  # Most recent tab
                self.switch_to_tab(next_tab_id)
            else:
                self.active_tab_id = None

        logger.info(f"Closed tab: {tab_id}")
        self.tab_closed.emit(tab_id)

        return True
    
    def switch_to_tab(self, tab_id: str):
        """Switch to a specific tab - simply shows the tab's widget, no save/restore needed."""
        if tab_id not in self.tabs:
            logger.warning(f"Tab not found: {tab_id}")
            return

        old_tab_id = self.active_tab_id

        # Debug: show all tab-conversation associations
        logger.info(f"📋 Current tab-conversation map:")
        for tid, tab in self.tabs.items():
            logger.info(f"   {tid[:12]}: {tab.conversation_id[:8] if tab.conversation_id else 'None'}")

        # Update old tab styling
        if self.active_tab_id and self.active_tab_id in self.tabs:
            old_tab = self.tabs[self.active_tab_id]
            if old_tab.button:
                self._style_tab_button(old_tab.button, active=False)
            old_tab.is_active = False

        # Update new active tab
        tab = self.tabs[tab_id]
        if tab.button:
            self._style_tab_button(tab.button, active=True)
        tab.is_active = True

        self.active_tab_id = tab_id

        # Move to end of order (most recently used)
        if tab_id in self.tab_order:
            self.tab_order.remove(tab_id)
        self.tab_order.append(tab_id)

        # Switch to this tab's output widget in the stacked widget
        # Each tab owns its own MixedContentDisplay widget - just show it!
        self.output_stack.setCurrentWidget(tab.output_display)
        logger.info(f"🔄 Switched QStackedWidget to tab {tab_id[:8]}'s output display")

        # Switch to this tab's file browser widget in the file browser stacked widget
        self.file_browser_stack.setCurrentWidget(tab.file_browser)
        logger.debug(f"🔄 Switched file browser stack to tab {tab_id[:8]}'s file browser")
        logger.debug(f"Switched to tab: {tab_id} (from {old_tab_id})")

        # Emit tab switch with both old and new IDs
        self.tab_switched.emit(old_tab_id or "", tab_id)

        # Emit conversation context switch
        conversation_id = tab.conversation_id or ""
        self.conversation_context_switched.emit(conversation_id)
        logger.debug(f"Tab {tab_id} conversation context: {conversation_id or 'NEW'}")
    
    def get_active_tab(self) -> Optional[ConversationTab]:
        """Get the currently active tab."""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            return self.tabs[self.active_tab_id]
        return None
    
    def update_tab_title(self, tab_id: str, new_title: str):
        """Update a tab's title."""
        if tab_id in self.tabs:
            self.tabs[tab_id].set_title(new_title)
            logger.debug(f"Updated tab {tab_id} title to: {new_title}")
    
    def associate_conversation_with_tab(self, tab_id: str, conversation_id: str, conversation_title: str = None):
        """Associate a conversation with a specific tab."""
        if tab_id not in self.tabs:
            logger.warning(f"Cannot associate conversation - tab not found: {tab_id}")
            return False

        tab = self.tabs[tab_id]
        logger.info(f"🔗 BEFORE: tab.conversation_id = {tab.conversation_id}")
        tab.conversation_id = conversation_id
        logger.info(f"🔗 AFTER: tab.conversation_id = {tab.conversation_id[:8]}")

        # Update tab title if conversation title provided
        if conversation_title:
            tab.set_title(conversation_title)

        logger.info(f"Associated conversation {conversation_id} with tab {tab_id}")

        # Verify the association stuck
        verify = self.tabs[tab_id].conversation_id
        if verify == conversation_id:
            logger.info(f"✅ Association verified: {tab_id[:12]} → {conversation_id[:8]}")
        else:
            logger.error(f"❌ Association FAILED: Expected {conversation_id[:8]}, got {verify}")

        return True
    
    def get_conversation_for_tab(self, tab_id: str) -> Optional[str]:
        """Get the conversation ID associated with a tab."""
        if tab_id in self.tabs:
            conv_id = self.tabs[tab_id].conversation_id
            logger.info(f"🔍 get_conversation_for_tab({tab_id[:12]}): {conv_id[:8] if conv_id else 'None'}")
            return conv_id
        logger.warning(f"🔍 get_conversation_for_tab({tab_id[:12]}): TAB NOT FOUND")
        return None
    
    def get_active_conversation_id(self) -> Optional[str]:
        """Get the conversation ID for the currently active tab."""
        if self.active_tab_id:
            return self.get_conversation_for_tab(self.active_tab_id)
        return None
    
    def find_tab_for_conversation(self, conversation_id: str) -> Optional[str]:
        """Find the tab associated with a specific conversation."""
        for tab_id, tab in self.tabs.items():
            if tab.conversation_id == conversation_id:
                return tab_id
        return None
    
    def _style_tab_button(self, button: QPushButton, active: bool):
        """Apply theme-aware styling to a tab button with consistent sizing."""
        try:
            # Try to get theme manager from parent REPL widget
            theme_manager = getattr(self.parent_repl, 'theme_manager', None)
            if theme_manager:
                colors = theme_manager.current_theme
                if colors:
                    from specter.src.ui.themes.style_templates import StyleTemplates
                    tab_style = StyleTemplates.get_conversation_tab_button_style(colors, active)
                    
                    # Apply enhanced styling with consistent sizing
                    enhanced_style = self._enhance_tab_style_with_sizing(tab_style)
                    button.setStyleSheet(enhanced_style)
                    
                    # Set consistent size constraints
                    button.setMinimumSize(100, 36)
                    button.setMaximumSize(200, 36)  # Prevent excessive growth
                    
                    logger.debug(f"Applied theme-aware tab styling: active={active}, primary={colors.primary}")
                    return
                else:
                    logger.debug("Theme manager has no current_theme")
            else:
                logger.debug("No theme manager found on parent REPL widget")
        except Exception as e:
            logger.debug(f"Failed to apply theme-aware tab styling: {e}")
        
        # Enhanced fallback with theme-neutral colors
        self._apply_fallback_tab_style(button, active)
    
    def _show_tab_context_menu(self, tab_id: str, position):
        """Show context menu for tab operations."""
        menu = QMenu()

        # Rename tab label (cosmetic, session-only)
        rename_action = QAction("Rename Tab", menu)
        rename_action.triggered.connect(lambda: self._rename_tab(tab_id))
        menu.addAction(rename_action)

        # Rename conversation title (persisted to DB, shown in conversation browser)
        rename_conv_action = QAction("Rename Conversation", menu)
        rename_conv_action.triggered.connect(lambda: self._rename_conversation(tab_id))
        menu.addAction(rename_conv_action)

        menu.addSeparator()

        # Close action (if not the last tab)
        if len(self.tabs) > 1:
            close_action = QAction("Close Tab", menu)
            close_action.triggered.connect(lambda: self.close_tab(tab_id))
            menu.addAction(close_action)

            # Close others action
            close_others_action = QAction("Close Other Tabs", menu)
            close_others_action.triggered.connect(lambda: self._close_other_tabs(tab_id))
            menu.addAction(close_others_action)

        # Apply theme-aware menu styling
        self._style_menu(menu)

        menu.exec(position)
    
    def _style_menu(self, menu):
        """Apply theme-aware styling to QMenu widgets."""
        try:
            # Try to get theme manager from parent REPL widget
            theme_manager = getattr(self.parent_repl, 'theme_manager', None)
            if not theme_manager:
                return
                
            try:
                from specter.src.ui.themes.theme_manager import THEME_SYSTEM_AVAILABLE
                if not THEME_SYSTEM_AVAILABLE:
                    return
            except ImportError:
                return
            
            colors = theme_manager.current_theme
            if colors:
                from specter.src.ui.themes.style_templates import StyleTemplates
                menu_style = StyleTemplates.get_menu_style(colors)
                menu.setStyleSheet(menu_style)
                
        except Exception as e:
            # Silently handle errors to avoid breaking functionality
            pass
    
    def _show_themed_input_dialog(self, title: str, label: str, default_text: str = ""):
        """Show a themed input dialog matching the app's current theme.

        Returns:
            (text, accepted) tuple matching QInputDialog.getText signature.
        """
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        )

        dlg = QDialog(self.parent_repl)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(340)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl = QLabel(label)
        layout.addWidget(lbl)

        line_edit = QLineEdit(default_text)
        line_edit.selectAll()
        layout.addWidget(line_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # Apply theme styling
        try:
            theme_manager = getattr(self.parent_repl, 'theme_manager', None)
            if theme_manager:
                try:
                    from specter.src.ui.themes.theme_manager import THEME_SYSTEM_AVAILABLE
                    if not THEME_SYSTEM_AVAILABLE:
                        theme_manager = None
                except ImportError:
                    theme_manager = None

            if theme_manager:
                colors = theme_manager.current_theme
                if colors:
                    from specter.src.ui.themes.style_templates import StyleTemplates
                    dlg.setStyleSheet(StyleTemplates.get_dialog_style(colors))

                    from specter.src.presentation.widgets.button_style_manager import ButtonStyleManager
                    ButtonStyleManager.apply_unified_button_style(ok_btn, colors, "dialog", "text", "primary")
                    ButtonStyleManager.apply_unified_button_style(cancel_btn, colors, "dialog", "text", "normal")
        except Exception as e:
            logger.debug(f"Could not apply theme to input dialog: {e}")

        result = dlg.exec()
        return (line_edit.text(), result == QDialog.DialogCode.Accepted)

    def _rename_tab(self, tab_id: str):
        """Rename a tab label (cosmetic only, does NOT persist to conversation DB)."""
        if tab_id not in self.tabs:
            return

        tab = self.tabs[tab_id]
        current_title = getattr(tab, 'full_title', tab.title)

        new_title, ok = self._show_themed_input_dialog(
            "Rename Tab", "Enter new tab label:", current_title
        )

        if ok and new_title.strip():
            title = new_title.strip()
            self.update_tab_title(tab_id, title)
            logger.info(f"Tab {tab_id} label renamed to: {title}")

    def _rename_conversation(self, tab_id: str):
        """Rename the conversation title (persisted to DB, shown in conversation browser)."""
        if tab_id not in self.tabs:
            return

        tab = self.tabs[tab_id]
        conversation_id = tab.conversation_id
        if not conversation_id:
            logger.warning(f"Tab {tab_id} has no conversation to rename")
            return

        current_title = getattr(tab, 'full_title', tab.title)
        new_title, ok = self._show_themed_input_dialog(
            "Rename Conversation", "Enter new conversation title:", current_title
        )

        if ok and new_title.strip():
            title = new_title.strip()
            self._persist_conversation_title(conversation_id, title)
            logger.info(f"Conversation {conversation_id[:8]} renamed to: {title}")

    def _persist_conversation_title(self, conversation_id: str, title: str):
        """Save renamed title to the conversation database."""
        try:
            import asyncio
            from ...infrastructure.ai.ai_service import AIService

            ai_service = AIService.get_instance()
            if ai_service and ai_service.conversation_service:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(
                        ai_service.conversation_service.update_conversation_title(
                            conversation_id, title
                        )
                    )
                    logger.info(f"Persisted conversation title '{title}' for {conversation_id[:8]}")
                finally:
                    loop.close()
        except Exception as e:
            logger.warning(f"Could not persist conversation title: {e}")
    
    def _close_other_tabs(self, keep_tab_id: str):
        """Close all tabs except the specified one."""
        tabs_to_close = [tid for tid in self.tabs.keys() if tid != keep_tab_id]
        for tab_id in tabs_to_close:
            self.close_tab(tab_id)
    
    def refresh_tab_styles(self):
        """Refresh all tab button styles with current theme."""
        for tab_id, tab in self.tabs.items():
            if tab.button:
                is_active = (tab_id == self.active_tab_id)
                self._style_tab_button(tab.button, is_active)
        logger.debug(f"Refreshed all {len(self.tabs)} tab styles with current theme")
    
    def _enhance_tab_style_with_sizing(self, base_style: str) -> str:
        """Enhance tab style with consistent sizing - avoid overriding theme colors."""
        # Only add sizing that doesn't conflict with theme-aware styles
        # The theme-aware styles already include all necessary properties
        return base_style
    
    def _apply_fallback_tab_style(self, button: QPushButton, active: bool):
        """Apply enhanced fallback styling, using theme tab colors when available."""
        # Attempt to read theme tab colors from theme_manager
        theme_manager = getattr(self.parent_repl, 'theme_manager', None)
        colors = None
        if theme_manager and hasattr(theme_manager, 'current_theme'):
            colors = theme_manager.current_theme

        if active:
            if colors:
                bg = getattr(colors, 'tab_active_background_color', 'rgba(120, 120, 120, 0.9)')
                text = getattr(colors, 'tab_active_text_color', '#ffffff')
                hover_bg = getattr(colors, 'interactive_hover', 'rgba(140, 140, 140, 1.0)')
                pressed_bg = getattr(colors, 'interactive_active', 'rgba(100, 100, 100, 1.0)')
            else:
                bg = 'rgba(120, 120, 120, 0.9)'
                text = '#ffffff'
                hover_bg = 'rgba(140, 140, 140, 1.0)'
                pressed_bg = 'rgba(100, 100, 100, 1.0)'

            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg} !important;
                    color: {text} !important;
                    border: none !important;
                    border-radius: 4px;
                    padding: 8px 10px;
                    min-width: 100px;
                    max-width: 200px;
                    height: 36px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 11px;
                    outline: none;
                }}
                QPushButton * {{
                    pointer-events: none;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg} !important;
                    border: none !important;
                    height: 36px !important;
                    cursor: pointer !important;
                }}
                QPushButton:pressed {{
                    background-color: {pressed_bg} !important;
                    border: none !important;
                    height: 36px !important;
                    cursor: pointer !important;
                    padding: 8px 10px !important;
                }}
                QPushButton:focus {{
                    outline: none !important;
                    border: none !important;
                }}
            """)
        else:
            if colors:
                bg = getattr(colors, 'tab_background_color', 'rgba(70, 70, 70, 0.9)')
                text = getattr(colors, 'tab_text_color', 'rgba(240, 240, 240, 0.9)')
                hover_bg = getattr(colors, 'interactive_hover', 'rgba(90, 90, 90, 0.9)')
                hover_text = getattr(colors, 'tab_active_text_color', '#ffffff')
                pressed_bg = getattr(colors, 'interactive_active', 'rgba(50, 50, 50, 1.0)')
            else:
                bg = 'rgba(70, 70, 70, 0.9)'
                text = 'rgba(240, 240, 240, 0.9)'
                hover_bg = 'rgba(90, 90, 90, 0.9)'
                hover_text = '#ffffff'
                pressed_bg = 'rgba(50, 50, 50, 1.0)'

            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg} !important;
                    color: {text} !important;
                    border: none !important;
                    border-radius: 4px;
                    padding: 8px 10px;
                    min-width: 100px;
                    max-width: 200px;
                    height: 36px;
                    cursor: pointer;
                    font-size: 11px;
                    outline: none;
                }}
                QPushButton * {{
                    pointer-events: none;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg} !important;
                    color: {hover_text} !important;
                    border: none !important;
                    height: 36px !important;
                    cursor: pointer !important;
                }}
                QPushButton:pressed {{
                    background-color: {pressed_bg} !important;
                    border: none !important;
                    height: 36px !important;
                    cursor: pointer !important;
                    padding: 8px 10px !important;
                }}
                QPushButton:focus {{
                    outline: none !important;
                    border: none !important;
                }}
            """)

        # Set consistent size constraints for fallback as well
        button.setMinimumSize(100, 36)
        button.setMaximumSize(200, 36)
    
    def cleanup(self):
        """Clean up resources."""
        for tab in self.tabs.values():
            if tab.button:
                tab.button.deleteLater()
        self.tabs.clear()
        self.tab_order.clear()
        logger.info("TabConversationManager cleaned up")