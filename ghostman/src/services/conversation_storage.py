"""Conversation storage and persistence service."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from services.models import SimpleMessage

class ConversationStorage:
    """Handles conversation persistence."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        
        if storage_path:
            self.storage_path = storage_path
        else:
            # Use APPDATA on Windows, fallback to home on other systems
            import os
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.storage_path = Path(appdata) / "Ghostman" / "conversations.json"
            else:
                self.storage_path = Path.home() / ".ghostman" / "conversations.json"
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def save_conversation(self, messages: List[SimpleMessage], session_id: Optional[str] = None) -> str:
        """Save a conversation to storage."""
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Load existing conversations
            conversations = self._load_conversations()
            
            # Convert messages to serializable format
            message_data = []
            for msg in messages:
                message_data.append({
                    'content': msg.content,
                    'is_user': msg.is_user,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Store conversation
            conversations[session_id] = {
                'messages': message_data,
                'created_at': datetime.now().isoformat(),
                'message_count': len(messages)
            }
            
            # Save to file
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Conversation saved with ID: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return ""
    
    def load_conversation(self, session_id: str) -> List[SimpleMessage]:
        """Load a conversation from storage."""
        try:
            conversations = self._load_conversations()
            
            if session_id not in conversations:
                self.logger.warning(f"Conversation {session_id} not found")
                return []
            
            conversation = conversations[session_id]
            messages = []
            
            for msg_data in conversation['messages']:
                message = SimpleMessage(
                    content=msg_data['content'],
                    is_user=msg_data['is_user']
                )
                messages.append(message)
            
            self.logger.info(f"Loaded conversation {session_id} with {len(messages)} messages")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error loading conversation: {e}")
            return []
    
    def list_conversations(self) -> Dict[str, Dict[str, Any]]:
        """List all saved conversations."""
        try:
            conversations = self._load_conversations()
            
            # Return summary info for each conversation
            summaries = {}
            for session_id, data in conversations.items():
                summaries[session_id] = {
                    'created_at': data['created_at'],
                    'message_count': data['message_count'],
                    'preview': self._get_conversation_preview(data['messages'])
                }
            
            return summaries
            
        except Exception as e:
            self.logger.error(f"Error listing conversations: {e}")
            return {}
    
    def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation from storage."""
        try:
            conversations = self._load_conversations()
            
            if session_id in conversations:
                del conversations[session_id]
                
                with open(self.storage_path, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Deleted conversation {session_id}")
                return True
            else:
                self.logger.warning(f"Conversation {session_id} not found for deletion")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False
    
    def _load_conversations(self) -> Dict[str, Dict[str, Any]]:
        """Load all conversations from storage file."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
            
        except Exception as e:
            self.logger.error(f"Error loading conversations file: {e}")
            return {}
    
    def _get_conversation_preview(self, messages: List[Dict]) -> str:
        """Get a preview of the conversation."""
        if not messages:
            return "Empty conversation"
        
        # Get first user message as preview
        for msg in messages:
            if msg['is_user'] and msg['content']:
                preview = msg['content'][:50]
                if len(msg['content']) > 50:
                    preview += "..."
                return preview
        
        return f"{len(messages)} messages"
    
    def cleanup_old_conversations(self, days_to_keep: int = 30):
        """Clean up conversations older than specified days."""
        try:
            conversations = self._load_conversations()
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            to_delete = []
            for session_id, data in conversations.items():
                created_at = datetime.fromisoformat(data['created_at']).timestamp()
                if created_at < cutoff_date:
                    to_delete.append(session_id)
            
            for session_id in to_delete:
                del conversations[session_id]
            
            if to_delete:
                with open(self.storage_path, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Cleaned up {len(to_delete)} old conversations")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up conversations: {e}")
    
    def export_conversations(self, export_path: Path) -> bool:
        """Export all conversations to a file."""
        try:
            conversations = self._load_conversations()
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported conversations to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting conversations: {e}")
            return False