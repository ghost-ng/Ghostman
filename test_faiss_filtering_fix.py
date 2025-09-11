#!/usr/bin/env python3
"""
Test script to verify the FAISS filtering bug fix.

This tests the specific issues identified:
1. Filtering logic was only applied to orphaned documents
2. Normal documents bypassed ALL filtering
3. Conversation metadata wasn't being stored properly
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
import sys
import os

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("faiss_fix_test")

def test_faiss_filtering_fix():
    """Test the FAISS filtering fix comprehensively."""
    
    print("🧪 Testing FAISS Filtering Fix")
    print("=" * 50)
    
    try:
        # Import required modules
        from ghostman.src.infrastructure.rag_pipeline.config.rag_config import get_config
        from ghostman.src.infrastructure.rag_pipeline.threading.simple_faiss_session import create_simple_faiss_session
        from ghostman.src.infrastructure.rag_pipeline.vector_store.faiss_client import FaissClient
        from ghostman.src.infrastructure.rag_pipeline.document_loaders.base_loader import Document, DocumentMetadata
        from ghostman.src.infrastructure.rag_pipeline.text_processing.text_splitter import TextChunk
        import numpy as np
        
        print("✅ Successfully imported required modules")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        try:
            # 1. Test FAISS Client directly
            print("\n1️⃣ Testing FAISS Client Filtering Logic")
            
            # Create config with temporary directory
            config = get_config()
            config.vector_store.persist_directory = temp_dir
            
            # Create FAISS client (pass vector_store config, not full config)
            faiss_client = FaissClient(config.vector_store)
            print("✅ FAISS client created successfully")
            
            # Create test documents with different conversation IDs
            test_data = [
                {
                    "content": "This is a document for conversation A about AI and machine learning.",
                    "conversation_id": "conv_a",
                    "filename": "doc_a.txt"
                },
                {
                    "content": "This is a document for conversation B about Python programming.",
                    "conversation_id": "conv_b", 
                    "filename": "doc_b.txt"
                },
                {
                    "content": "This is another document for conversation A about neural networks.",
                    "conversation_id": "conv_a",
                    "filename": "doc_a2.txt"
                }
            ]
            
            # Store documents with conversation metadata
            print("\n📊 Storing test documents...")
            document_ids = []
            
            async def store_documents():
                nonlocal document_ids
                for i, data in enumerate(test_data):
                    # Create document
                    doc_metadata = DocumentMetadata(
                        source=data["filename"],
                        source_type="file",
                        filename=data["filename"], 
                        file_extension=".txt"
                    )
                    document = Document(content=data["content"], metadata=doc_metadata)
                    
                    # Create chunk with conversation metadata
                    chunk = TextChunk(
                        content=data["content"],
                        chunk_index=0,
                        start_char=0,
                        end_char=len(data["content"]),
                        token_count=len(data["content"].split()),
                        metadata={"conversation_id": data["conversation_id"]}  # This is the key fix!
                    )
                    
                    # Create mock embedding
                    embedding = np.random.rand(1536).astype(np.float32)
                    embedding = embedding / np.linalg.norm(embedding)  # Normalize
                    
                    # Store in FAISS
                    chunk_ids = await faiss_client.store_document(
                        document=document,
                        chunks=[chunk],
                        embeddings=[embedding]
                    )
                    
                    document_ids.extend(chunk_ids)
                    print(f"   ✅ Stored document {i+1}: {data['filename']} (conv: {data['conversation_id']})")
            
            # Run async storage
            asyncio.run(store_documents())
            print(f"📊 Total documents stored: {len(document_ids)}")
            
            # Verify documents are stored
            collection_info = asyncio.run(faiss_client.get_collection_info())
            print(f"📈 Collection info: {collection_info}")
            
            # 2. Test filtering with conversation queries
            print("\n2️⃣ Testing Conversation Filtering")
            
            async def test_filtered_queries():
                # Create query embedding
                query_text = "artificial intelligence machine learning"
                query_embedding = np.random.rand(1536).astype(np.float32)
                query_embedding = query_embedding / np.linalg.norm(query_embedding)
                
                print(f"🔍 Query text: {query_text}")
                
                # Test 1: Query with conversation_id filter for conv_a
                print(f"\n   🎯 Testing filter for conversation_id='conv_a':")
                results_conv_a = await faiss_client.similarity_search(
                    query_embedding=query_embedding,
                    top_k=10,
                    filters={"conversation_id": "conv_a"},
                    include_embeddings=False
                )
                
                print(f"   📊 Results for conv_a: {len(results_conv_a)}")
                for i, result in enumerate(results_conv_a):
                    conv_id = result.metadata.get('conversation_id', 'NOT_FOUND')
                    filename = result.metadata.get('filename', 'unknown')
                    print(f"      {i+1}. {filename} (conv_id: {conv_id}, score: {result.score:.4f})")
                
                # Test 2: Query with conversation_id filter for conv_b
                print(f"\n   🎯 Testing filter for conversation_id='conv_b':")
                results_conv_b = await faiss_client.similarity_search(
                    query_embedding=query_embedding,
                    top_k=10,
                    filters={"conversation_id": "conv_b"},
                    include_embeddings=False
                )
                
                print(f"   📊 Results for conv_b: {len(results_conv_b)}")
                for i, result in enumerate(results_conv_b):
                    conv_id = result.metadata.get('conversation_id', 'NOT_FOUND')
                    filename = result.metadata.get('filename', 'unknown')
                    print(f"      {i+1}. {filename} (conv_id: {conv_id}, score: {result.score:.4f})")
                
                # Test 3: Query without filter (should return all)
                print(f"\n   🎯 Testing query without filters:")
                results_all = await faiss_client.similarity_search(
                    query_embedding=query_embedding,
                    top_k=10,
                    filters=None,
                    include_embeddings=False
                )
                
                print(f"   📊 Results without filter: {len(results_all)}")
                for i, result in enumerate(results_all):
                    conv_id = result.metadata.get('conversation_id', 'NOT_FOUND')
                    filename = result.metadata.get('filename', 'unknown')
                    print(f"      {i+1}. {filename} (conv_id: {conv_id}, score: {result.score:.4f})")
                
                # Verify results
                success = True
                
                # Check that conv_a filter only returns conv_a documents
                conv_a_results_valid = all(
                    result.metadata.get('conversation_id') == 'conv_a' 
                    for result in results_conv_a
                )
                if not conv_a_results_valid:
                    print("❌ Conv_a filter returned documents from other conversations!")
                    success = False
                else:
                    print("✅ Conv_a filter working correctly")
                
                # Check that conv_b filter only returns conv_b documents  
                conv_b_results_valid = all(
                    result.metadata.get('conversation_id') == 'conv_b'
                    for result in results_conv_b
                )
                if not conv_b_results_valid:
                    print("❌ Conv_b filter returned documents from other conversations!")
                    success = False
                else:
                    print("✅ Conv_b filter working correctly")
                
                # Check that we have expected number of results
                if len(results_conv_a) < 2:  # Should have 2 docs for conv_a
                    print(f"❌ Expected 2 documents for conv_a, got {len(results_conv_a)}")
                    success = False
                    
                if len(results_conv_b) < 1:  # Should have 1 doc for conv_b
                    print(f"❌ Expected 1 document for conv_b, got {len(results_conv_b)}")
                    success = False
                
                if len(results_all) < 3:  # Should have all 3 docs
                    print(f"❌ Expected 3 documents without filter, got {len(results_all)}")
                    success = False
                
                return success
            
            # Run filtering tests
            filter_success = asyncio.run(test_filtered_queries())
            
            # 3. Test SimpleFAISSSession integration
            print("\n3️⃣ Testing SimpleFAISSSession Integration")
            
            session = create_simple_faiss_session()
            if session.is_ready:
                print("✅ SimpleFAISSSession created and ready")
                
                # Test query through session
                test_query = "machine learning artificial intelligence"
                
                # Test with conversation filter
                response = session.query(
                    query_text=test_query,
                    top_k=5,
                    filters={"conversation_id": "conv_a"}
                )
                
                if response and response.get('sources'):
                    print(f"✅ Session query returned {len(response['sources'])} sources")
                    for i, source in enumerate(response['sources']):
                        conv_id = source.get('metadata', {}).get('conversation_id', 'NOT_FOUND')
                        filename = source.get('metadata', {}).get('filename', 'unknown')
                        print(f"   {i+1}. {filename} (conv_id: {conv_id})")
                else:
                    print("❌ Session query returned no results")
                    filter_success = False
                
                session.close()
            else:
                print("❌ SimpleFAISSSession not ready")
                filter_success = False
            
            # Clean up
            faiss_client.close()
            
            # Final result
            print("\n" + "=" * 50)
            if filter_success:
                print("✅ ALL TESTS PASSED! FAISS filtering fix is working correctly.")
                print("🎉 Documents are properly filtered by conversation_id")
                print("🎉 Metadata is correctly stored and retrieved")
                return True
            else:
                print("❌ SOME TESTS FAILED! There are still issues to resolve.")
                return False
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

def main():
    """Main test runner."""
    print("🔧 FAISS Filtering Fix Verification Test")
    print("Testing the fix for conversation-based document filtering")
    print()
    
    success = test_faiss_filtering_fix()
    
    if success:
        print("\n🎊 SUCCESS! The FAISS filtering fix is working correctly!")
        exit(0)
    else:
        print("\n💥 FAILURE! The fix needs more work.")
        exit(1)

if __name__ == "__main__":
    main()