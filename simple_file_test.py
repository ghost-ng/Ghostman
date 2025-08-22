#!/usr/bin/env python3
"""
Simple test script for the Ghostman File Retrieval System.

This test validates core functionality without requiring external dependencies.
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Add the ghostman package to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

def test_file_validation_service():
    """Test the file validation service."""
    print("🔍 Testing FileValidationService...")
    
    try:
        from ghostman.src.application.services.file_validation_service import FileValidationService
        
        # Create test service
        validation_service = FileValidationService()
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Valid text file
            valid_file = os.path.join(temp_dir, "test.txt")
            with open(valid_file, 'w') as f:
                f.write("Test content")
            
            # Test validation
            result = validation_service.validate_file(valid_file)
            assert result["is_valid"] == True, "Valid file should pass validation"
            assert len(result["errors"]) == 0, "Valid file should have no errors"
            
            # Test non-existent file
            nonexistent = os.path.join(temp_dir, "nonexistent.txt")
            result = validation_service.validate_file(nonexistent)
            assert result["is_valid"] == False, "Non-existent file should fail validation"
            assert len(result["errors"]) > 0, "Non-existent file should have errors"
        
        print("   ✅ FileValidationService tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ FileValidationService test failed: {e}")
        return False

def test_file_upload_service():
    """Test the file upload service (without actual uploads)."""
    print("📤 Testing FileUploadService...")
    
    try:
        from ghostman.src.application.services.file_upload_service import FileUploadService, UploadStatistics
        
        # Create mock client for testing
        class MockClient:
            async def upload_file_async(self, file_path, purpose="assistants", progress_callback=None):
                from ghostman.src.infrastructure.ai.file_models import FileOperationResult, OpenAIFile
                return FileOperationResult(
                    success=True,
                    data=OpenAIFile(
                        id="file-test-123",
                        filename=os.path.basename(file_path),
                        purpose=purpose,
                        bytes=1024,
                        created_at=1234567890
                    )
                )
        
        # Test service initialization
        mock_client = MockClient()
        upload_service = FileUploadService(mock_client)
        
        # Test statistics
        stats = UploadStatistics()
        stats.total_files = 5
        stats.completed_files = 3
        stats.failed_files = 1
        
        assert stats.get_success_rate() == 60.0, "Success rate calculation incorrect"
        
        print("   ✅ FileUploadService tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ FileUploadService test failed: {e}")
        return False

def test_fine_tuning_service():
    """Test the fine-tuning service."""
    print("🤖 Testing FineTuningService...")
    
    try:
        from ghostman.src.application.services.fine_tuning_service import FineTuningService
        
        # Create mock client
        class MockClient:
            async def create_vector_store_async(self, name, file_ids=None, metadata=None):
                from ghostman.src.infrastructure.ai.file_models import FileOperationResult, VectorStore
                return FileOperationResult(
                    success=True,
                    data=VectorStore(
                        id="vs-test-123",
                        name=name,
                        file_counts={"total": len(file_ids or [])},
                        created_at=1234567890
                    )
                )
        
        # Test service initialization
        mock_client = MockClient()
        fine_tuning_service = FineTuningService(mock_client)
        
        # Test service status
        status = fine_tuning_service.get_service_status()
        assert "vector_stores_count" in status, "Service status should include vector store count"
        assert "service_health" in status, "Service status should include health"
        
        print("   ✅ FineTuningService tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ FineTuningService test failed: {e}")
        return False

def test_database_models():
    """Test the database models."""
    print("🗄️ Testing Database Models...")
    
    try:
        from ghostman.src.infrastructure.storage.file_metadata_models import (
            FileMetadataModel, VectorStoreMetadataModel, FileStorageDatabaseManager
        )
        
        # Test model creation
        file_metadata = FileMetadataModel(
            openai_file_id="file-test-123",
            filename="test.txt",
            file_size=1024,
            status="completed"
        )
        
        # Test model methods
        file_dict = file_metadata.to_dict()
        assert file_dict["filename"] == "test.txt", "Model to_dict should work correctly"
        assert file_dict["file_size"] == 1024, "Model to_dict should include file size"
        
        # Test vector store model
        vs_metadata = VectorStoreMetadataModel(
            openai_vector_store_id="vs-test-123",
            name="Test Vector Store",
            total_files=5,
            completed_files=3
        )
        
        completion_pct = vs_metadata.get_completion_percentage()
        assert completion_pct == 60.0, "Completion percentage calculation incorrect"
        
        print("   ✅ Database Models tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Database Models test failed: {e}")
        return False

def test_file_toolbar_widget():
    """Test the file toolbar widget (basic instantiation)."""
    print("🎨 Testing FineTuningToolbar...")
    
    try:
        # Import Qt components first
        from PyQt6.QtWidgets import QApplication
        
        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from ghostman.src.presentation.widgets.file_toolbar import FineTuningToolbar
        
        # Test widget creation
        toolbar = FineTuningToolbar()
        
        # Test basic properties
        assert hasattr(toolbar, 'upload_button'), "Toolbar should have upload button"
        assert hasattr(toolbar, 'progress_bar'), "Toolbar should have progress bar"
        assert hasattr(toolbar, 'file_list_widget'), "Toolbar should have file list widget"
        
        # Clean up
        toolbar.close()
        
        print("   ✅ FineTuningToolbar tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ FineTuningToolbar test failed: {e}")
        return False

def test_repl_drag_drop():
    """Test REPL widget drag-drop functionality."""
    print("🖱️ Testing REPL Drag-Drop...")
    
    try:
        from ghostman.src.presentation.widgets.repl_widget import REPLWidget
        
        # Create widget
        repl = REPLWidget()
        
        # Test file support detection
        with tempfile.TemporaryDirectory() as temp_dir:
            # Supported file
            supported_file = os.path.join(temp_dir, "test.txt")
            with open(supported_file, 'w') as f:
                f.write("test")
            
            assert repl._is_supported_file(supported_file) == True, "Text file should be supported"
            
            # Unsupported file
            unsupported_file = os.path.join(temp_dir, "test.exe")
            with open(unsupported_file, 'wb') as f:
                f.write(b'\x00\x01')
            
            assert repl._is_supported_file(unsupported_file) == False, "Executable should not be supported"
        
        # Clean up
        repl.close()
        
        print("   ✅ REPL Drag-Drop tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ REPL Drag-Drop test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Ghostman File Retrieval System - Simple Test Suite")
    print("=" * 60)
    
    tests = [
        test_file_validation_service,
        test_file_upload_service,
        test_fine_tuning_service,
        test_database_models,
        test_file_toolbar_widget,
        test_repl_drag_drop
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test {test_func.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! File retrieval system is working correctly.")
        return True
    else:
        print(f"⚠️ {failed} tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)