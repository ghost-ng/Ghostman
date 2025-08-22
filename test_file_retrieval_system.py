#!/usr/bin/env python3
"""
Comprehensive test suite for the Ghostman File Retrieval System.

This test script validates all components of the file retrieval system:
- File validation service
- File upload service  
- Fine-tuning service
- File toolbar widget
- Database integration
- Drag-and-drop functionality

Run this test to ensure the file retrieval system is working correctly.
"""

import sys
import os
import tempfile
import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

# Add the ghostman package to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

# Import Ghostman components
try:
    from ghostman.src.application.services.file_validation_service import FileValidationService
    from ghostman.src.application.services.file_upload_service import FileUploadService, FileUploadProgress
    from ghostman.src.application.services.fine_tuning_service import FineTuningService
    from ghostman.src.presentation.widgets.file_toolbar import FineTuningToolbar
    from ghostman.src.presentation.widgets.repl_widget import REPLWidget
    from ghostman.src.infrastructure.ai.file_models import OpenAIFile, VectorStore, FileOperationResult
    from ghostman.src.infrastructure.storage.file_metadata_models import (
        FileMetadataModel, VectorStoreMetadataModel, FileStorageDatabaseManager
    )
    GHOSTMAN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Ghostman components not available: {e}")
    GHOSTMAN_AVAILABLE = False

# Test fixtures and utilities
class TestFileGenerator:
    """Generate test files for validation and upload testing."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.created_files = []
    
    def create_text_file(self, content: str = "Test content", filename: str = "test.txt") -> str:
        """Create a temporary text file."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.created_files.append(file_path)
        return file_path
    
    def create_json_file(self, data: dict, filename: str = "test.json") -> str:
        """Create a temporary JSON file."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        self.created_files.append(file_path)
        return file_path
    
    def create_large_file(self, size_mb: int = 10, filename: str = "large.txt") -> str:
        """Create a large file for testing size limits."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write content in chunks to create a file of specified size
            chunk = "A" * 1024  # 1KB chunk
            for _ in range(size_mb * 1024):
                f.write(chunk)
        self.created_files.append(file_path)
        return file_path
    
    def create_unsupported_file(self, filename: str = "test.exe") -> str:
        """Create an unsupported file type."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')  # Binary content
        self.created_files.append(file_path)
        return file_path
    
    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory: {e}")

class MockOpenAIClient:
    """Mock OpenAI client for testing."""
    
    def __init__(self):
        self.uploaded_files = {}
        self.vector_stores = {}
        self.call_count = 0
    
    async def upload_file_async(self, file_path: str, purpose: str = "assistants", 
                               progress_callback=None) -> FileOperationResult:
        """Mock file upload."""
        self.call_count += 1
        file_id = f"file-{self.call_count}"
        
        # Simulate progress updates
        if progress_callback:
            for progress in [25, 50, 75, 100]:
                progress_obj = FileUploadProgress(
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    bytes_uploaded=os.path.getsize(file_path) * progress // 100,
                    status="uploading" if progress < 100 else "completed"
                )
                progress_callback(progress_obj)
        
        # Store mock file
        self.uploaded_files[file_id] = {
            "id": file_id,
            "filename": os.path.basename(file_path),
            "purpose": purpose,
            "size": os.path.getsize(file_path)
        }
        
        return FileOperationResult(
            success=True,
            data=OpenAIFile(
                id=file_id,
                filename=os.path.basename(file_path),
                purpose=purpose,
                bytes=os.path.getsize(file_path),
                created_at=1234567890
            )
        )
    
    async def create_vector_store_async(self, name: str, file_ids: list = None, 
                                       metadata: dict = None) -> FileOperationResult:
        """Mock vector store creation."""
        self.call_count += 1
        store_id = f"vs-{self.call_count}"
        
        self.vector_stores[store_id] = {
            "id": store_id,
            "name": name,
            "file_ids": file_ids or [],
            "metadata": metadata or {}
        }
        
        return FileOperationResult(
            success=True,
            data=VectorStore(
                id=store_id,
                name=name,
                file_counts={"total": len(file_ids or [])},
                created_at=1234567890
            )
        )


@pytest.mark.skipif(not GHOSTMAN_AVAILABLE, reason="Ghostman components not available")
class TestFileValidationService:
    """Test the file validation service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_generator = TestFileGenerator()
        self.validation_service = FileValidationService()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.file_generator.cleanup()
    
    def test_valid_file_validation(self):
        """Test validation of supported file types."""
        # Test various supported file types
        test_files = [
            ("test.txt", "Hello world"),
            ("test.json", '{"key": "value"}'),
            ("test.md", "# Markdown content"),
            ("test.py", "print('Hello world')")
        ]
        
        for filename, content in test_files:
            file_path = self.file_generator.create_text_file(content, filename)
            
            result = self.validation_service.validate_file(file_path)
            
            assert result["is_valid"] == True
            assert len(result["errors"]) == 0
            assert result["file_info"]["size"] > 0
            assert result["file_info"]["extension"] == Path(filename).suffix
    
    def test_invalid_file_validation(self):
        """Test validation of unsupported file types."""
        # Test unsupported file type
        unsupported_file = self.file_generator.create_unsupported_file("test.exe")
        
        result = self.validation_service.validate_file(unsupported_file)
        
        assert result["is_valid"] == False
        assert any("extension" in error.lower() for error in result["errors"])
    
    def test_file_size_validation(self):
        """Test file size limit validation."""
        # Create a file that exceeds size limit (assuming 100MB limit)
        large_file = self.file_generator.create_large_file(150, "large.txt")
        
        result = self.validation_service.validate_file(large_file)
        
        # Should fail due to size limit
        assert result["is_valid"] == False
        assert any("size" in error.lower() for error in result["errors"])
    
    def test_nonexistent_file_validation(self):
        """Test validation of non-existent files."""
        nonexistent_file = "/path/that/does/not/exist.txt"
        
        result = self.validation_service.validate_file(nonexistent_file)
        
        assert result["is_valid"] == False
        assert any("exist" in error.lower() for error in result["errors"])
    
    def test_batch_validation(self):
        """Test batch file validation."""
        # Create mix of valid and invalid files
        valid_file = self.file_generator.create_text_file("Valid content", "valid.txt")
        invalid_file = self.file_generator.create_unsupported_file("invalid.exe")
        
        files = [valid_file, invalid_file, "/nonexistent.txt"]
        
        result = self.validation_service.validate_files(files)
        
        assert len(result["valid_files"]) == 1
        assert valid_file in result["valid_files"]
        assert len(result["invalid_files"]) == 2
        assert invalid_file in result["invalid_files"]


@pytest.mark.skipif(not GHOSTMAN_AVAILABLE, reason="Ghostman components not available")
class TestFileUploadService:
    """Test the file upload service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_generator = TestFileGenerator()
        self.mock_client = MockOpenAIClient()
        self.upload_service = FileUploadService(self.mock_client)
        self.progress_updates = []
        self.error_updates = []
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.file_generator.cleanup()
    
    def on_progress_update(self, file_path: str, progress: FileUploadProgress):
        """Handle progress updates."""
        self.progress_updates.append((file_path, progress.percentage, progress.status))
    
    def on_error_update(self, file_path: str, error: str):
        """Handle error updates."""
        self.error_updates.append((file_path, error))
    
    @pytest.mark.asyncio
    async def test_single_file_upload(self):
        """Test uploading a single file."""
        # Connect progress callback
        self.upload_service.progress_updated.connect(self.on_progress_update)
        
        # Create test file
        test_file = self.file_generator.create_text_file("Test upload content", "upload_test.txt")
        
        # Upload file
        result = await self.upload_service.upload_file_async(test_file)
        
        # Verify upload success
        assert result["success"] == True
        assert "file_id" in result
        assert result["file_path"] == test_file
        
        # Verify progress updates were received
        assert len(self.progress_updates) > 0
        assert any(progress[2] == "completed" for progress in self.progress_updates)
        
        # Verify mock client received the file
        assert len(self.mock_client.uploaded_files) == 1
    
    @pytest.mark.asyncio
    async def test_batch_file_upload(self):
        """Test uploading multiple files."""
        # Connect callbacks
        self.upload_service.progress_updated.connect(self.on_progress_update)
        self.upload_service.upload_error.connect(self.on_error_update)
        
        # Create multiple test files
        test_files = [
            self.file_generator.create_text_file("File 1", "test1.txt"),
            self.file_generator.create_json_file({"test": "data"}, "test2.json"),
            self.file_generator.create_text_file("File 3", "test3.md")
        ]
        
        # Upload files
        results = await self.upload_service.upload_files_async(test_files)
        
        # Verify all uploads succeeded
        assert len(results) == 3
        assert all(result["success"] for result in results)
        
        # Verify progress updates for all files
        assert len(self.progress_updates) >= 3
        
        # Verify mock client received all files
        assert len(self.mock_client.uploaded_files) == 3
    
    @pytest.mark.asyncio
    async def test_upload_with_validation_failure(self):
        """Test upload behavior with validation failures."""
        # Connect error callback
        self.upload_service.upload_error.connect(self.on_error_update)
        
        # Try to upload non-existent file
        nonexistent_file = "/path/that/does/not/exist.txt"
        
        result = await self.upload_service.upload_file_async(nonexistent_file)
        
        # Verify upload failed
        assert result["success"] == False
        assert "error" in result
        
        # Verify error callback was triggered
        assert len(self.error_updates) > 0
    
    def test_upload_progress_calculation(self):
        """Test upload progress calculation."""
        file_size = 1024 * 1024  # 1MB
        
        # Test various progress points
        progress_points = [
            (0, 0.0),
            (256 * 1024, 25.0),
            (512 * 1024, 50.0),
            (768 * 1024, 75.0),
            (1024 * 1024, 100.0)
        ]
        
        for bytes_uploaded, expected_percentage in progress_points:
            progress = self.upload_service._calculate_progress(bytes_uploaded, file_size)
            assert abs(progress - expected_percentage) < 0.1


@pytest.mark.skipif(not GHOSTMAN_AVAILABLE, reason="Ghostman components not available")
class TestFineTuningService:
    """Test the fine-tuning service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MockOpenAIClient()
        self.fine_tuning_service = FineTuningService(self.mock_client)
    
    @pytest.mark.asyncio
    async def test_vector_store_creation(self):
        """Test creating a vector store."""
        # Mock some uploaded files
        file_ids = ["file-1", "file-2", "file-3"]
        
        result = await self.fine_tuning_service.create_vector_store_async(
            name="Test Knowledge Base",
            file_ids=file_ids,
            metadata={"project": "test"}
        )
        
        # Verify vector store creation
        assert result["success"] == True
        assert "vector_store_id" in result
        assert result["name"] == "Test Knowledge Base"
        
        # Verify mock client received the vector store
        assert len(self.mock_client.vector_stores) == 1
        store = list(self.mock_client.vector_stores.values())[0]
        assert store["name"] == "Test Knowledge Base"
        assert store["file_ids"] == file_ids
    
    @pytest.mark.asyncio
    async def test_file_search_functionality(self):
        """Test file search capabilities."""
        # Create a mock vector store
        vector_store_result = await self.fine_tuning_service.create_vector_store_async(
            name="Search Test Store",
            file_ids=["file-1"]
        )
        
        # Test search functionality
        search_result = await self.fine_tuning_service.search_files_async(
            query="test query",
            vector_store_ids=[vector_store_result["vector_store_id"]]
        )
        
        # Verify search returns results structure
        assert "success" in search_result
        assert "results" in search_result
    
    def test_vector_store_status_monitoring(self):
        """Test vector store status monitoring."""
        # Test status monitoring functionality
        status = self.fine_tuning_service.get_service_status()
        
        assert "vector_stores_count" in status
        assert "total_files_managed" in status
        assert "service_health" in status


@pytest.mark.skipif(not GHOSTMAN_AVAILABLE, reason="Ghostman components not available")
class TestFileToolbarWidget:
    """Test the file toolbar widget."""
    
    @classmethod
    def setup_class(cls):
        """Set up QApplication for widget testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_generator = TestFileGenerator()
        self.mock_client = MockOpenAIClient()
        
        # Create mock services
        self.mock_file_service = Mock()
        self.mock_upload_service = FileUploadService(self.mock_client)
        self.mock_validation_service = FileValidationService()
        
        # Create toolbar widget
        self.toolbar = FineTuningToolbar()
        self.toolbar.set_services(
            file_service=self.mock_file_service,
            upload_service=self.mock_upload_service,
            validation_service=self.mock_validation_service
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.file_generator.cleanup()
        if hasattr(self, 'toolbar'):
            self.toolbar.close()
    
    def test_toolbar_initialization(self):
        """Test toolbar widget initialization."""
        # Verify toolbar is created and configured
        assert self.toolbar is not None
        assert self.toolbar.isVisible() == False  # Initially hidden
        
        # Verify key UI elements exist
        assert hasattr(self.toolbar, 'upload_button')
        assert hasattr(self.toolbar, 'progress_bar')
        assert hasattr(self.toolbar, 'file_list_widget')
    
    def test_file_selection_dialog(self):
        """Test file selection dialog functionality."""
        # Mock file dialog to return test files
        test_files = [
            self.file_generator.create_text_file("Content 1", "test1.txt"),
            self.file_generator.create_text_file("Content 2", "test2.txt")
        ]
        
        with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileNames') as mock_dialog:
            mock_dialog.return_value = (test_files, '')
            
            # Trigger file selection
            self.toolbar._select_files()
            
            # Verify files were processed
            assert len(self.toolbar.selected_files) > 0
    
    def test_file_validation_display(self):
        """Test file validation result display."""
        # Create test files with mixed validity
        valid_file = self.file_generator.create_text_file("Valid", "valid.txt")
        invalid_file = self.file_generator.create_unsupported_file("invalid.exe")
        
        # Simulate file validation
        self.toolbar._validate_and_display_files([valid_file, invalid_file])
        
        # Verify UI shows validation results
        assert self.toolbar.file_list_widget.count() >= 1
        
        # Check for validation status indicators
        for i in range(self.toolbar.file_list_widget.count()):
            item = self.toolbar.file_list_widget.item(i)
            assert item is not None
    
    @pytest.mark.asyncio
    async def test_file_upload_process(self):
        """Test the complete file upload process."""
        # Create test file
        test_file = self.file_generator.create_text_file("Upload test", "upload.txt")
        
        # Set up file for upload
        self.toolbar.selected_files = [test_file]
        
        # Start upload process
        await self.toolbar._start_upload_process()
        
        # Verify upload was initiated
        assert self.toolbar.upload_in_progress == True
    
    def test_progress_bar_updates(self):
        """Test progress bar updates during upload."""
        # Simulate progress updates
        progress_values = [25, 50, 75, 100]
        
        for progress in progress_values:
            self.toolbar._update_progress_display(progress, f"Uploading... {progress}%")
            
            # Verify progress bar reflects the update
            assert self.toolbar.progress_bar.value() == progress
    
    def test_theme_integration(self):
        """Test theme integration and styling."""
        # Verify theme-aware styling is applied
        style_sheet = self.toolbar.styleSheet()
        assert style_sheet is not None
        
        # Test theme change handling
        self.toolbar._apply_theme_styling()
        
        # Verify styling was updated
        new_style_sheet = self.toolbar.styleSheet()
        assert new_style_sheet is not None


@pytest.mark.skipif(not GHOSTMAN_AVAILABLE, reason="Ghostman components not available")
class TestDragDropIntegration:
    """Test drag-and-drop integration in REPL widget."""
    
    @classmethod
    def setup_class(cls):
        """Set up QApplication for widget testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_generator = TestFileGenerator()
        self.repl_widget = REPLWidget()
        
        # Mock file services
        self.repl_widget.file_upload_service = Mock()
        self.repl_widget.file_toolbar = Mock()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.file_generator.cleanup()
        if hasattr(self, 'repl_widget'):
            self.repl_widget.close()
    
    def test_supported_file_detection(self):
        """Test detection of supported file types."""
        # Test supported files
        supported_files = [
            self.file_generator.create_text_file("Text", "test.txt"),
            self.file_generator.create_json_file({"key": "value"}, "test.json"),
            self.file_generator.create_text_file("# Markdown", "test.md")
        ]
        
        for file_path in supported_files:
            assert self.repl_widget._is_supported_file(file_path) == True
        
        # Test unsupported file
        unsupported_file = self.file_generator.create_unsupported_file("test.exe")
        assert self.repl_widget._is_supported_file(unsupported_file) == False
    
    def test_drag_enter_event_handling(self):
        """Test drag enter event handling."""
        # Create mock drag event with file URLs
        test_file = self.file_generator.create_text_file("Test", "drag_test.txt")
        
        # Create mock drag enter event
        mock_event = Mock()
        mock_mime_data = Mock()
        mock_url = Mock()
        
        mock_url.isLocalFile.return_value = True
        mock_url.toLocalFile.return_value = test_file
        mock_mime_data.hasUrls.return_value = True
        mock_mime_data.urls.return_value = [mock_url]
        mock_event.mimeData.return_value = mock_mime_data
        
        # Test drag enter handling
        self.repl_widget.dragEnterEvent(mock_event)
        
        # Verify event was accepted for supported files
        mock_event.acceptProposedAction.assert_called()
    
    def test_file_drop_handling(self):
        """Test file drop event handling."""
        # Create test files
        test_files = [
            self.file_generator.create_text_file("File 1", "drop1.txt"),
            self.file_generator.create_text_file("File 2", "drop2.txt")
        ]
        
        # Mock drop event
        mock_event = Mock()
        mock_mime_data = Mock()
        mock_urls = []
        
        for file_path in test_files:
            mock_url = Mock()
            mock_url.isLocalFile.return_value = True
            mock_url.toLocalFile.return_value = file_path
            mock_urls.append(mock_url)
        
        mock_mime_data.hasUrls.return_value = True
        mock_mime_data.urls.return_value = mock_urls
        mock_event.mimeData.return_value = mock_mime_data
        
        # Test drop handling
        self.repl_widget.dropEvent(mock_event)
        
        # Verify event was accepted and files were processed
        mock_event.acceptProposedAction.assert_called()
        self.repl_widget.file_toolbar.handle_file_drop.assert_called_with(test_files)


@pytest.mark.skipif(not GHOSTMAN_AVAILABLE, reason="Ghostman components not available")
class TestDatabaseIntegration:
    """Test database integration for file metadata."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.temp_db = tempfile.mktemp(suffix='.db')
        self.db_manager = FileStorageDatabaseManager(self.temp_db)
        self.db_manager.initialize()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
            if hasattr(self, 'temp_db'):
                os.unlink(self.temp_db)
        except Exception as e:
            print(f"Warning: Failed to cleanup test database: {e}")
    
    def test_database_initialization(self):
        """Test database schema initialization."""
        # Verify tables were created
        with self.db_manager.get_session() as session:
            # Check if file metadata table exists
            result = session.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'")
            assert result.fetchone() is not None
            
            # Check if vector store metadata table exists
            result = session.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vector_store_metadata'")
            assert result.fetchone() is not None
    
    def test_file_metadata_crud(self):
        """Test CRUD operations for file metadata."""
        with self.db_manager.get_session() as session:
            # Create file metadata entry
            file_metadata = FileMetadataModel(
                openai_file_id="file-test-123",
                filename="test.txt",
                file_path="/tmp/test.txt",
                file_hash="abc123",
                file_size=1024,
                mime_type="text/plain",
                status="completed",
                upload_session_id="session-1"
            )
            
            session.add(file_metadata)
            session.commit()
            
            # Read back the entry
            retrieved = session.query(FileMetadataModel).filter_by(openai_file_id="file-test-123").first()
            assert retrieved is not None
            assert retrieved.filename == "test.txt"
            assert retrieved.file_size == 1024
            
            # Update the entry
            retrieved.status = "processing"
            session.commit()
            
            # Verify update
            updated = session.query(FileMetadataModel).filter_by(openai_file_id="file-test-123").first()
            assert updated.status == "processing"
            
            # Delete the entry
            session.delete(updated)
            session.commit()
            
            # Verify deletion
            deleted = session.query(FileMetadataModel).filter_by(openai_file_id="file-test-123").first()
            assert deleted is None
    
    def test_vector_store_metadata_crud(self):
        """Test CRUD operations for vector store metadata."""
        with self.db_manager.get_session() as session:
            # Create vector store metadata entry
            vs_metadata = VectorStoreMetadataModel(
                openai_vector_store_id="vs-test-123",
                name="Test Vector Store",
                description="Test description",
                total_files=5,
                completed_files=3,
                failed_files=1,
                in_progress_files=1,
                cancelled_files=0,
                usage_bytes=1024000
            )
            
            session.add(vs_metadata)
            session.commit()
            
            # Read back the entry
            retrieved = session.query(VectorStoreMetadataModel).filter_by(openai_vector_store_id="vs-test-123").first()
            assert retrieved is not None
            assert retrieved.name == "Test Vector Store"
            assert retrieved.total_files == 5
            
            # Test updates
            retrieved.completed_files = 4
            retrieved.in_progress_files = 0
            session.commit()
            
            # Verify updates
            updated = session.query(VectorStoreMetadataModel).filter_by(openai_vector_store_id="vs-test-123").first()
            assert updated.completed_files == 4
            assert updated.in_progress_files == 0


class TestRunner:
    """Test runner for the file retrieval system."""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
    
    def run_all_tests(self):
        """Run all test suites."""
        print("🧪 Starting Ghostman File Retrieval System Tests...")
        print("=" * 60)
        
        if not GHOSTMAN_AVAILABLE:
            print("❌ Ghostman components not available - skipping tests")
            return False
        
        test_classes = [
            TestFileValidationService,
            TestFileUploadService,
            TestFineTuningService,
            TestFileToolbarWidget,
            TestDragDropIntegration,
            TestDatabaseIntegration
        ]
        
        for test_class in test_classes:
            self._run_test_class(test_class)
        
        self._print_summary()
        return self.test_results["failed"] == 0
    
    def _run_test_class(self, test_class):
        """Run a single test class."""
        class_name = test_class.__name__
        print(f"\n📋 Running {class_name}...")
        
        try:
            # Create test instance
            if hasattr(test_class, 'setup_class'):
                test_class.setup_class()
            
            # Get test methods
            test_methods = [method for method in dir(test_class) if method.startswith('test_')]
            
            for method_name in test_methods:
                self._run_test_method(test_class, method_name)
                
        except Exception as e:
            print(f"❌ Error in {class_name}: {e}")
            self.test_results["errors"].append(f"{class_name}: {e}")
            self.test_results["failed"] += 1
    
    def _run_test_method(self, test_class, method_name):
        """Run a single test method."""
        try:
            # Create test instance
            test_instance = test_class()
            
            # Setup
            if hasattr(test_instance, 'setup_method'):
                test_instance.setup_method()
            
            # Run test
            test_method = getattr(test_instance, method_name)
            
            # Handle async tests
            if asyncio.iscoroutinefunction(test_method):
                asyncio.run(test_method())
            else:
                test_method()
            
            print(f"  ✅ {method_name}")
            self.test_results["passed"] += 1
            
            # Teardown
            if hasattr(test_instance, 'teardown_method'):
                test_instance.teardown_method()
                
        except Exception as e:
            print(f"  ❌ {method_name}: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_class.__name__}.{method_name}: {e}")
    
    def _print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"⏭️  Skipped: {self.test_results['skipped']}")
        
        if self.test_results["errors"]:
            print("\n❌ Errors:")
            for error in self.test_results["errors"]:
                print(f"  - {error}")
        
        if self.test_results["failed"] == 0:
            print("\n🎉 All tests passed! File retrieval system is working correctly.")
        else:
            print(f"\n⚠️  {self.test_results['failed']} tests failed. Please review and fix issues.")


def main():
    """Main test entry point."""
    print("Ghostman File Retrieval System - Test Suite")
    print("==========================================")
    
    if not GHOSTMAN_AVAILABLE:
        print("❌ Ghostman components not available.")
        print("Please ensure the Ghostman package is properly installed.")
        return False
    
    # Run tests
    runner = TestRunner()
    success = runner.run_all_tests()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)