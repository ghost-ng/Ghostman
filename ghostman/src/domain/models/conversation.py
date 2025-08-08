"""Conversation domain models with token management."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import tiktoken

class TokenCounter:
    """Utility class for accurate token counting."""
    
    _encoders = {}
    
    @classmethod
    def get_encoder(cls, model: str = "gpt-3.5-turbo"):
        """Get or create encoder for model."""
        if model not in cls._encoders:
            try:
                cls._encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base for unknown models
                cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
        return cls._encoders[model]
    
    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count tokens in text for specified model."""
        if not text:
            return 0
        encoder = cls.get_encoder(model)
        return len(encoder.encode(text))
    
    @classmethod
    def count_message_tokens(cls, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
        """Count tokens in a list of messages."""
        encoder = cls.get_encoder(model)
        
        # Token overhead per message (role, content structure)
        tokens_per_message = 3
        tokens_per_name = 1
        
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(encoder.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        
        # Every reply is primed with <|start|>assistant<|message|>
        num_tokens += 3
        
        return num_tokens

class Message(BaseModel):
    """Individual message in a conversation."""
    
    id: UUID = Field(default_factory=uuid4)
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional fields for memory management
    importance_score: float = Field(default=1.0, ge=0.0, le=10.0)
    is_summary: bool = Field(default=False)
    summarized_message_ids: List[UUID] = Field(default_factory=list)
    
    def calculate_tokens(self, model: str = "gpt-3.5-turbo") -> int:
        """Calculate and cache token count."""
        self.token_count = TokenCounter.count_tokens(self.content, model)
        return self.token_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "role": self.role,
            "content": self.content
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class Conversation(BaseModel):
    """Complete conversation with memory management."""
    
    id: UUID = Field(default_factory=uuid4)
    title: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Token management
    max_tokens: int = Field(default=4000, ge=1000, le=128000)
    model: str = Field(default="gpt-3.5-turbo")
    current_token_count: int = Field(default=0)
    
    # Memory management settings
    memory_strategy: str = Field(default="sliding_window")  # sliding_window, summarization, hybrid
    window_size: int = Field(default=10)  # For sliding window
    summary_threshold: int = Field(default=2000)  # Tokens before summarization
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add a message to the conversation."""
        message = Message(role=role, content=content, **kwargs)
        message.calculate_tokens(self.model)
        
        self.messages.append(message)
        self.current_token_count += message.token_count or 0
        self.updated_at = datetime.utcnow()
        
        # Check if memory management is needed
        if self.current_token_count > self.max_tokens:
            self.manage_memory()
        
        return message
    
    def manage_memory(self) -> None:
        """Apply memory management strategy."""
        if self.memory_strategy == "sliding_window":
            self._apply_sliding_window()
        elif self.memory_strategy == "summarization":
            self._apply_summarization()
        elif self.memory_strategy == "hybrid":
            self._apply_hybrid_strategy()
    
    def _apply_sliding_window(self) -> None:
        """Keep only recent messages within window."""
        if len(self.messages) <= self.window_size:
            return
        
        # Keep system messages and recent messages
        system_messages = [m for m in self.messages if m.role == "system"]
        recent_messages = self.messages[-self.window_size:]
        
        self.messages = system_messages + recent_messages
        self._recalculate_tokens()
    
    def _apply_summarization(self) -> None:
        """Summarize older messages when threshold exceeded."""
        if self.current_token_count <= self.summary_threshold:
            return
        
        # Find messages to summarize (keep recent ones)
        messages_to_keep = []
        messages_to_summarize = []
        recent_tokens = 0
        
        for message in reversed(self.messages):
            if recent_tokens < self.max_tokens // 2:
                messages_to_keep.insert(0, message)
                recent_tokens += message.token_count or 0
            else:
                messages_to_summarize.insert(0, message)
        
        if messages_to_summarize:
            # Create summary (placeholder - would use AI in production)
            summary = self._create_summary(messages_to_summarize)
            self.messages = [summary] + messages_to_keep
            self._recalculate_tokens()
    
    def _apply_hybrid_strategy(self) -> None:
        """Combine sliding window with summarization."""
        # First apply summarization to older messages
        if self.current_token_count > self.summary_threshold:
            self._apply_summarization()
        
        # Then apply sliding window to recent messages
        if len(self.messages) > self.window_size:
            self._apply_sliding_window()
    
    def _create_summary(self, messages: List[Message]) -> Message:
        """Create a summary message from multiple messages."""
        # In production, this would call the AI API to generate a summary
        summary_content = f"[Summary of {len(messages)} previous messages]\n"
        summary_content += "Key points discussed:\n"
        
        # Extract key points (simplified version)
        for msg in messages[-3:]:  # Last 3 messages as example
            if msg.role != "system":
                summary_content += f"- {msg.role}: {msg.content[:50]}...\n"
        
        summary_message = Message(
            role="system",
            content=summary_content,
            is_summary=True,
            summarized_message_ids=[m.id for m in messages]
        )
        summary_message.calculate_tokens(self.model)
        
        return summary_message
    
    def _recalculate_tokens(self) -> None:
        """Recalculate total token count."""
        self.current_token_count = sum(
            m.token_count or 0 for m in self.messages
        )
    
    def get_context_messages(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get messages formatted for API call within token limit."""
        max_tokens = max_tokens or self.max_tokens
        
        result = []
        token_count = 0
        
        # Always include system messages first
        for message in self.messages:
            if message.role == "system":
                result.append(message.to_dict())
                token_count += message.token_count or 0
        
        # Add other messages in reverse order (most recent first)
        for message in reversed(self.messages):
            if message.role != "system":
                message_tokens = message.token_count or 0
                if token_count + message_tokens <= max_tokens:
                    result.insert(len([m for m in result if m['role'] == 'system']), 
                                message.to_dict())
                    token_count += message_tokens
                else:
                    break
        
        return result
    
    def estimate_response_tokens(self) -> int:
        """Estimate tokens needed for AI response."""
        # Use historical average or heuristic
        avg_response_tokens = 150
        
        # Adjust based on recent message patterns
        recent_assistant_messages = [
            m for m in self.messages[-5:] 
            if m.role == "assistant"
        ]
        
        if recent_assistant_messages:
            avg_response_tokens = sum(
                m.token_count or 0 for m in recent_assistant_messages
            ) // len(recent_assistant_messages)
        
        return min(avg_response_tokens * 2, 500)  # Cap at 500 tokens
    
    def can_fit_response(self) -> bool:
        """Check if there's room for an AI response."""
        estimated_response = self.estimate_response_tokens()
        return self.current_token_count + estimated_response <= self.max_tokens
    
    def generate_title(self) -> str:
        """Generate a title from the first user message."""
        if self.title:
            return self.title
        
        for message in self.messages:
            if message.role == "user":
                # Use first 50 characters of first user message
                self.title = message.content[:50]
                if len(message.content) > 50:
                    self.title += "..."
                return self.title
        
        self.title = f"Conversation {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        return self.title
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }