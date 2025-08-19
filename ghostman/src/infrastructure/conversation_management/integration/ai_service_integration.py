"""
Integration between conversation management and existing AI service.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...ai.ai_service import AIService, ConversationContext, ConversationMessage
from ..models.conversation import Conversation, Message
from ..models.enums import MessageRole
from ..services.conversation_service import ConversationService

logger = logging.getLogger("ghostman.ai_integration")


class ConversationContextAdapter:
    """Adapter to bridge ConversationContext with Conversation model."""
    
    @staticmethod
    def to_conversation_context(conversation: Conversation) -> ConversationContext:
        """Convert Conversation to ConversationContext."""
        import logging
        logger = logging.getLogger("ghostman.ai_integration")
        
        context = ConversationContext(
            max_messages=conversation.metadata.custom_fields.get('max_messages', 50),
            max_tokens=conversation.metadata.estimated_tokens or 8000
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
        
        logger.info("ConversationAIService initialized")
    
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
            
            # Create new conversation
            conversation = await self.conversation_service.create_conversation(
                title=title or "New Conversation",
                initial_message=system_prompt,
                tags=tags,
                category=category
            )
            
            # Set as active
            self._current_conversation_id = conversation.id
            self.conversation_service.set_active_conversation(conversation.id)
            
            # Clear current context and reload from conversation
            logger.info(f"🔍 NEW CONVERSATION - Before clear: {len(self.conversation.messages)} messages")
            self.conversation.clear()
            logger.info(f"🔍 NEW CONVERSATION - After clear: {len(self.conversation.messages)} messages")
            
            await self._load_conversation_context(conversation.id)
            logger.info(f"🔍 NEW CONVERSATION - After load: {len(self.conversation.messages)} messages")
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
        save_conversation: bool = True
    ) -> Dict[str, Any]:
        """
        Send message with automatic conversation saving and robust persistence.
        
        Args:
            message: User message to send
            stream: Whether to stream the response
            save_conversation: Whether to save to conversation management
            
        Returns:
            Dict with response information
        """
        # Log the request with context info
        logger.info(f"💬 Sending message with conversation context (current: {self._current_conversation_id})")
        logger.debug(f"💬 Context before send: {len(self.conversation.messages)} messages")
        
        # Ensure we have a conversation to save to
        if save_conversation and self._auto_save_conversations and not self._current_conversation_id:
            logger.info("🆕 No active conversation, creating new one for message")
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    conversation_id = loop.run_until_complete(self.start_new_conversation())
                    if conversation_id:
                        logger.info(f"✓ Created new conversation for message: {conversation_id}")
                    else:
                        logger.error("✗ Failed to create conversation for message")
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"✗ Failed to create conversation for message: {e}")
        
        # Call parent method
        result = super().send_message(message, stream)
        
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
                try:
                    logger.debug("💾 Starting immediate conversation save...")
                    
                    def save_conversation_immediate():
                        try:
                            import asyncio
                            
                            # Try to use existing event loop if available
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # If loop is running, create a task
                                    asyncio.create_task(self._save_current_conversation())
                                    logger.debug("💾 Scheduled save as async task")
                                else:
                                    # Loop exists but not running, run until complete
                                    loop.run_until_complete(self._save_current_conversation())
                                    logger.debug("💾 Completed immediate save")
                            except RuntimeError:
                                # No event loop, create new one
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(self._save_current_conversation())
                                    logger.debug("💾 Completed save with new loop")
                                finally:
                                    loop.close()
                                    
                        except Exception as e:
                            logger.error(f"✗ Failed to save conversation immediately: {e}", exc_info=True)
                    
                    # Try immediate save first
                    save_conversation_immediate()
                    
                    # Also schedule a backup save with delay for safety
                    try:
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(500, save_conversation_immediate)
                        logger.debug("💾 Scheduled backup save in 500ms")
                    except Exception as e:
                        logger.debug(f"Could not schedule backup save: {e}")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to save conversation: {e}", exc_info=True)
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
            # Ensure we have an active conversation
            if not self._current_conversation_id:
                # Create new conversation if none exists
                conversation_id = await self.start_new_conversation()
                if not conversation_id:
                    logger.error("Failed to create conversation for saving")
                    return
            
            logger.debug(f"💾 Saving conversation context for {self._current_conversation_id}")
            logger.debug(f"💾 Current AI context has {len(self.conversation.messages)} messages")
            
            # Get the latest messages that need to be saved
            conversation = await self.conversation_service.get_conversation(
                self._current_conversation_id, include_messages=True
            )
            if not conversation:
                logger.error(f"Active conversation not found: {self._current_conversation_id}")
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
        """Set the current conversation ID and load its context."""
        try:
            logger.info(f"Setting current conversation to: {conversation_id}")
            self._current_conversation_id = conversation_id
            
            # Load conversation context - try sync first for better reliability
            try:
                self._load_conversation_context_sync(conversation_id)
            except Exception as e:
                logger.warning(f"Sync context loading failed, trying async: {e}")
                # Fallback to async
                import asyncio
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule the context loading as a task
                        asyncio.create_task(self._load_conversation_context(conversation_id))
                    else:
                        # Run synchronously
                        loop.run_until_complete(self._load_conversation_context(conversation_id))
                except RuntimeError:
                    # No event loop - create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._load_conversation_context(conversation_id))
                    loop.close()
                
        except Exception as e:
            logger.error(f"Failed to set current conversation {conversation_id}: {e}")
    
    def _load_conversation_context_sync(self, conversation_id: str):
        """Load conversation context synchronously using async tools."""
        import asyncio
        
        # Create a new event loop for this operation
        loop = asyncio.new_event_loop()
        old_loop = None
        try:
            # Check if there's an existing loop
            try:
                old_loop = asyncio.get_event_loop()
            except RuntimeError:
                pass  # No current loop
            
            # Set our new loop
            asyncio.set_event_loop(loop)
            
            # Run the async operation
            loop.run_until_complete(self._load_conversation_context(conversation_id))
            
        finally:
            # Clean up
            loop.close()
            if old_loop:
                asyncio.set_event_loop(old_loop)
    
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
        """Shutdown the service with conversation saving."""
        try:
            # Save current conversation before shutdown
            if self._current_conversation_id and self._auto_save_conversations:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if not loop.is_running():
                        loop.run_until_complete(self._save_current_conversation())
                except Exception as e:
                    logger.warning(f"Failed to save conversation on shutdown: {e}")
            
            # Shutdown conversation service
            if hasattr(self.conversation_service, 'shutdown'):
                asyncio.get_event_loop().run_until_complete(self.conversation_service.shutdown())
                
        except Exception as e:
            logger.error(f"Error during conversation service shutdown: {e}")
        finally:
            # Call parent shutdown
            super().shutdown()
        
        logger.info("ConversationAIService shut down")