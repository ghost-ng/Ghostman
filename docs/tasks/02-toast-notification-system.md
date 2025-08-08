# Toast Notification System Implementation Plan

## Overview

This document outlines the implementation plan for a cross-platform toast notification system that works alongside the PyQt6 main application without requiring administrator permissions. The system will use either tkinter-based custom toasts or native system notifications depending on the platform and user preferences.

## Technology Decision Matrix

Based on research findings, the recommended approach uses a hybrid system:

| Solution | Pros | Cons | Use Case |
|----------|------|------|----------|
| **desktop-notifier** | Native OS integration, async support | External dependency | Primary choice |
| **Custom tkinter** | No dependencies, full control | Framework mixing | Fallback option |
| **Native system calls** | True native experience | Platform-specific code | Advanced features |

## Implementation Architecture

### 1. Toast Manager Interface

**File**: `ghostman/src/ui/components/toast_manager.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
import asyncio
import threading
from dataclasses import dataclass

class ToastType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class ToastConfig:
    title: str
    message: str
    toast_type: ToastType = ToastType.INFO
    duration: int = 3000  # milliseconds
    position: str = "bottom-right"
    icon: Optional[str] = None
    sound: bool = False

class ToastProvider(ABC):
    """Abstract base class for toast notification providers."""
    
    @abstractmethod
    async def show_toast(self, config: ToastConfig) -> None:
        """Show a toast notification."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available on the current system."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass

class ToastManager:
    """Central manager for toast notifications with multiple providers."""
    
    def __init__(self):
        self.providers = []
        self.current_provider = None
        self.setup_providers()
    
    def setup_providers(self):
        """Initialize available toast providers."""
        # Try providers in order of preference
        providers = [
            NativeToastProvider(),
            TkinterToastProvider(),
            FallbackToastProvider()
        ]
        
        for provider in providers:
            if provider.is_available():
                self.providers.append(provider)
        
        if self.providers:
            self.current_provider = self.providers[0]
    
    async def show_toast(self, config: ToastConfig) -> None:
        """Show toast using the best available provider."""
        if not self.current_provider:
            print(f"No toast provider available: {config.title} - {config.message}")
            return
        
        try:
            await self.current_provider.show_toast(config)
        except Exception as e:
            print(f"Toast failed with {self.current_provider.__class__.__name__}: {e}")
            await self._try_fallback_providers(config)
    
    async def _try_fallback_providers(self, config: ToastConfig) -> None:
        """Try alternative providers if primary fails."""
        for provider in self.providers[1:]:
            try:
                await provider.show_toast(config)
                return
            except Exception as e:
                print(f"Fallback provider {provider.__class__.__name__} failed: {e}")
                continue
    
    # Convenience methods
    async def info(self, title: str, message: str, **kwargs) -> None:
        config = ToastConfig(title, message, ToastType.INFO, **kwargs)
        await self.show_toast(config)
    
    async def success(self, title: str, message: str, **kwargs) -> None:
        config = ToastConfig(title, message, ToastType.SUCCESS, **kwargs)
        await self.show_toast(config)
    
    async def warning(self, title: str, message: str, **kwargs) -> None:
        config = ToastConfig(title, message, ToastType.WARNING, **kwargs)
        await self.show_toast(config)
    
    async def error(self, title: str, message: str, **kwargs) -> None:
        config = ToastConfig(title, message, ToastType.ERROR, **kwargs)
        await self.show_toast(config)
    
    def cleanup(self):
        """Clean up all providers."""
        for provider in self.providers:
            provider.cleanup()
```

### 2. Native Toast Provider (Primary)

**File**: `ghostman/src/ui/components/native_toast_provider.py`

```python
import asyncio
import sys
from .toast_manager import ToastProvider, ToastConfig, ToastType

class NativeToastProvider(ToastProvider):
    """Native system toast notifications using desktop-notifier."""
    
    def __init__(self):
        self.notifier = None
        self._init_notifier()
    
    def _init_notifier(self):
        """Initialize desktop-notifier if available."""
        try:
            from desktop_notifier import DesktopNotifier
            self.notifier = DesktopNotifier(
                app_name="Ghostman",
                notification_limit=5
            )
        except ImportError:
            self.notifier = None
    
    def is_available(self) -> bool:
        """Check if desktop-notifier is available."""
        return self.notifier is not None
    
    async def show_toast(self, config: ToastConfig) -> None:
        """Show native toast notification."""
        if not self.notifier:
            raise RuntimeError("Native notifier not available")
        
        from desktop_notifier import Notification, Icon
        
        # Map toast types to appropriate urgency
        urgency_map = {
            ToastType.INFO: "normal",
            ToastType.SUCCESS: "normal", 
            ToastType.WARNING: "normal",
            ToastType.ERROR: "critical"
        }
        
        notification = Notification(
            title=config.title,
            message=config.message,
            urgency=urgency_map[config.toast_type],
            timeout=config.duration / 1000,  # Convert to seconds
            icon=Icon(name=self._get_icon_for_type(config.toast_type)) if not config.icon else Icon(path=config.icon)
        )
        
        await self.notifier.send(notification)
    
    def _get_icon_for_type(self, toast_type: ToastType) -> str:
        """Get system icon name for toast type."""
        icon_map = {
            ToastType.INFO: "dialog-information",
            ToastType.SUCCESS: "dialog-ok-apply",
            ToastType.WARNING: "dialog-warning", 
            ToastType.ERROR: "dialog-error"
        }
        return icon_map.get(toast_type, "dialog-information")
    
    def cleanup(self) -> None:
        """Clean up native notifier resources."""
        # desktop-notifier handles cleanup automatically
        pass
```

### 3. Tkinter Toast Provider (Fallback)

**File**: `ghostman/src/ui/components/tkinter_toast_provider.py`

```python
import tkinter as tk
from tkinter import ttk
import threading
import time
import asyncio
from typing import List, Dict, Tuple
from .toast_manager import ToastProvider, ToastConfig, ToastType

class TkinterToast:
    """Individual tkinter toast notification."""
    
    def __init__(self, config: ToastConfig, manager_callback=None):
        self.config = config
        self.manager_callback = manager_callback
        self.window = None
        self.fade_job = None
        
    def create_window(self):
        """Create the toast window."""
        self.window = tk.Toplevel()
        self.window.withdraw()  # Start hidden
        
        # Window configuration
        self.window.overrideredirect(True)  # Remove decorations
        self.window.attributes('-topmost', True)  # Always on top
        self.window.configure(bg='#2b2b2b')
        
        # Handle transparency on different platforms
        try:
            self.window.attributes('-alpha', 0.0)  # Start transparent
        except tk.TclError:
            # Some platforms don't support alpha
            pass
        
        # Create content
        self._create_content()
        
        # Position the window
        self._position_window()
    
    def _create_content(self):
        """Create toast content."""
        # Main frame
        main_frame = tk.Frame(
            self.window,
            bg=self._get_bg_color(),
            relief='raised',
            bd=1,
            padx=15,
            pady=10
        )
        main_frame.pack(fill='both', expand=True)
        
        # Icon and title frame
        header_frame = tk.Frame(main_frame, bg=self._get_bg_color())
        header_frame.pack(fill='x', pady=(0, 5))
        
        # Icon (simple colored circle)
        icon_canvas = tk.Canvas(
            header_frame, 
            width=20, 
            height=20, 
            bg=self._get_bg_color(),
            highlightthickness=0
        )
        icon_canvas.pack(side='left', padx=(0, 10))
        
        # Draw icon
        color = self._get_icon_color()
        icon_canvas.create_oval(2, 2, 18, 18, fill=color, outline='')
        
        # Title
        title_label = tk.Label(
            header_frame,
            text=self.config.title,
            font=('Segoe UI', 10, 'bold'),
            fg=self._get_text_color(),
            bg=self._get_bg_color()
        )
        title_label.pack(side='left')
        
        # Close button
        close_button = tk.Button(
            header_frame,
            text='×',
            font=('Arial', 12, 'bold'),
            fg=self._get_text_color(),
            bg=self._get_bg_color(),
            relief='flat',
            bd=0,
            padx=5,
            pady=0,
            command=self.close
        )
        close_button.pack(side='right')
        
        # Message
        message_label = tk.Label(
            main_frame,
            text=self.config.message,
            font=('Segoe UI', 9),
            fg=self._get_text_color(),
            bg=self._get_bg_color(),
            wraplength=280,
            justify='left'
        )
        message_label.pack(fill='x')
        
        # Progress bar for duration
        if self.config.duration > 0:
            self.progress_bar = ttk.Progressbar(
                main_frame,
                length=300,
                mode='determinate',
                style='Toast.Horizontal.TProgressbar'
            )
            self.progress_bar.pack(fill='x', pady=(10, 0))
    
    def _get_bg_color(self) -> str:
        """Get background color based on toast type."""
        colors = {
            ToastType.INFO: '#2d3748',
            ToastType.SUCCESS: '#065f46',
            ToastType.WARNING: '#92400e',
            ToastType.ERROR: '#7f1d1d'
        }
        return colors.get(self.config.toast_type, '#2d3748')
    
    def _get_text_color(self) -> str:
        """Get text color based on toast type."""
        return '#ffffff'
    
    def _get_icon_color(self) -> str:
        """Get icon color based on toast type."""
        colors = {
            ToastType.INFO: '#3b82f6',
            ToastType.SUCCESS: '#10b981',
            ToastType.WARNING: '#f59e0b',
            ToastType.ERROR: '#ef4444'
        }
        return colors.get(self.config.toast_type, '#3b82f6')
    
    def _position_window(self):
        """Position the toast window."""
        self.window.update_idletasks()
        
        # Get window dimensions
        window_width = self.window.winfo_reqwidth()
        window_height = self.window.winfo_reqheight()
        
        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Position based on config
        position_map = {
            'top-left': (20, 20),
            'top-right': (screen_width - window_width - 20, 20),
            'bottom-left': (20, screen_height - window_height - 60),
            'bottom-right': (screen_width - window_width - 20, screen_height - window_height - 60),
            'center': ((screen_width - window_width) // 2, (screen_height - window_height) // 2)
        }
        
        x, y = position_map.get(self.config.position, position_map['bottom-right'])
        
        # Adjust for multiple toasts (if callback provided)
        if self.manager_callback:
            y = self.manager_callback(y, window_height)
        
        self.window.geometry(f'+{x}+{y}')
    
    def show(self):
        """Show the toast with fade-in animation."""
        if not self.window:
            return
        
        self.window.deiconify()
        self._fade_in()
        
        # Start auto-hide timer
        if self.config.duration > 0:
            self._start_progress_animation()
            self.window.after(self.config.duration, self.close)
    
    def _fade_in(self):
        """Fade in animation."""
        try:
            alpha = 0.0
            def fade_step():
                nonlocal alpha
                alpha += 0.1
                if alpha <= 1.0:
                    try:
                        self.window.attributes('-alpha', alpha)
                        self.window.after(20, fade_step)
                    except tk.TclError:
                        pass
            fade_step()
        except tk.TclError:
            # Platform doesn't support alpha, just show
            pass
    
    def _start_progress_animation(self):
        """Animate progress bar."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar['maximum'] = self.config.duration
            
            start_time = time.time() * 1000
            
            def update_progress():
                if not self.window or not self.window.winfo_exists():
                    return
                
                current_time = time.time() * 1000
                elapsed = current_time - start_time
                
                if elapsed < self.config.duration:
                    progress = (elapsed / self.config.duration) * 100
                    try:
                        self.progress_bar['value'] = progress
                        self.window.after(50, update_progress)
                    except tk.TclError:
                        pass
            
            update_progress()
    
    def close(self):
        """Close the toast with fade-out animation."""
        if not self.window or not self.window.winfo_exists():
            return
        
        try:
            alpha = 1.0
            def fade_step():
                nonlocal alpha
                alpha -= 0.1
                if alpha >= 0.0:
                    try:
                        self.window.attributes('-alpha', alpha)
                        self.window.after(20, fade_step)
                    except tk.TclError:
                        self._destroy_window()
                else:
                    self._destroy_window()
            fade_step()
        except tk.TclError:
            self._destroy_window()
    
    def _destroy_window(self):
        """Destroy the window."""
        try:
            if self.window and self.window.winfo_exists():
                self.window.destroy()
        except tk.TclError:
            pass
        finally:
            self.window = None

class TkinterToastProvider(ToastProvider):
    """Tkinter-based toast provider."""
    
    def __init__(self):
        self.root = None
        self.active_toasts: List[TkinterToast] = []
        self.toast_positions: Dict[str, int] = {}
        self._setup_root()
    
    def _setup_root(self):
        """Setup hidden tkinter root."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # Hide the root window
            
            # Configure ttk styles
            style = ttk.Style()
            style.theme_use('clam')
            
            # Custom progress bar style
            style.configure(
                'Toast.Horizontal.TProgressbar',
                background='#4f46e5',
                troughcolor='#374151',
                borderwidth=0,
                lightcolor='#4f46e5',
                darkcolor='#4f46e5'
            )
            
        except Exception as e:
            print(f"Failed to setup tkinter root: {e}")
            self.root = None
    
    def is_available(self) -> bool:
        """Check if tkinter is available."""
        return self.root is not None
    
    async def show_toast(self, config: ToastConfig) -> None:
        """Show tkinter toast notification."""
        if not self.root:
            raise RuntimeError("Tkinter not available")
        
        # Run in thread to avoid blocking
        def show_toast_sync():
            try:
                toast = TkinterToast(config, self._get_position_callback(config.position))
                toast.create_window()
                toast.show()
                
                self.active_toasts.append(toast)
                
                # Clean up after duration + fade time
                cleanup_delay = config.duration + 500 if config.duration > 0 else 5000
                self.root.after(cleanup_delay, lambda: self._cleanup_toast(toast))
                
            except Exception as e:
                print(f"Error showing tkinter toast: {e}")
        
        # Use thread to avoid blocking async context
        thread = threading.Thread(target=show_toast_sync)
        thread.daemon = True
        thread.start()
    
    def _get_position_callback(self, position: str):
        """Get callback for positioning multiple toasts."""
        def position_callback(base_y: int, window_height: int) -> int:
            if position not in self.toast_positions:
                self.toast_positions[position] = 0
            
            # Stack toasts vertically
            offset = self.toast_positions[position] * (window_height + 10)
            self.toast_positions[position] += 1
            
            # Auto-cleanup position counter
            self.root.after(5000, lambda: self._cleanup_position(position))
            
            if 'top' in position:
                return base_y + offset
            else:
                return base_y - offset
        
        return position_callback
    
    def _cleanup_position(self, position: str):
        """Clean up position counter."""
        if position in self.toast_positions:
            self.toast_positions[position] = max(0, self.toast_positions[position] - 1)
    
    def _cleanup_toast(self, toast: TkinterToast):
        """Remove toast from active list."""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
    
    def cleanup(self) -> None:
        """Clean up tkinter resources."""
        # Close all active toasts
        for toast in self.active_toasts[:]:
            toast.close()
        
        self.active_toasts.clear()
        
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except tk.TclError:
                pass
            self.root = None
```

### 4. Fallback Console Provider

**File**: `ghostman/src/ui/components/fallback_toast_provider.py`

```python
from .toast_manager import ToastProvider, ToastConfig, ToastType
import sys
from datetime import datetime

class FallbackToastProvider(ToastProvider):
    """Console-based fallback toast provider."""
    
    def is_available(self) -> bool:
        """Always available as last resort."""
        return True
    
    async def show_toast(self, config: ToastConfig) -> None:
        """Show toast as console output."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        type_symbol = self._get_type_symbol(config.toast_type)
        
        message = f"[{timestamp}] {type_symbol} {config.title}: {config.message}"
        
        if config.toast_type == ToastType.ERROR:
            print(message, file=sys.stderr)
        else:
            print(message)
    
    def _get_type_symbol(self, toast_type: ToastType) -> str:
        """Get symbol for toast type."""
        symbols = {
            ToastType.INFO: "ℹ️",
            ToastType.SUCCESS: "✅", 
            ToastType.WARNING: "⚠️",
            ToastType.ERROR: "❌"
        }
        return symbols.get(toast_type, "ℹ️")
    
    def cleanup(self) -> None:
        """No cleanup needed for console output."""
        pass
```

### 5. PyQt6 Integration Layer

**File**: `ghostman/src/ui/components/qt_toast_bridge.py`

```python
from PyQt6.QtCore import QObject, QThread, pyqtSignal
import asyncio
from .toast_manager import ToastManager, ToastConfig

class ToastWorker(QThread):
    """Worker thread for handling async toast operations."""
    
    def __init__(self):
        super().__init__()
        self.toast_manager = ToastManager()
        self.toast_queue = []
        self.running = True
    
    def add_toast(self, config: ToastConfig):
        """Add toast to queue."""
        self.toast_queue.append(config)
    
    def run(self):
        """Main worker loop."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        async def process_toasts():
            while self.running:
                if self.toast_queue:
                    config = self.toast_queue.pop(0)
                    await self.toast_manager.show_toast(config)
                await asyncio.sleep(0.1)
        
        loop.run_until_complete(process_toasts())
    
    def cleanup(self):
        """Clean up worker."""
        self.running = False
        self.toast_manager.cleanup()
        self.quit()
        self.wait()

class QtToastManager(QObject):
    """PyQt6 integration layer for toast notifications."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = ToastWorker()
        self.worker.start()
    
    def show_info(self, title: str, message: str, **kwargs):
        """Show info toast."""
        config = ToastConfig(title, message, ToastType.INFO, **kwargs)
        self.worker.add_toast(config)
    
    def show_success(self, title: str, message: str, **kwargs):
        """Show success toast."""
        config = ToastConfig(title, message, ToastType.SUCCESS, **kwargs)
        self.worker.add_toast(config)
    
    def show_warning(self, title: str, message: str, **kwargs):
        """Show warning toast."""
        config = ToastConfig(title, message, ToastType.WARNING, **kwargs)
        self.worker.add_toast(config)
    
    def show_error(self, title: str, message: str, **kwargs):
        """Show error toast."""
        config = ToastConfig(title, message, ToastType.ERROR, **kwargs)
        self.worker.add_toast(config)
    
    def cleanup(self):
        """Clean up resources."""
        if self.worker:
            self.worker.cleanup()
```

## Integration with Main Application

### Usage in Ghostman Application

**File**: `ghostman/src/app/application.py` (excerpt)

```python
from PyQt6.QtWidgets import QApplication
from ghostman.ui.components.qt_toast_bridge import QtToastManager

class GhostmanApplication:
    def __init__(self):
        # ... other initialization
        self.toast_manager = QtToastManager()
        
        # Connect to application events
        self.setup_toast_notifications()
    
    def setup_toast_notifications(self):
        """Setup toast notification handlers."""
        # AI processing notifications
        self.conversation_manager.ai_request_started.connect(
            lambda: self.toast_manager.show_info("AI Assistant", "Processing your request...")
        )
        
        self.conversation_manager.ai_response_received.connect(
            lambda: self.toast_manager.show_success("AI Assistant", "Response ready!")
        )
        
        self.conversation_manager.ai_error.connect(
            lambda error: self.toast_manager.show_error("AI Assistant", f"Error: {error}")
        )
        
        # System notifications
        self.window_manager.state_changed.connect(self.on_window_state_changed)
    
    def on_window_state_changed(self, old_state, new_state):
        """Handle window state changes with toasts."""
        if new_state == WindowState.AVATAR:
            self.toast_manager.show_info(
                "Ghostman", 
                "Minimized to avatar mode",
                duration=2000
            )
    
    def shutdown(self):
        """Clean shutdown."""
        self.toast_manager.cleanup()
        # ... other cleanup
```

## Testing Plan

### Unit Tests

**File**: `ghostman/tests/test_toast_system.py`

```python
import pytest
import asyncio
from ghostman.ui.components.toast_manager import ToastManager, ToastConfig, ToastType

class TestToastManager:
    @pytest.fixture
    def toast_manager(self):
        return ToastManager()
    
    def test_provider_initialization(self, toast_manager):
        """Test that at least one provider is available."""
        assert len(toast_manager.providers) > 0
        assert toast_manager.current_provider is not None
    
    @pytest.mark.asyncio
    async def test_basic_toast(self, toast_manager):
        """Test basic toast functionality."""
        config = ToastConfig("Test Title", "Test Message")
        
        # Should not raise exception
        await toast_manager.show_toast(config)
    
    @pytest.mark.asyncio
    async def test_toast_types(self, toast_manager):
        """Test different toast types."""
        for toast_type in ToastType:
            config = ToastConfig("Test", "Message", toast_type)
            await toast_manager.show_toast(config)
    
    def test_cleanup(self, toast_manager):
        """Test cleanup functionality."""
        toast_manager.cleanup()
        # Should not raise exception
```

### Integration Tests

**File**: `ghostman/tests/test_toast_integration.py`

```python
import pytest
from PyQt6.QtWidgets import QApplication
from ghostman.ui.components.qt_toast_bridge import QtToastManager
import time

class TestToastIntegration:
    @pytest.fixture(scope="session")
    def app(self):
        app = QApplication([])
        yield app
        app.quit()
    
    def test_qt_integration(self, app):
        """Test PyQt6 integration."""
        manager = QtToastManager()
        
        # Test basic functionality
        manager.show_info("Test", "Integration test")
        manager.show_success("Test", "Success test")
        manager.show_warning("Test", "Warning test")
        manager.show_error("Test", "Error test")
        
        # Allow processing
        time.sleep(1)
        
        manager.cleanup()
```

## Deployment Considerations

### Dependencies

Add to `requirements.txt`:
```
desktop-notifier>=4.3.0  # For native notifications
```

### Optional Dependencies

For enhanced features:
```
plyer>=2.1.0  # Alternative native notifications
win10toast>=0.9  # Windows 10/11 specific toasts (Windows only)
```

### PyInstaller Configuration

Add to `Ghostman.spec`:
```python
# Hidden imports for toast system
hiddenimports += [
    'desktop_notifier',
    'desktop_notifier.backends',
    'plyer.platforms.win.notification',
    'tkinter',
    'tkinter.ttk',
]

# Data files for icons
datas += [
    ('assets/icons/*.png', 'assets/icons/'),
]
```

This comprehensive toast notification system provides multiple fallback options, ensuring reliable notifications across different platforms while maintaining integration with the PyQt6 main application.