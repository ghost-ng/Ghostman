"""
Conversation-Aware RAG Pipeline

Integrates RAG capabilities with existing conversation management system.
Provides context-aware retrieval, query rewriting, and document management.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from ...conversation_management.models.conversation import Conversation, Message
from ...conversation_management.models.enums import MessageRole
from ...conversation_management.services.conversation_service import ConversationService
from ...rag_pipeline.pipeline.rag_pipeline import RAGPipeline, RAGQuery, RAGResponse
from ...rag_pipeline.config.rag_config import RAGPipelineConfig

logger = logging.getLogger("specter.conversation_rag")


@dataclass
class ConversationContext:
    """Context for a conversation including documents and history."""
    conversation_id: str
    document_ids: List[str] = field(default_factory=list)
    document_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    max_history_length: int = 10
    include_system_messages: bool = False
    
    def add_document(self, doc_id: str, metadata: Dict[str, Any]):
        """Add a document to the conversation context."""
        if doc_id not in self.document_ids:
            self.document_ids.append(doc_id)
        self.document_metadata[doc_id] = metadata
    
    def remove_document(self, doc_id: str):
        """Remove a document from the conversation context."""
        if doc_id in self.document_ids:
            self.document_ids.remove(doc_id)
        self.document_metadata.pop(doc_id, None)
    
    def get_active_documents(self) -> List[str]:
        """Get list of active document IDs."""
        return self.document_ids.copy()


@dataclass 
class QueryRewriteResult:
    """Result of query rewriting operation."""
    original_query: str
    rewritten_query: str
    context_used: List[str]
    confidence: float
    reasoning: Optional[str] = None


class ConversationRAGPipeline:
    """
    RAG Pipeline enhanced with conversation awareness.
    
    Features:
    - Query rewriting based on conversation history
    - Document context management per conversation
    - Streaming response generation
    - Source attribution and tracking
    """
    
    def __init__(
        self, 
        rag_pipeline: RAGPipeline,
        conversation_service: ConversationService,
        config: Optional[RAGPipelineConfig] = None
    ):
        """Initialize conversation-aware RAG pipeline."""
        self.rag_pipeline = rag_pipeline
        self.conversation_service = conversation_service
        self.config = config or RAGPipelineConfig()
        
        # Conversation contexts
        self._contexts: Dict[str, ConversationContext] = {}
        
        # Document tracking
        self._document_conversations: Dict[str, List[str]] = {}  # doc_id -> [conv_ids]
        
        logger.info("ConversationRAGPipeline initialized")
    
    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get or create context for a conversation."""
        if conversation_id not in self._contexts:
            self._contexts[conversation_id] = ConversationContext(conversation_id)
        return self._contexts[conversation_id]
    
    async def add_document_to_conversation(
        self, 
        conversation_id: str,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a document to a conversation context.
        
        Args:
            conversation_id: ID of the conversation
            file_path: Path to the document
            metadata: Optional metadata for the document
            
        Returns:
            Document ID
        """
        try:
            # Get conversation context
            context = self.get_or_create_context(conversation_id)
            
            # Process document through RAG pipeline
            file_path = Path(file_path)
            doc_metadata = metadata or {}
            doc_metadata.update({
                'conversation_id': conversation_id,
                'filename': file_path.name,
                'added_at': datetime.now().isoformat()
            })
            
            # Ingest document
            doc_id = await self.rag_pipeline.ingest_document(
                source=str(file_path),
                metadata_override=doc_metadata
            )
            
            # Add to conversation context
            context.add_document(doc_id, doc_metadata)
            
            # Track document-conversation mapping
            if doc_id not in self._document_conversations:
                self._document_conversations[doc_id] = []
            if conversation_id not in self._document_conversations[doc_id]:
                self._document_conversations[doc_id].append(conversation_id)
            
            # Add system message to conversation
            conversation = await self.conversation_service.get_conversation(
                conversation_id, 
                include_messages=False
            )
            if conversation:
                await self.conversation_service.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.SYSTEM,
                    content=f"📎 Document added: {file_path.name}",
                    metadata={'document_id': doc_id, 'action': 'document_added'}
                )
            
            logger.info(f"Added document {doc_id} to conversation {conversation_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document to conversation: {e}")
            raise
    
    async def remove_document_from_conversation(
        self,
        conversation_id: str,
        document_id: str
    ) -> bool:
        """Remove a document from conversation context."""
        try:
            context = self.get_or_create_context(conversation_id)
            context.remove_document(document_id)
            
            # Update tracking
            if document_id in self._document_conversations:
                convs = self._document_conversations[document_id]
                if conversation_id in convs:
                    convs.remove(conversation_id)
                if not convs:
                    # No conversations using this document, can delete from vector store
                    await self.rag_pipeline.delete_document(document_id)
                    del self._document_conversations[document_id]
            
            # Add system message
            await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM,
                content=f"📎 Document removed: {document_id}",
                metadata={'document_id': document_id, 'action': 'document_removed'}
            )
            
            logger.info(f"Removed document {document_id} from conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove document: {e}")
            return False
    
    async def rewrite_query_with_history(
        self,
        conversation_id: str,
        query: str
    ) -> QueryRewriteResult:
        """
        Rewrite query based on conversation history.
        
        Uses conversation history to provide context and rewrite
        queries for better retrieval.
        """
        try:
            # Get conversation with recent messages
            conversation = await self.conversation_service.get_conversation(
                conversation_id,
                include_messages=True
            )
            
            if not conversation:
                return QueryRewriteResult(
                    original_query=query,
                    rewritten_query=query,
                    context_used=[],
                    confidence=1.0
                )
            
            # Get recent message history
            context = self.get_or_create_context(conversation_id)
            recent_messages = conversation.messages[-context.max_history_length:]
            
            # Filter messages based on settings
            if not context.include_system_messages:
                recent_messages = [
                    msg for msg in recent_messages 
                    if msg.role != MessageRole.SYSTEM
                ]
            
            # Build context for rewriting
            history_context = self._build_history_context(recent_messages)
            
            if not history_context:
                return QueryRewriteResult(
                    original_query=query,
                    rewritten_query=query,
                    context_used=[],
                    confidence=1.0
                )
            
            # Use LLM to rewrite query
            rewrite_prompt = self._build_rewrite_prompt(query, history_context)
            
            # Call LLM for rewriting
            rewritten = await self._call_llm_for_rewrite(rewrite_prompt)
            
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten.get('query', query),
                context_used=[msg.id for msg in recent_messages],
                confidence=rewritten.get('confidence', 0.8),
                reasoning=rewritten.get('reasoning')
            )
            
        except Exception as e:
            logger.error(f"Failed to rewrite query: {e}")
            # Fallback to original query
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=query,
                context_used=[],
                confidence=0.5
            )
    
    async def query_with_conversation_context(
        self,
        conversation_id: str,
        query: str,
        use_history: bool = True,
        use_documents: bool = True,
        rewrite_query: bool = True
    ) -> RAGResponse:
        """
        Process query with full conversation context.
        
        Args:
            conversation_id: Conversation ID
            query: User query
            use_history: Include conversation history
            use_documents: Use conversation documents
            rewrite_query: Rewrite query based on history
            
        Returns:
            RAG response with context
        """
        try:
            # Rewrite query if enabled
            if rewrite_query and use_history:
                rewrite_result = await self.rewrite_query_with_history(
                    conversation_id, 
                    query
                )
                processed_query = rewrite_result.rewritten_query
                logger.info(f"Query rewritten: '{query}' -> '{processed_query}'")
            else:
                processed_query = query
            
            # Get conversation context
            context = self.get_or_create_context(conversation_id)
            
            # Build filters for document retrieval
            filters = None
            if use_documents and context.document_ids:
                filters = {'document_id': {'$in': context.document_ids}}
            
            # Create RAG query
            rag_query = RAGQuery(
                text=processed_query,
                filters=filters,
                include_metadata=True
            )
            
            # Execute RAG pipeline
            response = await self.rag_pipeline.query(rag_query)
            
            # Enhance response with conversation context
            response.metadata['conversation_id'] = conversation_id
            response.metadata['documents_used'] = context.document_ids
            if rewrite_query and use_history:
                response.metadata['query_rewritten'] = True
                response.metadata['original_query'] = query
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to query with conversation context: {e}")
            raise
    
    async def stream_response(
        self,
        conversation_id: str,
        query: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> AsyncIterator[str]:
        """
        Stream response tokens for real-time display.
        
        Args:
            conversation_id: Conversation ID
            query: User query
            callback: Optional callback for each token
            
        Yields:
            Response tokens
        """
        try:
            # Get RAG response with context
            response = await self.query_with_conversation_context(
                conversation_id,
                query
            )
            
            # Simulate streaming (in production, use actual streaming API)
            tokens = response.answer.split()
            for i, token in enumerate(tokens):
                chunk = token + (" " if i < len(tokens) - 1 else "")
                
                if callback:
                    callback(chunk)
                
                yield chunk
                
                # Small delay for visual effect
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Failed to stream response: {e}")
            yield f"Error: {str(e)}"
    
    def _build_history_context(self, messages: List[Message]) -> str:
        """Build context string from message history."""
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages[-5:]:  # Last 5 messages for context
            role = msg.role.value.capitalize()
            content = msg.content[:200]  # Truncate long messages
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def _build_rewrite_prompt(self, query: str, history: str) -> str:
        """Build prompt for query rewriting."""
        return f"""Given the conversation history below, rewrite the user's query to be more specific and include necessary context. The rewritten query should be self-contained and optimized for retrieval.

Conversation History:
{history}

Current Query: {query}

Provide the rewritten query in JSON format:
{{
    "query": "rewritten query here",
    "confidence": 0.9,
    "reasoning": "brief explanation"
}}"""
    
    async def _call_llm_for_rewrite(self, prompt: str) -> Dict[str, Any]:
        """Call LLM for query rewriting."""
        try:
            # Use the session manager from RAG pipeline
            response = self.rag_pipeline.session_manager.make_request(
                method="POST",
                url=f"{self.config.llm.api_endpoint}/chat/completions",
                json={
                    "model": self.config.llm.model,
                    "messages": [
                        {"role": "system", "content": "You are a query rewriting assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
                headers={"Authorization": f"Bearer {self.config.llm.api_key}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # Parse JSON response
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Fallback if not valid JSON
                    return {"query": content.strip(), "confidence": 0.7}
            
        except Exception as e:
            logger.error(f"LLM rewrite call failed: {e}")
        
        return {"query": prompt.split("Current Query: ")[-1].strip(), "confidence": 0.5}
    
    def get_conversation_documents(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all documents associated with a conversation."""
        context = self.get_or_create_context(conversation_id)
        return [
            {
                'id': doc_id,
                'metadata': context.document_metadata.get(doc_id, {})
            }
            for doc_id in context.document_ids
        ]
    
    def clear_conversation_context(self, conversation_id: str):
        """Clear all context for a conversation."""
        if conversation_id in self._contexts:
            context = self._contexts[conversation_id]
            
            # Update document tracking
            for doc_id in context.document_ids:
                if doc_id in self._document_conversations:
                    convs = self._document_conversations[doc_id]
                    if conversation_id in convs:
                        convs.remove(conversation_id)
            
            # Remove context
            del self._contexts[conversation_id]
            
            logger.info(f"Cleared context for conversation {conversation_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        base_stats = self.rag_pipeline.get_stats()
        
        return {
            **base_stats,
            'conversation_contexts': len(self._contexts),
            'total_documents_tracked': len(self._document_conversations),
            'documents_per_conversation': {
                conv_id: len(ctx.document_ids)
                for conv_id, ctx in self._contexts.items()
            }
        }