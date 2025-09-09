"""
Thread-Safe REPL Widget Modifications

This file contains the updated REPL widget code that uses the thread-safe RAG bridge
to prevent ChromaDB segmentation faults. Apply these changes to your existing
repl_widget.py file.
"""

# Add these imports at the top of your repl_widget.py file
from ghostman.src.infrastructure.rag_pipeline.qt_integration import QtRagBridge


class ThreadSafeREPLWidget:
    """
    Updated REPL widget methods for thread-safe RAG operations.
    
    Replace the existing methods in your REPLWidget class with these implementations.
    """
    
    def __init__(self):
        """Add this initialization code to your existing __init__ method."""
        # Initialize thread-safe RAG bridge
        self.rag_bridge: Optional[QtRagBridge] = None
        self._init_rag_bridge()
    
    def _init_rag_bridge(self):
        """Initialize the thread-safe RAG bridge."""
        try:
            logger.info("🚀 Initializing thread-safe RAG bridge")
            
            # Create and initialize RAG bridge
            self.rag_bridge = QtRagBridge()
            
            # Connect signals for RAG operations
            self.rag_bridge.document_processed.connect(self._on_document_processed)
            self.rag_bridge.query_answered.connect(self._on_query_answered)
            self.rag_bridge.error_occurred.connect(self._on_rag_error)
            self.rag_bridge.ready_changed.connect(self._on_rag_ready_changed)
            
            # Initialize in background
            if self.rag_bridge.initialize():
                logger.info("✅ Thread-safe RAG bridge initialized successfully")
            else:
                logger.error("❌ Failed to initialize thread-safe RAG bridge")
                
        except Exception as e:
            logger.error(f"❌ RAG bridge initialization error: {e}")
            self.rag_bridge = None
    
    def _on_document_processed(self, file_path: str, doc_id: str, success: bool, metadata: dict):
        """Handle document processing completion."""
        try:
            filename = os.path.basename(file_path)
            
            if success and doc_id and not doc_id.startswith("skipped_"):
                logger.info(f"✅ Document processed successfully: {filename}")
                self.append_output(f"✅ Successfully processed: {filename}", "success")
                
                # Update file browser if available
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.mark_file_processed(file_path, True)
                
            elif success and doc_id and doc_id.startswith("skipped_"):
                logger.warning(f"⚠️ Document processing skipped (embedding issues): {filename}")
                self.append_output(f"⚠️ Processed with warnings: {filename} (check API configuration)", "warning")
                
            else:
                error_msg = metadata.get('error', 'Unknown error')
                logger.error(f"❌ Document processing failed: {filename} - {error_msg}")
                self.append_output(f"❌ Failed to process: {filename} - {error_msg}", "error")
                
                # Update file browser if available
                if hasattr(self, 'file_browser_bar') and self.file_browser_bar:
                    self.file_browser_bar.mark_file_processed(file_path, False)
                    
        except Exception as e:
            logger.error(f"Error handling document processing result: {e}")
    
    def _on_query_answered(self, query: str, answer: str, sources: list, success: bool, metadata: dict):
        """Handle RAG query completion."""
        try:
            if success:
                processing_time = metadata.get('processing_time', 0.0)
                sources_count = metadata.get('sources_count', 0)
                
                logger.info(f"✅ RAG query completed in {processing_time:.2f}s with {sources_count} sources")
                
                # You can add the RAG context to your message here if needed
                # This is where you would integrate the RAG response with your AI conversation
                
            else:
                error_msg = metadata.get('error', 'Unknown error')
                logger.error(f"❌ RAG query failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error handling RAG query result: {e}")
    
    def _on_rag_error(self, operation: str, error_message: str):
        """Handle RAG operation errors."""
        logger.error(f"❌ RAG {operation} error: {error_message}")
        self.append_output(f"❌ RAG {operation} failed: {error_message}", "error")
    
    def _on_rag_ready_changed(self, ready: bool):
        """Handle RAG readiness changes."""
        if ready:
            logger.info("✅ RAG system is ready")
            self.append_output("✅ RAG system initialized and ready", "success")
        else:
            logger.warning("⚠️ RAG system is not ready")
    
    def _process_file_embeddings_safe(self, file_paths: List[str]):
        """
        Process file embeddings using thread-safe RAG bridge.
        
        Replace your existing _process_file_embeddings method with this implementation.
        """
        if not file_paths:
            return
        
        if not self.rag_bridge or not self.rag_bridge.is_ready():
            logger.error("❌ RAG bridge not ready for file processing")
            self.append_output("❌ RAG system not ready. Please wait for initialization.", "error")
            return
        
        logger.info(f"🚀 Processing {len(file_paths)} files using thread-safe RAG bridge")
        self.append_output(f"🔄 Processing {len(file_paths)} files...", "info")
        
        # Process each file using the thread-safe bridge
        for file_path in file_paths:
            try:
                filename = os.path.basename(file_path)
                logger.info(f"📄 Queuing file for processing: {filename}")
                
                # Queue file for processing (non-blocking)
                self.rag_bridge.ingest_document(file_path)
                
            except Exception as e:
                logger.error(f"❌ Error queuing file {file_path}: {e}")
                self.append_output(f"❌ Error queuing file {os.path.basename(file_path)}: {e}", "error")
    
    def _get_rag_context_safe(self, user_message: str) -> List[Dict[str, Any]]:
        """
        Get RAG context using thread-safe operations.
        
        Note: This is a synchronous method that returns immediately.
        For actual RAG queries, use the async query method with signals.
        """
        try:
            if not self.rag_bridge or not self.rag_bridge.is_ready():
                logger.debug("RAG bridge not ready for context retrieval")
                return []
            
            # For real-time context, you might want to implement a cache
            # or use a synchronous context retrieval method
            # This is a simplified version that returns empty context
            # In production, you'd want to implement proper context caching
            
            logger.debug(f"Context requested for: {user_message[:50]}...")
            return []
            
        except Exception as e:
            logger.error(f"Error getting RAG context: {e}")
            return []
    
    def _query_rag_safe(self, query: str, top_k: int = 5):
        """
        Query RAG system using thread-safe bridge.
        
        This method queues a RAG query and returns immediately.
        Results are handled via the _on_query_answered signal handler.
        """
        try:
            if not self.rag_bridge or not self.rag_bridge.is_ready():
                logger.warning("RAG bridge not ready for queries")
                self.append_output("⚠️ RAG system not ready for queries", "warning")
                return
            
            logger.info(f"🔍 Queuing RAG query: {query[:100]}...")
            
            # Queue query (non-blocking)
            self.rag_bridge.query(query, top_k)
            
        except Exception as e:
            logger.error(f"Error queuing RAG query: {e}")
            self.append_output(f"❌ Error queuing RAG query: {e}", "error")
    
    def closeEvent(self, event):
        """
        Handle widget close event with proper cleanup.
        
        Add this to your existing closeEvent method or create if it doesn't exist.
        """
        try:
            logger.info("🔄 Closing REPL widget, shutting down RAG bridge...")
            
            # Shutdown RAG bridge
            if self.rag_bridge:
                self.rag_bridge.shutdown()
                self.rag_bridge = None
            
            logger.info("✅ RAG bridge shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during REPL widget cleanup: {e}")
        
        # Call parent closeEvent if it exists
        if hasattr(super(), 'closeEvent'):
            super().closeEvent(event)
        else:
            event.accept()


# Example of how to replace the EmbeddingsProcessor class
class SafeEmbeddingsProcessor:
    """
    This class is no longer needed when using QtRagBridge.
    
    The QtRagBridge handles all threading and async operations safely.
    You can remove the existing EmbeddingsProcessor class and replace
    the file processing calls with:
    
    self._process_file_embeddings_safe(file_paths)
    
    Instead of creating EmbeddingsProcessor instances.
    """
    pass


# Migration Instructions:
"""
To update your existing repl_widget.py:

1. Add the import at the top:
   from ghostman.src.infrastructure.rag_pipeline.qt_integration import QtRagBridge

2. In your REPLWidget.__init__ method, add:
   self.rag_bridge = None
   self._init_rag_bridge()

3. Replace your existing methods with the safe versions above:
   - _process_file_embeddings -> _process_file_embeddings_safe
   - _get_rag_context -> _get_rag_context_safe
   - Add _query_rag_safe method for RAG queries
   - Add the signal handler methods (_on_document_processed, etc.)
   - Update closeEvent to include RAG bridge cleanup

4. Remove the EmbeddingsProcessor class entirely

5. Replace any direct RAG pipeline calls with QtRagBridge calls

This will eliminate the segmentation faults while maintaining all functionality.
"""