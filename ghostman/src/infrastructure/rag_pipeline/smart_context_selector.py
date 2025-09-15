"""
SmartContextSelector: Sophisticated context selection system with progressive fallback.

This module implements a multi-tier approach to context selection that eliminates the 
"all or nothing" problem by providing intelligent fallback strategies while maintaining
quality control and transparency.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class ContextSource(Enum):
    """Source type for context results."""
    CONVERSATION = "conversation"        # Files from current conversation
    PENDING = "pending"                 # Files uploaded but not saved  
    RECENT = "recent"                   # Recent files with semantic similarity
    GLOBAL = "global"                   # Global relevant files (higher threshold)


@dataclass
class ContextResult:
    """Tagged context result with source information."""
    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str
    source_type: ContextSource
    selection_tier: int
    threshold_used: float


class SmartContextSelector:
    """
    Sophisticated context selection system with progressive fallback strategies.
    
    Implements a multi-tier approach:
    Level 1: Conversation-specific files → 
    Level 2: Pending conversation files → 
    Level 3: Recent files (semantic similarity) → 
    Level 4: Global relevant files (higher threshold)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Similarity thresholds for each tier (FIXED: Lowered thresholds for conversation isolation)
        self.thresholds = {
            ContextSource.CONVERSATION: 0.1,   # Very permissive for conversation files
            ContextSource.PENDING: 0.1,        # Very permissive for pending files  
            ContextSource.RECENT: 0.5,         # Moderate threshold for recent files (was 0.7)
            ContextSource.GLOBAL: 0.45         # Lowered threshold for global files (was 0.75)
        }
        
        # Quality gate - never go below this threshold (FIXED: Lowered for conversation isolation)
        self.minimum_threshold = 0.05
        
        # Token budget allocation per tier
        self.token_budgets = {
            ContextSource.CONVERSATION: 0.6,  # 60% for conversation context
            ContextSource.PENDING: 0.25,     # 25% for pending context
            ContextSource.RECENT: 0.1,       # 10% for recent context
            ContextSource.GLOBAL: 0.05       # 5% for global context
        }
    
    async def select_context(self, 
                           faiss_client,
                           embedding_service,
                           query_text: str,
                           top_k: int = 5,
                           conversation_id: Optional[str] = None,
                           max_tokens: int = 4000,
                           strict_conversation_isolation: bool = False) -> Tuple[List[ContextResult], Dict[str, Any]]:
        """
        Select context using progressive fallback strategy.
        
        Args:
            faiss_client: FAISS client for vector search
            embedding_service: Service for generating embeddings
            query_text: The query text to search for
            top_k: Maximum number of results to return
            conversation_id: Current conversation ID (if any)
            max_tokens: Maximum token budget for context
            strict_conversation_isolation: If True, ONLY search within conversation boundaries,
                                         no fallback to global/recent files
            
        Returns:
            Tuple of (results, selection_info) where selection_info contains
            transparency information about the selection process
        """
        start_time = time.time()
        selection_info = {
            'strategies_attempted': [],
            'results_by_tier': {},
            'final_strategy': None,
            'fallback_occurred': False,
            'quality_filtered': 0,
            'processing_time': 0
        }
        
        # Generate query embedding once
        query_embedding = embedding_service.create_embedding(query_text)
        if query_embedding is None:
            self.logger.error("Failed to generate query embedding")
            return [], selection_info
        
        all_results = []
        
        if strict_conversation_isolation:
            self.logger.warning("🚨 NUCLEAR OPTION: MAXIMUM STRICT CONVERSATION ISOLATION ENABLED")
            self.logger.warning("🚫 NO FALLBACKS - NO GLOBAL FILES - NO CROSS-CONTAMINATION")
            
            # In strict mode, ONLY search conversation-specific files
            if conversation_id:
                self.logger.warning(f"🔒 NUCLEAR: Searching ONLY for files in conversation {conversation_id[:8]}...")
                
                # Tier 1: Conversation-specific files
                conversation_results = await self._search_conversation_files(
                    faiss_client, query_embedding, conversation_id, top_k, selection_info
                )
                all_results.extend(conversation_results)
                selection_info['strategies_attempted'].append('conversation')
                
                # Tier 2: Pending conversation files
                pending_results = await self._search_pending_files(
                    faiss_client, query_embedding, conversation_id, top_k, selection_info
                )
                all_results.extend(pending_results)
                selection_info['strategies_attempted'].append('pending')
                
                # NUCLEAR OPTION: Log exactly what we found
                total_found = len(all_results)
                self.logger.warning(f"🔍 NUCLEAR RESULT: Found {total_found} files STRICTLY from conversation {conversation_id[:8]}...")
                
                if not all_results:
                    self.logger.warning(f"🚨 NUCLEAR: ZERO files found for conversation {conversation_id[:8]}... - NO FALLBACK - returning EMPTY")
                    selection_info['strict_isolation_enforced'] = True
                else:
                    self.logger.warning(f"✅ NUCLEAR: SUCCESS - {total_found} conversation-specific files found")
        else:
            # TEMPORARY FIX: Relaxed mode with time-based filtering for recent files
            self.logger.warning("🕒 TEMPORARY MODE: Using time-based filtering for recently uploaded files")
            
            # Try conversation files first
            if conversation_id:
                conversation_results = await self._search_conversation_files(
                    faiss_client, query_embedding, conversation_id, top_k, selection_info
                )
                all_results.extend(conversation_results)
                selection_info['strategies_attempted'].append('conversation')
                
                # Try pending files
                pending_results = await self._search_pending_files(
                    faiss_client, query_embedding, conversation_id, top_k, selection_info
                )
                all_results.extend(pending_results)
                selection_info['strategies_attempted'].append('pending')
            
            # If still no results, try recent files with time filter
            if len(all_results) < top_k:
                recent_results = await self._search_recent_files_with_time_filter(
                    faiss_client, query_embedding, top_k - len(all_results), selection_info
                )
                all_results.extend(recent_results)
                selection_info['strategies_attempted'].append('recent_time_filtered')
        
        # Apply quality filtering and token budget management
        filtered_results = self._apply_quality_filter_and_budget(all_results, max_tokens, selection_info)
        
        # Set final strategy
        if filtered_results:
            selection_info['final_strategy'] = filtered_results[0].source_type.value
        
        selection_info['processing_time'] = time.time() - start_time
        
        # Log selection transparency
        self._log_selection_transparency(query_text, filtered_results, selection_info)
        
        return filtered_results, selection_info
    
    async def _search_conversation_files(self, 
                                       faiss_client, 
                                       query_embedding, 
                                       conversation_id: str, 
                                       top_k: int,
                                       selection_info: Dict) -> List[ContextResult]:
        """Search for files specifically from the current conversation."""
        try:
            # FIXED: Enhanced conversation filters to handle both stored and pending associations
            filters = {
                'conversation_id': conversation_id,
                '_or_pending_conversation_id': conversation_id
            }
            
            # FIXED: Get more results for better filtering coverage
            raw_results = await faiss_client.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k * 3,  # Increased multiplier for better coverage
                filters=filters
            )
            
            # FIXED: Debug conversation search
            self.logger.info(f"🔍 DEBUG Conversation: Got {len(raw_results)} raw results for conversation {conversation_id[:8]}...")
            for i, result in enumerate(raw_results[:3]):  # Log first 3
                metadata_keys = list(result.metadata.keys()) if hasattr(result, 'metadata') else []
                self.logger.info(f"  Conv Result {i+1}: Score={result.score:.4f}, Metadata keys={metadata_keys}")
            
            results = []
            passed_count = 0
            failed_count = 0
            for result in raw_results:
                if result.score >= self.thresholds[ContextSource.CONVERSATION]:
                    results.append(ContextResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=result.score,
                        chunk_id=result.chunk_id,
                        source_type=ContextSource.CONVERSATION,
                        selection_tier=1,
                        threshold_used=self.thresholds[ContextSource.CONVERSATION]
                    ))
                    passed_count += 1
                else:
                    failed_count += 1
            
            # FIXED: Enhanced conversation search logging
            self.logger.info(f"🔍 Conversation threshold {self.thresholds[ContextSource.CONVERSATION]}: {passed_count} passed, {failed_count} filtered out")
            
            selection_info['results_by_tier']['conversation'] = len(results)
            self.logger.info(f"🔍 Tier 1 (Conversation): Found {len(results)} results")
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error searching conversation files: {e}")
            selection_info['results_by_tier']['conversation'] = 0
            return []
    
    async def _search_pending_files(self,
                                  faiss_client,
                                  query_embedding,
                                  conversation_id: str,
                                  top_k: int,
                                  selection_info: Dict) -> List[ContextResult]:
        """Search for files uploaded but not yet saved to conversation."""
        try:
            # FIXED: Multiple filter strategies for pending files
            filters = {'pending_conversation_id': conversation_id}
            
            raw_results = await faiss_client.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k * 3,  # Increased multiplier
                filters=filters
            )
            
            # FIXED: Debug pending search
            self.logger.info(f"🔍 DEBUG Pending: Got {len(raw_results)} raw results for pending conversation {conversation_id[:8]}...")
            for i, result in enumerate(raw_results[:3]):  # Log first 3
                metadata_keys = list(result.metadata.keys()) if hasattr(result, 'metadata') else []
                pending_id = result.metadata.get('pending_conversation_id', 'None') if hasattr(result, 'metadata') else 'None'
                self.logger.info(f"  Pending Result {i+1}: Score={result.score:.4f}, PendingID={pending_id[:8] if pending_id != 'None' else 'None'}")
            
            results = []
            passed_count = 0
            failed_count = 0
            for result in raw_results:
                if result.score >= self.thresholds[ContextSource.PENDING]:
                    results.append(ContextResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=result.score,
                        chunk_id=result.chunk_id,
                        source_type=ContextSource.PENDING,
                        selection_tier=2,
                        threshold_used=self.thresholds[ContextSource.PENDING]
                    ))
                    passed_count += 1
                else:
                    failed_count += 1
            
            # FIXED: Enhanced pending search logging
            self.logger.info(f"🔍 Pending threshold {self.thresholds[ContextSource.PENDING]}: {passed_count} passed, {failed_count} filtered out")
            
            selection_info['results_by_tier']['pending'] = len(results)
            self.logger.info(f"🔍 Tier 2 (Pending): Found {len(results)} results")
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error searching pending files: {e}")
            selection_info['results_by_tier']['pending'] = 0
            return []
    
    async def _search_recent_files(self,
                                 faiss_client,
                                 query_embedding,
                                 top_k: int,
                                 selection_info: Dict) -> List[ContextResult]:
        """Search for recent files with semantic similarity (no conversation filter)."""
        try:
            # Progressive threshold relaxation for recent files
            thresholds_to_try = [0.7, 0.6, 0.5]
            
            for threshold in thresholds_to_try:
                if threshold < self.minimum_threshold:
                    continue
                    
                raw_results = await faiss_client.similarity_search(
                    query_embedding=query_embedding,
                    top_k=top_k * 3,  # Get more for filtering
                    filters=None  # No conversation filter
                )
                
                # Debug: Log all raw results and their scores
                self.logger.info(f"🔍 DEBUG: Got {len(raw_results)} raw results from FAISS")
                for i, result in enumerate(raw_results[:5]):  # Log first 5
                    self.logger.info(f"  Result {i+1}: Score={result.score:.4f}, Content='{result.content[:100]}...'")
                
                results = []
                filtered_count = 0
                for result in raw_results:
                    if result.score >= threshold:
                        results.append(ContextResult(
                            content=result.content,
                            metadata=result.metadata,
                            score=result.score,
                            chunk_id=result.chunk_id,
                            source_type=ContextSource.RECENT,
                            selection_tier=3,
                            threshold_used=threshold
                        ))
                    else:
                        filtered_count += 1
                
                self.logger.info(f"🔍 DEBUG: Threshold {threshold}: {len(results)} passed, {filtered_count} filtered out")
                
                if results:
                    selection_info['results_by_tier']['recent'] = len(results)
                    self.logger.info(f"🔍 Tier 3 (Recent): Found {len(results)} results with threshold {threshold}")
                    return results[:top_k]
            
            selection_info['results_by_tier']['recent'] = 0
            return []
            
        except Exception as e:
            self.logger.error(f"Error searching recent files: {e}")
            selection_info['results_by_tier']['recent'] = 0
            return []
    
    async def _search_global_files(self,
                                 faiss_client,
                                 query_embedding,
                                 top_k: int,
                                 selection_info: Dict) -> List[ContextResult]:
        """Search for globally relevant files with strict threshold."""
        try:
            raw_results = await faiss_client.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k * 2,
                filters=None
            )
            
            # Debug: Log all raw results and their scores for global search
            self.logger.info(f"🔍 DEBUG Global: Got {len(raw_results)} raw results from FAISS")
            for i, result in enumerate(raw_results[:3]):  # Log first 3
                self.logger.info(f"  Global Result {i+1}: Score={result.score:.4f}, Content='{result.content[:100]}...'")
            
            results = []
            filtered_count = 0
            for result in raw_results:
                if result.score >= self.thresholds[ContextSource.GLOBAL]:
                    results.append(ContextResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=result.score,
                        chunk_id=result.chunk_id,
                        source_type=ContextSource.GLOBAL,
                        selection_tier=4,
                        threshold_used=self.thresholds[ContextSource.GLOBAL]
                    ))
                else:
                    filtered_count += 1
                    
            self.logger.info(f"🔍 DEBUG Global: Threshold {self.thresholds[ContextSource.GLOBAL]}: {len(results)} passed, {filtered_count} filtered out")
            
            selection_info['results_by_tier']['global'] = len(results)
            self.logger.info(f"🔍 Tier 4 (Global): Found {len(results)} results")
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error searching global files: {e}")
            selection_info['results_by_tier']['global'] = 0
            return []
    
    def _apply_quality_filter_and_budget(self, 
                                       results: List[ContextResult],
                                       max_tokens: int,
                                       selection_info: Dict) -> List[ContextResult]:
        """Apply quality filtering and token budget management."""
        # Quality filter: Remove results below minimum threshold
        quality_filtered = []
        filtered_count = 0
        
        for result in results:
            if result.score >= self.minimum_threshold:
                quality_filtered.append(result)
            else:
                filtered_count += 1
        
        selection_info['quality_filtered'] = filtered_count
        
        # Sort by score (descending) and tier priority
        quality_filtered.sort(key=lambda x: (x.selection_tier, -x.score))
        
        # Apply token budget (simple approximation)
        budget_filtered = []
        estimated_tokens = 0
        
        for result in quality_filtered:
            # Rough token estimation (4 chars per token)
            content_tokens = len(result.content) // 4
            
            if estimated_tokens + content_tokens <= max_tokens:
                budget_filtered.append(result)
                estimated_tokens += content_tokens
            else:
                break
        
        return budget_filtered
    
    async def _search_recent_files_with_time_filter(self,
                                                  faiss_client,
                                                  query_embedding,
                                                  top_k: int,
                                                  selection_info: Dict) -> List[ContextResult]:
        """Search for files uploaded in the last 10 minutes (temporary fix for conversation ID mismatch)."""
        try:
            import time
            current_time = time.time()
            recent_threshold = current_time - 600  # 10 minutes ago
            
            self.logger.warning(f"🕒 TEMPORAL: Searching for files uploaded after {time.ctime(recent_threshold)}")
            
            # Get all results without conversation filters
            raw_results = await faiss_client.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k * 4,  # Get more for time filtering
                filters=None  # No conversation filter
            )
            
            results = []
            time_filtered_count = 0
            for result in raw_results:
                # Check if file was uploaded recently
                created_at = result.metadata.get('created_at', 0)
                if created_at > recent_threshold:
                    if result.score >= 0.3:  # Lower threshold for recent files
                        results.append(ContextResult(
                            content=result.content,
                            metadata=result.metadata,
                            score=result.score,
                            chunk_id=result.chunk_id,
                            source_type=ContextSource.RECENT,
                            selection_tier=3,
                            threshold_used=0.3
                        ))
                    else:
                        time_filtered_count += 1
                else:
                    time_filtered_count += 1
            
            self.logger.warning(f"🕒 TEMPORAL: Found {len(results)} recent files, filtered {time_filtered_count} older/low-score files")
            
            selection_info['results_by_tier']['recent_time_filtered'] = len(results)
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error in time-based search: {e}")
            selection_info['results_by_tier']['recent_time_filtered'] = 0
            return []
    
    async def _emergency_search(self,
                              faiss_client,
                              query_embedding,
                              top_k: int,
                              selection_info: Dict) -> List[ContextResult]:
        """Emergency search with minimal threshold to ensure some results."""
        try:
            self.logger.warning("🚨 Attempting emergency search with minimal threshold")
            
            raw_results = await faiss_client.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k * 2,
                filters=None  # No filters - get anything
            )
            
            self.logger.info(f"🚨 Emergency search got {len(raw_results)} raw results")
            
            # Use minimal threshold (0.1) to get some results
            emergency_threshold = 0.1
            results = []
            
            for result in raw_results:
                if result.score >= emergency_threshold:
                    results.append(ContextResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=result.score,
                        chunk_id=result.chunk_id,
                        source_type=ContextSource.GLOBAL,  # Mark as global
                        selection_tier=5,  # Emergency tier
                        threshold_used=emergency_threshold
                    ))
            
            selection_info['results_by_tier']['emergency'] = len(results)
            self.logger.warning(f"🚨 Emergency search found {len(results)} results with threshold {emergency_threshold}")
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Emergency search failed: {e}")
            selection_info['results_by_tier']['emergency'] = 0
            return []
    
    def _log_selection_transparency(self, 
                                  query_text: str,
                                  results: List[ContextResult],
                                  selection_info: Dict):
        """Log transparency information about the selection process."""
        self.logger.info(f"🧠 Smart Context Selection for: '{query_text[:50]}...'")
        self.logger.info(f"📊 Strategies attempted: {selection_info['strategies_attempted']}")
        self.logger.info(f"📈 Results by tier: {selection_info['results_by_tier']}")
        self.logger.info(f"⚡ Processing time: {selection_info['processing_time']:.3f}s")
        
        if selection_info['fallback_occurred']:
            self.logger.info("🔄 Fallback strategies were used")
        
        if selection_info['quality_filtered'] > 0:
            self.logger.info(f"🚫 Quality filtered: {selection_info['quality_filtered']} low-quality results")
        
        if results:
            self.logger.info(f"✅ Final selection: {len(results)} results")
            for i, result in enumerate(results[:3]):  # Log top 3
                self.logger.info(f"  {i+1}. [{result.source_type.value}] Score: {result.score:.3f}, "
                               f"Tier: {result.selection_tier}, Content: {result.content[:50]}...")
        else:
            self.logger.warning("❌ No results selected")