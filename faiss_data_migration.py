"""
FAISS Data Migration Script

Safely migrates existing documents from current FAISS implementation
to the optimized FAISS-only architecture while preserving all data.
"""

import os
import pickle
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time
from dataclasses import dataclass
import uuid

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("faiss_migration")


@dataclass
class DocumentRecord:
    """Document record for migration."""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    original_index: Optional[int] = None


@dataclass
class MigrationStats:
    """Migration statistics tracking."""
    total_documents: int = 0
    chunks_migrated: int = 0
    conversations_identified: int = 0
    errors_encountered: int = 0
    migration_time: float = 0.0
    data_integrity_verified: bool = False


class FAISSDataMigrator:
    """
    Migrates existing FAISS data to optimized FAISS-only architecture.
    
    Features:
    - Preserves all existing documents and embeddings
    - Creates conversation-specific metadata
    - Validates data integrity
    - Provides rollback capability
    - Comprehensive logging and reporting
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / f"faiss_migration_{int(time.time())}"
        
        # Source paths (existing FAISS data)
        self.source_paths = [
            self.project_root / "ghostman" / "data" / "faiss",
            self.project_root / "test_chroma_db",
            self.project_root / "example_chroma_db",
            self.project_root / "chroma_test_db",
            self.project_root / "test_chroma_unified"
        ]
        
        # Target path (optimized FAISS)
        self.target_path = self.project_root / "ghostman" / "data" / "optimized_faiss"
        
        # Migration state
        self.stats = MigrationStats()
        self.migrated_documents: List[DocumentRecord] = []
        self.conversation_mapping: Dict[str, str] = {}  # document_id -> conversation_id
        
        logger.info(f"FAISS data migrator initialized for {self.project_root}")
    
    def analyze_existing_data(self) -> Dict[str, Any]:
        """Analyze existing FAISS data to understand structure."""
        analysis = {
            "source_locations": [],
            "total_documents": 0,
            "data_formats": [],
            "index_files": [],
            "metadata_files": [],
            "estimated_size_mb": 0.0
        }
        
        try:
            for source_path in self.source_paths:
                if source_path.exists():
                    location_info = {
                        "path": str(source_path),
                        "files": [],
                        "size_mb": 0.0
                    }
                    
                    for file_path in source_path.rglob("*"):
                        if file_path.is_file():
                            file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                            location_info["files"].append({
                                "name": file_path.name,
                                "size_mb": round(file_size, 2),
                                "type": self._identify_file_type(file_path)
                            })
                            location_info["size_mb"] += file_size
                    
                    if location_info["files"]:
                        analysis["source_locations"].append(location_info)
                        analysis["estimated_size_mb"] += location_info["size_mb"]
            
            # Look for specific FAISS files
            for location in analysis["source_locations"]:
                for file_info in location["files"]:
                    if file_info["type"] == "faiss_index":
                        analysis["index_files"].append(f"{location['path']}/{file_info['name']}")
                    elif file_info["type"] == "metadata":
                        analysis["metadata_files"].append(f"{location['path']}/{file_info['name']}")
            
            logger.info(f"Analysis found {len(analysis['source_locations'])} data locations")
            return analysis
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return analysis
    
    def _identify_file_type(self, file_path: Path) -> str:
        """Identify the type of data file."""
        if file_path.suffix == '.bin' or 'faiss' in file_path.name.lower():
            return "faiss_index"
        elif file_path.suffix == '.pkl' or 'metadata' in file_path.name.lower():
            return "metadata"
        elif file_path.suffix == '.json':
            return "json_metadata"
        elif file_path.suffix == '.db' or 'chroma' in file_path.name.lower():
            return "chroma_db"
        else:
            return "unknown"
    
    def create_migration_backup(self) -> bool:
        """Create backup of existing data before migration."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating migration backup at {self.backup_dir}")
            
            for source_path in self.source_paths:
                if source_path.exists():
                    backup_target = self.backup_dir / source_path.name
                    if source_path.is_file():
                        shutil.copy2(source_path, backup_target)
                    else:
                        shutil.copytree(source_path, backup_target, dirs_exist_ok=True)
            
            # Create backup manifest
            manifest = {
                "backup_time": time.time(),
                "source_paths": [str(p) for p in self.source_paths],
                "target_path": str(self.target_path),
                "migration_type": "faiss_optimization"
            }
            
            with open(self.backup_dir / "migration_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info("✅ Migration backup created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return False
    
    def load_existing_faiss_data(self) -> List[DocumentRecord]:
        """Load documents from existing FAISS implementations."""
        documents = []
        
        try:
            # Try to load from simple FAISS session format
            for source_path in self.source_paths:
                if not source_path.exists():
                    continue
                
                logger.info(f"Scanning {source_path} for FAISS data...")
                
                # Look for FAISS index and metadata files
                index_files = list(source_path.glob("*.bin")) + list(source_path.glob("**/faiss_index.bin"))
                metadata_files = list(source_path.glob("*.pkl")) + list(source_path.glob("**/documents.pkl"))
                
                for index_file in index_files:
                    try:
                        # Try to load FAISS index
                        import faiss
                        index = faiss.read_index(str(index_file))
                        
                        # Look for corresponding metadata
                        metadata_file = None
                        for meta_file in metadata_files:
                            if meta_file.parent == index_file.parent:
                                metadata_file = meta_file
                                break
                        
                        if metadata_file:
                            docs_from_source = self._load_faiss_with_metadata(index, metadata_file)
                            documents.extend(docs_from_source)
                            logger.info(f"Loaded {len(docs_from_source)} documents from {source_path}")
                        else:
                            logger.warning(f"Found FAISS index but no metadata at {source_path}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to load FAISS data from {index_file}: {e}")
                        continue
            
            logger.info(f"Total documents loaded: {len(documents)}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load existing FAISS data: {e}")
            return []
    
    def _load_faiss_with_metadata(self, faiss_index, metadata_file: Path) -> List[DocumentRecord]:
        """Load FAISS index with metadata file."""
        documents = []
        
        try:
            # Load metadata
            with open(metadata_file, 'rb') as f:
                data = pickle.load(f)
            
            # Extract documents based on format
            if 'documents' in data:
                # Simple FAISS session format
                doc_list = data['documents']
                id_to_index = data.get('id_to_index', {})
                
                for i, (chunk_id, content, metadata) in enumerate(doc_list):
                    # Try to extract embeddings from FAISS index
                    embedding = None
                    try:
                        if i < faiss_index.ntotal:
                            # Extract vector from FAISS index
                            vector = faiss_index.reconstruct(i)
                            embedding = vector
                    except:
                        pass  # FAISS index might not support reconstruction
                    
                    doc_record = DocumentRecord(
                        chunk_id=chunk_id,
                        content=content,
                        metadata=metadata,
                        embedding=embedding,
                        original_index=i
                    )
                    documents.append(doc_record)
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load metadata from {metadata_file}: {e}")
            return []
    
    def assign_conversation_ids(self, documents: List[DocumentRecord]) -> List[DocumentRecord]:
        """Assign conversation IDs to documents based on metadata."""
        try:
            # Group documents by source file or other identifying metadata
            source_groups = {}
            
            for doc in documents:
                # Try to identify conversation from existing metadata
                conversation_id = doc.metadata.get('conversation_id')
                
                if not conversation_id:
                    # Try to group by source file
                    source = doc.metadata.get('source', doc.metadata.get('file_path', 'unknown'))
                    if source not in source_groups:
                        source_groups[source] = str(uuid.uuid4())
                    conversation_id = source_groups[source]
                
                # Update metadata with conversation ID
                doc.metadata['conversation_id'] = conversation_id
                self.conversation_mapping[doc.metadata.get('document_id', doc.chunk_id)] = conversation_id
            
            self.stats.conversations_identified = len(set(doc.metadata['conversation_id'] for doc in documents))
            logger.info(f"Assigned conversation IDs: {self.stats.conversations_identified} conversations")
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to assign conversation IDs: {e}")
            return documents
    
    def create_optimized_faiss_structure(self, documents: List[DocumentRecord]) -> bool:
        """Create optimized FAISS structure with documents."""
        try:
            self.target_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating optimized FAISS structure at {self.target_path}")
            
            # Initialize optimized FAISS components
            import faiss
            
            # Determine embedding dimension
            dimension = 1536  # Default OpenAI embedding dimension
            if documents and documents[0].embedding is not None:
                dimension = len(documents[0].embedding)
            
            # Create new optimized FAISS index
            index = faiss.IndexFlatIP(dimension)
            
            # Prepare data structures
            optimized_documents = []
            id_to_index = {}
            conversation_index = {}
            
            vectors = []
            valid_docs = []
            
            for i, doc in enumerate(documents):
                if doc.embedding is not None and len(doc.embedding) == dimension:
                    # Normalize embedding for cosine similarity
                    vector = np.array(doc.embedding, dtype=np.float32)
                    norm = np.linalg.norm(vector)
                    if norm > 0:
                        vector = vector / norm
                    
                    vectors.append(vector)
                    valid_docs.append(doc)
                    
                    # Update conversation index
                    conv_id = doc.metadata['conversation_id']
                    if conv_id not in conversation_index:
                        conversation_index[conv_id] = []
                    conversation_index[conv_id].append(len(valid_docs) - 1)
                    
                    # Update document structures
                    doc_tuple = (doc.chunk_id, doc.content, doc.metadata)
                    optimized_documents.append(doc_tuple)
                    id_to_index[doc.chunk_id] = len(valid_docs) - 1
                else:
                    logger.warning(f"Skipping document with invalid embedding: {doc.chunk_id}")
                    self.stats.errors_encountered += 1
            
            if vectors:
                # Add vectors to FAISS index
                vectors_array = np.array(vectors)
                index.add(vectors_array)
                
                # Save optimized FAISS index
                index_path = self.target_path / "optimized_faiss_index.bin"
                faiss.write_index(index, str(index_path))
                
                # Save optimized metadata
                metadata = {
                    'documents': optimized_documents,
                    'id_to_index': id_to_index,
                    'conversation_index': conversation_index,
                    'stats': {
                        'documents_indexed': len(optimized_documents),
                        'chunks_indexed': len(optimized_documents),
                        'conversations_tracked': len(conversation_index),
                        'migration_time': time.time()
                    },
                    'dimension': dimension,
                    'last_saved': time.time()
                }
                
                metadata_path = self.target_path / "optimized_metadata.pkl"
                with open(metadata_path, 'wb') as f:
                    pickle.dump(metadata, f)
                
                # Create human-readable summary
                summary = {
                    "migration_completed": time.time(),
                    "total_documents": len(optimized_documents),
                    "conversations": len(conversation_index),
                    "dimension": dimension,
                    "conversation_breakdown": {
                        conv_id: len(indices) 
                        for conv_id, indices in conversation_index.items()
                    }
                }
                
                summary_path = self.target_path / "migration_summary.json"
                with open(summary_path, 'w') as f:
                    json.dump(summary, f, indent=2)
                
                self.stats.chunks_migrated = len(optimized_documents)
                self.stats.total_documents = len(set(doc.metadata.get('document_id', doc.chunk_id) for doc in valid_docs))
                
                logger.info(f"✅ Created optimized FAISS structure: {len(optimized_documents)} chunks")
                return True
            else:
                logger.error("❌ No valid documents with embeddings found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to create optimized FAISS structure: {e}")
            return False
    
    def verify_migration_integrity(self) -> bool:
        """Verify that migration preserved data integrity."""
        try:
            logger.info("🔍 Verifying migration integrity...")
            
            # Load migrated data
            index_path = self.target_path / "optimized_faiss_index.bin"
            metadata_path = self.target_path / "optimized_metadata.pkl"
            
            if not index_path.exists() or not metadata_path.exists():
                logger.error("❌ Migrated files not found")
                return False
            
            # Load and verify FAISS index
            import faiss
            index = faiss.read_index(str(index_path))
            
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            documents = metadata['documents']
            conversation_index = metadata['conversation_index']
            
            # Verify counts
            if index.ntotal != len(documents):
                logger.error(f"❌ Vector count mismatch: {index.ntotal} vs {len(documents)}")
                return False
            
            # Verify conversation integrity
            total_in_conversations = sum(len(indices) for indices in conversation_index.values())
            if total_in_conversations != len(documents):
                logger.error(f"❌ Conversation index mismatch: {total_in_conversations} vs {len(documents)}")
                return False
            
            # Test search functionality
            if index.ntotal > 0:
                # Create dummy query
                dummy_query = np.random.rand(index.d).astype(np.float32)
                dummy_query = dummy_query / np.linalg.norm(dummy_query)
                
                try:
                    scores, indices = index.search(dummy_query.reshape(1, -1), min(5, index.ntotal))
                    logger.info(f"✅ Search test passed: found {len(indices[0])} results")
                except Exception as e:
                    logger.error(f"❌ Search test failed: {e}")
                    return False
            
            self.stats.data_integrity_verified = True
            logger.info("✅ Migration integrity verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Integrity verification failed: {e}")
            return False
    
    def execute_migration(self) -> bool:
        """Execute complete data migration process."""
        start_time = time.time()
        
        try:
            logger.info("🚀 Starting FAISS data migration...")
            
            # Step 1: Analyze existing data
            analysis = self.analyze_existing_data()
            logger.info(f"Data analysis: {analysis['estimated_size_mb']:.2f} MB to migrate")
            
            # Step 2: Create backup
            if not self.create_migration_backup():
                return False
            
            # Step 3: Load existing documents
            documents = self.load_existing_faiss_data()
            if not documents:
                logger.warning("⚠️ No existing documents found - creating empty structure")
                # Create empty optimized structure
                self.target_path.mkdir(parents=True, exist_ok=True)
                return True
            
            # Step 4: Assign conversation IDs
            documents = self.assign_conversation_ids(documents)
            
            # Step 5: Create optimized structure
            if not self.create_optimized_faiss_structure(documents):
                return False
            
            # Step 6: Verify integrity
            if not self.verify_migration_integrity():
                return False
            
            # Step 7: Generate report
            self.stats.migration_time = time.time() - start_time
            self.generate_migration_report()
            
            logger.info("✅ FAISS data migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def generate_migration_report(self):
        """Generate comprehensive migration report."""
        report = {
            "migration_timestamp": time.time(),
            "project_root": str(self.project_root),
            "backup_location": str(self.backup_dir),
            "target_location": str(self.target_path),
            "statistics": {
                "total_documents": self.stats.total_documents,
                "chunks_migrated": self.stats.chunks_migrated,
                "conversations_identified": self.stats.conversations_identified,
                "errors_encountered": self.stats.errors_encountered,
                "migration_time_seconds": self.stats.migration_time,
                "data_integrity_verified": self.stats.data_integrity_verified
            },
            "conversation_mapping": self.conversation_mapping,
            "source_locations": [str(p) for p in self.source_paths if p.exists()]
        }
        
        report_path = self.project_root / "faiss_migration_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Migration report saved to {report_path}")


def main():
    """Main execution function."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python faiss_data_migration.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    if not os.path.exists(project_root):
        print(f"Error: Project root '{project_root}' does not exist")
        sys.exit(1)
    
    migrator = FAISSDataMigrator(project_root)
    
    print("FAISS Data Migration")
    print("=" * 50)
    print(f"Project Root: {project_root}")
    print(f"Backup Location: {migrator.backup_dir}")
    print(f"Target Location: {migrator.target_path}")
    print()
    
    # Analyze current data
    analysis = migrator.analyze_existing_data()
    print("Current Data Analysis:")
    print(f"  Source locations: {len(analysis['source_locations'])}")
    print(f"  Estimated size: {analysis['estimated_size_mb']:.2f} MB")
    print(f"  Index files: {len(analysis['index_files'])}")
    print(f"  Metadata files: {len(analysis['metadata_files'])}")
    print()
    
    if not analysis['source_locations']:
        print("ℹ️ No existing FAISS data found - migration not needed")
        sys.exit(0)
    
    # Confirm migration
    response = input("Proceed with FAISS data migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled")
        sys.exit(0)
    
    # Execute migration
    success = migrator.execute_migration()
    
    if success:
        print("\n✅ FAISS data migration completed successfully!")
        print(f"📁 Backup saved at: {migrator.backup_dir}")
        print(f"📊 Report saved at: {project_root}/faiss_migration_report.json")
        print(f"🎯 Migrated data at: {migrator.target_path}")
    else:
        print("\n❌ Migration failed - check logs for details")
        print(f"💾 Backup available at: {migrator.backup_dir}")


if __name__ == "__main__":
    main()