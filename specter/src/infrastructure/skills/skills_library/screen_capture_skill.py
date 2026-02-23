"""
Screen Capture Skill - Capture screen regions with shape selection and borders.

This skill provides a full-screen overlay for selecting screen regions to capture
using various shapes (rectangle, circle, freeform) with optional border rendering.
"""

import logging
from typing import List, Any, Dict, Optional
from pathlib import Path
import os

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)
from ..interfaces.screen_capture_skill import CaptureShape, CaptureResult

logger = logging.getLogger("specter.skills.screen_capture")


class ScreenCaptureSkill(BaseSkill):
    """
    Skill for capturing screen regions with shape selection and borders.

    Displays a full-screen overlay allowing users to select a region using
    different shapes (rectangle, circle, freeform) and optionally apply
    borders. Captured images can be saved or copied to clipboard.

    Requirements:
        - PyQt6 for overlay UI
        - Pillow for image capture and processing
        - Optional: pytesseract for OCR text extraction

    Example:
        >>> skill = ScreenCaptureSkill()
        >>> result = await skill.execute(
        ...     shape="rectangle",
        ...     border_width=2,
        ...     save_to_file=True
        ... )
        >>> print(result.data["file_path"])
        "C:\\Users\\...\\AppData\\Roaming\\Specter\\captures\\capture_20250122_143052.png"
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="screen_capture",
            name="Screen Capture",
            description="Capture screen regions with shapes and borders",
            category=SkillCategory.SCREEN_CAPTURE,
            icon="📸",
            enabled_by_default=True,
            requires_confirmation=False,  # Safe operation
            permissions_required=[PermissionType.SCREEN_CAPTURE],
            version="1.0.0",
            author="Specter"
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        """Return list of parameters this skill accepts."""
        return [
            SkillParameter(
                name="shape",
                type=str,
                required=False,
                description="Capture shape: 'rectangle', 'circle', or 'freeform'",
                default="rectangle",
                constraints={"enum": ["rectangle", "circle", "freeform"]}
            ),
            SkillParameter(
                name="border_width",
                type=int,
                required=False,
                description="Border width in pixels (0 = no border)",
                default=0,
                constraints={"min": 0, "max": 20}
            ),
            SkillParameter(
                name="border_color",
                type=str,
                required=False,
                description="Border color (hex format: #RRGGBB)",
                default="#FF0000",
                constraints={"pattern": r"^#[0-9A-Fa-f]{6}$"}
            ),
            SkillParameter(
                name="save_to_file",
                type=bool,
                required=False,
                description="Save capture to file (otherwise clipboard only)",
                default=True
            ),
            SkillParameter(
                name="copy_to_clipboard",
                type=bool,
                required=False,
                description="Copy capture to clipboard",
                default=True
            ),
            SkillParameter(
                name="extract_text",
                type=bool,
                required=False,
                description="Extract text from capture using OCR",
                default=False
            ),
        ]

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the screen capture skill.

        Opens a full-screen overlay for region selection, captures the selected
        region, and optionally applies borders, saves to file, or extracts text.

        Args:
            **params: Validated parameters (shape, border_width, etc.)

        Returns:
            SkillResult with capture information and file path
        """
        try:
            # Import dependencies
            try:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtCore import QEventLoop
                from PIL import ImageGrab, Image, ImageDraw
            except ImportError as e:
                return SkillResult(
                    success=False,
                    message="Screen capture dependencies not available",
                    error=f"Missing required package: {str(e)}"
                )

            # Import overlay widget
            try:
                from ....presentation.widgets.skills.screen_capture_overlay import ScreenCaptureOverlay
            except ImportError:
                return SkillResult(
                    success=False,
                    message="Screen capture overlay not available",
                    error="ScreenCaptureOverlay widget not found"
                )

            # Parse shape parameter
            shape_str = params.get("shape", "rectangle").lower()
            shape_map = {
                "rectangle": CaptureShape.RECTANGLE,
                "circle": CaptureShape.CIRCLE,
                "freeform": CaptureShape.FREEFORM,
            }
            shape = shape_map.get(shape_str, CaptureShape.RECTANGLE)

            # Get Qt application instance
            app = QApplication.instance()
            if not app:
                return SkillResult(
                    success=False,
                    message="Qt application not available",
                    error="Screen capture requires Qt application to be running"
                )

            # Create and show overlay
            overlay = ScreenCaptureOverlay(
                shape=shape,
                border_width=params.get("border_width", 0),
                border_color=params.get("border_color", "#FF0000")
            )

            # Wait for user to complete capture
            loop = QEventLoop()
            capture_result: Optional[CaptureResult] = None

            def on_capture_complete(result: CaptureResult):
                nonlocal capture_result
                capture_result = result
                loop.quit()

            def on_capture_cancelled():
                loop.quit()

            overlay.capture_completed.connect(on_capture_complete)
            overlay.capture_cancelled.connect(on_capture_cancelled)

            overlay.show()
            loop.exec()

            # Check if capture was cancelled
            if not capture_result or not capture_result.image_data:
                return SkillResult(
                    success=False,
                    message="Capture cancelled",
                    error="User cancelled screen capture"
                )

            # Process captured image
            image = Image.open(capture_result.image_data)

            # Apply border if requested
            if params.get("border_width", 0) > 0:
                image = self._apply_border(
                    image,
                    params["border_width"],
                    params.get("border_color", "#FF0000")
                )

            # Save to file if requested
            file_path = None
            if params.get("save_to_file", True):
                file_path = self._save_capture(image)

            # Copy to clipboard if requested
            if params.get("copy_to_clipboard", True):
                self._copy_to_clipboard(image)

            # Extract text if requested
            extracted_text = None
            if params.get("extract_text", False):
                extracted_text = self._extract_text(image)

            logger.info(f"✓ Screen capture completed: {file_path or 'clipboard'}")

            return SkillResult(
                success=True,
                message="Screen captured successfully",
                data={
                    "file_path": file_path,
                    "width": capture_result.width,
                    "height": capture_result.height,
                    "shape": shape_str,
                    "has_border": params.get("border_width", 0) > 0,
                    "copied_to_clipboard": params.get("copy_to_clipboard", True),
                    "extracted_text": extracted_text,
                },
                action_taken=f"Captured {shape_str} region ({capture_result.width}x{capture_result.height})",
            )

        except Exception as e:
            logger.error(f"Screen capture skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="Screen capture failed",
                error=str(e)
            )

    def _apply_border(self, image: 'Image.Image', width: int, color: str) -> 'Image.Image':
        """Apply border to captured image."""
        from PIL import ImageDraw

        draw = ImageDraw.Draw(image)

        # Draw border rectangle
        for i in range(width):
            draw.rectangle(
                [(i, i), (image.width - 1 - i, image.height - 1 - i)],
                outline=color
            )

        return image

    def _save_capture(self, image: 'Image.Image') -> str:
        """Save captured image to file."""
        from datetime import datetime
        from ...storage.settings_manager import settings

        # Get save directory from settings or use default
        custom_save_path = settings.get('screen_capture.default_save_path', '')

        if custom_save_path and Path(custom_save_path).exists():
            # Use custom path if set and exists
            captures_dir = Path(custom_save_path)
        else:
            # Use default %APPDATA%\Specter\captures
            appdata = os.environ.get('APPDATA', '')
            if not appdata:
                raise RuntimeError("APPDATA environment variable not found")
            captures_dir = Path(appdata) / "Specter" / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.png"
        file_path = captures_dir / filename

        # Save image
        image.save(str(file_path), "PNG")

        return str(file_path)

    def _copy_to_clipboard(self, image: 'Image.Image') -> None:
        """Copy image to system clipboard."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QImage, QPixmap
        from PyQt6.QtCore import QBuffer, QIODevice
        import io

        # Convert PIL Image to QPixmap
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        qimage = QImage()
        qimage.loadFromData(buffer.read())
        pixmap = QPixmap.fromImage(qimage)

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)

    def _extract_text(self, image: 'Image.Image') -> Optional[str]:
        """Extract text from image using OCR."""
        try:
            import pytesseract

            # Perform OCR
            text = pytesseract.image_to_string(image)
            return text.strip() if text else None

        except ImportError:
            logger.warning("pytesseract not available for OCR")
            return None
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return None

    async def on_success(self, result: SkillResult) -> None:
        """Log successful screen capture."""
        logger.info(f"Screen capture skill succeeded: {result.data}")

    async def on_error(self, result: SkillResult) -> None:
        """Log screen capture failure."""
        logger.warning(f"Screen capture skill failed: {result.error}")
