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
    max_tokens: int = 8000  # Approximate token limit for context
    
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
            logger.info("✅ AI service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI service: {e}")
            return False
    
    def _load_config_from_settings(self) -> Dict[str, Any]:
        """Load AI configuration from settings manager."""
        config = {
            'model_name': settings.get('ai_model.model_name', 'gpt-3.5-turbo'),
            'base_url': settings.get('ai_model.base_url', 'https://api.openai.com/v1'),
            'api_key': settings.get('ai_model.api_key', ''),
            'temperature': settings.get('ai_model.temperature', 0.7),
            'max_tokens': settings.get('ai_model.max_tokens', 2000),
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
        # For now, call the sync version
        # TODO: Implement proper async support
        return self.send_message(message, stream=stream)
    
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
            
            # Make API request
            response = self.client.chat_completion(
                messages=api_messages,
                model=self._config['model_name'],
                temperature=self._config['temperature'],
                max_tokens=self._config.get('max_tokens'),
                stream=stream
            )
            
            if response.success:
                # Extract response content
                assistant_message = self._extract_response_content(response.data)
                
                # Add assistant response to conversation
                self.conversation.add_message('assistant', assistant_message)
                
                # Call response callbacks
                for callback in self._response_callbacks:
                    try:
                        callback(assistant_message)
                    except Exception as e:
                        logger.error(f"Response callback error: {e}")
                
                logger.info("✅ AI response received successfully")
                return {
                    'success': True,
                    'response': assistant_message,
                    'usage': response.data.get('usage', {})
                }
            else:
                logger.error(f"❌ AI API request failed: {response.error}")
                return {
                    'success': False,
                    'error': response.error
                }
                
        except Exception as e:
            logger.error(f"❌ Error sending message to AI: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_response_content(self, api_response: Dict[str, Any]) -> str:
        """Extract the text content from an API response."""
        try:
            # Standard OpenAI format
            if 'choices' in api_response and api_response['choices']:
                choice = api_response['choices'][0]
                if 'message' in choice:
                    return choice['message'].get('content', '')
                elif 'text' in choice:
                    return choice['text']
            
            # Anthropic Claude format
            if 'content' in api_response:
                content = api_response['content']
                if isinstance(content, list) and content:
                    return content[0].get('text', '')
                elif isinstance(content, str):
                    return content
            
            # Fallback - try to find any text content
            response_str = str(api_response)
            logger.warning(f"Unrecognized response format, returning as string: {response_str[:100]}...")
            return response_str
            
        except Exception as e:
            logger.error(f"Failed to extract response content: {e}")
            return "Sorry, I couldn't process the response properly."
    
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
            
            logger.info("✅ AI service configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update AI service configuration: {e}")
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
        
        self._initialized = False
        self._response_callbacks.clear()
        logger.info("AI service shut down")
    
    @property
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._initialized
    
    @property
    def current_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self._config.copy()