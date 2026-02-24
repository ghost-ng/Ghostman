"""
DOCX File Preview - Opens documents in the system default application.

Workflow: close file -> make changes -> open file -> user reviews -> repeat.
Uses os.startfile() on Windows to open in Word (or whatever is default).
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("specter.skills.docx_preview")


class DocxBrowserPreview:
    """Opens DOCX files in the system default application for review.

    Workflow:
        preview.open_document("file.docx")   # opens in Word
        # ... skill makes changes ...
        preview.refresh_preview()             # re-opens the file
        preview.close()                       # marks session ended
    """

    def __init__(self, colors=None):
        self._file_path: Optional[str] = None
        self._active = False

    def open_document(self, file_path: str) -> bool:
        """Open the DOCX file in the system default application.

        Args:
            file_path: Absolute path to a .docx file.

        Returns:
            True if the file was opened successfully.
        """
        p = Path(file_path)
        if not p.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        self._file_path = str(p)
        self._active = True
        return self._launch_file()

    def refresh_preview(self):
        """Re-open the file so the user sees the latest changes."""
        if self._active and self._file_path:
            self._launch_file()

    @property
    def is_running(self) -> bool:
        return self._active

    @property
    def current_file(self) -> Optional[str]:
        return self._file_path

    def set_colors(self, colors):
        """No-op — native app handles its own styling."""
        pass

    def close(self):
        """Mark the preview session as ended."""
        self._active = False
        self._file_path = None

    def _launch_file(self) -> bool:
        """Open the file with the OS default handler."""
        if not self._file_path:
            return False
        try:
            if sys.platform == "win32":
                os.startfile(self._file_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self._file_path])
            else:
                subprocess.Popen(["xdg-open", self._file_path])
            logger.info(f"Opened in default app: {self._file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            return False


# Backwards-compatible alias
DocxPreviewPanel = DocxBrowserPreview
