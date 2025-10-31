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

        # Timer for periodic checks (5 minutes)
        self._timer = QTimer()
        self._timer.timeout.connect(self._perform_validation)
        self._validation_interval = 300000  # 5 minutes (300000 ms)

        # State tracking
        self._last_validation_success = None  # None = never validated, True/False = last result
        self._consecutive_failures = 0  # Track consecutive failures
        self._failure_threshold = 1  # 🧪 TESTING: Show banner on FIRST failure (production: 3)
        self._worker = None
        self._thread = None

        logger.info("Periodic API validator initialized (5-minute intervals, threshold=1)")

    def start_periodic_checks(self):
        """Start periodic validation checks."""
        if not self._timer.isActive():
            self._timer.start(self._validation_interval)
            logger.info("⏰ Periodic API validation timer started (interval: 5 minutes)")
            logger.debug(f"📊 Timer active: {self._timer.isActive()}, interval: {self._timer.interval()}ms")

            # Run first check immediately (but after a short delay to avoid startup congestion)
            logger.debug("⏰ Scheduling first validation check in 30 seconds...")
            QTimer.singleShot(30000, self._perform_validation)  # 30 seconds after startup

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
        """Trigger an immediate validation check and resume periodic checks."""
        logger.info("Manual validation triggered (will resume periodic checks if paused)")

        # Resume periodic checks (in case they were paused)
        if not self._timer.isActive():
            self.start_periodic_checks()
            logger.info("▶️ Resumed periodic validation after manual retry")

        self._perform_validation()

    def reset_failure_state(self):
        """
        Reset failure state to allow banner to show again.
        Call this when settings change or user explicitly requests re-validation.
        """
        self._consecutive_failures = 0
        self._last_validation_success = None
        logger.debug("Validation failure state reset")

    def _perform_validation(self):
        """Perform API validation check in background thread."""
        logger.debug("🔍 Starting periodic API validation check...")

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

            logger.debug(f"📊 API Config: base_url={api_config['base_url']}, has_key={bool(api_config['api_key'])}")

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
            logger.debug("✅ Background validation check started")

        except Exception as e:
            logger.error(f"Failed to start validation: {e}")

    def _on_validation_complete(self, result: ValidationResult):
        """
        Handle validation completion.

        Args:
            result: ValidationResult from worker
        """
        try:
            logger.debug(f"📊 Validation result: success={result.success}, provider={result.provider_name}, error={result.error_message}")
            logger.debug(f"📈 State tracking: consecutive_failures={self._consecutive_failures}, last_success={self._last_validation_success}")

            # Determine if state changed
            state_changed = self._last_validation_success != result.success

            if result.success:
                # Validation succeeded
                logger.info(f"✅ Validation SUCCESS - consecutive_failures={self._consecutive_failures}, last_success={self._last_validation_success}")

                # ALWAYS emit validation_succeeded on success to hide any visible banner
                # The banner should disappear on ANY successful test, not just after failures
                logger.info("🔔 EMITTING validation_succeeded signal - banner should hide if visible")
                self.validation_succeeded.emit()
                logger.info("✅ validation_succeeded signal emitted")

                # Reset failure counter on success
                self._consecutive_failures = 0
                self._last_validation_success = True
                logger.debug("✅ Validation passed, failure counter reset to 0")

            else:
                # Validation failed
                self._consecutive_failures += 1
                logger.warning(f"✗ API validation failed ({self._consecutive_failures}/{self._failure_threshold}): {result.error_message}")

                # Only emit signal after reaching threshold
                if self._consecutive_failures >= self._failure_threshold:
                    if self._consecutive_failures == self._failure_threshold:
                        # First time reaching threshold - emit signal and pause checks
                        logger.error(f"🚨 API validation failed {self._failure_threshold} times - emitting validation_failed signal")
                        logger.debug(f"🎯 About to emit validation_failed signal with result: provider={result.provider_name}, error={result.error_message}")
                        self.validation_failed.emit(result)
                        logger.debug("✅ validation_failed signal emitted successfully")

                        # Pause periodic checks after showing banner (resume via retry button)
                        self.pause_checks()
                        logger.info("⏸️ Periodic API validation paused after banner shown (retry to resume)")
                    else:
                        # Already shown banner, just log
                        logger.debug(f"⏭️ Banner already shown (failure #{self._consecutive_failures})")

                self._last_validation_success = False

        except Exception as e:
            logger.error(f"Error processing validation result: {e}", exc_info=True)

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
