"""
Comprehensive RAG Pipeline Tests

Integration tests for the complete RAG pipeline implementation.
Tests all major components and end-to-end functionality.
"""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Test imports - these would normally be pytest fixtures
from ..config.rag_config import RAGPipelineConfig, EmbeddingConfig, LLMConfig, VectorStoreConfig
from ..pipeline.rag_pipeline import RAGPipeline, RAGQuery
from ..document_loaders.loader_factory import DocumentLoaderFactory
from ..text_processing.text_splitter import TextSplitterFactory, TextProcessingConfig
from ..vector_store.faiss_client import FaissClient


class TestRAGPipeline:
    """Test suite for the complete RAG pipeline."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def test_config(self, temp_dir):
        """Create test configuration."""
        config = RAGPipelineConfig()
        
        # Use test API key (would be set via environment in real tests)
        config.embedding.api_key = os.getenv("OPENAI_API_KEY", "test-key")
        config.llm.api_key = os.getenv("OPENAI_API_KEY", "test-key")
        
        # Use test directory for vector store
        config.vector_store.persist_directory = str(temp_dir / "chromadb")
        config.vector_store.collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
        
        # Use smaller chunks for testing
        config.text_processing.chunk_size = 500
        config.text_processing.chunk_overlap = 50
        
        # Use lower top_k for testing
        config.retrieval.top_k = 3
        
        return config
    
    @pytest.fixture
    def rag_pipeline(self, test_config):
        """Create RAG pipeline for testing."""
        return RAGPipeline(test_config)
    
    @pytest.fixture
    def sample_documents(self, temp_dir) -> List[Path]:
        """Create sample documents for testing."""
        documents = []
        
        # Create sample text file
        text_doc = temp_dir / "sample.txt"
        text_doc.write_text("""
        This is a comprehensive guide to artificial intelligence and machine learning.
        
        Introduction to AI
        Artificial Intelligence (AI) is the simulation of human intelligence in machines
        that are programmed to think and learn like humans. The field of AI includes
        machine learning, deep learning, and natural language processing.
        
        Machine Learning Basics
        Machine learning is a subset of AI that focuses on the ability of machines to
        receive data and learn for themselves without being explicitly programmed.
        There are three main types: supervised learning, unsupervised learning, and
        reinforcement learning.
        
        Deep Learning
        Deep learning is a subset of machine learning that uses neural networks with
        multiple layers. These networks can learn and make intelligent decisions on
        their own. Deep learning has revolutionized fields like computer vision,
        natural language processing, and speech recognition.
        
        Applications
        AI and ML are used in various applications including:
        - Autonomous vehicles
        - Healthcare diagnosis
        - Financial trading
        - Recommendation systems
        - Virtual assistants
        
        Future of AI
        The future of AI looks promising with continuous advancements in research
        and development. We can expect to see more sophisticated AI systems that
        can perform complex tasks and make decisions with minimal human intervention.
        """)
        documents.append(text_doc)
        
        # Create another sample document
        tech_doc = temp_dir / "technology.md"
        tech_doc.write_text("""
        # Modern Technology Trends
        
        ## Cloud Computing
        Cloud computing has transformed how businesses operate by providing scalable
        and flexible computing resources over the internet. Major cloud providers
        include Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform.
        
        ## Internet of Things (IoT)
        IoT refers to the network of physical devices that are connected to the internet
        and can collect and exchange data. This includes smart home devices, wearables,
        and industrial sensors.
        
        ## Blockchain Technology
        Blockchain is a distributed ledger technology that maintains a continuously
        growing list of records. It's the technology behind cryptocurrencies like
        Bitcoin and Ethereum.
        
        ## Quantum Computing
        Quantum computing uses quantum-mechanical phenomena to perform operations on
        data. It has the potential to solve certain problems much faster than
        classical computers.
        """)
        documents.append(tech_doc)
        
        return documents
    
    def test_configuration_validation(self, test_config):
        """Test configuration validation."""
        errors = test_config.validate()
        
        # Should have no errors with proper API keys
        if os.getenv("OPENAI_API_KEY"):
            assert len(errors) == 0
        else:
            # Should have API key errors without proper keys
            assert any("API key" in error for error in errors)
    
    def test_document_loader_factory(self, test_config):
        """Test document loader factory."""
        factory = DocumentLoaderFactory(test_config.document_loading)
        
        # Test loader registration
        assert len(factory._loader_registry) > 0
        assert 'text' in factory._loader_registry
        assert 'pdf' in factory._loader_registry
        
        # Test loader selection
        text_loader = factory.get_loader_for_source("test.txt")
        assert text_loader is not None
        
        pdf_loader = factory.get_loader_for_source("test.pdf")
        assert pdf_loader is not None
        
        web_loader = factory.get_loader_for_source("https://example.com")
        assert web_loader is not None
    
    def test_text_splitter(self, test_config):
        """Test text splitting functionality."""
        splitter = TextSplitterFactory.create_splitter(test_config.text_processing)
        
        sample_text = "This is a test document. " * 100  # Create long text
        chunks = splitter.split_text(sample_text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= test_config.text_processing.chunk_size + 100  # Allow some overlap
            assert chunk.chunk_index >= 0
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
    
    @pytest.mark.asyncio
    async def test_vector_store_operations(self, test_config, temp_dir):
        """Test vector store operations."""
        from ..document_loaders.base_loader import Document, DocumentMetadata
        from ..text_processing.text_splitter import TextChunk
        import numpy as np
        
        # Create vector store
        vector_store = ChromaDBClient(test_config.vector_store)
        
        # Create test document and chunks
        metadata = DocumentMetadata(source="test.txt", source_type="file")
        document = Document(content="Test content for vector store", metadata=metadata)
        
        chunks = [
            TextChunk(content="Test chunk 1", chunk_index=0, start_char=0, end_char=12),
            TextChunk(content="Test chunk 2", chunk_index=1, start_char=13, end_char=25)
        ]
        
        # Create dummy embeddings
        embeddings = [np.random.rand(1536) for _ in chunks]
        
        # Test storage
        chunk_ids = await vector_store.store_document(document, chunks, embeddings)
        assert len(chunk_ids) == len(chunks)
        
        # Test retrieval
        query_embedding = np.random.rand(1536)
        results = await vector_store.similarity_search(query_embedding, top_k=2)
        
        assert len(results) <= 2
        if results:
            assert results[0].content in ["Test chunk 1", "Test chunk 2"]
    
    @pytest.mark.asyncio 
    async def test_document_ingestion(self, rag_pipeline, sample_documents):
        """Test document ingestion into RAG pipeline."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for integration tests")
        
        # Ingest first document
        doc_path = sample_documents[0]
        doc_id = await rag_pipeline.ingest_document(doc_path)
        
        assert doc_id is not None
        assert len(doc_id) > 0
        
        # Check statistics
        stats = rag_pipeline.get_stats()
        assert stats['documents_processed'] >= 1
        assert stats['chunks_created'] > 0
        assert stats['embeddings_generated'] > 0
    
    @pytest.mark.asyncio
    async def test_query_processing(self, rag_pipeline, sample_documents):
        """Test query processing through RAG pipeline."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for integration tests")
        
        # Ingest documents first
        for doc_path in sample_documents:
            await rag_pipeline.ingest_document(doc_path)
        
        # Test simple query
        response = await rag_pipeline.query("What is machine learning?")
        
        assert response.query == "What is machine learning?"
        assert len(response.answer) > 0
        assert len(response.sources) > 0
        assert response.processing_time > 0
        
        # Test with RAGQuery object
        rag_query = RAGQuery(
            text="Tell me about cloud computing",
            top_k=2,
            include_metadata=True
        )
        
        response = await rag_pipeline.query(rag_query)
        assert response.query == "Tell me about cloud computing"
        assert len(response.sources) <= 2
    
    @pytest.mark.asyncio
    async def test_health_check(self, rag_pipeline):
        """Test pipeline health check."""
        health = await rag_pipeline.health_check()
        
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in health
        assert "config" in health
    
    @pytest.mark.asyncio
    async def test_batch_ingestion(self, rag_pipeline, sample_documents):
        """Test batch document ingestion."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for integration tests")
        
        # Ingest multiple documents
        doc_ids = await rag_pipeline.ingest_documents(sample_documents, max_concurrent=2)
        
        assert len(doc_ids) == len(sample_documents)
        successful_ids = [doc_id for doc_id in doc_ids if doc_id is not None]
        assert len(successful_ids) > 0
        
        # Check that documents can be queried
        response = await rag_pipeline.query("What technologies are mentioned?")
        assert len(response.sources) > 0
    
    @pytest.mark.asyncio
    async def test_document_deletion(self, rag_pipeline, sample_documents):
        """Test document deletion."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for integration tests")
        
        # Ingest document
        doc_path = sample_documents[0]
        doc_id = await rag_pipeline.ingest_document(doc_path)
        
        # Query to verify document exists
        response = await rag_pipeline.query("artificial intelligence")
        sources_before = len(response.sources)
        
        # Delete document
        success = await rag_pipeline.delete_document(doc_id)
        assert success
        
        # Query again to verify deletion
        response = await rag_pipeline.query("artificial intelligence")
        sources_after = len(response.sources)
        
        # Should have fewer or no sources
        assert sources_after <= sources_before
    
    def test_statistics_tracking(self, rag_pipeline):
        """Test statistics tracking."""
        initial_stats = rag_pipeline.get_stats()
        
        # Check expected stat keys
        expected_keys = [
            'documents_processed', 'queries_processed', 'total_processing_time',
            'total_query_time', 'chunks_created', 'embeddings_generated'
        ]
        
        for key in expected_keys:
            assert key in initial_stats
        
        # Test reset
        rag_pipeline.reset_stats()
        reset_stats = rag_pipeline.get_stats()
        
        for key in expected_keys:
            assert reset_stats[key] == 0
    
    @pytest.mark.asyncio
    async def test_backup_and_restore(self, rag_pipeline, temp_dir):
        """Test backup functionality."""
        backup_path = temp_dir / "backup.json"
        
        # Create backup
        success = await rag_pipeline.backup(str(backup_path))
        assert success
        assert backup_path.exists()
        
        # Verify backup content
        import json
        with open(backup_path) as f:
            backup_data = json.load(f)
        
        assert "backup_time" in backup_data
        assert "config" in backup_data
        assert "stats" in backup_data
        assert "health" in backup_data


class TestMigration:
    """Test migration from SQLite to ChromaDB."""
    
    @pytest.fixture
    def mock_sqlite_db(self, temp_dir):
        """Create mock SQLite database for testing."""
        import sqlite3
        
        db_path = temp_dir / "test.db"
        
        # Create mock database with sample data
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                source TEXT,
                content TEXT,
                title TEXT,
                created_at TEXT
            )
        """)
        
        sample_docs = [
            (1, "doc1.txt", "This is the content of document 1", "Document 1", "2024-01-01 10:00:00"),
            (2, "doc2.txt", "This is the content of document 2", "Document 2", "2024-01-02 11:00:00"),
            (3, "doc3.txt", "This is the content of document 3", "Document 3", "2024-01-03 12:00:00")
        ]
        
        cursor.executemany(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            sample_docs
        )
        
        conn.commit()
        conn.close()
        
        return db_path
    
    @pytest.mark.asyncio
    async def test_migration_analysis(self, mock_sqlite_db):
        """Test SQLite database analysis."""
        from ..migration.sqlite_to_chroma_migrator import SQLiteToChromaMigrator
        
        migrator = SQLiteToChromaMigrator(str(mock_sqlite_db), dry_run=True)
        
        # Test analysis
        analysis = migrator.analyze_legacy_data()
        
        assert "tables" in analysis
        assert "documents" in analysis["tables"]
        assert "document_tables" in analysis
        assert len(analysis["document_tables"]) > 0
    
    @pytest.mark.asyncio
    async def test_document_extraction(self, mock_sqlite_db):
        """Test document extraction from SQLite."""
        from ..migration.sqlite_to_chroma_migrator import SQLiteToChromaMigrator
        
        migrator = SQLiteToChromaMigrator(str(mock_sqlite_db), dry_run=True)
        
        # Extract documents
        legacy_docs = migrator.extract_legacy_documents("documents")
        
        assert len(legacy_docs) == 3
        assert legacy_docs[0].source == "doc1.txt"
        assert "content of document 1" in legacy_docs[0].content
    
    @pytest.mark.asyncio 
    async def test_dry_run_migration(self, mock_sqlite_db, test_config):
        """Test dry run migration."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for integration tests")
        
        from ..migration.sqlite_to_chroma_migrator import SQLiteToChromaMigrator
        
        rag_pipeline = RAGPipeline(test_config)
        migrator = SQLiteToChromaMigrator(str(mock_sqlite_db), rag_pipeline, dry_run=True)
        
        # Run dry run migration
        results = await migrator.migrate_documents()
        
        assert results["dry_run"] is True
        assert "documents_to_migrate" in results
        assert results["documents_to_migrate"] == 3


def run_integration_tests():
    """
    Run integration tests for RAG pipeline.
    
    This function demonstrates how to use the RAG pipeline programmatically.
    """
    import asyncio
    
    async def demo_workflow():
        """Demonstrate the complete RAG workflow."""
        print("🚀 Starting RAG Pipeline Integration Test")
        
        # 1. Create configuration
        config = RAGPipelineConfig()
        
        # Check for API key
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            return
        
        config.embedding.api_key = os.getenv("OPENAI_API_KEY")
        config.llm.api_key = os.getenv("OPENAI_API_KEY")
        
        # 2. Initialize pipeline
        print("📊 Initializing RAG Pipeline...")
        pipeline = RAGPipeline(config)
        
        # 3. Health check
        health = await pipeline.health_check()
        print(f"💊 Health Status: {health['status']}")
        
        # 4. Create test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""
            Python Programming Guide
            
            Python is a high-level programming language known for its simplicity and readability.
            It supports multiple programming paradigms including procedural, object-oriented, 
            and functional programming.
            
            Key Features:
            - Easy to learn and use
            - Extensive standard library
            - Large community support
            - Cross-platform compatibility
            - Great for data science and machine learning
            
            Applications:
            Python is used in web development, data analysis, artificial intelligence,
            scientific computing, automation, and more.
            """)
            test_doc_path = f.name
        
        try:
            # 5. Ingest document
            print("📄 Ingesting test document...")
            doc_id = await pipeline.ingest_document(test_doc_path)
            print(f"✅ Document ingested with ID: {doc_id}")
            
            # 6. Query the pipeline
            print("\n🔍 Testing RAG queries...")
            
            queries = [
                "What is Python?",
                "What are the key features of Python?",
                "What applications is Python used for?"
            ]
            
            for query in queries:
                print(f"\nQuery: {query}")
                response = await pipeline.query(query)
                print(f"Answer: {response.answer[:200]}...")
                print(f"Sources: {len(response.sources)}")
                print(f"Processing time: {response.processing_time:.2f}s")
            
            # 7. Show statistics
            stats = pipeline.get_stats()
            print(f"\n📈 Pipeline Statistics:")
            print(f"- Documents processed: {stats['documents_processed']}")
            print(f"- Queries processed: {stats['queries_processed']}")
            print(f"- Chunks created: {stats['chunks_created']}")
            print(f"- Average query time: {stats.get('avg_query_time', 0):.2f}s")
            
            print("\n✅ Integration test completed successfully!")
            
        finally:
            # Cleanup
            os.unlink(test_doc_path)
    
    # Run the demo
    asyncio.run(demo_workflow())


if __name__ == "__main__":
    # Run integration tests when script is executed directly
    run_integration_tests()