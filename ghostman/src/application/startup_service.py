"""
Minimal Startup Service for Ghostman.

Handles API connection testing and initial REPL preamble configuration only.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime

from ..infrastructure.ai.api_client import OpenAICompatibleClient
from ..infrastructure.storage.settings_manager import settings

logger = logging.getLogger("ghostman.startup_service")


class StartupService:
    """Minimal service for startup tasks - API test and preamble only."""
    
    def __init__(self):
        """Initialize the startup service."""
        self.api_client = None
        self.api_status = None
        self.api_error_message = None
        self.is_first_run = False
        
    def check_first_run(self) -> bool:
        """
        Check if this is the first time the app is being run.
        
        Returns:
            True if first run, False otherwise
        """
        try:
            # Check if we have a flag in settings
            first_run = settings.get('app.first_run', True)
            if first_run:
                # Mark as no longer first run
                settings.set('app.first_run', False)
                settings.save()
                self.is_first_run = True
                logger.info("First run detected")
            return first_run
        except Exception as e:
            logger.error(f"Error checking first run status: {e}")
            return False
    
    def test_api_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the API connection on startup.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            logger.info("Testing API connection on startup...")
            
            # Get API configuration (no fallbacks - require explicit configuration)
            api_config = {
                'api_key': settings.get('ai_model.api_key'),
                'base_url': settings.get('ai_model.base_url', ''),
                'model': settings.get('ai_model.model_name', ''),
                'temperature': settings.get('ai_model.temperature', 0.7),
                'max_tokens': settings.get('ai_model.max_tokens', 2000)
            }
            
            # Check if API key is configured
            if not api_config['api_key']:
                error_msg = "No API key configured. Please set your API key in settings."
                logger.warning(error_msg)
                self.api_status = False
                self.api_error_message = error_msg
                return False, error_msg
            
            # Create API client
            self.api_client = OpenAICompatibleClient(
                api_key=api_config['api_key'],
                base_url=api_config['base_url']
            )
            
            # Test connection
            response = self.api_client.test_connection()
            
            if response.success:
                logger.info("✓ API connection successful")
                self.api_status = True
                self.api_error_message = None
                return True, None
            else:
                error_msg = f"API connection failed: {response.error}"
                logger.error(error_msg)
                self.api_status = False
                self.api_error_message = error_msg
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Failed to test API connection: {str(e)}"
            logger.error(error_msg)
            self.api_status = False
            self.api_error_message = error_msg
            return False, error_msg
    
    def get_preamble_content(self) -> str:
        """
        Get the appropriate preamble content for the REPL.
        
        Returns:
            String containing the preamble to display
        """
        preamble_lines = []
        
        # Check if first run
        if self.is_first_run:
            # Empty preamble for first run as requested
            logger.info("First run - returning empty preamble")
            return ""
        
        # Check API status and add appropriate message
        if self.api_status is None:
            # API test hasn't run yet
            preamble_lines.append("⏳ Testing API connection...")
        elif self.api_status is False:
            # API test failed
            preamble_lines.append("✗ API Connection Error")
            if self.api_error_message:
                preamble_lines.append(f"   {self.api_error_message}")
            preamble_lines.append("")
            preamble_lines.append("📝 Please check your API settings:")
            preamble_lines.append("   • Right-click avatar → Settings")
            preamble_lines.append("   • Configure your API key and endpoint")
            preamble_lines.append("   • Test connection and save")
        else:
            # API test successful - show normal welcome
            preamble_lines.append("✓ Connected!")
            preamble_lines.append("")
            
            # Get custom preamble from settings if available
            custom_preamble = settings.get('ui.custom_preamble', None)
            if custom_preamble:
                preamble_lines.append(custom_preamble)
            else:
                # Default preamble
                preamble_lines.append("💬 I am Spector your AI Assistant")
                preamble_lines.append("Type your message or 'help' for commands")
        
        return "\n".join(preamble_lines)
    
    def perform_startup_tasks(self) -> dict:
        """
        Perform startup tasks and return status.
        
        Returns:
            Dictionary with startup status information
        """
        logger.info("Performing startup tasks...")
        
        # Check first run
        is_first_run = self.check_first_run()
        
        # Test API connection (unless first run)
        if not is_first_run:
            api_success, api_error = self.test_api_connection()
        else:
            api_success = None
            api_error = None
        
        # Get preamble
        preamble = self.get_preamble_content()
        
        return {
            'first_run': is_first_run,
            'api_status': api_success,
            'api_error': api_error,
            'preamble': preamble,
            'timestamp': datetime.now()
        }


# Global instance
startup_service = StartupService()