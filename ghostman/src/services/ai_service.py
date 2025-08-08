"""AI service integration for Ghostman."""

import asyncio
import logging
from typing import Optional, Callable, Any
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
import openai
from dataclasses import dataclass
from typing import List
from services.models import SimpleMessage

class AIProvider(Enum):
    OPENAI = "openai"

@dataclass
class AIConfig:
    """AI service configuration."""
    provider: AIProvider = AIProvider.OPENAI
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"  # Support custom endpoints
    model: str = "gpt-3.5-turbo"  # Support any model name
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30
    max_conversation_tokens: int = 4000

class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass

class APIKeyError(AIServiceError):
    """API key related errors."""
    pass

class RateLimitError(AIServiceError):
    """Rate limit exceeded errors."""
    pass

class NetworkError(AIServiceError):
    """Network connectivity errors."""
    pass

class AIRequestWorker(QThread):
    """Worker thread for AI requests to avoid blocking the UI."""
    
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    
    def __init__(self, config: AIConfig, messages: list, parent=None):
        super().__init__(parent)
        self.config = config
        self.messages = messages
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Execute the AI request in background thread."""
        try:
            # Set up OpenAI client with custom base URL if specified
            client_kwargs = {'api_key': self.config.api_key}
            if hasattr(self.config, 'api_base') and self.config.api_base != "https://api.openai.com/v1":
                client_kwargs['base_url'] = self.config.api_base
            client = openai.OpenAI(**client_kwargs)
            
            # Convert messages to OpenAI format
            openai_messages = []
            for msg in self.messages:
                role = "user" if msg.is_user else "assistant"
                openai_messages.append({"role": role, "content": msg.content})
            
            # Make the request
            response = client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            # Extract response
            if response.choices and len(response.choices) > 0:
                ai_response = response.choices[0].message.content
                if ai_response:
                    self.response_ready.emit(ai_response)
                else:
                    self.error_occurred.emit("empty_response", "AI returned empty response")
            else:
                self.error_occurred.emit("no_choices", "AI returned no response choices")
                
        except openai.AuthenticationError as e:
            self.error_occurred.emit("auth_error", "Invalid API key. Please check your OpenAI API key in settings.")
        except openai.RateLimitError as e:
            self.error_occurred.emit("rate_limit", "Rate limit exceeded. Please try again later.")
        except openai.APITimeoutError as e:
            self.error_occurred.emit("timeout", f"Request timed out after {self.config.timeout} seconds.")
        except openai.APIConnectionError as e:
            self.error_occurred.emit("network_error", "Unable to connect to OpenAI. Please check your internet connection.")
        except openai.APIError as e:
            self.error_occurred.emit("api_error", f"OpenAI API error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error in AI request: {e}")
            self.error_occurred.emit("unexpected_error", f"Unexpected error: {str(e)}")

class AIService(QObject):
    """Main AI service for handling AI requests and responses."""
    
    # Signals
    response_received = pyqtSignal(str)  # AI response text
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    request_started = pyqtSignal()
    request_finished = pyqtSignal()
    
    def __init__(self, config_path: Optional[Path] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration - use APPDATA on Windows, fallback to home on other systems
        if config_path:
            self.config_path = config_path
        else:
            import os
            if os.name == 'nt':  # Windows
                appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.config_path = Path(appdata) / "Ghostman" / "ai_config.json"
            else:
                self.config_path = Path.home() / ".ghostman" / "ai_config.json"
        
        self.config = AIConfig()
        
        # State
        self.conversation_history: List[SimpleMessage] = []
        self.is_processing = False
        self.current_worker = None
        self.current_session_id = None
        
        # Storage (lazy import to avoid circular dependency)
        from services.conversation_storage import ConversationStorage
        self.storage = ConversationStorage()
        
        # Load configuration
        self.load_config()
        
        # Request timeout timer
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self.handle_timeout)
        self.timeout_timer.setSingleShot(True)
        
        self.logger.info("AI service initialized")
    
    def load_config(self):
        """Load AI configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Update config from loaded data
                if 'provider' in data:
                    self.config.provider = AIProvider(data['provider'])
                if 'api_key' in data:
                    self.config.api_key = data['api_key']
                if 'api_base' in data:
                    self.config.api_base = data['api_base']
                if 'model' in data:
                    self.config.model = data['model']
                if 'max_tokens' in data:
                    self.config.max_tokens = data['max_tokens']
                if 'temperature' in data:
                    self.config.temperature = data['temperature']
                if 'timeout' in data:
                    self.config.timeout = data['timeout']
                if 'max_conversation_tokens' in data:
                    self.config.max_conversation_tokens = data['max_conversation_tokens']
                
                self.logger.info("AI configuration loaded")
            else:
                self.logger.info("No AI configuration found, using defaults")
                self.save_config()  # Save default config
                
        except Exception as e:
            self.logger.error(f"Error loading AI configuration: {e}")
            # Use default config
    
    def save_config(self):
        """Save AI configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = {
                'provider': self.config.provider.value,
                'api_key': self.config.api_key,
                'api_base': self.config.api_base,
                'model': self.config.model,
                'max_tokens': self.config.max_tokens,
                'temperature': self.config.temperature,
                'timeout': self.config.timeout,
                'max_conversation_tokens': self.config.max_conversation_tokens
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            
            self.logger.info("AI configuration saved")
            
        except Exception as e:
            self.logger.error(f"Error saving AI configuration: {e}")
    
    def update_config(self, **kwargs):
        """Update AI configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.debug(f"Updated AI config: {key} = {value}")
        
        self.save_config()
    
    def is_configured(self) -> bool:
        """Check if AI service is properly configured."""
        return bool(self.config.api_key.strip())
    
    def validate_config(self) -> tuple[bool, str]:
        """Validate the current configuration."""
        if not self.config.api_key.strip():
            return False, "API key is required"
        
        if self.config.max_tokens <= 0:
            return False, "Max tokens must be greater than 0"
        
        if not (0.0 <= self.config.temperature <= 2.0):
            return False, "Temperature must be between 0.0 and 2.0"
        
        if self.config.timeout <= 0:
            return False, "Timeout must be greater than 0"
        
        return True, "Configuration is valid"
    
    def send_message(self, message: str) -> bool:
        """Send a message to the AI and get a response."""
        if self.is_processing:
            self.logger.warning("AI request already in progress")
            return False
        
        if not self.is_configured():
            self.error_occurred.emit("not_configured", "AI service is not configured. Please set your API key in settings.")
            return False
        
        # Validate config
        is_valid, error_msg = self.validate_config()
        if not is_valid:
            self.error_occurred.emit("invalid_config", f"Configuration error: {error_msg}")
            return False
        
        try:
            # Add user message to conversation
            user_message = SimpleMessage(content=message, is_user=True)
            self.conversation_history.append(user_message)
            
            # Check token limits and manage conversation
            self.manage_conversation_length()
            
            # Prepare messages for AI request
            messages = list(self.conversation_history)
            
            # Start processing
            self.is_processing = True
            self.request_started.emit()
            
            # Create and start worker thread
            self.current_worker = AIRequestWorker(self.config, messages)
            self.current_worker.response_ready.connect(self.handle_response)
            self.current_worker.error_occurred.connect(self.handle_error)
            self.current_worker.finished.connect(self.cleanup_worker)
            self.current_worker.start()
            
            # Start timeout timer
            self.timeout_timer.start(self.config.timeout * 1000 + 5000)  # Add 5s buffer
            
            self.logger.info(f"AI request sent: {message[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message to AI: {e}")
            self.error_occurred.emit("send_error", f"Error sending message: {str(e)}")
            self.is_processing = False
            return False
    
    def handle_response(self, response: str):
        """Handle AI response."""
        try:
            # Stop timeout timer
            self.timeout_timer.stop()
            
            # Add AI response to conversation
            ai_message = SimpleMessage(content=response, is_user=False)
            self.conversation_history.append(ai_message)
            
            # Emit response
            self.response_received.emit(response)
            
            self.logger.info(f"AI response received: {response[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error handling AI response: {e}")
            self.error_occurred.emit("response_error", f"Error processing response: {str(e)}")
    
    def handle_error(self, error_type: str, error_message: str):
        """Handle AI request errors."""
        self.timeout_timer.stop()
        self.error_occurred.emit(error_type, error_message)
        self.logger.error(f"AI request error ({error_type}): {error_message}")
    
    def handle_timeout(self):
        """Handle request timeout."""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait(1000)  # Wait up to 1 second for termination
        
        self.error_occurred.emit("timeout", f"Request timed out after {self.config.timeout} seconds")
        self.logger.warning("AI request timed out")
    
    def cleanup_worker(self):
        """Clean up worker thread."""
        self.is_processing = False
        self.request_finished.emit()
        
        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None
    
    def manage_conversation_length(self):
        """Manage conversation length to stay within token limits."""
        try:
            # Simple approach: keep last N messages if we exceed limit
            if len(self.conversation_history) > 20:  # Simple limit
                # Keep last 15 messages (preserve recent context)
                self.conversation_history = self.conversation_history[-15:]
                self.logger.info(f"Conversation trimmed to {len(self.conversation_history)} messages")
                
        except Exception as e:
            self.logger.error(f"Error managing conversation length: {e}")
    
    def clear_conversation(self):
        """Clear the current conversation."""
        # Save current conversation before clearing
        if self.conversation_history:
            self.current_session_id = self.storage.save_conversation(self.conversation_history, self.current_session_id)
        
        self.conversation_history = []
        self.current_session_id = None
        self.logger.info("Conversation cleared")
    
    def cancel_request(self):
        """Cancel the current AI request."""
        if self.is_processing and self.current_worker:
            self.timeout_timer.stop()
            self.current_worker.terminate()
            self.current_worker.wait(1000)
            self.logger.info("AI request cancelled")
    
    def get_conversation(self) -> List[SimpleMessage]:
        """Get the current conversation."""
        return self.conversation_history
    
    def get_config(self) -> AIConfig:
        """Get the current AI configuration."""
        return self.config
    
    def save_current_conversation(self) -> str:
        """Save the current conversation and return session ID."""
        if self.conversation_history:
            self.current_session_id = self.storage.save_conversation(self.conversation_history, self.current_session_id)
            return self.current_session_id
        return ""
    
    def load_conversation(self, session_id: str) -> bool:
        """Load a conversation from storage."""
        try:
            messages = self.storage.load_conversation(session_id)
            if messages:
                self.conversation_history = messages
                self.current_session_id = session_id
                self.logger.info(f"Loaded conversation {session_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error loading conversation: {e}")
            return False
    
    def list_conversations(self):
        """Get list of saved conversations."""
        return self.storage.list_conversations()