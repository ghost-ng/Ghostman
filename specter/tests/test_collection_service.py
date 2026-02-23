"""
Integration tests for CollectionService.

Tests the application service layer's interaction with repository,
storage service, and domain models.
"""

import asyncio
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specter.src.application.services.collection_service import CollectionService
from specter.src.domain.models.collection import FileCollection, FileCollectionItem
from specter.src.infrastructure.conversation_management.database_manager import DatabaseManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_manager = DatabaseManager(str(db_path))

        # Run migrations
        from specter.src.infrastructure.conversation_management.migrations.env import run_migrations
        run_migrations(str(db_path))

        yield db_manager

        # Cleanup
        db_manager.close()


@pytest.fixture
def temp_files():
    """Create temporary test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = []
        for i in range(3):
            file_path = Path(tmpdir) / f"test_file_{i}.txt"
            file_path.write_text(f"Test content {i}\n" * 100)
            files.append(str(file_path))

        yield tmpdir, files


@pytest.fixture
def collection_service(temp_db):
    """Create CollectionService instance with test database."""
    # Reset singleton
    CollectionService._instance = None
    service = CollectionService(temp_db)
    yield service
    # Reset singleton after test
    CollectionService._instance = None


class TestCollectionManagement:
    """Test collection CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_collection(self, collection_service):
        """Test creating a new collection."""
        collection = await collection_service.create_collection(
            name="Test Collection",
            description="A test collection",
            tags=["test", "python"],
            chunk_size=1000,
            chunk_overlap=200
        )

        assert collection is not None
        assert collection.name == "Test Collection"
        assert collection.description == "A test collection"
        assert "test" in collection.tags
        assert "python" in collection.tags
        assert collection.chunk_size == 1000
        assert collection.chunk_overlap == 200
        assert collection.file_count == 0

    @pytest.mark.asyncio
    async def test_create_collection_duplicate_name(self, collection_service):
        """Test that duplicate collection names are rejected."""
        # Create first collection
        collection1 = await collection_service.create_collection(
            name="Duplicate Test",
            description="First"
        )
        assert collection1 is not None

        # Attempt to create duplicate
        collection2 = await collection_service.create_collection(
            name="Duplicate Test",
            description="Second"
        )
        assert collection2 is None

    @pytest.mark.asyncio
    async def test_create_collection_validation(self, collection_service):
        """Test collection creation validation."""
        # Empty name
        result = await collection_service.create_collection(name="")
        assert result is None

        # Name too long
        result = await collection_service.create_collection(name="x" * 201)
        assert result is None

        # Invalid chunk size
        result = await collection_service.create_collection(
            name="Test", chunk_size=50  # Too small
        )
        assert result is None

        # Invalid chunk overlap
        result = await collection_service.create_collection(
            name="Test", chunk_size=1000, chunk_overlap=1500  # Overlap > size
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_collection(self, collection_service):
        """Test retrieving a collection by ID."""
        # Create collection
        created = await collection_service.create_collection(
            name="Get Test",
            description="Testing retrieval"
        )
        assert created is not None

        # Retrieve by ID
        retrieved = await collection_service.get_collection(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Get Test"

        # Non-existent ID
        not_found = await collection_service.get_collection("non-existent-id")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_collection_by_name(self, collection_service):
        """Test retrieving a collection by name."""
        # Create collection
        created = await collection_service.create_collection(
            name="Name Test",
            description="Testing name lookup"
        )
        assert created is not None

        # Retrieve by name
        retrieved = await collection_service.get_collection_by_name("Name Test")
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Name Test"

        # Non-existent name
        not_found = await collection_service.get_collection_by_name("Non-existent")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_list_collections(self, collection_service):
        """Test listing collections with filtering."""
        # Create multiple collections
        await collection_service.create_collection(
            name="Collection 1",
            tags=["python", "test"]
        )
        await collection_service.create_collection(
            name="Collection 2",
            tags=["javascript", "test"]
        )
        await collection_service.create_collection(
            name="Template 1",
            tags=["python"],
            is_template=True
        )

        # List all collections
        all_collections = await collection_service.list_collections()
        assert len(all_collections) == 3

        # List without templates
        non_templates = await collection_service.list_collections(include_templates=False)
        assert len(non_templates) == 2

        # Filter by tags
        python_collections = await collection_service.list_collections(tags=["python"])
        assert len(python_collections) == 2

    @pytest.mark.asyncio
    async def test_update_collection(self, collection_service):
        """Test updating collection metadata."""
        # Create collection
        collection = await collection_service.create_collection(
            name="Update Test",
            description="Original description",
            tags=["original"],
            chunk_size=1000
        )
        assert collection is not None

        # Update name
        success = await collection_service.update_collection(
            collection.id,
            name="Updated Name"
        )
        assert success is True

        # Verify update
        updated = await collection_service.get_collection(collection.id)
        assert updated.name == "Updated Name"

        # Update description and tags
        success = await collection_service.update_collection(
            collection.id,
            description="Updated description",
            tags=["updated", "test"]
        )
        assert success is True

        updated = await collection_service.get_collection(collection.id)
        assert updated.description == "Updated description"
        assert "updated" in updated.tags

        # Update RAG settings
        success = await collection_service.update_collection(
            collection.id,
            chunk_size=1500,
            chunk_overlap=300
        )
        assert success is True

        updated = await collection_service.get_collection(collection.id)
        assert updated.chunk_size == 1500
        assert updated.chunk_overlap == 300

    @pytest.mark.asyncio
    async def test_delete_collection(self, collection_service):
        """Test deleting a collection."""
        # Create collection
        collection = await collection_service.create_collection(
            name="Delete Test"
        )
        assert collection is not None

        # Delete collection
        success = await collection_service.delete_collection(collection.id)
        assert success is True

        # Verify deletion
        deleted = await collection_service.get_collection(collection.id)
        assert deleted is None


class TestFileManagement:
    """Test file operations within collections."""

    @pytest.mark.asyncio
    async def test_add_file_to_collection(self, collection_service, temp_files):
        """Test adding a file to a collection."""
        tmpdir, files = temp_files

        # Create collection
        collection = await collection_service.create_collection(
            name="File Test"
        )
        assert collection is not None

        # Add file
        success, error = await collection_service.add_file_to_collection(
            collection.id,
            files[0]
        )
        assert success is True
        assert error is None

        # Verify file was added
        collection_files = await collection_service.get_collection_files(collection.id)
        assert len(collection_files) == 1
        assert collection_files[0].file_name == "test_file_0.txt"

    @pytest.mark.asyncio
    async def test_add_file_duplicate_detection(self, collection_service, temp_files):
        """Test duplicate file detection within a collection."""
        tmpdir, files = temp_files

        # Create collection
        collection = await collection_service.create_collection(
            name="Duplicate Test"
        )

        # Add file first time
        success1, _ = await collection_service.add_file_to_collection(
            collection.id,
            files[0]
        )
        assert success1 is True

        # Try to add same file again (should fail)
        success2, error = await collection_service.add_file_to_collection(
            collection.id,
            files[0]
        )
        assert success2 is False
        assert "already exist" in error.lower()

    @pytest.mark.asyncio
    async def test_add_files_batch(self, collection_service, temp_files):
        """Test adding multiple files at once."""
        tmpdir, files = temp_files

        # Create collection
        collection = await collection_service.create_collection(
            name="Batch Test"
        )

        # Add multiple files
        successful, errors = await collection_service.add_files_to_collection(
            collection.id,
            files
        )
        assert successful == 3
        assert len(errors) == 0

        # Verify all files added
        collection_files = await collection_service.get_collection_files(collection.id)
        assert len(collection_files) == 3

    @pytest.mark.asyncio
    async def test_add_file_size_limit(self, collection_service, temp_files):
        """Test that size limit is enforced."""
        tmpdir, files = temp_files

        # Create collection with very small size limit
        collection = await collection_service.create_collection(
            name="Size Limit Test",
            max_size_mb=0.001  # 1KB limit
        )

        # Try to add file larger than limit
        success, error = await collection_service.add_file_to_collection(
            collection.id,
            files[0]
        )
        assert success is False
        assert "exceed" in error.lower()

    @pytest.mark.asyncio
    async def test_remove_file_from_collection(self, collection_service, temp_files):
        """Test removing a file from a collection."""
        tmpdir, files = temp_files

        # Create collection and add file
        collection = await collection_service.create_collection(
            name="Remove Test"
        )
        success, _ = await collection_service.add_file_to_collection(
            collection.id,
            files[0]
        )
        assert success is True

        # Get file ID
        collection_files = await collection_service.get_collection_files(collection.id)
        file_id = collection_files[0].id

        # Remove file
        success = await collection_service.remove_file_from_collection(
            collection.id,
            file_id
        )
        assert success is True

        # Verify removal
        collection_files = await collection_service.get_collection_files(collection.id)
        assert len(collection_files) == 0

    @pytest.mark.asyncio
    async def test_verify_file_integrity(self, collection_service, temp_files):
        """Test file integrity verification."""
        tmpdir, files = temp_files

        # Create collection and add file
        collection = await collection_service.create_collection(
            name="Integrity Test"
        )
        await collection_service.add_file_to_collection(
            collection.id,
            files[0]
        )

        # Get file ID
        collection_files = await collection_service.get_collection_files(collection.id)
        file_id = collection_files[0].id

        # Verify integrity (should pass)
        is_valid, message = await collection_service.verify_file_integrity(
            collection.id,
            file_id
        )
        assert is_valid is True
        assert "verified" in message.lower()

        # Modify file
        Path(files[0]).write_text("Modified content")

        # Verify integrity again (should fail)
        is_valid, message = await collection_service.verify_file_integrity(
            collection.id,
            file_id
        )
        assert is_valid is False
        assert "modified" in message.lower()

    @pytest.mark.asyncio
    async def test_verify_collection_integrity(self, collection_service, temp_files):
        """Test verifying integrity of all files in a collection."""
        tmpdir, files = temp_files

        # Create collection and add files
        collection = await collection_service.create_collection(
            name="Collection Integrity Test"
        )
        await collection_service.add_files_to_collection(
            collection.id,
            files
        )

        # Verify all files (should pass)
        all_valid, errors = await collection_service.verify_collection_integrity(
            collection.id
        )
        assert all_valid is True
        assert len(errors) == 0

        # Modify one file
        Path(files[1]).write_text("Modified content")

        # Verify again (should fail with one error)
        all_valid, errors = await collection_service.verify_collection_integrity(
            collection.id
        )
        assert all_valid is False
        assert len(errors) == 1
        assert "test_file_1.txt" in errors[0]


class TestTemplates:
    """Test template functionality."""

    @pytest.mark.asyncio
    async def test_get_builtin_templates(self, collection_service):
        """Test retrieving built-in templates."""
        templates = await collection_service.get_builtin_templates()

        assert len(templates) == 5
        template_names = [t["name"] for t in templates]
        assert "Python Project" in template_names
        assert "JavaScript Project" in template_names
        assert "Documentation" in template_names

    @pytest.mark.asyncio
    async def test_instantiate_template(self, collection_service, temp_files):
        """Test creating a collection from a template."""
        tmpdir, files = temp_files

        # Instantiate Python Project template
        collection = await collection_service.instantiate_template(
            template_name="Python Project",
            new_collection_name="My Python Project",
            file_paths=files
        )

        assert collection is not None
        assert collection.name == "My Python Project"
        assert "python" in collection.tags
        assert collection.file_count == 3

    @pytest.mark.asyncio
    async def test_instantiate_nonexistent_template(self, collection_service):
        """Test that instantiating non-existent template fails."""
        collection = await collection_service.instantiate_template(
            template_name="Non-existent Template",
            new_collection_name="Test",
            file_paths=[]
        )
        assert collection is None


class TestImportExport:
    """Test collection import/export functionality."""

    @pytest.mark.asyncio
    async def test_export_collection_with_files(self, collection_service, temp_files):
        """Test exporting a collection with file contents."""
        tmpdir, files = temp_files

        # Create collection with files
        collection = await collection_service.create_collection(
            name="Export Test"
        )
        await collection_service.add_files_to_collection(
            collection.id,
            files
        )

        # Export to ZIP
        export_path = Path(tmpdir) / "export.zip"
        success, error = await collection_service.export_collection(
            collection.id,
            str(export_path),
            include_files=True
        )
        assert success is True
        assert error is None
        assert export_path.exists()

        # Verify ZIP contents
        with zipfile.ZipFile(export_path, 'r') as zf:
            namelist = zf.namelist()
            assert "collection.json" in namelist
            assert "files/test_file_0.txt" in namelist
            assert "files/test_file_1.txt" in namelist
            assert "files/test_file_2.txt" in namelist

            # Verify manifest
            manifest_data = zf.read("collection.json")
            manifest = json.loads(manifest_data)
            assert manifest["collection"]["name"] == "Export Test"
            assert len(manifest["files"]) == 3

    @pytest.mark.asyncio
    async def test_export_collection_metadata_only(self, collection_service, temp_files):
        """Test exporting collection without file contents."""
        tmpdir, files = temp_files

        # Create collection with files
        collection = await collection_service.create_collection(
            name="Metadata Export Test"
        )
        await collection_service.add_files_to_collection(
            collection.id,
            files
        )

        # Export without files
        export_path = Path(tmpdir) / "export_no_files.zip"
        success, error = await collection_service.export_collection(
            collection.id,
            str(export_path),
            include_files=False
        )
        assert success is True

        # Verify ZIP contains only manifest
        with zipfile.ZipFile(export_path, 'r') as zf:
            namelist = zf.namelist()
            assert "collection.json" in namelist
            assert len(namelist) == 1  # Only manifest

    @pytest.mark.asyncio
    async def test_import_collection_with_files(self, collection_service, temp_files):
        """Test importing a collection with file restoration."""
        tmpdir, files = temp_files

        # Create and export collection
        collection = await collection_service.create_collection(
            name="Import Test Original"
        )
        await collection_service.add_files_to_collection(
            collection.id,
            files
        )

        export_path = Path(tmpdir) / "export.zip"
        await collection_service.export_collection(
            collection.id,
            str(export_path),
            include_files=True
        )

        # Import to new location
        restore_dir = Path(tmpdir) / "restored"
        imported, errors = await collection_service.import_collection(
            str(export_path),
            new_name="Import Test Restored",
            restore_files=True,
            target_directory=str(restore_dir)
        )

        assert imported is not None
        assert imported.name == "Import Test Restored"
        assert len(errors) == 0

        # Verify files were restored
        restored_files = await collection_service.get_collection_files(imported.id)
        assert len(restored_files) == 3

        # Verify file contents
        for i in range(3):
            restored_file = restore_dir / f"test_file_{i}.txt"
            assert restored_file.exists()
            content = restored_file.read_text()
            assert f"Test content {i}" in content

    @pytest.mark.asyncio
    async def test_import_collection_name_conflict(self, collection_service, temp_files):
        """Test that import handles name conflicts."""
        tmpdir, files = temp_files

        # Create and export collection
        collection = await collection_service.create_collection(
            name="Conflict Test"
        )
        export_path = Path(tmpdir) / "export.zip"
        await collection_service.export_collection(
            collection.id,
            str(export_path),
            include_files=False
        )

        # Import (should auto-rename due to conflict)
        imported, errors = await collection_service.import_collection(
            str(export_path),
            restore_files=False
        )

        assert imported is not None
        assert imported.name != "Conflict Test"  # Should be renamed
        assert "Conflict Test (1)" in imported.name
        assert any("renamed" in e.lower() for e in errors)

    @pytest.mark.asyncio
    async def test_export_collection_metadata_dict(self, collection_service, temp_files):
        """Test exporting collection metadata as dictionary."""
        tmpdir, files = temp_files

        # Create collection with files
        collection = await collection_service.create_collection(
            name="Metadata Dict Test",
            description="Test description",
            tags=["test"]
        )
        await collection_service.add_files_to_collection(
            collection.id,
            files[:2]
        )

        # Export metadata
        metadata = await collection_service.export_collection_metadata_only(
            collection.id
        )

        assert metadata is not None
        assert metadata["name"] == "Metadata Dict Test"
        assert metadata["description"] == "Test description"
        assert "test" in metadata["tags"]
        assert metadata["file_count"] == 2
        assert metadata["total_size_mb"] > 0


class TestConversationAssociations:
    """Test collection-conversation associations."""

    @pytest.mark.asyncio
    async def test_attach_collection_to_conversation(self, collection_service):
        """Test attaching a collection to a conversation."""
        # Create collection
        collection = await collection_service.create_collection(
            name="Attach Test"
        )

        # Attach to conversation
        conversation_id = "test-conversation-id"
        success = await collection_service.attach_collection_to_conversation(
            conversation_id,
            collection.id
        )
        assert success is True

        # Verify attachment
        collections = await collection_service.get_conversation_collections(
            conversation_id
        )
        assert len(collections) == 1
        assert collections[0].id == collection.id

    @pytest.mark.asyncio
    async def test_detach_collection_from_conversation(self, collection_service):
        """Test detaching a collection from a conversation."""
        # Create and attach collection
        collection = await collection_service.create_collection(
            name="Detach Test"
        )
        conversation_id = "test-conversation-id"
        await collection_service.attach_collection_to_conversation(
            conversation_id,
            collection.id
        )

        # Detach
        success = await collection_service.detach_collection_from_conversation(
            conversation_id,
            collection.id
        )
        assert success is True

        # Verify detachment
        collections = await collection_service.get_conversation_collections(
            conversation_id
        )
        assert len(collections) == 0


class TestSearch:
    """Test collection search functionality."""

    @pytest.mark.asyncio
    async def test_search_collections(self, collection_service):
        """Test searching collections by name/description."""
        # Create test collections
        await collection_service.create_collection(
            name="Python Utils",
            description="Python utility functions"
        )
        await collection_service.create_collection(
            name="JavaScript Helpers",
            description="JS helper functions"
        )
        await collection_service.create_collection(
            name="Python Testing",
            description="Test utilities"
        )

        # Search for "Python"
        results = await collection_service.search_collections("Python")
        assert len(results) == 2

        # Search for "utils"
        results = await collection_service.search_collections("utils")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_collections_with_tags(self, collection_service):
        """Test searching collections with tag filtering."""
        # Create collections with tags
        await collection_service.create_collection(
            name="Collection 1",
            tags=["python", "testing"]
        )
        await collection_service.create_collection(
            name="Collection 2",
            tags=["javascript", "testing"]
        )
        await collection_service.create_collection(
            name="Collection 3",
            tags=["python", "utilities"]
        )

        # Search with tag filter
        results = await collection_service.search_collections(
            "Collection",
            tags=["python"]
        )
        assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
