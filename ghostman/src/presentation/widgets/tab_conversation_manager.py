"""
Tab Conversation Manager for Ghostman.

Manages multiple conversation tabs with context switching and state isolation.
"""

import logging
import uuid
from typing import Dict, List, Optional
from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QHBoxLayout, QMenu
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QAction

logger = logging.getLogger("ghostman.tab_conversation_manager")


class ConversationTab:
    """Represents a single conversation tab with its state and UI button."""
    
    def __init__(self, tab_id: str, title: str = "New Conversation"):
        self.tab_id = tab_id
        self.conversation_id: Optional[str] = None
        self.is_active = False
        self.is_modified = False
        self.button: Optional[QPushButton] = None
        
        # Initialize title using the setter to ensure proper truncation
        self.set_title(title)
        
    def set_title(self, title: str):
        """Update tab title and button text with 25 character limit."""
        # Store full title
        self.full_title = title
        
        # Apply 25 character limit or truncate to 23 + "..."
        if len(title) > 25:
            self.title = title[:23] + "..."
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
    tab_switched = pyqtSignal(str)  # tab_id
    tab_created = pyqtSignal(str)   # tab_id
    tab_closed = pyqtSignal(str)    # tab_id
    new_tab_requested = pyqtSignal()
    
    def __init__(self, parent_repl_widget, tab_frame: QFrame, tab_layout: QHBoxLayout, create_initial_tab: bool = True):
        super().__init__()
        self.parent_repl = parent_repl_widget
        self.tab_frame = tab_frame
        self.tab_layout = tab_layout
        
        # Tab management
        self.tabs: Dict[str, ConversationTab] = {}
        self.active_tab_id: Optional[str] = None
        self.tab_order: List[str] = []
        
        # Initialize with first tab if requested
        if create_initial_tab:
            self._create_initial_tab()
        
        logger.info(f"TabConversationManager initialized (initial_tab={create_initial_tab})")
    
    def _create_initial_tab(self):
        """Create the initial default tab."""
        initial_id = f"tab-{str(uuid.uuid4())[:8]}"
        self.create_tab(initial_id, "New Conversation", activate=True)
    
    def create_tab(self, tab_id: str = None, title: str = "New Conversation", activate: bool = True) -> str:
        """Create a new conversation tab."""
        if not tab_id:
            tab_id = f"tab-{str(uuid.uuid4())[:8]}"
        
        # Check if tab already exists
        if tab_id in self.tabs:
            if activate:
                self.switch_to_tab(tab_id)
            return tab_id
        
        # Create tab object
        tab = ConversationTab(tab_id, title)
        
        # Create tab button
        tab_button = QPushButton(title)
        tab_button.setObjectName(f"tab_button_{tab_id}")
        
        # Style the button
        self._style_tab_button(tab_button, active=False)
        
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
        
        # Activate if requested
        if activate:
            self.switch_to_tab(tab_id)
        
        logger.info(f"Created tab: {tab_id} - {title}")
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
        """Switch to a specific tab."""
        if tab_id not in self.tabs:
            logger.warning(f"Tab not found: {tab_id}")
            return
        
        # Update previous active tab styling
        if self.active_tab_id and self.active_tab_id in self.tabs:
            prev_tab = self.tabs[self.active_tab_id]
            if prev_tab.button:
                self._style_tab_button(prev_tab.button, active=False)
            prev_tab.is_active = False
        
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
        
        logger.debug(f"Switched to tab: {tab_id}")
        self.tab_switched.emit(tab_id)
    
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
    
    def _style_tab_button(self, button: QPushButton, active: bool):
        """Apply styling to a tab button."""
        if active:
            # Active tab style (purple)
            button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(147, 112, 219, 0.9);
                    color: white;
                    border: 1px solid rgba(147, 112, 219, 1.0);
                    border-radius: 3px;
                    padding: 4px 12px;
                    min-width: 60px;
                    max-height: 22px;
                }
                QPushButton:hover {
                    background-color: rgba(147, 112, 219, 1.0);
                }
            """)
        else:
            # Inactive tab style (gray)
            button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(60, 60, 60, 0.8);
                    color: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 3px;
                    padding: 4px 12px;
                    min-width: 60px;
                    max-height: 22px;
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 0.9);
                }
            """)
    
    def _show_tab_context_menu(self, tab_id: str, position):
        """Show context menu for tab operations."""
        menu = QMenu()
        
        # Rename action
        rename_action = QAction("Rename Tab", menu)
        rename_action.triggered.connect(lambda: self._rename_tab(tab_id))
        menu.addAction(rename_action)
        
        # Close action (if not the last tab)
        if len(self.tabs) > 1:
            close_action = QAction("Close Tab", menu)
            close_action.triggered.connect(lambda: self.close_tab(tab_id))
            menu.addAction(close_action)
            
            # Close others action
            close_others_action = QAction("Close Other Tabs", menu)
            close_others_action.triggered.connect(lambda: self._close_other_tabs(tab_id))
            menu.addAction(close_others_action)
        
        menu.exec(position)
    
    def _rename_tab(self, tab_id: str):
        """Rename a tab with user input dialog."""
        if tab_id not in self.tabs:
            return
            
        tab = self.tabs[tab_id]
        current_title = getattr(tab, 'full_title', tab.title)
        
        # Show input dialog for new title
        from PyQt6.QtWidgets import QInputDialog
        new_title, ok = QInputDialog.getText(
            self.parent_repl,
            "Rename Tab",
            "Enter new tab name:",
            text=current_title
        )
        
        if ok and new_title.strip():
            self.update_tab_title(tab_id, new_title.strip())
            logger.info(f"Tab {tab_id} renamed to: {new_title.strip()}")
    
    def _close_other_tabs(self, keep_tab_id: str):
        """Close all tabs except the specified one."""
        tabs_to_close = [tid for tid in self.tabs.keys() if tid != keep_tab_id]
        for tab_id in tabs_to_close:
            self.close_tab(tab_id)
    
    def cleanup(self):
        """Clean up resources."""
        for tab in self.tabs.values():
            if tab.button:
                tab.button.deleteLater()
        self.tabs.clear()
        self.tab_order.clear()
        logger.info("TabConversationManager cleaned up")