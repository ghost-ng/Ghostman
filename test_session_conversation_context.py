#!/usr/bin/env python3
"""
Test SimpleFAISSSession with conversation context metadata.
This test validates that conversation_id is properly stored and used for filtering.
"""

import tempfile
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_session_conversation_context():
    """Test that SimpleFAISSSession properly handles conversation context."""
    print("🧪 Testing SimpleFAISSSession with Conversation Context")
    print("=" * 60)
    
    try:
        from ghostman.src.infrastructure.rag_pipeline.threading.simple_faiss_session import create_simple_faiss_session
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"📁 Using temporary directory: {temp_dir}")
            
            # Create test files with different content
            test_files = []
            test_data = [
                {
                    "filename": "conv_a_doc1.txt",
                    "content": """# Artificial Intelligence and Machine Learning

Artificial intelligence (AI) is a branch of computer science that aims to create intelligent machines. Machine learning is a subset of AI that focuses on the development of algorithms that can learn and make predictions or decisions without being explicitly programmed.

## Key Concepts

1. **Supervised Learning**: Uses labeled training data to learn a mapping from inputs to outputs.
2. **Unsupervised Learning**: Finds hidden patterns or structures in unlabeled data.
3. **Reinforcement Learning**: Learns through interaction with an environment using rewards and punishments.

## Applications

- Image recognition
- Natural language processing
- Autonomous vehicles
- Recommendation systems""",
                    "conversation_id": "conv_a"
                },
                {
                    "filename": "conv_a_doc2.txt", 
                    "content": """# Neural Networks and Deep Learning

Neural networks are computing systems inspired by biological neural networks. Deep learning is a subset of machine learning that uses artificial neural networks with multiple layers.

## Architecture

1. **Input Layer**: Receives data
2. **Hidden Layers**: Process information
3. **Output Layer**: Produces results

## Types of Networks

- **Feedforward Networks**: Information flows in one direction
- **Convolutional Networks**: Specialized for image processing
- **Recurrent Networks**: Can process sequential data

## Training Process

Neural networks learn through backpropagation, adjusting weights based on prediction errors.""",
                    "conversation_id": "conv_a"
                },
                {
                    "filename": "conv_b_doc1.txt",
                    "content": """# Python Programming and Software Development

Python is a high-level, interpreted programming language known for its readability and versatility. It's widely used in software development, web development, data science, and automation.

## Key Features

1. **Simple Syntax**: Easy to read and write
2. **Dynamic Typing**: Variables don't need explicit type declarations
3. **Extensive Libraries**: Large ecosystem of third-party packages
4. **Cross-platform**: Runs on Windows, macOS, and Linux

## Development Practices

- **Version Control**: Use Git for tracking changes
- **Testing**: Write unit tests for code reliability
- **Documentation**: Keep code well-documented
- **Code Style**: Follow PEP 8 guidelines

## Popular Frameworks

- Django and Flask for web development
- NumPy and Pandas for data science
- PyQt and Tkinter for GUI applications""",
                    "conversation_id": "conv_b"
                }
            ]
            
            # Create test files
            for data in test_data:
                file_path = Path(temp_dir) / data["filename"]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data["content"])
                test_files.append({
                    "path": str(file_path),
                    "conversation_id": data["conversation_id"],
                    "filename": data["filename"],
                    "content": data["content"]
                })
                print(f"  ✅ Created test file: {data['filename']}")
            
            # Create session
            session = create_simple_faiss_session()
            if not session.is_ready:
                print("❌ Session not ready")
                return False
            
            print("✅ SimpleFAISSSession created and ready")
            
            # Ingest documents with conversation context
            print(f"\n📊 Ingesting {len(test_files)} documents...")
            document_ids = []
            
            for file_data in test_files:
                # Prepare metadata override with conversation_id
                metadata_override = {
                    "conversation_id": file_data["conversation_id"]
                }
                
                # Ingest document
                doc_id = session.ingest_document(
                    file_path=file_data["path"],
                    metadata_override=metadata_override
                )
                
                if doc_id:
                    document_ids.append(doc_id)
                    print(f"  ✅ Ingested: {file_data['filename']} (conv: {file_data['conversation_id']}, id: {doc_id})")
                else:
                    print(f"  ❌ Failed to ingest: {file_data['filename']}")
                    return False
            
            print(f"\n📈 Total documents ingested: {len(document_ids)}")
            
            # Test queries with conversation filtering
            print(f"\n🔍 Testing conversation-filtered queries...")
            
            test_query = "artificial intelligence machine learning"
            
            # Test 1: Query for conversation A
            print(f"\n  🎯 Querying conversation 'conv_a' for: {test_query}")
            results_a = session.query(
                query_text=test_query,
                top_k=10,
                filters={"conversation_id": "conv_a"}
            )
            
            if results_a and results_a.get('sources'):
                print(f"     📊 Found {len(results_a['sources'])} results for conv_a:")
                for i, source in enumerate(results_a['sources']):
                    conv_id = source.get('metadata', {}).get('conversation_id', 'NOT_FOUND')
                    filename = source.get('metadata', {}).get('filename', 'unknown')
                    score = source.get('score', 0.0)
                    print(f"       {i+1}. {filename} (conv_id: {conv_id}, score: {score:.4f})")
            else:
                print("     ❌ No results found for conv_a")
                return False
            
            # Test 2: Query for conversation B
            print(f"\n  🎯 Querying conversation 'conv_b' for: {test_query}")
            results_b = session.query(
                query_text=test_query,
                top_k=10,
                filters={"conversation_id": "conv_b"}
            )
            
            if results_b and results_b.get('sources'):
                print(f"     📊 Found {len(results_b['sources'])} results for conv_b:")
                for i, source in enumerate(results_b['sources']):
                    conv_id = source.get('metadata', {}).get('conversation_id', 'NOT_FOUND')
                    filename = source.get('metadata', {}).get('filename', 'unknown')
                    score = source.get('score', 0.0)
                    print(f"       {i+1}. {filename} (conv_id: {conv_id}, score: {score:.4f})")
            else:
                print("     ❌ No results found for conv_b")
                return False
            
            # Test 3: Query without filter (should return all)
            print(f"\n  🎯 Querying without filter for: {test_query}")
            results_all = session.query(
                query_text=test_query,
                top_k=10,
                filters=None
            )
            
            if results_all and results_all.get('sources'):
                print(f"     📊 Found {len(results_all['sources'])} results without filter:")
                for i, source in enumerate(results_all['sources']):
                    conv_id = source.get('metadata', {}).get('conversation_id', 'NOT_FOUND')
                    filename = source.get('metadata', {}).get('filename', 'unknown')
                    score = source.get('score', 0.0)
                    print(f"       {i+1}. {filename} (conv_id: {conv_id}, score: {score:.4f})")
            else:
                print("     ❌ No results found without filter")
                return False
            
            # Validate results
            print(f"\n🔍 Validating filtering results...")
            success = True
            
            # Check conv_a results only contain conv_a documents
            if results_a and results_a.get('sources'):
                for source in results_a['sources']:
                    conv_id = source.get('metadata', {}).get('conversation_id')
                    if conv_id != 'conv_a':
                        print(f"❌ Conv_a query returned document from conversation: {conv_id}")
                        success = False
                        
                if len(results_a['sources']) != 2:  # Should have 2 conv_a documents
                    print(f"❌ Expected 2 documents for conv_a, got {len(results_a['sources'])}")
                    success = False
            
            # Check conv_b results only contain conv_b documents
            if results_b and results_b.get('sources'):
                for source in results_b['sources']:
                    conv_id = source.get('metadata', {}).get('conversation_id')
                    if conv_id != 'conv_b':
                        print(f"❌ Conv_b query returned document from conversation: {conv_id}")
                        success = False
                        
                if len(results_b['sources']) != 1:  # Should have 1 conv_b document
                    print(f"❌ Expected 1 document for conv_b, got {len(results_b['sources'])}")
                    success = False
            
            # Check that unfiltered query returns all documents
            if results_all and results_all.get('sources'):
                if len(results_all['sources']) != 3:  # Should have all 3 documents
                    print(f"❌ Expected 3 documents without filter, got {len(results_all['sources'])}")
                    success = False
            
            # Clean up
            session.close()
            
            # Final result
            print("\n" + "=" * 60)
            if success:
                print("✅ ALL TESTS PASSED! SimpleFAISSSession conversation filtering is working correctly.")
                print("🎉 Documents are properly filtered by conversation_id")
                print("🎉 Metadata override mechanism is functioning properly")
                return True
            else:
                print("❌ SOME TESTS FAILED! There are still issues to resolve.")
                return False
                
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_session_conversation_context()
    if success:
        print("\n🎊 SUCCESS! SimpleFAISSSession conversation context is working!")
        exit(0)
    else:
        print("\n💥 FAILURE! The session needs more work.")
        exit(1)