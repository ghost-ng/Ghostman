"""
Advanced features for conversation management system.

Includes templates, favorites, analytics, and other enhanced features.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

from ..models.conversation import Conversation, ConversationMetadata
from ..models.enums import ConversationStatus, MessageRole
from ..repositories.conversation_repository import ConversationRepository

logger = logging.getLogger("specter.advanced_features")


@dataclass
class ConversationTemplate:
    """Template for creating conversations with predefined settings."""
    id: str
    name: str
    description: str
    system_prompt: Optional[str] = None
    initial_tags: Set[str] = field(default_factory=set)
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'initial_tags': list(self.initial_tags),
            'category': self.category,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'usage_count': self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTemplate':
        """Create template from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            system_prompt=data.get('system_prompt'),
            initial_tags=set(data.get('initial_tags', [])),
            category=data.get('category'),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            usage_count=data.get('usage_count', 0)
        )


@dataclass
class ConversationAnalytics:
    """Analytics data for conversations."""
    total_conversations: int
    active_conversations: int
    archived_conversations: int
    deleted_conversations: int
    pinned_conversations: int
    total_messages: int
    total_tokens: int
    avg_messages_per_conversation: float
    avg_tokens_per_conversation: float
    most_active_days: List[Dict[str, Any]]
    most_used_tags: List[Dict[str, Any]]
    conversation_length_distribution: Dict[str, int]
    daily_activity: List[Dict[str, Any]]
    top_conversations: List[Dict[str, Any]]
    model_usage: Dict[str, int]
    generated_at: datetime = field(default_factory=datetime.now)


class ConversationTemplateService:
    """Service for managing conversation templates."""
    
    DEFAULT_TEMPLATES = [
        {
            'id': 'general_chat',
            'name': 'General Chat',
            'description': 'General conversation with AI assistant',
            'system_prompt': 'You are a helpful AI assistant. Be conversational and friendly.',
            'initial_tags': {'general', 'chat'},
            'category': 'general'
        },
        {
            'id': 'coding_help',
            'name': 'Coding Assistant',
            'description': 'Get help with programming and coding tasks',
            'system_prompt': 'You are an expert programming assistant. Help with code, debugging, and technical questions.',
            'initial_tags': {'coding', 'programming', 'tech'},
            'category': 'development'
        },
        {
            'id': 'creative_writing',
            'name': 'Creative Writing',
            'description': 'Creative writing and storytelling assistance',
            'system_prompt': 'You are a creative writing assistant. Help with stories, poems, and creative content.',
            'initial_tags': {'creative', 'writing', 'stories'},
            'category': 'creative'
        },
        {
            'id': 'research_analysis',
            'name': 'Research & Analysis',
            'description': 'Research assistance and data analysis',
            'system_prompt': 'You are a research assistant. Help with analysis, fact-checking, and information gathering.',
            'initial_tags': {'research', 'analysis', 'facts'},
            'category': 'research'
        }
    ]
    
    def __init__(self, settings_dir: Path):
        """Initialize template service."""
        self.settings_dir = settings_dir
        self.templates_file = settings_dir / "conversation_templates.json"
        self.templates: Dict[str, ConversationTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from file."""
        try:
            if self.templates_file.exists():
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_data in data.get('templates', []):
                        template = ConversationTemplate.from_dict(template_data)
                        self.templates[template.id] = template
                
                logger.info(f"Loaded {len(self.templates)} conversation templates")
            else:
                # Create default templates
                self._create_default_templates()
                
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default templates."""
        from uuid import uuid4
        
        for template_data in self.DEFAULT_TEMPLATES:
            template = ConversationTemplate(
                id=template_data['id'],
                name=template_data['name'],
                description=template_data['description'],
                system_prompt=template_data.get('system_prompt'),
                initial_tags=set(template_data.get('initial_tags', [])),
                category=template_data.get('category')
            )
            self.templates[template.id] = template
        
        self._save_templates()
        logger.info(f"Created {len(self.DEFAULT_TEMPLATES)} default templates")
    
    def _save_templates(self):
        """Save templates to file."""
        try:
            data = {
                'templates': [template.to_dict() for template in self.templates.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
    
    def get_all_templates(self) -> List[ConversationTemplate]:
        """Get all available templates."""
        return list(self.templates.values())
    
    def get_template(self, template_id: str) -> Optional[ConversationTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def create_conversation_from_template(self, template_id: str, title: str) -> Optional[Conversation]:
        """Create a conversation from a template."""
        template = self.get_template(template_id)
        if not template:
            return None
        
        # Create metadata
        metadata = ConversationMetadata(
            tags=template.initial_tags.copy(),
            category=template.category,
            custom_fields=template.metadata.copy()
        )
        
        # Create conversation
        conversation = Conversation.create(
            title=title,
            initial_message=template.system_prompt,
            metadata=metadata
        )
        
        # Update template usage
        template.usage_count += 1
        self._save_templates()
        
        logger.info(f"Created conversation from template: {template.name}")
        return conversation


class ConversationFavoriteService:
    """Service for managing favorite conversations."""
    
    def __init__(self, repository: ConversationRepository, settings_dir: Path):
        """Initialize favorites service."""
        self.repository = repository
        self.settings_dir = settings_dir
        self.favorites_file = settings_dir / "conversation_favorites.json"
        self.favorites: Set[str] = set()
        self._load_favorites()
    
    def _load_favorites(self):
        """Load favorites from file."""
        try:
            if self.favorites_file.exists():
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.favorites = set(data.get('favorites', []))
                    
                logger.info(f"Loaded {len(self.favorites)} favorite conversations")
                
        except Exception as e:
            logger.error(f"Failed to load favorites: {e}")
            self.favorites = set()
    
    def _save_favorites(self):
        """Save favorites to file."""
        try:
            data = {
                'favorites': list(self.favorites),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save favorites: {e}")
    
    def add_favorite(self, conversation_id: str):
        """Add conversation to favorites."""
        self.favorites.add(conversation_id)
        self._save_favorites()
        logger.info(f"Added conversation to favorites: {conversation_id}")
    
    def remove_favorite(self, conversation_id: str):
        """Remove conversation from favorites."""
        self.favorites.discard(conversation_id)
        self._save_favorites()
        logger.info(f"Removed conversation from favorites: {conversation_id}")
    
    def is_favorite(self, conversation_id: str) -> bool:
        """Check if conversation is a favorite."""
        return conversation_id in self.favorites
    
    def get_favorite_count(self) -> int:
        """Get number of favorite conversations."""
        return len(self.favorites)
    
    async def get_favorite_conversations(self) -> List[Conversation]:
        """Get all favorite conversations."""
        conversations = []
        
        for conv_id in self.favorites:
            conversation = await self.repository.get_conversation(conv_id, include_messages=False)
            if conversation:
                conversations.append(conversation)
        
        # Sort by updated date
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations


class ConversationAnalyticsService:
    """Service for generating conversation analytics."""
    
    def __init__(self, repository: ConversationRepository):
        """Initialize analytics service."""
        self.repository = repository
    
    async def generate_analytics(self) -> ConversationAnalytics:
        """Generate comprehensive conversation analytics."""
        try:
            # Get all conversations for analysis
            all_conversations = await self.repository.list_conversations(limit=None)
            
            # Basic counts
            total_conversations = len(all_conversations)
            status_counts = {}
            total_messages = 0
            total_tokens = 0
            
            # Collect data
            conversation_lengths = []
            daily_activity = {}
            tag_usage = {}
            model_usage = {}
            top_conversations_by_messages = []
            
            for conv in all_conversations:
                # Status counting
                status = conv.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Message and token counting
                msg_count = conv.get_message_count()
                token_count = conv.get_token_count()
                total_messages += msg_count
                total_tokens += token_count
                
                conversation_lengths.append(msg_count)
                
                # Top conversations
                top_conversations_by_messages.append({
                    'id': conv.id,
                    'title': conv.title,
                    'message_count': msg_count,
                    'token_count': token_count
                })
                
                # Daily activity
                date_key = conv.created_at.date().isoformat()
                daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
                
                # Tag usage
                for tag in conv.metadata.tags:
                    tag_usage[tag] = tag_usage.get(tag, 0) + 1
                
                # Model usage (if available)
                model = conv.metadata.model_used
                if model:
                    model_usage[model] = model_usage.get(model, 0) + 1
            
            # Calculate averages
            avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
            avg_tokens = total_tokens / total_conversations if total_conversations > 0 else 0
            
            # Sort top conversations
            top_conversations_by_messages.sort(key=lambda x: x['message_count'], reverse=True)
            top_conversations_by_messages = top_conversations_by_messages[:10]
            
            # Conversation length distribution
            length_distribution = {}
            for length in conversation_lengths:
                if length == 0:
                    bucket = "0"
                elif length <= 5:
                    bucket = "1-5"
                elif length <= 10:
                    bucket = "6-10"
                elif length <= 20:
                    bucket = "11-20"
                elif length <= 50:
                    bucket = "21-50"
                else:
                    bucket = "50+"
                
                length_distribution[bucket] = length_distribution.get(bucket, 0) + 1
            
            # Most active days (last 30 days)
            recent_activity = []
            today = datetime.now().date()
            for i in range(30):
                date = today - timedelta(days=i)
                date_key = date.isoformat()
                count = daily_activity.get(date_key, 0)
                recent_activity.append({
                    'date': date_key,
                    'conversation_count': count
                })
            
            recent_activity.reverse()  # Show oldest to newest
            
            # Most used tags
            most_used_tags = [
                {'tag': tag, 'usage_count': count}
                for tag, count in sorted(tag_usage.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Create analytics object
            analytics = ConversationAnalytics(
                total_conversations=total_conversations,
                active_conversations=status_counts.get('active', 0),
                archived_conversations=status_counts.get('archived', 0),
                deleted_conversations=status_counts.get('deleted', 0),
                pinned_conversations=status_counts.get('pinned', 0),
                total_messages=total_messages,
                total_tokens=total_tokens,
                avg_messages_per_conversation=round(avg_messages, 2),
                avg_tokens_per_conversation=round(avg_tokens, 2),
                most_active_days=recent_activity,
                most_used_tags=most_used_tags,
                conversation_length_distribution=length_distribution,
                daily_activity=recent_activity,
                top_conversations=top_conversations_by_messages,
                model_usage=model_usage
            )
            
            logger.info("✓ Generated conversation analytics")
            return analytics
            
        except Exception as e:
            logger.error(f"✗ Failed to generate analytics: {e}")
            # Return empty analytics
            return ConversationAnalytics(
                total_conversations=0,
                active_conversations=0,
                archived_conversations=0,
                deleted_conversations=0,
                pinned_conversations=0,
                total_messages=0,
                total_tokens=0,
                avg_messages_per_conversation=0.0,
                avg_tokens_per_conversation=0.0,
                most_active_days=[],
                most_used_tags=[],
                conversation_length_distribution={},
                daily_activity=[],
                top_conversations=[],
                model_usage={}
            )


class AdvancedFeaturesManager:
    """Manager for all advanced conversation features."""
    
    def __init__(self, repository: ConversationRepository, settings_dir: Path):
        """Initialize advanced features manager."""
        self.repository = repository
        self.settings_dir = settings_dir
        
        # Initialize services
        self.templates = ConversationTemplateService(settings_dir)
        self.favorites = ConversationFavoriteService(repository, settings_dir)
        self.analytics = ConversationAnalyticsService(repository)
        
        logger.info("AdvancedFeaturesManager initialized")
    
    # Template methods
    def get_templates(self) -> List[ConversationTemplate]:
        """Get all conversation templates."""
        return self.templates.get_all_templates()
    
    def create_from_template(self, template_id: str, title: str) -> Optional[Conversation]:
        """Create conversation from template."""
        return self.templates.create_conversation_from_template(template_id, title)
    
    # Favorites methods
    def add_favorite(self, conversation_id: str):
        """Add conversation to favorites."""
        self.favorites.add_favorite(conversation_id)
    
    def remove_favorite(self, conversation_id: str):
        """Remove conversation from favorites."""
        self.favorites.remove_favorite(conversation_id)
    
    def is_favorite(self, conversation_id: str) -> bool:
        """Check if conversation is favorite."""
        return self.favorites.is_favorite(conversation_id)
    
    async def get_favorites(self) -> List[Conversation]:
        """Get favorite conversations."""
        return await self.favorites.get_favorite_conversations()
    
    # Analytics methods
    async def get_analytics(self) -> ConversationAnalytics:
        """Get conversation analytics."""
        return await self.analytics.generate_analytics()
    
    # Combined features
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data combining all features."""
        analytics = await self.get_analytics()
        favorites = await self.get_favorites()
        templates = self.get_templates()
        
        return {
            'analytics': analytics,
            'favorite_count': len(favorites),
            'recent_favorites': favorites[:5],
            'template_count': len(templates),
            'most_used_templates': sorted(templates, key=lambda t: t.usage_count, reverse=True)[:5]
        }