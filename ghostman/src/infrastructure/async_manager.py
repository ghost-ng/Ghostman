"""
Async Manager for PyQt + AsyncIO Integration.

This module provides robust PyQt6 + asyncio integration patterns for the Ghostman application.
It handles event loop management, thread safety, and proper async task execution within
the PyQt environment.
"""

import asyncio
import logging
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Coroutine, Any, Union
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class AsyncIOManager(QObject):
    """
    Thread-safe AsyncIO manager for PyQt applications.
    
    This class provides a robust interface for running async operations
    within PyQt applications without blocking the GUI thread.
    """
    
    # Signals for communication with PyQt main thread
    async_task_completed = pyqtSignal(object, object)  # result, error
    async_task_started = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._shutdown_requested = False
        self._active_tasks = weakref.WeakSet()
        
    def initialize(self) -> bool:
        """
        Initialize the async manager with a dedicated event loop.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if self._loop and not self._loop.is_closed():
                logger.debug("AsyncIO manager already initialized")
                return True
                
            # Create thread pool executor
            self._executor = ThreadPoolExecutor(
                max_workers=2, 
                thread_name_prefix="ghostman_async"
            )
            
            # Create event loop in dedicated thread
            self._create_event_loop_thread()
            
            logger.info("AsyncIO manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AsyncIO manager: {e}")
            return False
    
    def _create_event_loop_thread(self):
        """Create and start the dedicated event loop thread."""
        def run_event_loop():
            """Run the event loop in a dedicated thread."""
            try:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                
                logger.debug("Event loop thread started")
                self._loop.run_forever()
                
            except Exception as e:
                logger.error(f"Event loop thread error: {e}")
            finally:
                if self._loop and not self._loop.is_closed():
                    self._loop.close()
                logger.debug("Event loop thread stopped")
        
        self._loop_thread = threading.Thread(
            target=run_event_loop,
            name="ghostman_event_loop",
            daemon=True
        )
        self._loop_thread.start()
        
        # Wait for loop to be created
        import time
        timeout = 5.0
        start_time = time.time()
        while self._loop is None and (time.time() - start_time) < timeout:
            time.sleep(0.01)
            
        if self._loop is None:
            raise RuntimeError("Failed to create event loop within timeout")
    
    def run_async_task(
        self,
        coro: Coroutine,
        callback: Optional[Callable[[Any, Optional[Exception]], None]] = None,
        timeout: Optional[float] = None
    ) -> None:
        """
        Run an async coroutine in the dedicated event loop.
        
        Args:
            coro: The coroutine to execute
            callback: Optional callback for result/error handling
            timeout: Optional timeout in seconds
        """
        if not self._loop or self._loop.is_closed():
            error = RuntimeError("AsyncIO manager not initialized")
            logger.error(str(error))
            if callback:
                callback(None, error)
            return
            
        try:
            # Schedule the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self._run_with_timeout(coro, timeout), 
                self._loop
            )
            
            # Add to active tasks
            self._active_tasks.add(future)
            
            # Handle result asynchronously
            def handle_result():
                try:
                    result = future.result()
                    self.async_task_completed.emit(result, None)
                    if callback:
                        callback(result, None)
                except Exception as e:
                    self.async_task_completed.emit(None, e)
                    if callback:
                        callback(None, e)
                finally:
                    # Remove from active tasks (if still in set)
                    try:
                        self._active_tasks.discard(future)
                    except:
                        pass
            
            # Use QTimer to check for completion (PyQt-safe approach)
            self._schedule_result_check(future, handle_result)
            
            self.async_task_started.emit()
            
        except Exception as e:
            logger.error(f"Failed to schedule async task: {e}")
            if callback:
                callback(None, e)
    
    def _schedule_result_check(self, future, callback):
        """Schedule periodic checks for future completion."""
        timer = QTimer()
        timer.timeout.connect(lambda: self._check_future_done(future, callback, timer))
        timer.start(50)  # Check every 50ms
    
    def _check_future_done(self, future, callback, timer):
        """Check if future is done and handle result."""
        if future.done():
            timer.stop()
            timer.deleteLater()
            callback()
    
    async def _run_with_timeout(self, coro: Coroutine, timeout: Optional[float]):
        """Run coroutine with optional timeout."""
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        else:
            return await coro
    
    def run_sync_in_async_context(
        self,
        func: Callable,
        *args,
        callback: Optional[Callable[[Any, Optional[Exception]], None]] = None,
        **kwargs
    ) -> None:
        """
        Run a synchronous function in the async executor.
        
        Args:
            func: The synchronous function to execute
            *args: Positional arguments for the function
            callback: Optional callback for result/error handling
            **kwargs: Keyword arguments for the function
        """
        if not self._executor:
            error = RuntimeError("Executor not initialized")
            logger.error(str(error))
            if callback:
                callback(None, error)
            return
            
        try:
            future = self._executor.submit(func, *args, **kwargs)
            
            def handle_result():
                try:
                    result = future.result()
                    if callback:
                        callback(result, None)
                except Exception as e:
                    if callback:
                        callback(None, e)
            
            self._schedule_executor_result_check(future, handle_result)
            
        except Exception as e:
            logger.error(f"Failed to schedule sync task: {e}")
            if callback:
                callback(None, e)
    
    def _schedule_executor_result_check(self, future, callback):
        """Schedule periodic checks for executor future completion."""
        timer = QTimer()
        timer.timeout.connect(lambda: self._check_executor_future_done(future, callback, timer))
        timer.start(50)  # Check every 50ms
    
    def _check_executor_future_done(self, future, callback, timer):
        """Check if executor future is done and handle result."""
        if future.done():
            timer.stop()
            timer.deleteLater()
            callback()
    
    def schedule_delayed_async_task(
        self,
        coro: Coroutine,
        delay_ms: int,
        callback: Optional[Callable[[Any, Optional[Exception]], None]] = None
    ) -> None:
        """
        Schedule an async task to run after a delay.
        
        Args:
            coro: The coroutine to execute
            delay_ms: Delay in milliseconds
            callback: Optional callback for result/error handling
        """
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.run_async_task(coro, callback))
        timer.start(delay_ms)
    
    def is_initialized(self) -> bool:
        """Check if the async manager is properly initialized."""
        return (
            self._loop is not None and
            not self._loop.is_closed() and
            self._loop_thread is not None and
            self._loop_thread.is_alive() and
            self._executor is not None
        )
    
    def shutdown(self):
        """Shutdown the async manager and clean up resources."""
        if self._shutdown_requested:
            return
            
        self._shutdown_requested = True
        logger.info("Shutting down AsyncIO manager...")
        
        try:
            # Cancel active tasks
            for task in list(self._active_tasks):
                if not task.done():
                    task.cancel()
            
            # Shutdown event loop
            if self._loop and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._loop.stop)
                
            # Wait for loop thread to finish
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=2.0)
                
            # Shutdown executor
            if self._executor:
                self._executor.shutdown(wait=True)
                
        except Exception as e:
            logger.error(f"Error during AsyncIO manager shutdown: {e}")
        finally:
            self._executor = None
            self._loop = None
            self._loop_thread = None
            logger.info("AsyncIO manager shutdown completed")


# Global instance (singleton pattern)
_async_manager: Optional[AsyncIOManager] = None


def get_async_manager() -> AsyncIOManager:
    """
    Get the global AsyncIOManager instance.
    
    Returns:
        AsyncIOManager: The global async manager instance
    """
    global _async_manager
    if _async_manager is None:
        _async_manager = AsyncIOManager()
        # Initialize automatically
        if not _async_manager.initialize():
            logger.error("Failed to initialize global AsyncIOManager")
    return _async_manager


def shutdown_async_manager():
    """Shutdown the global async manager."""
    global _async_manager
    if _async_manager:
        _async_manager.shutdown()
        _async_manager = None


def run_async_task_safe(
    coro: Coroutine,
    callback: Optional[Callable[[Any, Optional[Exception]], None]] = None,
    timeout: Optional[float] = None
) -> None:
    """
    Convenience function to run async task safely in PyQt context.
    
    Args:
        coro: The coroutine to execute
        callback: Optional callback for result/error handling
        timeout: Optional timeout in seconds
    """
    manager = get_async_manager()
    manager.run_async_task(coro, callback, timeout)


# Cleanup on application exit
def _cleanup_on_exit():
    """Cleanup function called on application exit."""
    shutdown_async_manager()


# Register cleanup function
import atexit
atexit.register(_cleanup_on_exit)