"""
Tests for AI Service functionality.

Covers API client, AI service, error handling, and configuration.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add project root to path for imports
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from specter.src.infrastructure.ai.api_client import (
    OpenAICompatibleClient, 
    APIResponse, 
    AuthenticationError, 
    RateLimitError, 
    APIServerError
)
from specter.src.infrastructure.ai.ai_service import (
    AIService, 
    ConversationContext, 
    ConversationMessage,
    AIConfigurationError
)


class TestOpenAICompatibleClient:
    """Test cases for OpenAI-compatible API client."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.base_url = "https://api.openai.com/v1"
        self.api_key = "test-api-key"
        self.client = OpenAICompatibleClient(
            self.base_url, self.api_key, retry_delay=0.0
        )
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
    
    def test_client_initialization(self):
        """Test client initialization with various parameters."""
        assert self.client.base_url == self.base_url
        assert self.client.api_key == self.api_key
        assert self.client.timeout == 30
        assert self.client.max_retries == 3
        
        # Test with custom parameters
        custom_client = OpenAICompatibleClient(
            base_url="https://api.anthropic.com/v1",
            api_key="anthropic-key",
            timeout=60,
            max_retries=5,
            retry_delay=2.0
        )
        
        assert custom_client.base_url == "https://api.anthropic.com/v1"
        assert custom_client.timeout == 60
        assert custom_client.max_retries == 5
        assert custom_client.retry_delay == 2.0
        
        custom_client.close()
    
    @patch('specter.src.infrastructure.ai.api_client.session_manager')
    def test_successful_request(self, mock_sm):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Hello!"}}]}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"choices": [{"message": {"content": "Hello!"}}]}'
        mock_sm.make_request.return_value = mock_response

        result = self.client._make_request("POST", "chat/completions", {"model": "gpt-3.5-turbo"})

        assert result.success is True
        assert result.data == {"choices": [{"message": {"content": "Hello!"}}]}
        assert result.status_code == 200

    @patch('specter.src.infrastructure.ai.api_client.session_manager')
    def test_authentication_error(self, mock_sm):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.headers = {}
        mock_sm.make_request.return_value = mock_response

        result = self.client._make_request("POST", "chat/completions")

        assert result.success is False
        assert "Authentication failed" in result.error
        assert result.status_code == 401

    @patch('specter.src.infrastructure.ai.api_client.time.sleep')
    @patch('specter.src.infrastructure.ai.api_client.session_manager')
    def test_rate_limit_error(self, mock_sm, mock_sleep):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        mock_response.headers = {"retry-after": "60"}
        mock_sm.make_request.return_value = mock_response

        # Client retries on 429 with retry-after, so after max_retries it returns error
        result = self.client._make_request("POST", "chat/completions")

        assert result.success is False
        assert "Rate limit exceeded" in result.error
        assert result.status_code == 429

    @patch('specter.src.infrastructure.ai.api_client.time.sleep')
    @patch('specter.src.infrastructure.ai.api_client.session_manager')
    def test_server_error_with_retry(self, mock_sm, mock_sleep):
        """Test server error with retry logic."""
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_error.json.return_value = {"error": {"message": "Internal server error"}}
        mock_response_error.headers = {}

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"choices": [{"message": {"content": "Success"}}]}
        mock_response_success.headers = {"content-type": "application/json"}
        mock_response_success.text = '{"choices": [{"message": {"content": "Success"}}]}'

        mock_sm.make_request.side_effect = [mock_response_error, mock_response_success]

        result = self.client._make_request("POST", "chat/completions")

        assert result.success is True
        assert mock_sm.make_request.call_count == 2  # Initial + 1 retry

    @patch('specter.src.infrastructure.ai.api_client.time.sleep')
    @patch('specter.src.infrastructure.ai.api_client.session_manager')
    def test_timeout_with_retry(self, mock_sm, mock_sleep):
        """Test timeout handling with retry."""
        import requests as req

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Success"}}]}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"choices": [{"message": {"content": "Success"}}]}'

        mock_sm.make_request.side_effect = [req.Timeout("Timeout"), mock_response]

        result = self.client._make_request("POST", "chat/completions")

        assert result.success is True
        assert mock_sm.make_request.call_count == 2
    
    def test_chat_completion_parameters(self):
        """Test chat completion parameter handling."""
        with patch.object(self.client, '_make_request') as mock_make_request:
            mock_make_request.return_value = APIResponse(success=True, data={})
            
            messages = [{"role": "user", "content": "Hello"}]
            self.client.chat_completion(
                messages=messages,
                model="gpt-4",
                temperature=0.8,
                max_tokens=1000,
                stream=True,
                presence_penalty=0.5
            )
            
            # Verify the request data
            call_args = mock_make_request.call_args
            assert call_args[0][0] == "POST"  # method
            assert call_args[0][1] == "chat/completions"  # endpoint
            
            request_data = call_args[0][2]  # data
            assert request_data["messages"] == messages
            assert request_data["model"] == "gpt-4"
            assert request_data["temperature"] == 0.8
            assert request_data["max_tokens"] == 1000
            assert request_data["stream"] is True
            assert request_data["presence_penalty"] == 0.5


class TestConversationContext:
    """Test cases for conversation context management."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.context = ConversationContext(max_messages=5)
    
    def test_add_message(self):
        """Test adding messages to context."""
        message = self.context.add_message("user", "Hello")
        
        assert len(self.context.messages) == 1
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.timestamp is not None
    
    def test_context_trimming(self):
        """Test context trimming when exceeding limits."""
        # Add system message
        self.context.add_message("system", "You are a helpful assistant")
        
        # Add more messages than the limit
        for i in range(10):
            self.context.add_message("user", f"Message {i}")
            self.context.add_message("assistant", f"Response {i}")
        
        # Should keep system message + max_messages-1 other messages
        assert len(self.context.messages) <= self.context.max_messages
        
        # System message should be preserved
        assert self.context.messages[0].role == "system"
        assert self.context.messages[0].content == "You are a helpful assistant"
    
    def test_to_api_format(self):
        """Test conversion to API format."""
        self.context.add_message("system", "You are helpful")
        self.context.add_message("user", "Hello")
        self.context.add_message("assistant", "Hi there!")
        
        api_format = self.context.to_api_format()
        
        expected = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        assert api_format == expected
    
    def test_clear_context(self):
        """Test clearing context."""
        self.context.add_message("user", "Hello")
        self.context.add_message("assistant", "Hi!")
        
        assert len(self.context.messages) == 2
        
        self.context.clear()
        
        assert len(self.context.messages) == 0


class TestAIService:
    """Test cases for AI service."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.service = AIService()
        self.test_config = {
            'model_name': 'gpt-3.5-turbo',
            'base_url': 'https://api.openai.com/v1',
            'api_key': 'test-key',
            'temperature': 0.7,
            'max_tokens': 1000,
            'system_prompt': 'You are a helpful assistant'
        }
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if hasattr(self, 'service') and self.service:
            self.service.shutdown()
    
    def test_service_initialization(self):
        """Test service initialization."""
        assert not self.service.is_initialized
        
        # Mock the API client
        with patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient'):
            result = self.service.initialize(self.test_config)
            
            assert result is True
            assert self.service.is_initialized
            assert len(self.service.conversation.messages) == 1  # System message added
            assert self.service.conversation.messages[0].role == "system"
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Missing required fields
        invalid_config = {'model_name': 'gpt-3.5-turbo'}
        
        with patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient'):
            result = self.service.initialize(invalid_config)
            
            assert result is False
            assert not self.service.is_initialized
    
    @patch('specter.src.infrastructure.ai.ai_service.settings')
    def test_load_config_from_settings(self, mock_settings):
        """Test loading configuration from settings manager."""
        mock_settings.get.side_effect = lambda key, default: {
            'ai_model.model_name': 'gpt-4',
            'ai_model.base_url': 'https://api.openai.com/v1',
            'ai_model.api_key': 'settings-key',
            'ai_model.temperature': 0.8,
            'ai_model.max_tokens': 2000,
            'ai_model.system_prompt': 'Test prompt'
        }.get(key, default)
        
        config = self.service._load_config_from_settings()
        
        assert config['model_name'] == 'gpt-4'
        assert config['api_key'] == 'settings-key'
        assert config['temperature'] == 0.8
    
    def test_send_message_not_initialized(self):
        """Test sending message when service not initialized."""
        result = self.service.send_message("Hello")
        
        assert result['success'] is False
        assert 'not initialized' in result['error']
    
    @patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient')
    def test_send_message_success(self, mock_client_class):
        """Test successful message sending."""
        # Setup mock client
        mock_client = Mock()
        mock_response = APIResponse(
            success=True,
            data={
                'choices': [{'message': {'content': 'Hello back!'}}],
                'usage': {'total_tokens': 10}
            }
        )
        mock_client.chat_completion.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        # Initialize service
        self.service.initialize(self.test_config)
        
        # Send message
        result = self.service.send_message("Hello")
        
        assert result['success'] is True
        assert result['response'] == 'Hello back!'
        assert 'usage' in result
        
        # Verify conversation updated
        assert len(self.service.conversation.messages) == 3  # system + user + assistant
        assert self.service.conversation.messages[-2].role == "user"
        assert self.service.conversation.messages[-2].content == "Hello"
        assert self.service.conversation.messages[-1].role == "assistant"
        assert self.service.conversation.messages[-1].content == "Hello back!"
    
    @patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient')
    def test_send_message_api_error(self, mock_client_class):
        """Test message sending with API error."""
        mock_client = Mock()
        mock_response = APIResponse(success=False, error="API Error")
        mock_client.chat_completion.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        self.service.initialize(self.test_config)
        result = self.service.send_message("Hello")
        
        assert result['success'] is False
        assert result['error'] == "API Error"
    
    @patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient')
    def test_test_connection(self, mock_client_class):
        """Test connection testing functionality."""
        mock_client = Mock()
        mock_response = APIResponse(success=True, data={'models': []})
        mock_client.test_connection.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        self.service.initialize(self.test_config)
        result = self.service.test_connection()
        
        assert result['success'] is True
        assert 'Connection successful' in result['message']
    
    @patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient')
    def test_update_config(self, mock_client_class):
        """Test configuration update."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        self.service.initialize(self.test_config)
        
        new_config = {'temperature': 0.9, 'max_tokens': 1500}
        result = self.service.update_config(new_config)
        
        assert result is True
        assert self.service._config['temperature'] == 0.9
        assert self.service._config['max_tokens'] == 1500
        # Old values should be preserved
        assert self.service._config['model_name'] == 'gpt-3.5-turbo'
    
    def test_response_callbacks(self):
        """Test response callback functionality."""
        callback_responses = []
        
        def test_callback(response):
            callback_responses.append(response)
        
        self.service.add_response_callback(test_callback)
        
        with patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient'):
            self.service.initialize(self.test_config)
            
            # Mock successful response
            mock_response = APIResponse(
                success=True,
                data={'choices': [{'message': {'content': 'Test response'}}]}
            )
            self.service.client = Mock()
            self.service.client.chat_completion.return_value = mock_response
            
            self.service.send_message("Test")
            
            assert len(callback_responses) == 1
            assert callback_responses[0] == 'Test response'
        
        # Test callback removal
        self.service.remove_response_callback(test_callback)
        self.service.send_message("Test 2")
        
        assert len(callback_responses) == 1  # Should not have increased
    
    def test_clear_conversation(self):
        """Test conversation clearing."""
        with patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient'):
            self.service.initialize(self.test_config)
            
            # Add some messages
            self.service.conversation.add_message("user", "Hello")
            self.service.conversation.add_message("assistant", "Hi!")
            
            assert len(self.service.conversation.messages) == 3  # system + user + assistant
            
            self.service.clear_conversation()
            
            # Should only have system message
            assert len(self.service.conversation.messages) == 1
            assert self.service.conversation.messages[0].role == "system"
    
    def test_conversation_summary(self):
        """Test conversation summary generation."""
        with patch('specter.src.infrastructure.ai.ai_service.OpenAICompatibleClient'):
            self.service.initialize(self.test_config)
            
            summary = self.service.get_conversation_summary()
            
            assert 'message_count' in summary
            assert 'config' in summary
            assert summary['config']['model'] == 'gpt-3.5-turbo'
            assert summary['config']['has_api_key'] is True


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_response_extraction_error(self):
        """Test response extraction with malformed data."""
        service = AIService()
        
        # Test with malformed response
        malformed_response = {"unexpected": "format"}
        result = service._extract_response_content(malformed_response)
        
        # Should return the stringified response as fallback
        assert isinstance(result, str)
        assert "unexpected" in result


@pytest.mark.integration
class TestIntegration:
    """Integration tests (require actual API or mock server)."""
    
    @pytest.mark.skip(reason="Requires actual API key")
    def test_real_openai_integration(self):
        """Test with real OpenAI API (skipped by default)."""
        # This test would require a real API key and should be run manually
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("No OpenAI API key provided")
        
        client = OpenAICompatibleClient(
            base_url="https://api.openai.com/v1",
            api_key=api_key
        )
        
        try:
            response = client.test_connection()
            assert response.success is True
        finally:
            client.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])