"""
Search models for conversation management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from .enums import ConversationStatus, SortOrder, SearchScope


@dataclass
class SearchQuery:
    """Search query parameters."""
    text: Optional[str] = None
    scope: SearchScope = SearchScope.ALL
    tags: Set[str] = field(default_factory=set)
    category: Optional[str] = None
    status: Optional[ConversationStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    min_messages: Optional[int] = None
    max_messages: Optional[int] = None
    priority: Optional[int] = None
    has_summary: Optional[bool] = None
    model_used: Optional[str] = None
    sort_order: SortOrder = SortOrder.UPDATED_DESC
    limit: Optional[int] = None
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search query to dictionary."""
        return {
            'text': self.text,
            'scope': self.scope.value,
            'tags': list(self.tags),
            'category': self.category,
            'status': self.status.value if self.status else None,
            'created_after': self.created_after.isoformat() if self.created_after else None,
            'created_before': self.created_before.isoformat() if self.created_before else None,
            'updated_after': self.updated_after.isoformat() if self.updated_after else None,
            'updated_before': self.updated_before.isoformat() if self.updated_before else None,
            'min_messages': self.min_messages,
            'max_messages': self.max_messages,
            'priority': self.priority,
            'has_summary': self.has_summary,
            'model_used': self.model_used,
            'sort_order': self.sort_order.value,
            'limit': self.limit,
            'offset': self.offset
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchQuery':
        """Create search query from dictionary."""
        query = cls(
            text=data.get('text'),
            scope=SearchScope(data.get('scope', SearchScope.ALL.value)),
            tags=set(data.get('tags', [])),
            category=data.get('category'),
            min_messages=data.get('min_messages'),
            max_messages=data.get('max_messages'),
            priority=data.get('priority'),
            has_summary=data.get('has_summary'),
            model_used=data.get('model_used'),
            sort_order=SortOrder(data.get('sort_order', SortOrder.UPDATED_DESC.value)),
            limit=data.get('limit'),
            offset=data.get('offset', 0)
        )
        
        # Handle status
        if data.get('status'):
            query.status = ConversationStatus(data['status'])
        
        # Handle dates
        for date_field in ['created_after', 'created_before', 'updated_after', 'updated_before']:
            if data.get(date_field):
                setattr(query, date_field, datetime.fromisoformat(data[date_field]))
        
        return query
    
    @classmethod
    def create_simple_text_search(cls, text: str, limit: Optional[int] = None) -> 'SearchQuery':
        """Create a simple text search query."""
        return cls(text=text, scope=SearchScope.ALL, limit=limit)
    
    @classmethod
    def create_tag_search(cls, tags: Set[str]) -> 'SearchQuery':
        """Create a tag-based search query."""
        return cls(tags=tags)
    
    @classmethod
    def create_recent_search(cls, days: int = 7, limit: Optional[int] = None) -> 'SearchQuery':
        """Create a search for recent conversations."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        return cls(updated_after=cutoff, sort_order=SortOrder.UPDATED_DESC, limit=limit)


@dataclass
class SearchResult:
    """Search result with metadata."""
    conversation_id: str
    title: str
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None
    match_count: int = 0
    matched_fields: List[str] = field(default_factory=list)
    highlighted_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            'conversation_id': self.conversation_id,
            'title': self.title,
            'snippet': self.snippet,
            'relevance_score': self.relevance_score,
            'match_count': self.match_count,
            'matched_fields': self.matched_fields,
            'highlighted_text': self.highlighted_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create search result from dictionary."""
        return cls(
            conversation_id=data['conversation_id'],
            title=data['title'],
            snippet=data.get('snippet'),
            relevance_score=data.get('relevance_score'),
            match_count=data.get('match_count', 0),
            matched_fields=data.get('matched_fields', []),
            highlighted_text=data.get('highlighted_text')
        )


@dataclass
class SearchResults:
    """Collection of search results with metadata."""
    results: List[SearchResult]
    total_count: int
    query_time_ms: Optional[float] = None
    offset: int = 0
    limit: Optional[int] = None
    
    @property
    def has_more(self) -> bool:
        """Check if there are more results available."""
        if self.limit is None:
            return False
        return (self.offset + len(self.results)) < self.total_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search results to dictionary."""
        return {
            'results': [result.to_dict() for result in self.results],
            'total_count': self.total_count,
            'query_time_ms': self.query_time_ms,
            'offset': self.offset,
            'limit': self.limit,
            'has_more': self.has_more
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResults':
        """Create search results from dictionary."""
        return cls(
            results=[SearchResult.from_dict(r) for r in data['results']],
            total_count=data['total_count'],
            query_time_ms=data.get('query_time_ms'),
            offset=data.get('offset', 0),
            limit=data.get('limit')
        )