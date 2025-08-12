"""
Core conversation data models.
"""

import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from uuid import UUID, uuid4

from .enums import MessageRole, ConversationStatus


@dataclass
class Message:
    """A single message in a conversation."""
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        conversation_id: str,
        role: MessageRole,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Message':
        """Create a new message with generated ID and timestamp."""
        return cls(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            token_count=token_count,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'token_count': self.token_count,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            id=data['id'],
            conversation_id=data['conversation_id'],
            role=MessageRole(data['role']),
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            token_count=data.get('token_count'),
            metadata=data.get('metadata', {})
        )


@dataclass
class ConversationMetadata:
    """Extended metadata for conversations."""
    tags: Set[str] = field(default_factory=set)
    category: Optional[str] = None
    priority: int = 0  # 0=normal, 1=high, -1=low
    estimated_tokens: Optional[int] = None
    model_used: Optional[str] = None
    temperature: Optional[float] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'tags': list(self.tags),
            'category': self.category,
            'priority': self.priority,
            'estimated_tokens': self.estimated_tokens,
            'model_used': self.model_used,
            'temperature': self.temperature,
            'custom_fields': self.custom_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMetadata':
        """Create metadata from dictionary."""
        return cls(
            tags=set(data.get('tags', [])),
            category=data.get('category'),
            priority=data.get('priority', 0),
            estimated_tokens=data.get('estimated_tokens'),
            model_used=data.get('model_used'),
            temperature=data.get('temperature'),
            custom_fields=data.get('custom_fields', {})
        )


@dataclass
class ConversationSummary:
    """AI-generated summary of a conversation."""
    id: str
    conversation_id: str
    summary: str
    key_topics: List[str]
    generated_at: datetime
    model_used: Optional[str] = None
    confidence_score: Optional[float] = None
    
    @classmethod
    def create(
        cls,
        conversation_id: str,
        summary: str,
        key_topics: List[str],
        model_used: Optional[str] = None,
        confidence_score: Optional[float] = None
    ) -> 'ConversationSummary':
        """Create a new conversation summary."""
        return cls(
            id=str(uuid4()),
            conversation_id=conversation_id,
            summary=summary,
            key_topics=key_topics,
            generated_at=datetime.now(),
            model_used=model_used,
            confidence_score=confidence_score
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'summary': self.summary,
            'key_topics': self.key_topics,
            'generated_at': self.generated_at.isoformat(),
            'model_used': self.model_used,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        """Create summary from dictionary."""
        return cls(
            id=data['id'],
            conversation_id=data['conversation_id'],
            summary=data['summary'],
            key_topics=data['key_topics'],
            generated_at=datetime.fromisoformat(data['generated_at']),
            model_used=data.get('model_used'),
            confidence_score=data.get('confidence_score')
        )


@dataclass
class Conversation:
    """A complete conversation with messages and metadata."""
    id: str
    title: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    metadata: ConversationMetadata = field(default_factory=ConversationMetadata)
    summary: Optional[ConversationSummary] = None
    
    @classmethod
    def create(
        cls,
        title: str,
        initial_message: Optional[str] = None,
        metadata: Optional[ConversationMetadata] = None
    ) -> 'Conversation':
        """Create a new conversation with optional initial message."""
        now = datetime.now()
        conversation_id = str(uuid4())
        
        conversation = cls(
            id=conversation_id,
            title=title,
            status=ConversationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            messages=[],
            metadata=metadata or ConversationMetadata()
        )
        
        # Add initial system message if provided
        if initial_message:
            system_message = Message.create(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM,
                content=initial_message
            )
            conversation.messages.append(system_message)
        
        return conversation
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to the conversation."""
        message = Message.create(
            conversation_id=self.id,
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata
        )
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message
    
    def get_message_count(self) -> int:
        """Get total message count."""
        # If messages are loaded, use actual count
        if hasattr(self, 'messages') and self.messages:
            return len(self.messages)
        
        # If we have a cached message count from database, use it
        if hasattr(self, '_message_count'):
            return self._message_count
        
        # Fallback to 0 if no messages loaded and no cached count
        return 0
    
    def get_token_count(self) -> int:
        """Get estimated total token count."""
        return sum(msg.token_count or 0 for msg in self.messages)
    
    def get_messages_by_role(self, role: MessageRole) -> List[Message]:
        """Get all messages by role."""
        return [msg for msg in self.messages if msg.role == role]
    
    def get_latest_message(self) -> Optional[Message]:
        """Get the most recent message."""
        return self.messages[-1] if self.messages else None
    
    def to_api_format(self) -> List[Dict[str, str]]:
        """Convert messages to OpenAI API format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.messages
        ]
    
    def to_dict(self, include_messages: bool = True) -> Dict[str, Any]:
        """Convert conversation to dictionary."""
        result = {
            'id': self.id,
            'title': self.title,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata.to_dict()
        }
        
        if include_messages:
            result['messages'] = [msg.to_dict() for msg in self.messages]
        
        if self.summary:
            result['summary'] = self.summary.to_dict()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create conversation from dictionary."""
        conversation = cls(
            id=data['id'],
            title=data['title'],
            status=ConversationStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=ConversationMetadata.from_dict(data.get('metadata', {}))
        )
        
        # Load messages if present
        if 'messages' in data:
            conversation.messages = [
                Message.from_dict(msg_data) 
                for msg_data in data['messages']
            ]
        
        # Load summary if present
        if 'summary' in data:
            conversation.summary = ConversationSummary.from_dict(data['summary'])
            
        return conversation
    
    def archive(self):
        """Archive this conversation."""
        self.status = ConversationStatus.ARCHIVED
        self.updated_at = datetime.now()
    
    def pin(self):
        """Pin this conversation."""
        self.status = ConversationStatus.PINNED
        self.updated_at = datetime.now()
        
    def delete(self):
        """Mark conversation as deleted.""" 
        self.status = ConversationStatus.DELETED
        self.updated_at = datetime.now()
    
    def restore(self):
        """Restore conversation to active status."""
        self.status = ConversationStatus.ACTIVE
        self.updated_at = datetime.now()
        
    def update_title(self, new_title: str):
        """Update conversation title."""
        self.title = new_title
        self.updated_at = datetime.now()
        
    def add_tags(self, *tags: str):
        """Add tags to conversation."""
        self.metadata.tags.update(tags)
        self.updated_at = datetime.now()
        
    def remove_tags(self, *tags: str):
        """Remove tags from conversation."""
        self.metadata.tags.difference_update(tags)
        self.updated_at = datetime.now()
        
    def set_category(self, category: str):
        """Set conversation category."""
        self.metadata.category = category
        self.updated_at = datetime.now()
        
    def set_priority(self, priority: int):
        """Set conversation priority (-1=low, 0=normal, 1=high)."""
        self.metadata.priority = max(-1, min(1, priority))
        self.updated_at = datetime.now()
    
    def generate_auto_title(self, max_length: int = 50) -> str:
        """Generate automatic title from first user message."""
        user_messages = self.get_messages_by_role(MessageRole.USER)
        if not user_messages:
            return "New Conversation"
            
        first_user_msg = user_messages[0].content.strip()
        if len(first_user_msg) <= max_length:
            return first_user_msg
        
        # Truncate and add ellipsis
        return first_user_msg[:max_length-3] + "..."