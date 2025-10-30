"""
Periodic API Validator for Ghostman.

Runs background validation checks every 10 minutes to monitor API connectivity.
Shows error banner only on first failure, auto-hides when connection restored.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from ...infrastructure.storage.settings_manager import settings
from ...infrastructure.ai.api_client import OpenAICompatibleClient

logger = logging.getLogger("ghostman.periodic_api_validator")


@dataclass
class ValidationResult:
    """Result from API validation check."""
    success: bool
    error_message: Optional[str] = None
    provider_name: Optional[str] = None
    timestamp: Optional[str] = None


class ValidationWorker(QObject):
    """Worker that runs API validation in background thread."""

    finished = pyqtSignal(object)  # Emits ValidationResult

    def __init__(self, api_config: Dict[str, Any]):
        """
        Initialize validation worker.

        Args:
            api_config: API configuration dict with keys: api_key, base_url, model_name
        """
        super().__init__()
        self.api_config = api_config

    def run(self):
        """Run the validation check (runs in background thread)."""
        try:
            from datetime import datetime

            # Check if API key is configured
            if not self.api_config.get('api_key'):
                result = ValidationResult(
                    success=False,
                    error_message="No API key configured",
                    provider_name=self._get_provider_name(),
                    timestamp=datetime.now().isoformat()
                )
                self.finished.emit(result)
                return

            # Create API client
            client = OpenAICompatibleClient(
                api_key=self.api_config['api_key'],
                base_url=self.api_config['base_url']
            )

            # Test connection
            response = client.test_connection()

            if response.success:
                result = ValidationResult(
                    success=True,
                    error_message=None,
                    provider_name=self._get_provider_name(),
                    timestamp=datetime.now().isoformat()
                )
            else:
                result = ValidationResult(
                    success=False,
                    error_message=response.error or "Connection test failed",
                    provider_name=self._get_provider_name(),
                    timestamp=datetime.now().isoformat()
                )

            self.finished.emit(result)

        except Exception as e:
            # Don't show banner for validation errors (transient network issues)
            logger.error(f"Validation check failed: {e}")
            result = ValidationResult(
                success=False,
                error_message=str(e),
                provider_name=self._get_provider_name(),
                timestamp=None
            )
            self.finished.emit(result)

    def _get_provider_name(self) -> str:
        """Extract provider name from base URL."""
        base_url = self.api_config.get('base_url', '').lower()

        if 'openai.com' in base_url:
            return "OpenAI API"
        elif 'anthropic.com' in base_url or 'claude' in base_url:
            return "Anthropic Claude API"
        elif 'openrouter.ai' in base_url:
            return "OpenRouter"
        elif 'localhost' in base_url or '127.0.0.1' in base_url:
            return "Local API"
        else:
            return "Custom API"


class PeriodicAPIValidator(QObject):
    """
    Background API validation service.

    Runs validation checks every 10 minutes and emits signals
    when validation state changes (success ↔ failure).
    """

    # Signals
    validation_failed = pyqtSignal(object)  # Emits ValidationResult on FIRST failure
    validation_succeeded = pyqtSignal()  # Emitted when connection restored

    def __init__(self):
        """Initialize periodic API validator."""
        super().__init__()

        # Timer for periodic checks (10 minutes = 600000 ms)
        self._timer = QTimer()
        self._timer.timeout.connect(self._perform_validation)
        self._validation_interval = 600000  # 10 minutes

        # State tracking
        self._last_validation_success = None  # None = never validated, True/False = last result
        self._is_first_failure = True
        self._worker = None
        self._thread = None

        logger.info("Periodic API validator initialized (10-minute intervals)")

    def start_periodic_checks(self):
        """Start periodic validation checks."""
        if not self._timer.isActive():
            self._timer.start(self._validation_interval)
            logger.info("Periodic API validation started")

            # Run first check immediately (but after a short delay to avoid startup congestion)
            QTimer.singleShot(5000, self._perform_validation)  # 5 seconds after startup

    def stop_periodic_checks(self):
        """Stop periodic validation checks."""
        if self._timer.isActive():
            self._timer.stop()
            logger.info("Periodic API validation stopped")

    def pause_checks(self):
        """Pause validation checks (e.g., when app minimized)."""
        self.stop_periodic_checks()

    def resume_checks(self):
        """Resume validation checks."""
        self.start_periodic_checks()

    def validate_now(self):
        """Trigger an immediate validation check."""
        logger.info("Manual validation triggered")
        self._perform_validation()

    def reset_failure_state(self):
        """
        Reset failure state to allow banner to show again.
        Call this when settings change or user explicitly requests re-validation.
        """
        self._is_first_failure = True
        self._last_validation_success = None
        logger.debug("Validation failure state reset")

    def _perform_validation(self):
        """Perform API validation check in background thread."""
        # Prevent multiple simultaneous validations
        if self._thread and self._thread.isRunning():
            logger.debug("Validation already in progress, skipping")
            return

        try:
            # Build API config from settings
            api_config = {
                'api_key': settings.get('ai_model.api_key'),
                'base_url': settings.get('ai_model.base_url', 'https://api.openai.com/v1'),
                'model_name': settings.get('ai_model.model_name', 'gpt-3.5-turbo')
            }

            # Create worker and thread
            self._worker = ValidationWorker(api_config)
            self._thread = QThread()
            self._worker.moveToThread(self._thread)

            # Connect signals
            self._thread.started.connect(self._worker.run)
            self._worker.finished.connect(self._on_validation_complete)
            self._worker.finished.connect(self._thread.quit)
            self._thread.finished.connect(self._cleanup_thread)

            # Start validation
            self._thread.start()
            logger.debug("Background validation check started")

        except Exception as e:
            logger.error(f"Failed to start validation: {e}")

    def _on_validation_complete(self, result: ValidationResult):
        """
        Handle validation completion.

        Args:
            result: ValidationResult from worker
        """
        try:
            logger.debug(f"Validation complete: success={result.success}, provider={result.provider_name}")

            # Determine if state changed
            state_changed = self._last_validation_success != result.success

            if result.success:
                # Validation succeeded
                if state_changed and self._last_validation_success is False:
                    # Connection restored!
                    logger.info("✓ API connection restored")
                    self.validation_succeeded.emit()
                    self._is_first_failure = True  # Reset for next failure

                self._last_validation_success = True

            else:
                # Validation failed
                if state_changed or self._is_first_failure:
                    # First failure or state change from success to failure
                    logger.warning(f"✗ API validation failed: {result.error_message}")

                    # Only emit signal if this is the first failure
                    if self._is_first_failure:
                        self.validation_failed.emit(result)
                        self._is_first_failure = False

                self._last_validation_success = False

        except Exception as e:
            logger.error(f"Error processing validation result: {e}")

    def _cleanup_thread(self):
        """Clean up validation thread."""
        try:
            if self._thread:
                self._thread.deleteLater()
                self._thread = None
            if self._worker:
                self._worker.deleteLater()
                self._worker = None
        except Exception as e:
            logger.warning(f"Error cleaning up validation thread: {e}")

    def shutdown(self):
        """Shutdown validator (called on app exit)."""
        try:
            self.stop_periodic_checks()

            # Wait for any running validation to complete
            if self._thread and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)  # Wait up to 2 seconds

            self._cleanup_thread()
            logger.info("Periodic API validator shut down")

        except Exception as e:
            logger.warning(f"Error during validator shutdown: {e}")
