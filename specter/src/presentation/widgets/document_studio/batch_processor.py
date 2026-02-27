"""
Background batch processor for the Document Studio.

Provides a QThread-based worker that processes multiple DOCX files
sequentially using DocxFormatterSkill, emitting progress signals for
thread-safe UI updates.

Classes:
    BatchWorker  -- QObject that runs inside a QThread, processes files
    BatchProcessor -- High-level manager that creates/owns the thread
"""

import asyncio
import logging
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .studio_state import DocumentStudioState, DocumentStatus, Recipe

logger = logging.getLogger("specter.document_studio.batch_processor")


class BatchWorker(QObject):
    """
    Background worker that processes files sequentially.

    Runs inside a QThread. For each file, it creates a DocxFormatterSkill
    instance, builds parameters from the active recipe, and executes the
    formatting operation via ``asyncio.new_event_loop()`` (since
    ``DocxFormatterSkill.execute()`` is async).

    Signals:
        file_started(str)                -- file_path
        file_progress(str, float)        -- file_path, 0.0-1.0
        file_completed(str, bool, str, str) -- file_path, success, message, formatted_path
        batch_finished(int, int)         -- success_count, total_count
        error_occurred(str, str)         -- file_path, error_message
    """

    file_started = pyqtSignal(str)
    file_progress = pyqtSignal(str, float)
    file_completed = pyqtSignal(str, bool, str, str)
    batch_finished = pyqtSignal(int, int)
    error_occurred = pyqtSignal(str, str)

    def __init__(
        self,
        file_paths: List[str],
        recipe: Recipe,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._file_paths = list(file_paths)
        self._recipe = recipe
        self._cancelled = False

    # -- Public API --

    def cancel(self):
        """Request cancellation. Checked between files."""
        self._cancelled = True
        logger.info("Batch cancellation requested")

    def run(self):
        """
        Main entry point invoked when the thread starts.

        Iterates over file paths, calling ``_process_single_file()`` for
        each. Emits ``batch_finished`` when all files are processed or
        the batch is cancelled.
        """
        success_count = 0
        total = len(self._file_paths)
        logger.info(
            f"Batch processing started: {total} file(s), "
            f"recipe={self._recipe.name!r}"
        )

        for i, file_path in enumerate(self._file_paths):
            if self._cancelled:
                logger.info(
                    f"Batch cancelled after {i} of {total} files"
                )
                break

            self.file_started.emit(file_path)
            self.file_progress.emit(file_path, 0.0)

            try:
                formatted_path = self._process_single_file(file_path)
                success_count += 1
                self.file_progress.emit(file_path, 1.0)
                self.file_completed.emit(
                    file_path, True, "Formatted successfully", formatted_path
                )
            except Exception as exc:
                error_msg = str(exc) or "Unknown error"
                logger.error(
                    f"Error processing {file_path}: {error_msg}", exc_info=True
                )
                self.file_progress.emit(file_path, 1.0)
                self.file_completed.emit(file_path, False, error_msg, "")
                self.error_occurred.emit(file_path, error_msg)

        self.batch_finished.emit(success_count, total)
        logger.info(
            f"Batch processing finished: {success_count}/{total} succeeded"
        )

    # -- Internal --

    def _process_single_file(self, file_path: str) -> str:
        """
        Format a single file using DocxFormatterSkill.

        Creates a fresh skill instance, builds keyword params from the
        recipe (operations list + parameter overrides), and runs the
        async ``execute()`` method in a dedicated event loop.

        Args:
            file_path: Absolute path to the DOCX file.

        Returns:
            Path to the formatted output file.

        Raises:
            RuntimeError: If skill execution fails.
        """
        # Lazy import to avoid circular imports at module level
        from specter.src.infrastructure.skills.skills_library.docx_formatter_skill import (
            DocxFormatterSkill,
        )

        skill = DocxFormatterSkill()

        # Build params from recipe
        params = dict(self._recipe.parameters)  # copy overrides
        params["file_path"] = file_path
        params["operations"] = list(self._recipe.operations)

        logger.debug(
            f"Processing {file_path} with operations={params['operations']}"
        )

        # Run the async execute() in a new event loop
        # (Qt threads cannot use asyncio.run() safely; create a dedicated loop)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(skill.execute(**params))
        finally:
            loop.close()

        if not result.success:
            raise RuntimeError(result.error or result.message)

        formatted_path = ""
        if result.data and isinstance(result.data, dict):
            formatted_path = result.data.get("formatted_path", "")

        return formatted_path


class BatchProcessor(QObject):
    """
    High-level manager that creates a QThread + BatchWorker pair.

    Bridges worker signals to ``DocumentStudioState`` so that the state
    model stays in sync and UI widgets are updated automatically.

    Usage::

        processor = BatchProcessor(state)
        processor.start_batch(file_paths, recipe)
        # ... state signals drive UI updates ...
        processor.cancel()  # optional early stop
    """

    def __init__(
        self,
        state: DocumentStudioState,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._state = state
        self._thread: Optional[QThread] = None
        self._worker: Optional[BatchWorker] = None

    # -- Properties --

    @property
    def is_running(self) -> bool:
        """True while a batch is in progress."""
        return self._thread is not None and self._thread.isRunning()

    # -- Public API --

    def start_batch(self, file_paths: List[str], recipe: Recipe):
        """
        Begin batch processing.

        Marks every file as QUEUED in the state, creates a QThread with
        a BatchWorker, wires up signals, and starts the thread.

        Args:
            file_paths: Absolute paths to DOCX files to process.
            recipe: The Recipe defining operations and parameters.

        Raises:
            RuntimeError: If a batch is already running.
        """
        if self.is_running:
            raise RuntimeError("A batch is already running")

        if not file_paths:
            logger.warning("start_batch called with empty file list")
            return

        # Mark all files as queued
        for fp in file_paths:
            self._state.update_status(fp, DocumentStatus.QUEUED)
            self._state.update_progress(fp, 0.0)

        self._state.is_batch_running = True
        self._state.batch_started.emit(recipe.recipe_id)

        # Create thread and worker
        self._thread = QThread()
        self._worker = BatchWorker(file_paths, recipe)
        self._worker.moveToThread(self._thread)

        # Wire worker signals -> state updates
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.error_occurred.connect(self._on_error_occurred)

        # Start worker when thread begins
        self._thread.started.connect(self._worker.run)

        # Clean up when thread finishes
        self._thread.finished.connect(self._cleanup_thread)

        logger.info(
            f"Starting batch: {len(file_paths)} file(s), "
            f"recipe={recipe.name!r}"
        )
        self._thread.start()

    def cancel(self):
        """Cancel the running batch. Finishes current file then stops."""
        if self._worker:
            self._worker.cancel()

    # -- Signal handlers (worker -> state) --

    def _on_file_started(self, file_path: str):
        """Update state when a file begins processing."""
        self._state.update_status(file_path, DocumentStatus.PROCESSING)
        self._state.update_progress(file_path, 0.0)

    def _on_file_progress(self, file_path: str, progress: float):
        """Forward progress updates to state."""
        self._state.update_progress(file_path, progress)

    def _on_file_completed(
        self, file_path: str, success: bool, message: str, formatted_path: str
    ):
        """Update state when a file finishes processing."""
        if success:
            self._state.update_status(file_path, DocumentStatus.COMPLETED)
            entry = self._state.documents.get(file_path)
            if entry:
                entry.formatted_path = formatted_path
        else:
            self._state.update_status(
                file_path, DocumentStatus.FAILED, error=message
            )

    def _on_batch_finished(self, success_count: int, total_count: int):
        """Update state when the entire batch completes."""
        self._state.is_batch_running = False
        all_ok = success_count == total_count
        summary = f"{success_count}/{total_count} files formatted successfully"
        self._state.batch_progress.emit(success_count, total_count)
        self._state.batch_completed.emit(all_ok, summary)
        logger.info(f"Batch complete: {summary}")

        # Quit the thread's event loop so it can finish
        if self._thread and self._thread.isRunning():
            self._thread.quit()

    def _on_error_occurred(self, file_path: str, error_message: str):
        """Log errors from the worker."""
        logger.error(f"Batch error for {file_path}: {error_message}")

    # -- Cleanup --

    def _cleanup_thread(self):
        """Release thread and worker after the thread finishes."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        logger.debug("Batch thread cleaned up")
