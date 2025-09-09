"""
SQLite to ChromaDB Migration Tool

Migrates data from the existing SQLite-based file context system to the new ChromaDB-based RAG pipeline.
Preserves metadata and document relationships while upgrading to the vector storage system.
"""

import asyncio
import logging
import sqlite3
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from ..pipeline.rag_pipeline import RAGPipeline, get_rag_pipeline
from ..config.rag_config import RAGPipelineConfig
from ..document_loaders.base_loader import Document, DocumentMetadata

logger = logging.getLogger("ghostman.migrator")


@dataclass
class LegacyDocument:
    """Represents a document from the legacy SQLite system."""
    id: int
    source: str
    content: str
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


class SQLiteToChromaMigrator:
    """
    Migrates data from SQLite file context system to ChromaDB RAG pipeline.
    
    Features:
    - Data extraction from existing SQLite database
    - Metadata preservation and mapping
    - Batch processing for large datasets
    - Progress tracking and error handling
    - Validation and rollback capabilities
    """
    
    def __init__(self, sqlite_db_path: str, rag_pipeline: Optional[RAGPipeline] = None,
                 batch_size: int = 10, dry_run: bool = False):
        """
        Initialize migrator.
        
        Args:
            sqlite_db_path: Path to existing SQLite database
            rag_pipeline: RAG pipeline instance (creates one if not provided)
            batch_size: Number of documents to process per batch
            dry_run: If True, only analyze without migrating
        """
        self.sqlite_db_path = Path(sqlite_db_path)
        self.rag_pipeline = rag_pipeline or get_rag_pipeline()
        self.batch_size = batch_size
        self.dry_run = dry_run
        
        # Migration statistics
        self.stats = {
            'total_documents': 0,
            'migrated_documents': 0,
            'failed_documents': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        
        self.logger = logging.getLogger(f"{__name__}.SQLiteToChromaMigrator")
        
        if not self.sqlite_db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {sqlite_db_path}")
    
    def _connect_sqlite(self) -> sqlite3.Connection:
        """Connect to SQLite database."""
        conn = sqlite3.connect(str(self.sqlite_db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def analyze_legacy_data(self) -> Dict[str, Any]:
        """
        Analyze the legacy SQLite database structure and data.
        
        Returns:
            Analysis report
        """
        self.logger.info("Analyzing legacy SQLite database...")
        
        with self._connect_sqlite() as conn:
            cursor = conn.cursor()
            
            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            analysis = {
                'database_path': str(self.sqlite_db_path),
                'tables': tables,
                'table_info': {}
            }
            
            # Analyze each table
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [{'name': row[1], 'type': row[2]} for row in cursor.fetchall()]
                
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                
                analysis['table_info'][table] = {
                    'columns': columns,
                    'row_count': row_count
                }
            
            # Look for document-like tables
            document_tables = []
            for table in tables:
                columns = [col['name'].lower() for col in analysis['table_info'][table]['columns']]
                if any(field in columns for field in ['content', 'text', 'document']):
                    document_tables.append(table)
            
            analysis['document_tables'] = document_tables
            
            self.logger.info(f"Analysis complete: {len(tables)} tables, "
                           f"{len(document_tables)} potential document tables")
            
            return analysis
    
    def extract_legacy_documents(self, table_name: str = None) -> List[LegacyDocument]:
        """
        Extract documents from the legacy database.
        
        Args:
            table_name: Specific table to extract from (auto-detect if None)
            
        Returns:
            List of legacy documents
        """
        if table_name is None:
            analysis = self.analyze_legacy_data()
            if not analysis['document_tables']:
                raise ValueError("No document tables found in database")
            table_name = analysis['document_tables'][0]  # Use first document table
        
        self.logger.info(f"Extracting documents from table: {table_name}")
        
        documents = []
        
        with self._connect_sqlite() as conn:
            cursor = conn.cursor()
            
            # Get all rows from the table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    # Convert row to dictionary
                    row_dict = dict(row)
                    
                    # Extract common fields
                    doc_id = row_dict.get('id')
                    source = row_dict.get('source', row_dict.get('path', row_dict.get('filename', 'unknown')))
                    content = row_dict.get('content', row_dict.get('text', ''))
                    
                    # Extract timestamps
                    created_at = self._parse_timestamp(row_dict.get('created_at', row_dict.get('timestamp')))
                    modified_at = self._parse_timestamp(row_dict.get('modified_at', row_dict.get('updated_at')))
                    
                    # Build metadata from remaining fields
                    metadata = {}
                    for key, value in row_dict.items():
                        if key not in ['id', 'content', 'text', 'source', 'path', 'filename', 
                                     'created_at', 'modified_at', 'timestamp', 'updated_at']:
                            if value is not None:
                                metadata[key] = value
                    
                    document = LegacyDocument(
                        id=doc_id,
                        source=str(source),
                        content=str(content) if content else '',
                        metadata=metadata,
                        created_at=created_at,
                        modified_at=modified_at
                    )
                    
                    documents.append(document)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse row {row_dict.get('id', 'unknown')}: {e}")
        
        self.stats['total_documents'] = len(documents)
        self.logger.info(f"Extracted {len(documents)} documents from {table_name}")
        
        return documents
    
    def _parse_timestamp(self, timestamp_str: Any) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
        
        try:
            if isinstance(timestamp_str, (int, float)):
                return datetime.fromtimestamp(timestamp_str)
            
            timestamp_str = str(timestamp_str)
            
            # Try common timestamp formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _convert_legacy_to_document(self, legacy_doc: LegacyDocument) -> Document:
        """Convert legacy document to new Document format."""
        # Create document metadata
        metadata = DocumentMetadata(
            source=legacy_doc.source,
            source_type="file",  # Assume file for legacy documents
            created_at=legacy_doc.created_at,
            modified_at=legacy_doc.modified_at,
            custom={
                'legacy_id': legacy_doc.id,
                'migrated_at': datetime.now().isoformat(),
                **legacy_doc.metadata
            }
        )
        
        # Try to infer additional metadata from source path
        if legacy_doc.source:
            source_path = Path(legacy_doc.source)
            metadata.filename = source_path.name
            metadata.file_extension = source_path.suffix.lower()
            
            # Try to determine source type
            if source_path.suffix.lower() in ['.pdf']:
                metadata.custom['original_format'] = 'pdf'
            elif source_path.suffix.lower() in ['.txt', '.md']:
                metadata.custom['original_format'] = 'text'
            elif str(legacy_doc.source).startswith(('http://', 'https://')):
                metadata.source_type = 'url'
        
        return Document(content=legacy_doc.content, metadata=metadata)
    
    async def migrate_documents(self, table_name: str = None, 
                              validate_after: bool = True) -> Dict[str, Any]:
        """
        Migrate documents from SQLite to ChromaDB.
        
        Args:
            table_name: Table to migrate from (auto-detect if None)
            validate_after: Whether to validate migration results
            
        Returns:
            Migration results
        """
        self.stats['start_time'] = datetime.now()
        
        try:
            # Extract legacy documents
            legacy_documents = self.extract_legacy_documents(table_name)
            
            if self.dry_run:
                self.logger.info("DRY RUN: Would migrate {len(legacy_documents)} documents")
                return {
                    'dry_run': True,
                    'documents_to_migrate': len(legacy_documents),
                    'estimated_time': len(legacy_documents) * 0.5  # Rough estimate
                }
            
            # Process in batches
            migrated_docs = []
            failed_docs = []
            
            for i in range(0, len(legacy_documents), self.batch_size):
                batch = legacy_documents[i:i + self.batch_size]
                
                self.logger.info(f"Processing batch {i//self.batch_size + 1}: "
                               f"{len(batch)} documents")
                
                for legacy_doc in batch:
                    try:
                        # Convert to new format
                        document = self._convert_legacy_to_document(legacy_doc)
                        
                        # Ingest into RAG pipeline
                        doc_id = await self.rag_pipeline.ingest_document(
                            source=f"migrated:{legacy_doc.source}",
                            metadata_override=document.metadata.to_dict()
                        )
                        
                        migrated_docs.append({
                            'legacy_id': legacy_doc.id,
                            'new_id': doc_id,
                            'source': legacy_doc.source
                        })
                        
                        self.stats['migrated_documents'] += 1
                        
                    except Exception as e:
                        error_info = {
                            'legacy_id': legacy_doc.id,
                            'source': legacy_doc.source,
                            'error': str(e)
                        }
                        failed_docs.append(error_info)
                        self.stats['errors'].append(error_info)
                        self.stats['failed_documents'] += 1
                        
                        self.logger.error(f"Failed to migrate document {legacy_doc.id}: {e}")
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            self.stats['end_time'] = datetime.now()
            
            # Validation
            validation_results = None
            if validate_after and migrated_docs:
                validation_results = await self._validate_migration(migrated_docs[:5])  # Sample validation
            
            migration_results = {
                'success': True,
                'stats': self.stats,
                'migrated_documents': migrated_docs,
                'failed_documents': failed_docs,
                'validation': validation_results
            }
            
            self.logger.info(f"Migration completed: {self.stats['migrated_documents']} successful, "
                           f"{self.stats['failed_documents']} failed")
            
            return migration_results
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            self.stats['end_time'] = datetime.now()
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    async def _validate_migration(self, sample_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate migration by checking a sample of documents."""
        self.logger.info(f"Validating migration with {len(sample_docs)} sample documents")
        
        validation_results = {
            'total_checked': len(sample_docs),
            'successful_retrievals': 0,
            'failed_retrievals': 0,
            'errors': []
        }
        
        for doc_info in sample_docs:
            try:
                # Try to query the document using RAG pipeline
                query = f"content from {doc_info['source']}"
                response = await self.rag_pipeline.query(query)
                
                if response.sources:
                    validation_results['successful_retrievals'] += 1
                else:
                    validation_results['failed_retrievals'] += 1
                    validation_results['errors'].append({
                        'doc_id': doc_info['new_id'],
                        'error': 'No sources returned in query'
                    })
                    
            except Exception as e:
                validation_results['failed_retrievals'] += 1
                validation_results['errors'].append({
                    'doc_id': doc_info['new_id'],
                    'error': str(e)
                })
        
        self.logger.info(f"Validation complete: {validation_results['successful_retrievals']}"
                       f"/{validation_results['total_checked']} successful")
        
        return validation_results
    
    async def rollback_migration(self, migration_results: Dict[str, Any]) -> bool:
        """
        Rollback migration by deleting migrated documents.
        
        Args:
            migration_results: Results from migration
            
        Returns:
            True if rollback successful
        """
        if not migration_results.get('migrated_documents'):
            self.logger.info("No documents to rollback")
            return True
        
        self.logger.info(f"Rolling back {len(migration_results['migrated_documents'])} documents")
        
        try:
            rollback_count = 0
            for doc_info in migration_results['migrated_documents']:
                try:
                    success = await self.rag_pipeline.delete_document(doc_info['new_id'])
                    if success:
                        rollback_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to delete document {doc_info['new_id']}: {e}")
            
            self.logger.info(f"Rollback completed: {rollback_count} documents deleted")
            return rollback_count == len(migration_results['migrated_documents'])
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def generate_migration_report(self, migration_results: Dict[str, Any]) -> str:
        """Generate a human-readable migration report."""
        if migration_results.get('dry_run'):
            return f"""
Migration Analysis Report (Dry Run)
=====================================

Documents to migrate: {migration_results['documents_to_migrate']}
Estimated time: {migration_results.get('estimated_time', 0):.1f} seconds

This would migrate documents from SQLite to ChromaDB vector storage.
Run with dry_run=False to perform actual migration.
"""
        
        stats = migration_results.get('stats', {})
        start_time = stats.get('start_time')
        end_time = stats.get('end_time')
        duration = (end_time - start_time).total_seconds() if start_time and end_time else 0
        
        report = f"""
Migration Report
================

Database: {self.sqlite_db_path}
Started: {start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'}
Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'}
Duration: {duration:.1f} seconds

Results:
- Total documents: {stats.get('total_documents', 0)}
- Successfully migrated: {stats.get('migrated_documents', 0)}
- Failed: {stats.get('failed_documents', 0)}
- Success rate: {(stats.get('migrated_documents', 0) / max(stats.get('total_documents', 1), 1) * 100):.1f}%

"""
        
        # Add validation results
        if migration_results.get('validation'):
            validation = migration_results['validation']
            report += f"""
Validation Results:
- Documents checked: {validation['total_checked']}
- Successful retrievals: {validation['successful_retrievals']}
- Failed retrievals: {validation['failed_retrievals']}
"""
        
        # Add errors if any
        errors = stats.get('errors', [])
        if errors:
            report += f"\nErrors ({len(errors)}):\n"
            for i, error in enumerate(errors[:5]):  # Show first 5 errors
                report += f"- {error.get('source', 'unknown')}: {error.get('error', 'unknown error')}\n"
            if len(errors) > 5:
                report += f"... and {len(errors) - 5} more errors\n"
        
        return report