"""
Screen capture skill interfaces and data structures.

This module defines the specific interfaces, enums, and dataclasses
for the screen capture skill functionality.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
from pathlib import Path


class CaptureMode(Enum):
    """
    Screen capture modes supported by the skill.

    Attributes:
        RECTANGLE: User selects a rectangular region
        CIRCLE: User selects a circular region
        FREEFORM: User draws a custom shape
        WINDOW: Captures a specific window
        FULLSCREEN: Captures entire screen(s)
        SCROLLING: Captures scrolling content (long webpage, etc.)
    """

    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    FREEFORM = "freeform"
    WINDOW = "window"
    FULLSCREEN = "fullscreen"
    SCROLLING = "scrolling"


class BorderStyle(Enum):
    """
    Border line styles for annotations.

    Attributes:
        SOLID: Solid line
        DASHED: Dashed line
        DOTTED: Dotted line
        DOUBLE: Double line
    """

    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DOUBLE = "double"


class AnnotationType(Enum):
    """
    Types of annotations that can be added to screenshots.

    Attributes:
        ARROW: Arrow pointing to something
        RECTANGLE: Rectangle shape
        CIRCLE: Circle/ellipse shape
        TEXT: Text label
        FREEHAND: Freehand drawing
        HIGHLIGHT: Highlight/blur region
        BLUR: Blur sensitive content
        NUMBER: Numbered marker (1, 2, 3...)
    """

    ARROW = "arrow"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    TEXT = "text"
    FREEHAND = "freehand"
    HIGHLIGHT = "highlight"
    BLUR = "blur"
    NUMBER = "number"


class ImageFormat(Enum):
    """
    Supported image output formats.

    Attributes:
        PNG: PNG format (lossless)
        JPEG: JPEG format (lossy)
        BMP: BMP format (uncompressed)
        WEBP: WebP format (modern compression)
    """

    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"
    WEBP = "webp"


@dataclass(frozen=True)
class BorderConfig:
    """
    Configuration for border/outline styling.

    Attributes:
        width: Border width in pixels
        color: Border color (hex format: #RRGGBB or #RRGGBBAA)
        style: Border line style
        opacity: Border opacity (0.0 to 1.0)

    Example:
        >>> border = BorderConfig(
        ...     width=3,
        ...     color="#FF0000",
        ...     style=BorderStyle.DASHED,
        ...     opacity=0.8
        ... )
    """

    width: int
    color: str
    style: BorderStyle = BorderStyle.SOLID
    opacity: float = 1.0

    def __post_init__(self):
        """Validate border configuration."""
        if self.width < 0:
            raise ValueError(f"width must be >= 0, got {self.width}")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError(f"opacity must be between 0.0 and 1.0, got {self.opacity}")
        if not self._is_valid_color(self.color):
            raise ValueError(f"color must be in format #RRGGBB or #RRGGBBAA, got {self.color}")

    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Validate hex color format."""
        if not color.startswith("#"):
            return False
        hex_part = color[1:]
        return len(hex_part) in (6, 8) and all(c in "0123456789ABCDEFabcdef" for c in hex_part)


@dataclass
class Annotation:
    """
    An annotation added to a screenshot.

    Attributes:
        type: Type of annotation
        position: (x, y) position in pixels
        size: (width, height) in pixels for shapes
        color: Annotation color (hex format)
        text: Text content (for TEXT annotations)
        points: List of points for FREEHAND annotations
        thickness: Line thickness in pixels
        opacity: Annotation opacity (0.0 to 1.0)
        metadata: Additional annotation-specific data

    Example:
        >>> # Arrow annotation
        >>> arrow = Annotation(
        ...     type=AnnotationType.ARROW,
        ...     position=(100, 100),
        ...     size=(50, 50),
        ...     color="#FF0000",
        ...     thickness=3
        ... )
        >>>
        >>> # Text annotation
        >>> text = Annotation(
        ...     type=AnnotationType.TEXT,
        ...     position=(200, 200),
        ...     color="#000000",
        ...     text="Important section"
        ... )
    """

    type: AnnotationType
    position: Tuple[int, int]
    color: str = "#FF0000"
    size: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    points: List[Tuple[int, int]] = field(default_factory=list)
    thickness: int = 2
    opacity: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate annotation."""
        if self.type == AnnotationType.TEXT and not self.text:
            raise ValueError("TEXT annotation requires text attribute")
        if self.type == AnnotationType.FREEHAND and not self.points:
            raise ValueError("FREEHAND annotation requires points attribute")
        if self.thickness < 1:
            raise ValueError(f"thickness must be >= 1, got {self.thickness}")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError(f"opacity must be between 0.0 and 1.0, got {self.opacity}")


@dataclass
class CaptureRegion:
    """
    Defines a region of the screen to capture.

    Attributes:
        x: Left edge in pixels
        y: Top edge in pixels
        width: Width in pixels
        height: Height in pixels
        monitor: Monitor index (0 for primary, 1+ for additional monitors)

    Example:
        >>> # Capture top-left 800x600 region
        >>> region = CaptureRegion(x=0, y=0, width=800, height=600)
        >>>
        >>> # Capture from second monitor
        >>> region = CaptureRegion(x=0, y=0, width=1920, height=1080, monitor=1)
    """

    x: int
    y: int
    width: int
    height: int
    monitor: int = 0

    def __post_init__(self):
        """Validate region."""
        if self.width <= 0:
            raise ValueError(f"width must be > 0, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"height must be > 0, got {self.height}")
        if self.monitor < 0:
            raise ValueError(f"monitor must be >= 0, got {self.monitor}")

    @property
    def area(self) -> int:
        """Calculate region area in pixels."""
        return self.width * self.height

    @property
    def bottom_right(self) -> Tuple[int, int]:
        """Get bottom-right corner coordinates."""
        return (self.x + self.width, self.y + self.height)


@dataclass
class CaptureOptions:
    """
    Options for configuring screen capture behavior.

    Attributes:
        mode: Capture mode
        region: Specific region to capture (None for interactive selection)
        border: Border configuration (None for no border)
        cursor_visible: Whether to include mouse cursor
        format: Output image format
        quality: JPEG quality (1-100, only for JPEG format)
        save_to_file: Whether to save to disk
        save_path: File path to save to (None for default location)
        copy_to_clipboard: Whether to copy to clipboard
        show_editor: Whether to open annotation editor after capture
        ocr_enabled: Whether to perform OCR on captured image
        delay_seconds: Delay before capture (useful for menus)
        annotations: Pre-defined annotations to apply

    Example:
        >>> options = CaptureOptions(
        ...     mode=CaptureMode.RECTANGLE,
        ...     border=BorderConfig(width=2, color="#FF0000"),
        ...     cursor_visible=False,
        ...     format=ImageFormat.PNG,
        ...     copy_to_clipboard=True,
        ...     show_editor=True,
        ...     ocr_enabled=True
        ... )
    """

    mode: CaptureMode = CaptureMode.RECTANGLE
    region: Optional[CaptureRegion] = None
    border: Optional[BorderConfig] = None
    cursor_visible: bool = False
    format: ImageFormat = ImageFormat.PNG
    quality: int = 95
    save_to_file: bool = True
    save_path: Optional[Path] = None
    copy_to_clipboard: bool = True
    show_editor: bool = False
    ocr_enabled: bool = False
    delay_seconds: float = 0.0
    annotations: List[Annotation] = field(default_factory=list)

    def __post_init__(self):
        """Validate options."""
        if not 1 <= self.quality <= 100:
            raise ValueError(f"quality must be between 1 and 100, got {self.quality}")
        if self.delay_seconds < 0:
            raise ValueError(f"delay_seconds must be >= 0, got {self.delay_seconds}")
        if not self.save_to_file and not self.copy_to_clipboard:
            raise ValueError("At least one of save_to_file or copy_to_clipboard must be True")


@dataclass
class OCRResult:
    """
    Result of OCR (Optical Character Recognition) on captured image.

    Attributes:
        text: Extracted text content
        confidence: OCR confidence score (0.0 to 1.0)
        language: Detected language code
        blocks: List of text blocks with positions
        processing_time_ms: Time taken for OCR in milliseconds

    Example:
        >>> ocr = OCRResult(
        ...     text="Hello World\nThis is a test",
        ...     confidence=0.95,
        ...     language="en",
        ...     blocks=[
        ...         {"text": "Hello World", "position": (10, 10, 100, 30)},
        ...         {"text": "This is a test", "position": (10, 40, 120, 60)}
        ...     ],
        ...     processing_time_ms=250
        ... )
    """

    text: str
    confidence: float
    language: str = "en"
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: int = 0

    def __post_init__(self):
        """Validate OCR result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class CaptureResult:
    """
    Result of a screen capture operation.

    This extends SkillResult with screen-capture-specific data.

    Attributes:
        image_path: Path to saved image file (None if not saved)
        image_size: (width, height) of captured image
        image_format: Format of the saved image
        ocr_result: OCR result if OCR was enabled
        thumbnail_path: Path to thumbnail image (if generated)
        clipboard_copied: Whether image was copied to clipboard
        annotations_applied: List of annotations applied
        capture_duration_ms: Time taken to capture in milliseconds
        file_size_bytes: Size of saved file in bytes
        metadata: Additional capture metadata

    Example:
        >>> result = CaptureResult(
        ...     image_path=Path("C:/screenshots/screenshot_001.png"),
        ...     image_size=(1920, 1080),
        ...     image_format=ImageFormat.PNG,
        ...     ocr_result=ocr_data,
        ...     clipboard_copied=True,
        ...     annotations_applied=[arrow_annotation],
        ...     capture_duration_ms=150,
        ...     file_size_bytes=524288
        ... )
    """

    image_path: Optional[Path] = None
    image_size: Optional[Tuple[int, int]] = None
    image_format: ImageFormat = ImageFormat.PNG
    ocr_result: Optional[OCRResult] = None
    thumbnail_path: Optional[Path] = None
    clipboard_copied: bool = False
    annotations_applied: List[Annotation] = field(default_factory=list)
    capture_duration_ms: int = 0
    file_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate capture result."""
        if self.image_size:
            width, height = self.image_size
            if width <= 0 or height <= 0:
                raise ValueError(f"image_size dimensions must be > 0, got {self.image_size}")

    @property
    def aspect_ratio(self) -> Optional[float]:
        """Calculate aspect ratio of captured image."""
        if self.image_size:
            width, height = self.image_size
            return width / height if height > 0 else None
        return None

    @property
    def file_size_kb(self) -> float:
        """Get file size in kilobytes."""
        return self.file_size_bytes / 1024

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the capture result
        """
        return {
            "image_path": str(self.image_path) if self.image_path else None,
            "image_size": self.image_size,
            "image_format": self.image_format.value,
            "ocr_text": self.ocr_result.text if self.ocr_result else None,
            "ocr_confidence": self.ocr_result.confidence if self.ocr_result else None,
            "clipboard_copied": self.clipboard_copied,
            "annotations_count": len(self.annotations_applied),
            "capture_duration_ms": self.capture_duration_ms,
            "file_size_bytes": self.file_size_bytes,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ScreenInfo:
    """
    Information about available screens/monitors.

    Attributes:
        monitor_id: Monitor index
        name: Monitor name/description
        width: Screen width in pixels
        height: Screen height in pixels
        x: Screen X offset (for multi-monitor setups)
        y: Screen Y offset (for multi-monitor setups)
        is_primary: Whether this is the primary monitor
        scale_factor: DPI scale factor (1.0 = 100%, 1.5 = 150%, etc.)

    Example:
        >>> screen = ScreenInfo(
        ...     monitor_id=0,
        ...     name="Primary Display",
        ...     width=1920,
        ...     height=1080,
        ...     x=0,
        ...     y=0,
        ...     is_primary=True,
        ...     scale_factor=1.0
        ... )
    """

    monitor_id: int
    name: str
    width: int
    height: int
    x: int = 0
    y: int = 0
    is_primary: bool = False
    scale_factor: float = 1.0

    @property
    def resolution(self) -> str:
        """Get resolution as formatted string."""
        return f"{self.width}x{self.height}"

    @property
    def bounds(self) -> CaptureRegion:
        """Get screen bounds as CaptureRegion."""
        return CaptureRegion(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            monitor=self.monitor_id
        )


# Usage Examples
if __name__ == "__main__":
    # Example 1: Simple fullscreen capture
    simple_options = CaptureOptions(
        mode=CaptureMode.FULLSCREEN,
        copy_to_clipboard=True
    )

    # Example 2: Rectangle capture with border and OCR
    advanced_options = CaptureOptions(
        mode=CaptureMode.RECTANGLE,
        border=BorderConfig(
            width=3,
            color="#FF0000",
            style=BorderStyle.DASHED,
            opacity=0.8
        ),
        ocr_enabled=True,
        show_editor=True
    )

    # Example 3: Capture specific region with annotations
    region = CaptureRegion(x=100, y=100, width=800, height=600)
    arrow = Annotation(
        type=AnnotationType.ARROW,
        position=(150, 150),
        size=(50, 50),
        color="#00FF00",
        thickness=3
    )
    text = Annotation(
        type=AnnotationType.TEXT,
        position=(200, 200),
        text="Look here!",
        color="#000000"
    )

    region_options = CaptureOptions(
        mode=CaptureMode.RECTANGLE,
        region=region,
        annotations=[arrow, text],
        format=ImageFormat.PNG,
        save_to_file=True,
        save_path=Path("C:/screenshots/annotated.png")
    )

    # Example 4: Window capture with delay
    window_options = CaptureOptions(
        mode=CaptureMode.WINDOW,
        delay_seconds=2.0,  # Give user time to focus the window
        cursor_visible=False,
        copy_to_clipboard=True
    )

    # Example 5: Processing capture result
    result = CaptureResult(
        image_path=Path("C:/screenshots/test.png"),
        image_size=(1920, 1080),
        image_format=ImageFormat.PNG,
        clipboard_copied=True,
        capture_duration_ms=125,
        file_size_bytes=524288
    )

    print(f"Captured image: {result.image_path}")
    print(f"Size: {result.image_size}")
    print(f"Aspect ratio: {result.aspect_ratio:.2f}")
    print(f"File size: {result.file_size_kb:.2f} KB")
    print(f"Capture took: {result.capture_duration_ms} ms")

    # Example 6: OCR result
    if result.ocr_result:
        print(f"OCR Text: {result.ocr_result.text}")
        print(f"OCR Confidence: {result.ocr_result.confidence:.2%}")
