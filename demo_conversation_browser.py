#!/usr/bin/env python3
"""
Demo script to showcase the Visual Conversation Browser interface.

This script demonstrates the key features of the new conversation browser:
- Modern dark-themed interface with gradient backgrounds
- Rich conversation cards with status badges and metadata
- Grid and list view toggle with smooth transitions
- Real-time search and filtering capabilities
- Interactive cards with hover effects and context menus
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Add the ghostman directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

class MockConversationStatus(Enum):
    """Mock status enum for demo."""
    ACTIVE = "active"
    PINNED = "pinned" 
    ARCHIVED = "archived"

class MockMessageRole(Enum):
    """Mock message role enum for demo."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class MockMessage:
    """Mock message for demo."""
    role: MockMessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass 
class MockMetadata:
    """Mock metadata for demo."""
    tags: set = field(default_factory=set)
    category: str = None

@dataclass
class MockConversation:
    """Mock conversation for demo."""
    id: str
    title: str
    status: MockConversationStatus
    created_at: datetime
    updated_at: datetime
    messages: List[MockMessage] = field(default_factory=list)
    metadata: MockMetadata = field(default_factory=MockMetadata)
    
    def get_message_count(self) -> int:
        return len(self.messages)
    
    def get_token_count(self) -> int:
        return sum(len(msg.content.split()) for msg in self.messages) * 4

class MockConversationManager:
    """Mock conversation manager for demo."""
    
    def __init__(self):
        self.conversations = self._create_demo_conversations()
    
    async def list_conversations(self, limit=None):
        """Mock list conversations method."""
        return self.conversations[:limit] if limit else self.conversations
    
    def _create_demo_conversations(self) -> List[MockConversation]:
        """Create demo conversations with realistic content."""
        conversations = []
        
        # Active conversation with recent activity
        conv1 = MockConversation(
            id="conv-001-demo-active",
            title="🚀 Python Development Help",
            status=MockConversationStatus.ACTIVE,
            created_at=datetime.now() - timedelta(hours=2),
            updated_at=datetime.now() - timedelta(minutes=5),
            metadata=MockMetadata(tags={"python", "coding", "help"})
        )
        conv1.messages = [
            MockMessage(MockMessageRole.USER, "How do I create a proper class structure in Python?"),
            MockMessage(MockMessageRole.ASSISTANT, "Great question! Here's how to create well-structured classes in Python using dataclasses and proper inheritance..."),
            MockMessage(MockMessageRole.USER, "That's really helpful! Can you show me an example with inheritance?"),
            MockMessage(MockMessageRole.ASSISTANT, "Absolutely! Here's a comprehensive example showing class inheritance with proper method overriding...")
        ]
        conversations.append(conv1)
        
        # Pinned conversation
        conv2 = MockConversation(
            id="conv-002-demo-pinned",
            title="⭐ Project Architecture Discussion",
            status=MockConversationStatus.PINNED,
            created_at=datetime.now() - timedelta(days=1),
            updated_at=datetime.now() - timedelta(hours=3),
            metadata=MockMetadata(tags={"architecture", "design", "planning"})
        )
        conv2.messages = [
            MockMessage(MockMessageRole.USER, "I need help designing a scalable architecture for my new application."),
            MockMessage(MockMessageRole.ASSISTANT, "Let's break down your requirements and design a robust architecture. What kind of application are you building?"),
            MockMessage(MockMessageRole.USER, "It's a real-time chat application with conversation management."),
            MockMessage(MockMessageRole.ASSISTANT, "Perfect! For a real-time chat app with conversation management, I recommend a microservices architecture...")
        ]
        conversations.append(conv2)
        
        # Archived conversation
        conv3 = MockConversation(
            id="conv-003-demo-archived", 
            title="📦 Docker Configuration",
            status=MockConversationStatus.ARCHIVED,
            created_at=datetime.now() - timedelta(days=7),
            updated_at=datetime.now() - timedelta(days=3),
            metadata=MockMetadata(tags={"docker", "devops", "containers"})
        )
        conv3.messages = [
            MockMessage(MockMessageRole.USER, "Help me create a Docker configuration for my Python app."),
            MockMessage(MockMessageRole.ASSISTANT, "I'll help you create an efficient Docker setup. Let's start with a Dockerfile...")
        ]
        conversations.append(conv3)
        
        # Add more demo conversations
        for i in range(4, 15):
            conv = MockConversation(
                id=f"conv-{i:03d}-demo",
                title=f"📝 Conversation {i}: {['Machine Learning', 'Web Development', 'Data Analysis', 'API Design', 'UI/UX Design', 'Database Design', 'Security', 'Testing', 'Performance', 'Cloud Services', 'Mobile Development'][i % 11]}",
                status=MockConversationStatus.ACTIVE if i % 3 == 0 else (MockConversationStatus.PINNED if i % 5 == 0 else MockConversationStatus.ARCHIVED),
                created_at=datetime.now() - timedelta(days=i),
                updated_at=datetime.now() - timedelta(hours=i),
                metadata=MockMetadata(tags={f"tag{i}", f"demo{i % 3}", "example"})
            )
            conv.messages = [
                MockMessage(MockMessageRole.USER, f"This is a demo question about topic {i}"),
                MockMessage(MockMessageRole.ASSISTANT, f"This is a demo response for conversation {i} with helpful information...")
            ]
            conversations.append(conv)
        
        return conversations

class DemoMainWindow(QMainWindow):
    """Main demo window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎮 Visual Conversation Browser Demo")
        self.setGeometry(100, 100, 400, 200)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Demo button
        demo_btn = QPushButton("🚀 Launch Visual Conversation Browser")
        demo_btn.setFixedHeight(50)
        demo_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #45a049, stop:1 #3d8b40);
            }
        """)
        demo_btn.clicked.connect(self.launch_browser)
        layout.addWidget(demo_btn)
        
        # Apply dark theme to main window
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
            }
            QWidget {
                color: white;
            }
        """)
    
    def launch_browser(self):
        """Launch the conversation browser."""
        try:
            from infrastructure.conversation_management.ui.conversation_browser import ConversationBrowserDialog
            
            # Create mock conversation manager
            mock_manager = MockConversationManager()
            
            # Create and show browser
            browser = ConversationBrowserDialog(mock_manager, self)
            browser.show()
            browser.raise_()
            browser.activateWindow()
            
        except ImportError as e:
            print(f"Import error: {e}")
            print("Make sure you're running this from the correct directory with ghostman in your path")
        except Exception as e:
            print(f"Error launching browser: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Run the demo application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Conversation Browser Demo")
    
    # Create and show main window
    window = DemoMainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()