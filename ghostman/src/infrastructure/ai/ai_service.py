"""
AI Service for Ghostman.

High-level service that manages AI interactions, conversation context,
and integrates with the OpenAI-compatible API client.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

from .api_client import OpenAICompatibleClient, APIResponse
from ...infrastructure.storage.settings_manager import settings

logger = logging.getLogger("ghostman.ai_service")


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class AIConfigurationError(AIServiceError):
    """AI service configuration error."""
    pass


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: Optional[int] = None


@dataclass 
class ConversationContext:
    """Manages conversation history and context."""
    messages: List[ConversationMessage] = field(default_factory=list)
    max_messages: int = 50  # Maximum messages to keep in context
    max_tokens: int = 32768  # Increased token limit for context (suitable for modern models)
    
    def add_message(self, role: str, content: str) -> ConversationMessage:
        """Add a message to the conversation."""
        message = ConversationMessage(role=role, content=content)
        self.messages.append(message)
        
        # Trim old messages if we exceed limits
        self._trim_context()
        
        return message
    
    def _trim_context(self):
        """Trim conversation context to stay within limits."""
        if len(self.messages) <= self.max_messages:
            return  # No trimming needed
            
        # Keep system message if it exists
        system_messages = [msg for msg in self.messages if msg.role == 'system']
        other_messages = [msg for msg in self.messages if msg.role != 'system']
        
        # Calculate how many non-system messages we can keep
        available_slots = self.max_messages - len(system_messages)
        
        # Trim other messages if needed, keeping the most recent ones
        if len(other_messages) > available_slots:
            # Keep most recent messages (preserve conversation flow)
            other_messages = other_messages[-available_slots:]
        
        # Rebuild messages list with system messages first
        self.messages = system_messages + other_messages
        
        # Log the trimming operation
        from datetime import datetime
        import logging
        logger = logging.getLogger("ghostman.ai_service")
        logger.info(f"🔄 Context trimmed to {len(self.messages)} messages (max: {self.max_messages})")
    
    def to_api_format(self) -> List[Dict[str, str]]:
        """Convert messages to API format."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def clear(self):
        """Clear all messages."""
        self.messages.clear()


class AIService:
    """
    High-level AI service for Ghostman.
    
    Manages AI interactions, conversation context, and API communication.
    """
    
    def __init__(self):
        self.client: Optional[OpenAICompatibleClient] = None
        self.conversation = ConversationContext()
        self._initialized = False
        self._config = {}
        
        # Response callbacks
        self._response_callbacks: List[Callable[[str], None]] = []
        
        logger.info("AIService created")
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the AI service with configuration.
        
        Args:
            config: Optional configuration dict. If None, loads from settings.
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing AI service...")
            
            # Load configuration
            if config:
                self._config = config
            else:
                self._config = self._load_config_from_settings()
            
            # Validate configuration
            if not self._validate_config():
                return False
            
            # Configure PKI if enabled before creating API client
            self._configure_pki_if_enabled()
            
            # Create API client
            self.client = OpenAICompatibleClient(
                base_url=self._config['base_url'],
                api_key=self._config.get('api_key'),
                timeout=self._config.get('timeout', 30),
                max_retries=self._config.get('max_retries', 3)
            )
            
            # Set up system prompt
            system_prompt = self._config.get('system_prompt', '')
            if system_prompt:
                self.conversation.add_message('system', system_prompt)
            
            self._initialized = True
            logger.info("✓ AI service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize AI service: {e}")
            return False
    
    def _load_config_from_settings(self) -> Dict[str, Any]:
        """Load AI configuration from settings manager."""
        config = {
            'model_name': settings.get('ai_model.model_name', 'gpt-3.5-turbo'),
            'base_url': settings.get('ai_model.base_url', 'https://api.openai.com/v1'),
            'api_key': settings.get('ai_model.api_key', ''),
            'temperature': settings.get('ai_model.temperature', 0.7),
            'max_tokens': settings.get('ai_model.max_tokens', 16384),  # Increased default for modern models
            'system_prompt': settings.get('ai_model.system_prompt', 'You are Spector, a helpful AI assistant.')
        }
        
        logger.debug("Configuration loaded from settings")
        return config
    
    def _validate_config(self) -> bool:
        """Validate the AI configuration."""
        required_fields = ['model_name', 'base_url']
        
        for field in required_fields:
            if not self._config.get(field):
                logger.error(f"Missing required configuration field: {field}")
                return False
        
        # Warn about missing API key (some local services don't need it)
        if not self._config.get('api_key'):
            logger.warning("No API key configured - this may be required for some services")
        
        # Validate URL format
        base_url = self._config['base_url']
        if not base_url.startswith(('http://', 'https://')):
            logger.error(f"Invalid base URL format: {base_url}")
            return False
        
        logger.debug("Configuration validation passed")
        return True
    
    def _configure_pki_if_enabled(self):
        """Configure PKI authentication if enabled."""
        try:
            from ..pki.pki_service import pki_service
            
            if pki_service.cert_manager.is_pki_enabled():
                cert_info = pki_service.cert_manager.get_client_cert_files()
                ca_bundle_path = pki_service.cert_manager.get_ca_chain_file()
                
                if cert_info:
                    from .session_manager import session_manager
                    session_manager.configure_pki(
                        cert_path=cert_info[0],  # client cert path
                        key_path=cert_info[1],   # client key path
                        ca_path=ca_bundle_path   # CA bundle path (can be None)
                    )
                    logger.info(f"✓ PKI configured for AI service: cert={cert_info[0]}, ca={'Yes' if ca_bundle_path else 'Default'}")
                else:
                    logger.warning("PKI is enabled but certificate files not available")
            else:
                logger.debug("PKI not enabled, using default SSL configuration")
                
        except Exception as e:
            logger.error(f"Failed to configure PKI for AI service: {e}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection.
        
        Returns:
            Dict with 'success', 'message', and optional 'details' keys
        """
        if not self._initialized:
            return {
                'success': False,
                'message': 'AI service not initialized'
            }
        
        try:
            logger.info("Testing AI service connection...")
            response = self.client.test_connection()
            
            if response.success:
                return {
                    'success': True,
                    'message': 'Connection successful',
                    'details': response.data
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection failed: {response.error}',
                    'details': {'status_code': response.status_code}
                }
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test error: {str(e)}'
            }
    
    async def send_message_async(
        self, 
        message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message to the AI asynchronously.
        
        Args:
            message: User message to send
            stream: Whether to stream the response
            
        Returns:
            Dict with response information
        """
        # Run the synchronous send_message in an executor to avoid blocking the event loop
        import asyncio
        import concurrent.futures
        
        # Create executor if not exists
        if not hasattr(self, '_executor'):
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Run sync method in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.send_message(message, stream=stream)
        )
    
    def send_message(
        self, 
        message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message to the AI and get a response.
        
        Args:
            message: User message to send
            stream: Whether to stream the response (not implemented yet)
            
        Returns:
            Dict with response information including 'success', 'response', 'error'
        """
        if not self._initialized:
            logger.error("AI service not initialized")
            return {
                'success': False,
                'error': 'AI service not initialized'
            }
        
        try:
            logger.info(f"Sending message to AI: {message[:100]}...")
            
            # Add user message to conversation
            self.conversation.add_message('user', message)
            
            # Prepare API request
            api_messages = self.conversation.to_api_format()
            
            # Log the full context being sent
            logger.debug(f"Full conversation context ({len(api_messages)} messages):")
            for i, msg in enumerate(api_messages):
                preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                logger.debug(f"  Message {i+1} [{msg['role']}]: {preview}")
            
            # Prepare parameters for API request
            model_name = self._config['model_name']
            api_params = {
                'messages': api_messages,
                'model': model_name,
                'temperature': self._config['temperature'],
                'max_tokens': self._config.get('max_tokens'),
                'stream': stream
            }
            
            # Add GPT-5 specific parameters for better responses
            if model_name.startswith('gpt-5'):
                # Default verbosity to 'medium' for gpt-5-nano to ensure content generation
                api_params['verbosity'] = 'medium'
                logger.debug(f"Using default verbosity 'medium' for {model_name}")
                
                # Set reasoning_effort to 'low' for gpt-5-nano for faster responses
                if 'nano' in model_name.lower():
                    api_params['reasoning_effort'] = 'low'
                    logger.debug(f"Using reasoning_effort 'low' for {model_name}")
                    
                    # Handle max_tokens for gpt-5-nano properly (remove hard cap)
                    current_max_tokens = api_params.get('max_tokens', 16384)
                    if current_max_tokens:
                        # gpt-5-nano supports up to 128k tokens, don't artificially limit it
                        # Only adjust for very small requests that need reasoning overhead
                        if current_max_tokens < 200:
                            # Small requests need more tokens for reasoning overhead
                            adjusted_tokens = max(200, current_max_tokens * 2)
                            api_params['max_tokens'] = adjusted_tokens
                            logger.info(f"Adjusted max_tokens from {current_max_tokens} to {adjusted_tokens} for {model_name} (small request reasoning buffer)")
                        else:
                            # For normal and large requests, respect user's token setting
                            # gpt-5-nano can handle up to 128k tokens efficiently
                            logger.info(f"Using user-specified max_tokens {current_max_tokens} for {model_name} (no artificial cap)")
                            # Keep the original max_tokens value - don't cap it
            
            # Make API request
            response = self.client.chat_completion(**api_params)
            
            # Log raw response for debugging gpt-5-nano
            if model_name.startswith('gpt-5'):
                logger.info(f"🔍 GPT-5 RAW RESPONSE - Success: {response.success}")
                logger.info(f"🔍 GPT-5 RAW RESPONSE - Status code: {response.status_code}")
                logger.info(f"🔍 GPT-5 RAW RESPONSE - Data keys: {list(response.data.keys()) if response.data else None}")
                logger.info(f"🔍 GPT-5 RAW RESPONSE - Full data: {response.data}")
            
            if response.success:
                # Extract response content
                assistant_message = self._extract_response_content(response.data)
                
                # Log the AI response
                preview = assistant_message[:200] + "..." if len(assistant_message) > 200 else assistant_message
                logger.info(f"AI response received: {preview}")
                logger.debug(f"Full AI response: {assistant_message}")
                
                # Add assistant response to conversation
                self.conversation.add_message('assistant', assistant_message)
                
                # Log conversation state after response
                logger.debug(f"Conversation now has {len(self.conversation.messages)} messages")
                
                # Call response callbacks
                for callback in self._response_callbacks:
                    try:
                        callback(assistant_message)
                    except Exception as e:
                        logger.error(f"Response callback error: {e}")
                
                logger.info("✓ AI response received successfully")
                return {
                    'success': True,
                    'response': assistant_message,
                    'usage': response.data.get('usage', {})
                }
            else:
                logger.error(f"✗ AI API request failed: {response.error}")
                return {
                    'success': False,
                    'error': response.error
                }
                
        except Exception as e:
            logger.error(f"✗ Error sending message to AI: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_response_content(self, api_response: Dict[str, Any]) -> str:
        """Extract the text content from an API response."""
        try:
            # Debug: Log the full API response structure
            logger.info(f"🔍 EXTRACTING RESPONSE CONTENT - Raw API response keys: {list(api_response.keys())}")
            logger.debug(f"🔍 EXTRACTING RESPONSE CONTENT - Full API response: {api_response}")
            
            # Check for empty or null response first
            if not api_response:
                logger.error("🔍 EXTRACTING - API response is empty or None")
                return "[No response content received]"
            
            # Standard OpenAI format
            if 'choices' in api_response and api_response['choices']:
                choice = api_response['choices'][0]
                logger.info(f"🔍 EXTRACTING - Found choices format, choice keys: {list(choice.keys())}")
                
                # Handle different choice formats
                if 'message' in choice and choice['message']:
                    message = choice['message']
                    content = message.get('content', '')
                    logger.info(f"🔍 EXTRACTING - Message content type: {type(content)}, value: '{content}'")
                    
                    # Handle empty content specifically
                    if content is None or content == '':
                        logger.warning("🔍 EXTRACTING - Message content is empty or None")
                        # Check if there's a finish_reason that explains why
                        finish_reason = choice.get('finish_reason', 'unknown')
                        logger.warning(f"🔍 EXTRACTING - Finish reason: {finish_reason}")
                        return f"[No response content received - finish_reason: {finish_reason}]"
                    
                    return str(content)
                    
                elif 'text' in choice:
                    content = choice['text']
                    logger.info(f"🔍 EXTRACTING - Extracted from text: '{content}'")
                    return str(content) if content is not None else "[No text content]"
                
                elif 'delta' in choice and 'content' in choice['delta']:
                    # Streaming format
                    content = choice['delta']['content']
                    logger.info(f"🔍 EXTRACTING - Extracted from delta.content: '{content}'")
                    return str(content) if content is not None else "[No delta content]"
                
                else:
                    logger.warning(f"🔍 EXTRACTING - Choice has unexpected format: {choice}")
                    return f"[Unexpected choice format: {list(choice.keys())}]"
            
            # Check if choices array is empty
            elif 'choices' in api_response:
                logger.warning("🔍 EXTRACTING - Choices array is empty")
                return "[No choices in response]"
            
            # Anthropic Claude format
            if 'content' in api_response:
                content = api_response['content']
                logger.info(f"🔍 EXTRACTING - Found content format, type: {type(content)}")
                if isinstance(content, list) and content:
                    extracted = content[0].get('text', '')
                    logger.info(f"🔍 EXTRACTING - Extracted from content[0].text: '{extracted}'")
                    return str(extracted) if extracted else "[No text in content array]"
                elif isinstance(content, str):
                    logger.info(f"🔍 EXTRACTING - Extracted from content string: '{content}'")
                    return content if content else "[Empty content string]"
            
            # Check for error in response
            if 'error' in api_response:
                error_info = api_response['error']
                logger.error(f"🔍 EXTRACTING - API returned error: {error_info}")
                return f"[API Error: {error_info}]"
            
            # Fallback - try to find any text content
            logger.warning(f"🔍 EXTRACTING - Unrecognized response format. Available keys: {list(api_response.keys())}")
            
            # Check specific keys that might contain content
            potential_content_keys = ['text', 'output', 'result', 'response', 'data']
            for key in potential_content_keys:
                if key in api_response and api_response[key]:
                    logger.info(f"🔍 EXTRACTING - Found content in '{key}': {api_response[key]}")
                    return str(api_response[key])
            
            return f"[Unrecognized response format - keys: {list(api_response.keys())}]"
            
        except Exception as e:
            logger.error(f"🔍 EXTRACTING - Failed to extract response content: {e}")
            import traceback
            logger.error(f"🔍 EXTRACTING - Stack trace: {traceback.format_exc()}")
            return f"[Error processing response: {str(e)}]"
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the AI service configuration.
        
        Args:
            config: New configuration values
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Update configuration
            self._config.update(config)
            
            # Validate new configuration
            if not self._validate_config():
                return False
            
            # Reconfigure PKI if needed
            self._configure_pki_if_enabled()
            
            # Reinitialize client if needed
            if self.client:
                self.client.close()
            
            self.client = OpenAICompatibleClient(
                base_url=self._config['base_url'],
                api_key=self._config.get('api_key'),
                timeout=self._config.get('timeout', 30),
                max_retries=self._config.get('max_retries', 3)
            )
            
            # Update system prompt if changed
            system_prompt = self._config.get('system_prompt', '')
            if system_prompt:
                # Remove old system messages and add new one
                self.conversation.messages = [
                    msg for msg in self.conversation.messages 
                    if msg.role != 'system'
                ]
                self.conversation.add_message('system', system_prompt)
            
            logger.info("✓ AI service configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to update AI service configuration: {e}")
            return False
    
    def clear_conversation(self):
        """Clear the conversation history."""
        # Keep system message if it exists
        system_messages = [msg for msg in self.conversation.messages if msg.role == 'system']
        self.conversation.clear()
        
        # Re-add system messages
        for msg in system_messages:
            self.conversation.add_message('system', msg.content)
        
        logger.info("Conversation history cleared")
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        return {
            'message_count': len(self.conversation.messages),
            'last_message_time': (
                self.conversation.messages[-1].timestamp.isoformat()
                if self.conversation.messages else None
            ),
            'config': {
                'model': self._config.get('model_name'),
                'base_url': self._config.get('base_url'),
                'has_api_key': bool(self._config.get('api_key'))
            }
        }
    
    def add_response_callback(self, callback: Callable[[str], None]):
        """Add a callback to be called when a response is received."""
        self._response_callbacks.append(callback)
    
    def remove_response_callback(self, callback: Callable[[str], None]):
        """Remove a response callback."""
        if callback in self._response_callbacks:
            self._response_callbacks.remove(callback)
    
    def shutdown(self):
        """Shutdown the AI service."""
        if self.client:
            self.client.close()
            self.client = None
        
        # Shutdown executor if it exists
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
            delattr(self, '_executor')
        
        self._initialized = False
        self._response_callbacks.clear()
        logger.info("AI service shut down")
    
    async def send_message_without_system_prompt_async(
        self, 
        message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message to the AI without system prompt (for title generation).
        
        Args:
            message: User message to send
            stream: Whether to stream the response
            
        Returns:
            Dict with response information
        """
        # Run the synchronous method in an executor
        import asyncio
        import concurrent.futures
        
        # Create executor if not exists
        if not hasattr(self, '_executor'):
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Run sync method in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.send_message_without_system_prompt(message, stream=stream)
        )
    
    def send_message_without_system_prompt(
        self, 
        message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message to the AI without system prompt (for title generation).
        
        Args:
            message: User message to send
            stream: Whether to stream the response
            
        Returns:
            Dict with response information including 'success', 'response', 'error'
        """
        if not self._initialized:
            logger.error("AI service not initialized")
            return {
                'success': False,
                'error': 'AI service not initialized'
            }
        
        try:
            # Create messages list without system prompt (just the user message)
            messages = [
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            model_name = self._config.get('model_name', 'gpt-3.5-turbo')
            api_params = {
                "model": model_name,
                "messages": messages,
                "temperature": self._config.get('temperature', 0.7),
                "max_tokens": self._config.get('max_tokens', 16384),  # Updated default
                "stream": stream
            }
            
            # Add GPT-5 specific parameters for better responses
            if model_name.startswith('gpt-5'):
                # Default verbosity to 'medium' for gpt-5-nano to ensure content generation
                api_params['verbosity'] = 'medium'
                logger.debug(f"Using default verbosity 'medium' for {model_name} (title generation)")
                
                # Set reasoning_effort to 'low' for gpt-5-nano for faster responses
                if 'nano' in model_name.lower():
                    api_params['reasoning_effort'] = 'low'
                    logger.debug(f"Using reasoning_effort 'low' for {model_name} (title generation)")
                    
                    # Limit max_tokens for gpt-5-nano to avoid issues (titles should be short anyway)
                    current_max_tokens = api_params.get('max_tokens', 16384)
                    if current_max_tokens and current_max_tokens > 100:
                        api_params['max_tokens'] = 100
                        logger.info(f"Reduced max_tokens from {current_max_tokens} to 100 for {model_name} title generation")
            
            logger.debug(f"Sending title generation request (no system prompt): {len(messages)} messages")
            
            # Make request using the existing client infrastructure
            response = self.client.chat_completion(**api_params)
            
            if response.success:
                # Extract response content using existing method
                assistant_message = self._extract_response_content(response.data)
                
                logger.debug(f"Title generation response received: {len(assistant_message) if assistant_message else 0} chars")
                
                return {
                    'success': True,
                    'response': assistant_message,
                    'usage': response.data.get('usage', {})
                }
            else:
                logger.error(f"Title generation API request failed: {response.error}")
                return {
                    'success': False,
                    'error': response.error
                }
                    
        except Exception as e:
            logger.error(f"Error sending title generation message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @property
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized
    
    @property
    def current_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self._config.copy()