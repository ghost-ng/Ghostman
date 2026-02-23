"""
Integration between conversation management and existing AI service.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from ...ai.ai_service import AIService, ConversationContext, ConversationMessage
from ..models.conversation import Conversation, Message
from ..models.enums import MessageRole
from ..services.conversation_service import ConversationService

logger = logging.getLogger("specter.ai_integration")


class ConversationContextAdapter:
    """Adapter to bridge ConversationContext with Conversation model."""
    
    @staticmethod
    def to_conversation_context(conversation: Conversation) -> ConversationContext:
        """Convert Conversation to ConversationContext."""
        import logging
        logger = logging.getLogger("specter.ai_integration")
        
        context = ConversationContext(
            max_messages=conversation.metadata.custom_fields.get('max_messages', 50),
            max_tokens=conversation.metadata.estimated_tokens or 32768  # Increased for modern models
        )
        
        # Convert messages with proper error handling
        converted_count = 0
        for msg in conversation.messages:
            try:
                context_msg = ConversationMessage(
                    role=msg.role.value,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    token_count=msg.token_count
                )
                context.messages.append(context_msg)
                converted_count += 1
            except Exception as e:
                logger.error(f"Failed to convert message {msg.id}: {e}")
                continue
        
        logger.info(f"✓ Converted {converted_count}/{len(conversation.messages)} messages to conversation context")
        return context
    
    @staticmethod
    def from_conversation_context(
        context: ConversationContext,
        conversation_id: str
    ) -> List[Message]:
        """Convert ConversationContext messages to Message models."""
        messages = []
        
        for msg in context.messages:
            message = Message(
                id="",  # Will be generated when saved
                conversation_id=conversation_id,
                role=MessageRole(msg.role),
                content=msg.content,
                timestamp=msg.timestamp,
                token_count=msg.token_count,
                metadata={}
            )
            messages.append(message)
        
        return messages


class ConversationAIService(AIService):
    """
    Extended AI service with conversation management integration.
    
    This class extends the existing AIService to automatically save
    conversations and provide enhanced conversation management features.
    """
    
    def __init__(self, conversation_service: Optional[ConversationService] = None):
        """Initialize conversation-aware AI service."""
        super().__init__()

        self.conversation_service = conversation_service or ConversationService()
        self._current_conversation_id: Optional[str] = None
        self._auto_save_conversations = True
        self._auto_generate_titles = True
        self._auto_generate_summaries = False
        self._conversation_update_callbacks = []

        # Reference to file browser for checking file counts (set by REPL widget)
        self._file_browser_ref = None

        logger.info("ConversationAIService initialized")

    def set_file_browser_reference(self, file_browser):
        """Set reference to file browser for file count checking (optimization)."""
        self._file_browser_ref = file_browser
        logger.debug("File browser reference set for RAG optimization")

    # --- Conversation Management Integration ---
    
    async def start_new_conversation(
        self,
        title: Optional[str] = None,
        tags: Optional[set] = None,
        category: Optional[str] = None
    ) -> Optional[str]:
        """Start a new conversation and set it as active."""
        try:
            # Get current system prompt
            system_prompt = None
            if self.conversation.messages and self.conversation.messages[0].role == 'system':
                system_prompt = self.conversation.messages[0].content
            
            # Create new conversation in-memory only (don't save to DB yet)
            # It will be saved automatically when the first user message is sent
            from ..models.conversation import Conversation
            from ..models.metadata import ConversationMetadata

            conversation = Conversation.create(
                title=title or "New Conversation",
                initial_message=system_prompt,
                metadata=ConversationMetadata(
                    tags=tags or set(),
                    category=category
                )
            )

            # Set as active (in-memory only for now)
            self._current_conversation_id = conversation.id
            # Don't call set_active_conversation since conversation isn't in DB yet
            logger.info(f"✓ Created in-memory conversation: {conversation.id} (will save on first message)")

            # Clear current context and set to new empty conversation
            logger.info(f"🔍 NEW CONVERSATION - Before clear: {len(self.conversation.messages)} messages")
            self.conversation.clear()
            logger.info(f"🔍 NEW CONVERSATION - After clear: {len(self.conversation.messages)} messages")

            # Add system prompt if provided
            if system_prompt:
                from ..models.message import Message, MessageRole
                system_message = Message(
                    role=MessageRole.SYSTEM,
                    content=system_prompt,
                    conversation_id=conversation.id
                )
                self.conversation.add_message(system_message)
                logger.info(f"Added system prompt to new conversation")

            logger.info(f"🔍 NEW CONVERSATION - After setup: {len(self.conversation.messages)} messages")
            logger.info(f"🔍 NEW CONVERSATION - Conversation ID: {conversation.id}")
            logger.info(f"🔍 NEW CONVERSATION - Current active ID: {self._current_conversation_id}")

            logger.info(f"✓ Started new conversation: {conversation.id}")
            return conversation.id
            
        except Exception as e:
            logger.error(f"✗ Failed to start new conversation: {e}")
            return None
    
    async def load_conversation(self, conversation_id: str) -> bool:
        """Load an existing conversation."""
        try:
            # Get conversation
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation not found: {conversation_id}")
                return False
            
            # Set as active
            self._current_conversation_id = conversation_id
            self.conversation_service.set_active_conversation(conversation_id)
            
            # Load into context
            self.conversation.clear()
            await self._load_conversation_context(conversation_id)
            
            logger.info(f"✓ Loaded conversation: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to load conversation: {e}")
            return False
    
    async def _load_conversation_context(self, conversation_id: str):
        """Load conversation messages into current context with enhanced error handling."""
        try:
            logger.debug(f"🔄 Loading conversation context for: {conversation_id}")
            
            conversation = await self.conversation_service.get_conversation(conversation_id, include_messages=True)
            if not conversation:
                logger.error(f"Failed to load conversation {conversation_id} for context")
                return
            
            logger.info(f"📋 Loading conversation context: {len(conversation.messages)} messages from database")
            
            # Detailed logging for debugging
            logger.debug(f"🔍 Messages from database for conversation {conversation_id}:")
            for i, msg in enumerate(conversation.messages):
                preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                logger.debug(f"  📄 DB Message {i+1} [{msg.role.value}] at {msg.timestamp}: {preview}")
            
            if not conversation.messages:
                logger.warning(f"⚠  No messages found in conversation {conversation_id}")
            
            # Convert and load messages
            context = ConversationContextAdapter.to_conversation_context(conversation)
            
            # Clear existing context and load new one
            self.conversation.clear()
            self.conversation = context
            
            logger.info(f"✓ Conversation context loaded: {len(self.conversation.messages)} messages in AI context")
            
            # Verify context was loaded properly
            logger.debug(f"🔍 AI context messages after loading:")
            for i, msg in enumerate(self.conversation.messages):
                preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                logger.debug(f"  🤖 AI Message {i+1} [{msg.role}] at {msg.timestamp}: {preview}")
                
            if len(self.conversation.messages) != len(conversation.messages):
                logger.error(f"✗ Context loading mismatch: DB has {len(conversation.messages)} messages, AI context has {len(self.conversation.messages)} messages")
            else:
                logger.debug(f"✓ Context loading verified: {len(self.conversation.messages)} messages loaded correctly")
                
        except Exception as e:
            logger.error(f"✗ Failed to load conversation context for {conversation_id}: {e}", exc_info=True)
    
    # --- Enhanced Message Handling ---
    
    def send_message(
        self,
        message: str,
        stream: bool = False,
        save_conversation: bool = True,
        conversation_context: Optional[Dict[str, Any]] = None,
        tool_status_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        thinking_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Send message with automatic conversation saving and robust persistence.

        Args:
            message: User message to send
            stream: Whether to stream the response
            save_conversation: Whether to save to conversation management
            conversation_context: Optional context about conversation (includes conversation_id)
            tool_status_callback: Optional callback for tool execution status updates.
            thinking_callback: Optional callback for reasoning/thinking chunks.

        Returns:
            Dict with response information
        """
        # Log the request with context info
        logger.info(f"💬 Sending message with conversation context (current: {self._current_conversation_id})")
        logger.debug(f"💬 Context before send: {len(self.conversation.messages)} messages")
        
        # Handle conversation context if provided
        if conversation_context and 'conversation_id' in conversation_context:
            context_conv_id = conversation_context['conversation_id']
            if context_conv_id != self._current_conversation_id:
                logger.info(f"🔄 Switching conversation context from {self._current_conversation_id} to {context_conv_id}")
                self.set_current_conversation(context_conv_id)
        
        # NUCLEAR DEBUG: Log the AI service state before RAG enhancement
        logger.warning(f"🚨 NUCLEAR DEBUG: AI Service conversation ID: {self._current_conversation_id}")

        # Check if current conversation exists in database (handle deleted conversations)
        conversation_exists = False
        if self._current_conversation_id:
            try:
                # Check if conversation exists in database (synchronously)
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    test_conv = loop.run_until_complete(
                        self.conversation_service.get_conversation(
                            self._current_conversation_id, include_messages=False
                        )
                    )
                    conversation_exists = test_conv is not None
                finally:
                    loop.close()

                if not conversation_exists:
                    logger.error(f"⚠️ Conversation {self._current_conversation_id} not found in database (may have been deleted)")
                    logger.info("🔄 Clearing invalid conversation ID and will create new one")
                    self._current_conversation_id = None
            except Exception as e:
                logger.error(f"Failed to load conversation {self._current_conversation_id} for context: {e}")
                logger.info("🔄 Clearing invalid conversation ID and will create new one")
                self._current_conversation_id = None

        if not self._current_conversation_id:
            logger.error("🚨 NUCLEAR CRITICAL: AI Service has NO conversation ID - this will cause isolation failure")
            logger.error("🚫 Files uploaded to this conversation may not be findable")

        # Store the original message (without RAG context) for conversation history
        original_message = message

        # Enhance message with RAG context if available (with strict conversation isolation)
        enhanced_message = self._enhance_message_with_rag_context(message)

        # Ensure we have a conversation to save to (create if none exists OR if conversation was deleted)
        if save_conversation and self._auto_save_conversations and not self._current_conversation_id:
            logger.info("🆕 No active conversation, creating new one for message")
            try:
                from ...async_manager import get_async_manager
                
                async_manager = get_async_manager()
                if async_manager and async_manager.is_initialized():
                    # Use async manager for thread-safe conversation creation
                    def on_conversation_created(result, error):
                        if error:
                            logger.error(f"✗ Failed to create conversation for message: {error}")
                        elif result:
                            self._current_conversation_id = result
                            logger.info(f"✓ Created new conversation for message: {result}")
                        else:
                            logger.error("✗ Failed to create conversation for message - no result")
                    
                    async_manager.run_async_task(
                        self.start_new_conversation(),
                        callback=on_conversation_created,
                        timeout=10.0
                    )
                else:
                    logger.warning("AsyncManager not available, attempting direct conversation creation")
                    # Fallback with better error handling
                    import asyncio
                    try:
                        current_loop = asyncio.get_event_loop()
                        if current_loop.is_closed():
                            raise RuntimeError("Event loop is closed")
                        
                        if not current_loop.is_running():
                            conversation_id = current_loop.run_until_complete(self.start_new_conversation())
                            if conversation_id:
                                logger.info(f"✓ Created new conversation for message: {conversation_id}")
                            else:
                                logger.error("✗ Failed to create conversation for message")
                    except (RuntimeError, Exception) as loop_error:
                        logger.warning(f"Event loop issue during conversation creation: {loop_error}")
                        # Create new loop as last resort
                        loop = asyncio.new_event_loop()
                        try:
                            asyncio.set_event_loop(loop)
                            conversation_id = loop.run_until_complete(self.start_new_conversation())
                            if conversation_id:
                                logger.info(f"✓ Created new conversation for message: {conversation_id}")
                            else:
                                logger.error("✗ Failed to create conversation for message")
                        finally:
                            try:
                                loop.close()
                            except Exception as e:
                                logger.debug(f"Error closing conversation creation loop: {e}")
                        
            except Exception as e:
                logger.error(f"✗ Failed to create conversation for message: {e}")
        
        # Call parent method with enhanced message for API, but replace with original for conversation history
        # The parent will add the message to self.conversation.messages, so we temporarily use enhanced
        result = super().send_message(enhanced_message, stream, tool_status_callback=tool_status_callback, stream_callback=stream_callback, thinking_callback=thinking_callback)

        # IMPORTANT: Replace the last user message in conversation history with the original (without RAG context)
        # This ensures that when we save to the database, we save the clean user message without RAG metadata
        if result.get('success') and len(self.conversation.messages) >= 2:
            # The last two messages should be: user message (enhanced) and assistant response
            # Replace the user message with the original
            for i in range(len(self.conversation.messages) - 1, -1, -1):
                if self.conversation.messages[i].role == 'user':
                    # Found the user message, replace its content with original
                    self.conversation.messages[i].content = original_message
                    logger.debug(f"✓ Replaced enhanced message with original in conversation history")
                    break

        # Debug: Log what the parent method returned
        logger.info(f"🔍 CONVERSATION AI SERVICE - Parent result: success={result.get('success')}")
        logger.info(f"🔍 CONVERSATION AI SERVICE - Parent response length: {len(result.get('response', '')) if result.get('response') else 0}")
        logger.info(f"🔍 CONVERSATION AI SERVICE - Parent response content: '{result.get('response', '')}'")

        # Log the result with updated context info
        if result.get('success'):
            logger.info(f"✓ Message sent successfully. Context now has: {len(self.conversation.messages)} messages")
            
            # Trigger conversation update callbacks to refresh UI immediately
            if self._current_conversation_id and save_conversation:
                try:
                    # Call any registered conversation update callbacks
                    for callback in getattr(self, '_conversation_update_callbacks', []):
                        try:
                            callback(self._current_conversation_id, len(self.conversation.messages))
                        except Exception as e:
                            logger.error(f"Conversation update callback error: {e}")
                except Exception as e:
                    logger.error(f"Failed to trigger conversation update callbacks: {e}")
            
            # Immediate save to ensure persistence
            if save_conversation and self._auto_save_conversations:
                logger.info(f"💾 ATTEMPTING TO SAVE CONVERSATION: {self._current_conversation_id}")
                logger.info(f"💾 Messages in AI context: {len(self.conversation.messages)}")
                try:
                    logger.info("💾 Starting conversation save using async manager...")

                    # Import the async manager
                    from ...async_manager import run_async_task_safe

                    def on_save_complete(result, error):
                        if error:
                            logger.error(f"✗ SAVE CALLBACK - Failed to save conversation: {error}")
                        else:
                            logger.info(f"✓ SAVE CALLBACK - Conversation saved successfully")

                    # Use the async manager to handle the save operation safely
                    run_async_task_safe(
                        self._save_current_conversation(),
                        callback=on_save_complete,
                        timeout=10.0  # 10 second timeout
                    )
                    logger.info("💾 Save task submitted to async manager")
                    
                    # Also schedule a backup save with delay for safety
                    try:
                        from PyQt6.QtCore import QTimer
                        
                        def backup_save():
                            run_async_task_safe(
                                self._save_current_conversation(),
                                callback=lambda r, e: logger.debug("💾 Backup save completed") if not e else logger.debug(f"💾 Backup save failed: {e}"),
                                timeout=10.0
                            )
                        
                        QTimer.singleShot(500, backup_save)
                        logger.debug("💾 Scheduled backup save in 500ms")
                    except Exception as e:
                        logger.debug(f"Could not schedule backup save: {e}")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to schedule conversation save: {e}", exc_info=True)
        else:
            logger.error(f"✗ Message send failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    async def send_message_async(
        self,
        message: str,
        stream: bool = False,
        save_conversation: bool = True
    ) -> Dict[str, Any]:
        """Async version of send_message with conversation saving."""
        # Call parent method (will call sync version for now)
        result = await super().send_message_async(message, stream)
        
        # Save to conversation management if enabled
        if save_conversation and self._auto_save_conversations and result.get('success'):
            try:
                await self._save_current_conversation()
            except Exception as e:
                logger.error(f"Failed to save conversation: {e}")
        
        return result
    
    async def _save_current_conversation(self):
        """Save current conversation context to persistent storage with robust error handling."""
        try:
            logger.info("💾 _save_current_conversation() CALLED")

            # Ensure we have an active conversation
            if not self._current_conversation_id:
                logger.warning("💾 No active conversation ID, creating new one...")
                # Create new conversation if none exists
                conversation_id = await self.start_new_conversation()
                if not conversation_id:
                    logger.error("💾 Failed to create conversation for saving")
                    return
                logger.info(f"💾 Created new conversation: {conversation_id}")

            logger.info(f"💾 Saving conversation context for {self._current_conversation_id}")
            logger.info(f"💾 Current AI context has {len(self.conversation.messages)} messages")

            # RULE: Do not save conversations with 0 messages
            if len(self.conversation.messages) == 0:
                logger.info("💾 Skipping save - conversation has 0 messages")
                return

            # Get the latest messages that need to be saved
            conversation = await self.conversation_service.get_conversation(
                self._current_conversation_id, include_messages=True
            )
            if not conversation:
                # Conversation doesn't exist in DB yet (in-memory only)
                # Create it now since we have messages to save
                logger.info(f"💾 Conversation {self._current_conversation_id} not in DB, creating it now...")
                try:
                    # Create conversation in database with current messages
                    from ..models.conversation import Conversation as ConvModel
                    # Build conversation object from current context
                    conv_to_save = ConvModel(
                        id=self._current_conversation_id,
                        title="New Conversation",
                        messages=self.conversation.messages.copy()
                    )
                    # Save to database (will skip if empty, but we checked len > 0 above)
                    await self.conversation_service.repository.create_conversation(conv_to_save, force_create=False)
                    logger.info(f"✓ Created conversation in DB with {len(self.conversation.messages)} messages")
                    # Now get it from DB for normal processing
                    conversation = await self.conversation_service.get_conversation(
                        self._current_conversation_id, include_messages=True
                    )
                    if not conversation:
                        logger.error("Failed to retrieve newly created conversation")
                        return
                except Exception as create_error:
                    logger.error(f"Failed to create conversation in DB: {create_error}")
                    return

            # Check if we have new messages to save
            existing_message_count = len(conversation.messages)
            current_message_count = len(self.conversation.messages)

            logger.debug(f"💾 Database has {existing_message_count} messages, AI context has {current_message_count} messages")

            if current_message_count > existing_message_count:
                # Save new messages
                new_messages = self.conversation.messages[existing_message_count:]
                logger.info(f"💾 Saving {len(new_messages)} new messages to database")
                
                # Save messages in sequence to ensure proper ordering
                for i, context_msg in enumerate(new_messages):
                    logger.debug(f"💾 Saving message {i+1}/{len(new_messages)}: {context_msg.role} - {context_msg.content[:50]}...")
                    
                    saved_message = await self.conversation_service.add_message_to_conversation(
                        self._current_conversation_id,
                        MessageRole(context_msg.role),
                        context_msg.content,
                        context_msg.token_count,
                        {}
                    )
                    
                    if saved_message:
                        logger.debug(f"✓ Message {i+1} saved successfully with ID: {saved_message.id}")
                    else:
                        logger.error(f"✗ Failed to save message {i+1}")
                
                # Verify all messages were saved by reloading conversation
                verification_conversation = await self.conversation_service.get_conversation(
                    self._current_conversation_id, include_messages=True
                )
                
                if verification_conversation:
                    logger.info(f"✓ Verification: Database now has {len(verification_conversation.messages)} messages")
                    
                    # Update the AI context to match what's in the database (for consistency)
                    if len(verification_conversation.messages) > len(self.conversation.messages):
                        logger.warning("🔄 Database has more messages than AI context, this shouldn't happen")
                    
                # Auto-generate summary if enabled and conversation is substantial
                if self._auto_generate_summaries and current_message_count >= 6:
                    logger.debug("📝 Generating conversation summary...")
                    await self.conversation_service.generate_conversation_summary(self._current_conversation_id)
            else:
                logger.debug(f"💾 No new messages to save (DB: {existing_message_count}, Context: {current_message_count})")
                    
        except Exception as e:
            logger.error(f"✗ Failed to save current conversation: {e}", exc_info=True)
    
    def _enhance_message_with_rag_context(self, message: str) -> str:
        """Enhance message with RAG context using FAISS pipeline."""
        logger.debug(f"_enhance_message_with_rag_context called with message: '{message[:50]}...'")

        try:
            # --- Cheap skip checks BEFORE creating a session ---
            current_conversation_id = self._current_conversation_id

            if not self._file_browser_ref:
                logger.info("⏭️ SKIPPING RAG: file_browser_ref not set — REPL worker handles RAG")
                return message
            if not current_conversation_id:
                logger.info("⏭️ SKIPPING RAG: no conversation ID — cannot isolate context")
                return message

            # Check file count before creating an expensive session
            try:
                files = self._file_browser_ref.get_files_for_conversation(current_conversation_id)
                file_count = len(files) if files else 0
            except Exception as e:
                logger.warning(f"File browser check failed: {e} — skipping RAG")
                return message

            if file_count == 0:
                logger.info(f"⏭️ SKIPPING RAG: Conversation {current_conversation_id[:8]} has no files")
                return message

            logger.info(f"✅ Conversation {current_conversation_id[:8]} has {file_count} files — querying RAG")

            # --- Now create session (we know we need it) ---
            from ...rag_pipeline.threading.safe_rag_session import create_safe_rag_session
            safe_rag = create_safe_rag_session()

            if not safe_rag or not safe_rag.is_ready:
                logger.warning("⚠️ SafeRAG session not available for context retrieval")
                return message

            try:
                
                # Use SafeRAG query to get relevant context (thread-safe)
                logger.info(f"Querying SafeRAG pipeline with: '{message[:100]}...'")
                
                # Get current conversation ID for filtering
                current_conversation_id = self._current_conversation_id
                logger.info(f"🔍 DEBUG: Retrieved conversation ID for RAG filtering: {current_conversation_id}")
                
                # NUCLEAR OPTION: FLEXIBLE conversation isolation
                if not current_conversation_id:
                    logger.warning("🚨 NUCLEAR OPTION: No conversation ID found - creating emergency conversation context")
                    # Create an emergency conversation ID to prevent global contamination
                    import uuid
                    current_conversation_id = str(uuid.uuid4())
                    logger.warning(f"🚨 EMERGENCY: Created isolation ID {current_conversation_id[:8]}... to prevent cross-conversation contamination")
                
                # FINAL NUCLEAR OPTION: Check for recently uploaded files from current session
                # Since conversation IDs might be inconsistent, look for files uploaded in last 10 minutes
                import time
                current_time = time.time()
                recent_threshold = current_time - 600  # 10 minutes ago
                
                logger.warning(f"🚨 FINAL NUCLEAR OPTION: Searching for conversation {current_conversation_id[:8]}... AND recent files")
                logger.warning(f"🕒 Will also include files uploaded after {time.ctime(recent_threshold)}")
                
                response = safe_rag.query(
                    query_text=message,
                    top_k=3,
                    filters=None,  # Filters now handled by SmartContextSelector
                    timeout=10.0,
                    conversation_id=current_conversation_id  # Pass conversation_id for smart selection
                )
                
                if response:
                    sources = response.get('sources', [])
                    selection_info = response.get('selection_info', {})
                    built_in_context = response.get('context', '')
                    
                    # Log transparency information
                    strategies = selection_info.get('strategies_attempted', [])
                    final_strategy = selection_info.get('final_strategy', 'unknown')
                    fallback_occurred = selection_info.get('fallback_occurred', False)
                    
                    logger.info(f"🧠 SmartContextSelector results: {len(sources)} sources using strategy '{final_strategy}'")
                    logger.info(f"🔄 Strategies attempted: {strategies}")
                    if fallback_occurred:
                        logger.info("🔄 Fallback strategies were activated")
                    
                    if sources:
                        # Log detailed source information with transparency
                        for i, source in enumerate(sources):
                            if isinstance(source, dict):
                                content_preview = source.get('content', '')[:100]
                                source_type = source.get('source_type', 'unknown')
                                score = source.get('score', 0.0)
                                tier = source.get('selection_tier', 0)
                                threshold = source.get('threshold_used', 0.0)
                                
                                # FIXED: Enhanced logging with conversation association info
                                metadata = source.get('metadata', {})
                                conv_id = metadata.get('conversation_id', 'None')
                                pending_id = metadata.get('pending_conversation_id', 'None')
                                
                                logger.info(f"  Source {i+1} [{source_type.upper()}]: Score={score:.3f}, Tier={tier}, "
                                          f"Threshold={threshold:.3f}")
                                logger.info(f"    ConvID: {conv_id[:8] if conv_id != 'None' else 'None'}, "
                                          f"PendingID: {pending_id[:8] if pending_id != 'None' else 'None'}")
                                logger.info(f"    Content: {content_preview}...")
                        
                        # Use the built-in context from SmartContextSelector
                        if built_in_context:
                            enhanced_message = f"Context from files:\n{built_in_context}\n\nUser question: {message}"
                            
                            logger.info(f"✅ Enhanced message with {len(sources)} smart-selected context sources")
                            safe_rag.close()
                            return enhanced_message
                        else:
                            logger.warning("⚠️ SmartContextSelector returned sources but no built context")
                    else:
                        # Log why no sources were found with enhanced debugging
                        message_text = response.get('message', 'No explanation provided')
                        results_by_tier = selection_info.get('results_by_tier', {})
                        logger.warning(f"⚠️ SmartContextSelector found no sources: {message_text}")
                        logger.warning(f"🔍 Results by tier: {results_by_tier}")
                        
                        # FIXED: Suggest debugging steps for users
                        if not any(results_by_tier.values()):
                            logger.warning("📝 Debugging suggestions:")
                            logger.warning("  1. Check if files were actually processed and stored")
                            logger.warning("  2. Verify conversation association is working")
                            logger.warning("  3. Try a more general query (e.g., 'content' instead of specific terms)")
                            logger.warning("  4. Check if similarity thresholds are too high")
                else:
                    logger.warning("⚠️ SafeRAG query returned no response")
                    logger.warning("📝 This usually means:")
                    logger.warning("  1. No documents in the RAG pipeline")
                    logger.warning("  2. SafeRAG session is not properly initialized")
                    logger.warning("  3. Query processing failed internally")
                
                safe_rag.close()
                
            except Exception as query_error:
                logger.error(f"Error during RAG query: {query_error}")
                safe_rag.close()
                return message
                
        except Exception as e:
            logger.error(f"Error enhancing message with RAG context: {e}")
            return message
        
        logger.info("🔍 DEBUG: No context found, returning original message")
        return message
    
    # --- Configuration ---
    
    def set_auto_save(self, enabled: bool):
        """Enable or disable automatic conversation saving."""
        self._auto_save_conversations = enabled
        logger.info(f"Auto-save conversations: {'enabled' if enabled else 'disabled'}")
    
    def set_auto_generate_titles(self, enabled: bool):
        """Enable or disable automatic title generation."""
        self._auto_generate_titles = enabled
        logger.info(f"Auto-generate titles: {'enabled' if enabled else 'disabled'}")
    
    def set_auto_generate_summaries(self, enabled: bool):
        """Enable or disable automatic summary generation."""
        self._auto_generate_summaries = enabled
        logger.info(f"Auto-generate summaries: {'enabled' if enabled else 'disabled'}")
    
    def add_conversation_update_callback(self, callback):
        """Add a callback to be called when conversation is updated with new messages.
        
        Args:
            callback: Function that takes (conversation_id: str, message_count: int)
        """
        if callback not in self._conversation_update_callbacks:
            self._conversation_update_callbacks.append(callback)
            logger.debug(f"Added conversation update callback")
    
    def remove_conversation_update_callback(self, callback):
        """Remove a conversation update callback."""
        if callback in self._conversation_update_callbacks:
            self._conversation_update_callbacks.remove(callback)
            logger.debug(f"Removed conversation update callback")
    
    # --- Conversation Info ---
    
    def get_current_conversation_id(self) -> Optional[str]:
        """Get the current conversation ID."""
        return self._current_conversation_id
    
    def set_current_conversation(self, conversation_id: str):
        """Set the current conversation ID and load its context using thread-safe patterns."""
        try:
            logger.info(f"Setting current conversation to: {conversation_id}")
            self._current_conversation_id = conversation_id
            
            # AUTO-RESTORE DELETED CONVERSATIONS: If conversation is deleted, restore it automatically
            # This ensures files uploaded to this conversation remain accessible
            try:
                if hasattr(self, 'conversation_service') and self.conversation_service:
                    async def check_and_restore():
                        conv = await self.conversation_service.get_conversation(conversation_id, include_messages=False)
                        if conv and conv.status.value == 'deleted':
                            logger.warning(f"🔄 Auto-restoring deleted conversation {conversation_id[:8]}... to access its files")
                            success = await self.conversation_service.restore_conversation(conversation_id)
                            if success:
                                logger.info(f"✅ Successfully restored conversation {conversation_id[:8]}... for file access")
                            else:
                                logger.error(f"❌ Failed to restore conversation {conversation_id[:8]}...")
                    
                    # Execute restoration asynchronously
                    import asyncio
                    try:
                        # Try to get existing event loop, if none exists, create one
                        try:
                            loop = asyncio.get_running_loop()
                            # Loop is running - create task
                            asyncio.create_task(check_and_restore())
                        except RuntimeError:
                            # No running loop - use async manager or skip
                            logger.debug("No running event loop - skipping auto-restore (non-critical)")
                    except Exception as restore_error:
                        logger.debug(f"Auto-restore attempt failed (non-critical): {restore_error}")
            except Exception as e:
                logger.debug(f"Auto-restore check failed (this is non-critical): {e}")
            
            # Use async manager for thread-safe context loading
            try:
                from ...async_manager import get_async_manager
                
                async_manager = get_async_manager()
                if async_manager and async_manager.is_initialized():
                    # Use async manager for thread-safe context loading
                    def on_context_loaded(result, error):
                        if error:
                            logger.error(f"Failed to load conversation context: {error}")
                        else:
                            logger.debug(f"Conversation context loaded successfully for {conversation_id}")
                    
                    async_manager.run_async_task(
                        self._load_conversation_context(conversation_id),
                        callback=on_context_loaded,
                        timeout=10.0
                    )
                else:
                    logger.warning("AsyncManager not available, falling back to sync loading")
                    # Fallback to sync method
                    self._load_conversation_context_sync(conversation_id)
                    
            except Exception as e:
                logger.error(f"Failed to load conversation context using async manager: {e}")
                # Last resort fallback
                try:
                    self._load_conversation_context_sync(conversation_id)
                except Exception as sync_error:
                    logger.error(f"Sync fallback also failed: {sync_error}")
                
        except Exception as e:
            logger.error(f"Failed to set current conversation {conversation_id}: {e}")
    
    def _load_conversation_context_sync(self, conversation_id: str):
        """Load conversation context synchronously with proper event loop handling."""
        import asyncio
        
        try:
            # Check if there's an existing event loop and if it's running
            current_loop = None
            loop_was_running = False
            
            try:
                current_loop = asyncio.get_event_loop()
                loop_was_running = current_loop.is_running()
            except RuntimeError:
                # No event loop exists
                current_loop = None
            
            if current_loop and not loop_was_running and not current_loop.is_closed():
                # We have a loop that's not running and not closed - use it
                current_loop.run_until_complete(self._load_conversation_context(conversation_id))
            else:
                # Create a new event loop for this operation
                loop = asyncio.new_event_loop()
                try:
                    # Temporarily set this as the current loop
                    asyncio.set_event_loop(loop)
                    
                    # Run the async operation
                    loop.run_until_complete(self._load_conversation_context(conversation_id))
                    
                finally:
                    # Clean up the loop
                    try:
                        loop.close()
                    except Exception as e:
                        logger.debug(f"Error closing temporary event loop: {e}")
                    
                    # Restore the original loop if it existed and wasn't closed
                    if current_loop and not current_loop.is_closed():
                        asyncio.set_event_loop(current_loop)
                    
        except Exception as e:
            logger.error(f"Failed to load conversation context synchronously: {e}")
    
    async def get_current_conversation_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current conversation."""
        if not self._current_conversation_id:
            return None
        
        conversation = await self.conversation_service.get_conversation(
            self._current_conversation_id, 
            include_messages=False
        )
        
        if not conversation:
            return None
        
        return {
            'id': conversation.id,
            'title': conversation.title,
            'status': conversation.status.value,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'message_count': len(self.conversation.messages),
            'tags': list(conversation.metadata.tags),
            'category': conversation.metadata.category
        }
    
    # --- Enhanced Summary ---
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get enhanced conversation summary."""
        # Get base summary from parent
        base_summary = super().get_conversation_summary()
        
        # Add conversation management info
        base_summary.update({
            'conversation_id': self._current_conversation_id,
            'auto_save_enabled': self._auto_save_conversations,
            'auto_titles_enabled': self._auto_generate_titles,
            'auto_summaries_enabled': self._auto_generate_summaries
        })
        
        return base_summary
    
    # --- Shutdown ---
    
    def shutdown(self):
        """Shutdown the service with conversation saving using thread-safe patterns."""
        logger.info("Starting ConversationAIService shutdown...")
        
        try:
            # Save current conversation before shutdown using async manager
            if self._current_conversation_id and self._auto_save_conversations:
                logger.debug("Attempting to save conversation on shutdown...")
                try:
                    from ...async_manager import get_async_manager
                    
                    async_manager = get_async_manager()
                    if async_manager and async_manager.is_initialized():
                        # Use the async manager for thread-safe shutdown save
                        def on_shutdown_save_complete(result, error):
                            if error:
                                logger.warning(f"Failed to save conversation on shutdown: {error}")
                            else:
                                logger.debug("Conversation saved successfully during shutdown")
                        
                        async_manager.run_async_task(
                            self._save_current_conversation(),
                            callback=on_shutdown_save_complete,
                            timeout=5.0  # Short timeout for shutdown
                        )
                    else:
                        logger.debug("AsyncManager not available for shutdown save")
                        
                except Exception as e:
                    logger.warning(f"Failed to schedule conversation save on shutdown: {e}")
            
            # Shutdown conversation service using async manager
            if hasattr(self.conversation_service, 'shutdown'):
                logger.debug("Attempting to shutdown conversation service...")
                try:
                    from ...async_manager import get_async_manager
                    
                    async_manager = get_async_manager()
                    if async_manager and async_manager.is_initialized():
                        # Use async manager for thread-safe service shutdown
                        def on_service_shutdown_complete(result, error):
                            if error:
                                logger.warning(f"Failed to shutdown conversation service: {error}")
                            else:
                                logger.debug("Conversation service shutdown completed")
                        
                        async_manager.run_async_task(
                            self.conversation_service.shutdown(),
                            callback=on_service_shutdown_complete,
                            timeout=5.0  # Short timeout for shutdown
                        )
                    else:
                        logger.debug("AsyncManager not available for service shutdown")
                        
                except Exception as e:
                    logger.warning(f"Failed to schedule conversation service shutdown: {e}")
                
        except Exception as e:
            logger.error(f"Error during conversation service shutdown: {e}")
        finally:
            # Call parent shutdown
            try:
                super().shutdown()
            except Exception as e:
                logger.warning(f"Error during parent shutdown: {e}")
        
        logger.info("ConversationAIService shutdown completed")