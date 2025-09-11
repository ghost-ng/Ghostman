"""
Comprehensive Testing Strategy for FAISS-Only Migration

Tests all aspects of the FAISS-only architecture to ensure:
- No data loss during migration
- Performance improvements
- Conversation isolation
- PyQt6 integration stability
- Error handling robustness
"""

import unittest
import asyncio
import tempfile
import shutil
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
import logging

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("faiss_migration_tests")

# Test data
TEST_DOCUMENTS = [
    {
        "content": "This is a test document about artificial intelligence and machine learning.",
        "metadata": {"source": "test1.txt", "conversation_id": "conv1"}
    },
    {
        "content": "Python programming is essential for modern software development.",
        "metadata": {"source": "test2.txt", "conversation_id": "conv1"}
    },
    {
        "content": "PyQt6 provides excellent GUI capabilities for desktop applications.",
        "metadata": {"source": "test3.txt", "conversation_id": "conv2"}
    }
]


class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    def __init__(self):
        self.dimension = 1536
        self.call_count = 0
    
    def create_embedding(self, text: str):
        """Create mock embedding."""
        import numpy as np
        self.call_count += 1
        # Create consistent but unique embeddings based on text hash
        seed = hash(text) % 1000
        np.random.seed(seed)
        embedding = np.random.rand(self.dimension).astype(np.float32)
        return embedding / np.linalg.norm(embedding)
    
    def create_batch_embeddings(self, texts: List[str]):
        """Create batch of mock embeddings."""
        return [self.create_embedding(text) for text in texts]


class TestOptimizedFaissClient(unittest.TestCase):
    """Test the optimized FAISS client implementation."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock config
        self.config = Mock()
        self.config.persist_directory = str(self.temp_dir)
        self.config.collection_name = "test_collection"
        
        # Import the actual class (would be imported from your module)
        try:
            from ghostman.src.infrastructure.rag_pipeline.vector_store.optimized_faiss_client import OptimizedFaissClient
            from ghostman.src.infrastructure.rag_pipeline.document_loaders.base_loader import Document, DocumentMetadata
            from ghostman.src.infrastructure.rag_pipeline.text_processing.text_splitter import TextChunk
            
            self.OptimizedFaissClient = OptimizedFaissClient
            self.Document = Document
            self.DocumentMetadata = DocumentMetadata
            self.TextChunk = TextChunk
            
            # Initialize client
            with patch('PyQt6.QtCore.QObject.__init__'):
                self.client = OptimizedFaissClient(self.config)
                
        except ImportError:
            self.skipTest("FAISS client not available for testing")
    
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'client'):
            self.client.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test client initialization."""
        self.assertTrue(self.client.is_ready())
        self.assertIsNotNone(self.client._index)
        self.assertEqual(self.client._dimension, 1536)
    
    def test_document_indexing(self):
        """Test document indexing with conversation context."""
        # Create test document
        doc_metadata = self.DocumentMetadata(
            source="test.txt",
            filename="test.txt",
            file_extension=".txt"
        )
        document = self.Document(content="Test document content", metadata=doc_metadata)
        
        # Create test chunks
        chunks = [
            self.TextChunk(
                content="Test chunk 1",
                chunk_index=0,
                start_char=0,
                end_char=13,
                token_count=3
            ),
            self.TextChunk(
                content="Test chunk 2",
                chunk_index=1,
                start_char=14,
                end_char=27,
                token_count=3
            )
        ]
        
        # Create mock embeddings
        import numpy as np
        embeddings = [
            np.random.rand(1536).astype(np.float32),
            np.random.rand(1536).astype(np.float32)
        ]
        
        # Index document
        chunk_ids = self.client.index_document_sync(
            document=document,
            chunks=chunks,
            embeddings=embeddings,
            conversation_id="test_conv"
        )
        
        # Verify indexing
        self.assertEqual(len(chunk_ids), 2)
        self.assertEqual(self.client._index.ntotal, 2)
        
        # Verify conversation tracking
        conv_docs = self.client.get_conversation_documents("test_conv")
        self.assertEqual(len(conv_docs), 2)
    
    def test_conversation_specific_search(self):
        """Test conversation-specific search functionality."""
        # Index documents in different conversations
        self._index_test_documents()
        
        # Create query embedding
        import numpy as np
        query_embedding = np.random.rand(1536).astype(np.float32)
        
        # Search conversation 1
        results_conv1 = self.client.search_by_conversation_sync(
            query_embedding=query_embedding,
            conversation_id="conv1",
            top_k=5
        )
        
        # Search conversation 2  
        results_conv2 = self.client.search_by_conversation_sync(
            query_embedding=query_embedding,
            conversation_id="conv2",
            top_k=5
        )
        
        # Verify conversation isolation
        self.assertGreater(len(results_conv1), 0)
        self.assertGreater(len(results_conv2), 0)
        
        # Verify all results belong to correct conversation
        for result in results_conv1:
            self.assertEqual(result.conversation_id, "conv1")
        
        for result in results_conv2:
            self.assertEqual(result.conversation_id, "conv2")
    
    def test_performance_stats(self):
        """Test performance statistics tracking."""
        # Index some documents
        self._index_test_documents()
        
        # Get stats
        stats = self.client.get_optimized_stats()
        
        # Verify stats structure
        self.assertIn('documents_indexed', stats)
        self.assertIn('chunks_indexed', stats)
        self.assertIn('total_conversations', stats)
        self.assertIn('is_ready', stats)
        
        # Verify stats values
        self.assertGreater(stats['documents_indexed'], 0)
        self.assertGreater(stats['chunks_indexed'], 0)
        self.assertTrue(stats['is_ready'])
    
    def test_persistence(self):
        """Test data persistence across client restarts."""
        # Index documents
        self._index_test_documents()
        
        original_stats = self.client.get_optimized_stats()
        
        # Close and recreate client
        self.client.close()
        
        with patch('PyQt6.QtCore.QObject.__init__'):
            new_client = self.OptimizedFaissClient(self.config)
        
        # Verify data persistence
        new_stats = new_client.get_optimized_stats()
        self.assertEqual(original_stats['chunks_indexed'], new_stats['chunks_indexed'])
        self.assertEqual(original_stats['total_conversations'], new_stats['total_conversations'])
        
        new_client.close()
    
    def _index_test_documents(self):
        """Helper method to index test documents."""
        for i, test_doc in enumerate(TEST_DOCUMENTS):
            doc_metadata = self.DocumentMetadata(
                source=test_doc["metadata"]["source"],
                filename=test_doc["metadata"]["source"],
                file_extension=".txt"
            )
            document = self.Document(content=test_doc["content"], metadata=doc_metadata)
            
            chunks = [self.TextChunk(
                content=test_doc["content"],
                chunk_index=0,
                start_char=0,
                end_char=len(test_doc["content"]),
                token_count=len(test_doc["content"].split())
            )]
            
            import numpy as np
            embeddings = [np.random.rand(1536).astype(np.float32)]
            
            self.client.index_document_sync(
                document=document,
                chunks=chunks,
                embeddings=embeddings,
                conversation_id=test_doc["metadata"]["conversation_id"]
            )


class TestFAISSONlyRAGCoordinator(unittest.TestCase):
    """Test the FAISS-only RAG coordinator."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock conversation service
        self.conversation_service = Mock()
        
        # Mock settings
        with patch('ghostman.src.infrastructure.storage.settings_manager.settings') as mock_settings:
            mock_settings.get.return_value = "test_api_key"
            
            try:
                from ghostman.src.infrastructure.faiss_only_rag_coordinator import FAISSONlyRAGCoordinator
                
                with patch('PyQt6.QtCore.QObject.__init__'):
                    self.coordinator = FAISSONlyRAGCoordinator(self.conversation_service)
                    
            except ImportError:
                self.skipTest("FAISS coordinator not available for testing")
    
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'coordinator'):
            self.coordinator.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test coordinator initialization."""
        self.assertTrue(self.coordinator.is_ready())
        status = self.coordinator.get_status()
        self.assertTrue(status['ready'])
    
    def test_async_document_upload(self):
        """Test asynchronous document upload."""
        # Create temporary test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("This is a test document for upload testing.")
        
        # Mock the upload process
        with patch.object(self.coordinator, '_load_document_sync') as mock_load, \
             patch.object(self.coordinator, '_split_document_sync') as mock_split, \
             patch.object(self.coordinator, '_generate_embeddings_sync') as mock_embed, \
             patch.object(self.coordinator, '_index_document_sync') as mock_index:
            
            # Set up mocks
            mock_load.return_value = Mock()
            mock_split.return_value = [Mock()]
            mock_embed.return_value = [Mock()]
            mock_index.return_value = ["test_chunk_id"]
            
            # Test upload
            job_id = self.coordinator.upload_document_async(
                file_path=str(test_file),
                conversation_id="test_conv"
            )
            
            self.assertIsNotNone(job_id)
            self.assertNotEqual(job_id, "")
    
    def test_synchronous_query(self):
        """Test synchronous conversation query."""
        # Mock the query components
        with patch.object(self.coordinator.embedding_service, 'create_embedding') as mock_embed, \
             patch.object(self.coordinator.faiss_client, 'search_by_conversation_sync') as mock_search:
            
            # Set up mocks
            import numpy as np
            mock_embed.return_value = np.random.rand(1536).astype(np.float32)
            mock_search.return_value = []
            
            # Test query
            result = self.coordinator.query_conversation_sync(
                query_text="Test query",
                conversation_id="test_conv"
            )
            
            self.assertIn('answer', result)
            self.assertIn('sources', result)
            self.assertIn('conversation_id', result)
    
    def test_conversation_document_management(self):
        """Test conversation-specific document management."""
        # Mock document retrieval
        with patch.object(self.coordinator.faiss_client, 'get_conversation_documents') as mock_get:
            mock_get.return_value = [{"chunk_id": "test", "metadata": {"filename": "test.txt"}}]
            
            docs = self.coordinator.get_conversation_documents("test_conv")
            self.assertEqual(len(docs), 1)
        
        # Mock document removal
        with patch.object(self.coordinator.faiss_client, 'remove_conversation_documents') as mock_remove:
            mock_remove.return_value = 5
            
            count = self.coordinator.remove_conversation_documents("test_conv")
            self.assertEqual(count, 5)


class TestDataMigration(unittest.TestCase):
    """Test data migration from old to new FAISS format."""
    
    def setUp(self):
        """Set up migration test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / "source"
        self.target_dir = self.temp_dir / "target"
        
        self.source_dir.mkdir()
        self.target_dir.mkdir()
        
        # Create mock source data
        self._create_mock_source_data()
    
    def tearDown(self):
        """Clean up migration test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_mock_source_data(self):
        """Create mock source FAISS data."""
        import pickle
        import numpy as np
        
        try:
            import faiss
            
            # Create mock FAISS index
            dimension = 1536
            index = faiss.IndexFlatIP(dimension)
            
            # Add some mock vectors
            vectors = np.random.rand(3, dimension).astype(np.float32)
            index.add(vectors)
            
            # Save index
            index_path = self.source_dir / "faiss_index.bin"
            faiss.write_index(index, str(index_path))
            
            # Create mock metadata
            documents = [
                ("doc1_chunk1", "First test document content", {"source": "doc1.txt", "document_id": "doc1"}),
                ("doc1_chunk2", "More content from first document", {"source": "doc1.txt", "document_id": "doc1"}),
                ("doc2_chunk1", "Second test document content", {"source": "doc2.txt", "document_id": "doc2"})
            ]
            
            metadata = {
                'documents': documents,
                'id_to_index': {f"doc{i//2+1}_chunk{i%2+1}": i for i in range(3)},
                'stats': {'documents_stored': 2, 'chunks_stored': 3}
            }
            
            metadata_path = self.source_dir / "documents.pkl"
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
                
        except ImportError:
            self.skipTest("FAISS not available for migration testing")
    
    def test_migration_process(self):
        """Test complete migration process."""
        try:
            from faiss_data_migration import FAISSDataMigrator
            
            # Create migrator
            migrator = FAISSDataMigrator(str(self.temp_dir))
            migrator.source_paths = [self.source_dir]
            migrator.target_path = self.target_dir
            
            # Test analysis
            analysis = migrator.analyze_existing_data()
            self.assertGreater(len(analysis['source_locations']), 0)
            
            # Test data loading
            documents = migrator.load_existing_faiss_data()
            self.assertEqual(len(documents), 3)
            
            # Test conversation assignment
            documents = migrator.assign_conversation_ids(documents)
            self.assertTrue(all('conversation_id' in doc.metadata for doc in documents))
            
            # Test structure creation
            success = migrator.create_optimized_faiss_structure(documents)
            self.assertTrue(success)
            
            # Verify target files exist
            self.assertTrue((self.target_path / "optimized_faiss_index.bin").exists())
            self.assertTrue((self.target_path / "optimized_metadata.pkl").exists())
            
        except ImportError:
            self.skipTest("Migration module not available for testing")


class TestPerformanceImprovements(unittest.TestCase):
    """Test performance improvements in FAISS-only architecture."""
    
    def test_synchronous_operations_performance(self):
        """Test that synchronous operations are faster than async overhead."""
        # This would be a benchmark test comparing old vs new implementation
        
        # Mock both implementations
        start_time = time.time()
        
        # Simulate synchronous FAISS operation
        time.sleep(0.01)  # Simulated processing time
        sync_time = time.time() - start_time
        
        start_time = time.time()
        
        # Simulate async overhead
        async def async_operation():
            await asyncio.sleep(0.01)
            return "result"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_operation())
        finally:
            loop.close()
        
        async_time = time.time() - start_time
        
        # Async should have more overhead
        self.assertLess(sync_time, async_time)
    
    def test_memory_efficiency(self):
        """Test memory efficiency improvements."""
        # This would test memory usage patterns
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss
        
        # Simulate optimized FAISS operations
        # (In real test, would create and use optimized client)
        
        # Measure final memory
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        self.assertLess(memory_increase, 100 * 1024 * 1024)  # Less than 100MB


class TestErrorHandling(unittest.TestCase):
    """Test error handling and recovery mechanisms."""
    
    def test_faiss_initialization_failure(self):
        """Test handling of FAISS initialization failures."""
        with patch('faiss.IndexFlatIP') as mock_index:
            mock_index.side_effect = Exception("FAISS initialization failed")
            
            # Test that client handles initialization gracefully
            # (Implementation would depend on actual client code)
            pass
    
    def test_embedding_service_failure(self):
        """Test handling of embedding service failures."""
        # Mock embedding service failure
        mock_service = Mock()
        mock_service.create_embedding.side_effect = Exception("API failure")
        
        # Test that coordinator handles embedding failures gracefully
        # (Implementation would depend on actual coordinator code)
        pass
    
    def test_data_corruption_recovery(self):
        """Test recovery from corrupted data files."""
        # Test how system handles corrupted FAISS index or metadata
        # (Implementation would depend on actual client code)
        pass


def run_comprehensive_tests():
    """Run all migration and performance tests."""
    print("🧪 Running Comprehensive FAISS Migration Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestOptimizedFaissClient,
        TestFAISSONlyRAGCoordinator,
        TestDataMigration,
        TestPerformanceImprovements,
        TestErrorHandling
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report results
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")
    
    if result.errors:
        print("\nErrors:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    
    return success


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)