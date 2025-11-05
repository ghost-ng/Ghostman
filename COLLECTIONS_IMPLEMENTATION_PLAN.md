# File Collections Manager - Implementation Plan

## Overview
Implement a file collections management system that allows users to create, manage, and reuse groups of files across multiple conversations. This enables better organization and faster context setup for recurring workflows.

## ⚠️ CRITICAL: Leverage Existing RAG Infrastructure

**Collections are a METADATA and UI layer only. DO NOT reimplement RAG pipeline.**

**Existing RAG Pipeline (`ghostman/src/infrastructure/rag_pipeline/`) already provides:**
- ✅ Document loading (`DocumentLoaderFactory`)
- ✅ Text chunking (`TextSplitterFactory`)
- ✅ Embedding generation (`EmbeddingService` with OpenAI API)
- ✅ Vector storage (`FaissClient` - FAISS only, no ChromaDB)
- ✅ Async batch ingestion (`RAGPipeline.ingest_documents()`)
- ✅ Query and retrieval
- ✅ Caching and rate limiting

**What Collections Add:**
1. **Database layer** - Track which files belong to which collections
2. **UI layer** - Manage collections visually
3. **Metadata tagging** - Tag embeddings with `collection_id` and `collection_name`
4. **Batch operations** - Load/unload all files in a collection at once
5. **Persistence** - Remember collection-conversation associations
6. **Import/Export** - Share collections as portable packages

**Collections DO NOT:**
- ❌ Create new embedding service
- ❌ Create new vector store
- ❌ Duplicate text processing
- ❌ Reimplement document loading
- ❌ Replace existing RAG pipeline

**Integration Strategy:**
Collections call `RAGPipeline.ingest_documents(file_paths, metadata_override={'collection_id': ...})` and the existing pipeline handles everything else.

---

## Feature Requirements (From ROADMAP.md #12)

1. Create named collections (e.g., "Project Docs", "Python Utils", "Research Papers")
2. Add/remove files from collections with drag-drop
3. Collection browser with search and filter
4. Attach entire collection to conversation with one click
5. Collection templates for common use cases
6. Import/export collections for sharing
7. Collection size limits and warnings
8. Per-collection RAG settings (chunk size, overlap)

---

## Architecture Design

### 1. Data Models

#### Collection Model
**Location:** `ghostman/src/domain/models/collection.py`

```python
@dataclass
class FileCollectionItem:
    """Individual file within a collection."""
    file_path: str  # Absolute path to file
    file_name: str  # Display name
    file_size: int  # Size in bytes
    file_type: str  # MIME type or extension
    added_at: datetime
    checksum: str  # MD5/SHA256 for integrity checking

@dataclass
class FileCollection:
    """A named collection of files for reusable context."""
    id: str  # UUID
    name: str  # User-defined name
    description: str  # Optional description
    files: List[FileCollectionItem]
    created_at: datetime
    updated_at: datetime
    tags: List[str]  # For categorization

    # RAG settings per collection
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Metadata
    total_size: int  # Computed property
    file_count: int  # Computed property

    # Settings
    is_template: bool = False  # Template collections
    max_size_mb: int = 500  # Size limit
```

#### Database Schema
**Location:** Add migration in `ghostman/src/infrastructure/conversation_management/migrations/`

```sql
-- collections table
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    chunk_size INTEGER DEFAULT 1000,
    chunk_overlap INTEGER DEFAULT 200,
    is_template BOOLEAN DEFAULT FALSE,
    max_size_mb INTEGER DEFAULT 500
);

-- collection_files table
CREATE TABLE collection_files (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_type TEXT,
    added_at TIMESTAMP NOT NULL,
    checksum TEXT NOT NULL,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);

-- collection_tags table
CREATE TABLE collection_tags (
    collection_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (collection_id, tag),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);

-- conversation_collections table (many-to-many)
CREATE TABLE conversation_collections (
    conversation_id TEXT NOT NULL,
    collection_id TEXT NOT NULL,
    attached_at TIMESTAMP NOT NULL,
    PRIMARY KEY (conversation_id, collection_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
```

---

### 2. Storage Layer

#### Collection Repository
**Location:** `ghostman/src/infrastructure/conversation_management/repositories/collection_repository.py`

**Methods:**
- `create_collection(name, description, tags) -> FileCollection`
- `get_collection(collection_id) -> FileCollection`
- `list_collections(limit, offset, filter_tags) -> List[FileCollection]`
- `update_collection(collection_id, **kwargs) -> FileCollection`
- `delete_collection(collection_id) -> bool`
- `add_file_to_collection(collection_id, file_path) -> FileCollectionItem`
- `remove_file_from_collection(collection_id, file_item_id) -> bool`
- `get_collection_files(collection_id) -> List[FileCollectionItem]`
- `search_collections(query) -> List[FileCollection]`
- `attach_collection_to_conversation(conversation_id, collection_id) -> bool`
- `detach_collection_from_conversation(conversation_id, collection_id) -> bool`
- `get_conversation_collections(conversation_id) -> List[FileCollection]`

#### Collection Storage Service
**Location:** `ghostman/src/infrastructure/storage/collection_storage.py`

**Responsibilities:**
- File integrity verification (checksums)
- Collection size validation
- File path resolution (absolute/relative)
- Import/export collection manifests (JSON format)
- Template collection management

---

### 3. Application Layer

#### Collection Service
**Location:** `ghostman/src/application/collection_service.py`

**Methods:**
- `create_collection_with_files(name, description, file_paths) -> FileCollection`
- `validate_collection_size(files) -> Tuple[bool, str]`
- `process_collection_files(collection_id) -> List[FileCollectionItem]`
- `export_collection(collection_id, output_path) -> str`
- `import_collection(import_path) -> FileCollection`
- `duplicate_collection(collection_id, new_name) -> FileCollection`
- `get_collection_stats(collection_id) -> dict`

#### Collection Templates
**Location:** `ghostman/src/application/collection_templates.py`

**Built-in Templates:**
1. **Python Project** - Common Python files (.py, requirements.txt, README.md)
2. **JavaScript Project** - package.json, .js/.ts files, README.md
3. **Documentation Set** - .md, .pdf, .txt files
4. **Research Papers** - .pdf, .docx, citation files
5. **Code Review** - Source code files with specific patterns

---

### 4. Presentation Layer

#### Collections Manager Dialog
**Location:** `ghostman/src/presentation/dialogs/collections_manager_dialog.py`

**UI Components:**

```
┌─────────────────────────────────────────────────────────────┐
│ File Collections Manager                          [✕]       │
├─────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌──────────────────────────────────────────┐│
│ │ Collections│ │ Collection: "Python Utils"               ││
│ ├────────────┤ │                                          ││
│ │ [+ New]    │ │ Description: Common Python utilities     ││
│ │ [📁 Import]│ │ Files: 12 | Size: 45.2 MB               ││
│ │            │ │                                          ││
│ │ 📚 Python  │ │ ┌──────────────────────────────────────┐││
│ │   Utils    │ │ │ [🔍 Search] [🏷️ Tags] [⚙️ Settings]│││
│ │ 📄 Research│ │ └──────────────────────────────────────┘││
│ │   Papers   │ │                                          ││
│ │ 💻 JS Libs │ │ Files:                                   ││
│ │            │ │ ☑ utils.py          12 KB  [Remove]     ││
│ │ Templates: │ │ ☑ helpers.py        8 KB   [Remove]     ││
│ │ ⭐ Python  │ │ ☑ config.py         5 KB   [Remove]     ││
│ │   Project  │ │ ☐ (disabled file)   3 KB   [Remove]     ││
│ │ ⭐ Docs Set│ │                                          ││
│ │            │ │ [+ Add Files] [+ Add Folder]            ││
│ └────────────┘ │ [Attach to Conversation] [Export]       ││
│                │ [Delete Collection]                      ││
│                └──────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                                       [Close] [Save]        │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Collection list (left panel) with search/filter
- Collection details (right panel) with file list
- Drag-drop files into collection
- Checkboxes to enable/disable files
- Tags for organization
- Size warnings when approaching limits
- Template collections clearly marked

#### Collection Quick-Attach Widget
**Location:** `ghostman/src/presentation/widgets/collection_attach_widget.py`

**UI (Dropdown in REPL):**
```
┌────────────────────────────┐
│ 📚 Collections ▼          │
├────────────────────────────┤
│ ☐ Python Utils (12 files) │
│ ☐ Research Papers (8 pdfs)│
│ ☑ Project Docs (15 files) │ ← Currently attached
│ ─────────────────────────  │
│ [Manage Collections...]    │
└────────────────────────────┘
```

**Integration:**
- Add to file browser bar OR toolbar
- Quick checkbox to attach/detach collections
- Shows attached collections with count
- Click item to toggle attachment
- "Manage Collections" opens full dialog

---

### 5. RAG Integration

#### IMPORTANT: Leverage Existing RAG Pipeline
**The existing RAG pipeline (`rag_pipeline.py`) already handles:**
- ✅ Document loading via `DocumentLoaderFactory`
- ✅ Text chunking via `TextSplitterFactory`
- ✅ Embedding generation via `EmbeddingService`
- ✅ Vector storage via `FaissClient` (FAISS-only, no ChromaDB)
- ✅ Query processing and retrieval
- ✅ Async document ingestion with `ingest_document()` and `ingest_documents()`

**Collections should NOT duplicate this infrastructure. Instead:**

#### Collection RAG Integration Strategy
**Location:** `ghostman/src/infrastructure/rag_pipeline/collection_rag_handler.py`

**Core Principle:** Collections are a **metadata layer** on top of existing RAG pipeline.

**Responsibilities:**
1. **Coordinate** collection file ingestion using existing `RAGPipeline.ingest_documents()`
2. **Tag** embedded chunks with collection metadata (collection_id, collection_name)
3. **Track** which files belong to which collections in vector store metadata
4. **Filter** retrieval results by collection when needed
5. **Manage** conversation-collection associations

**Key Methods:**
```python
class CollectionRAGHandler:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline  # Reuse existing pipeline!
        self.collection_repo = CollectionRepository()

    async def load_collection_into_rag(
        self,
        collection_id: str,
        conversation_id: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> bool:
        """
        Load collection files into RAG using existing pipeline.

        Strategy:
        1. Get collection files from repository
        2. Add collection metadata to each file
        3. Use RAGPipeline.ingest_documents() with metadata override
        4. Track ingestion in conversation_collections table
        """
        collection = self.collection_repo.get_collection(collection_id)

        # Prepare metadata for each file
        file_paths = [f.file_path for f in collection.files]
        metadata_overrides = {
            'collection_id': collection_id,
            'collection_name': collection.name,
            'conversation_id': conversation_id
        }

        # Override chunk settings if collection specifies custom ones
        if chunk_size or collection.chunk_size != 1000:
            # Temporarily override config for this ingestion
            # (existing pipeline supports this via config parameter)
            pass

        # Use existing pipeline to ingest files
        doc_ids = await self.rag_pipeline.ingest_documents(
            sources=file_paths,
            metadata_override=metadata_overrides
        )

        # Track in database
        self.collection_repo.attach_collection_to_conversation(
            conversation_id,
            collection_id
        )

        return all(doc_id is not None for doc_id in doc_ids)

    async def unload_collection_from_rag(
        self,
        collection_id: str,
        conversation_id: str
    ) -> bool:
        """
        Remove collection files from RAG context.

        Strategy:
        1. Query vector store for all docs with collection_id metadata
        2. Use vector_store.delete() to remove those embeddings
        3. Update conversation_collections table
        """
        # Detach from database
        self.collection_repo.detach_collection_from_conversation(
            conversation_id,
            collection_id
        )

        # Note: Actual deletion from vector store depends on
        # whether other conversations are using this collection
        # For now, keep embeddings and just filter by conversation_id

        return True

    def filter_results_by_collections(
        self,
        results: List[SearchResult],
        collection_ids: List[str]
    ) -> List[SearchResult]:
        """Filter retrieval results to only include specific collections."""
        return [
            r for r in results
            if r.metadata.get('collection_id') in collection_ids
        ]
```

**Integration Points:**
1. **No new embedding service** - Use existing `EmbeddingService`
2. **No new vector store** - Use existing `FaissClient`
3. **No new text splitter** - Use existing `TextSplitterFactory`
4. **No new document loader** - Use existing `DocumentLoaderFactory`

**What Collections Add:**
- Metadata tagging (collection_id, collection_name)
- Batch operations (load/unload all files in collection)
- Persistence (track which collections attached to which conversations)
- UI layer (manage groups of files)

---

### 6. Import/Export Format

#### Collection Manifest (JSON)
```json
{
  "version": "1.0",
  "collection": {
    "name": "Python Utils",
    "description": "Common Python utilities and helpers",
    "tags": ["python", "utilities", "helpers"],
    "created_at": "2025-01-15T10:30:00Z",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "is_template": false,
    "max_size_mb": 500
  },
  "files": [
    {
      "file_name": "utils.py",
      "relative_path": "src/utils.py",
      "file_size": 12288,
      "file_type": "text/x-python",
      "checksum": "a1b2c3d4e5f6...",
      "added_at": "2025-01-15T10:35:00Z"
    }
  ]
}
```

**Export Package Structure:**
```
collection_export_python_utils_20250115/
├── manifest.json
└── files/
    ├── utils.py
    ├── helpers.py
    └── config.py
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Core data models and storage layer

1. Create domain models (`collection.py`)
2. Create database migration for collections tables
3. Implement `CollectionRepository` with CRUD operations
4. Write unit tests for repository
5. Implement `CollectionStorageService` for file validation

**Deliverables:**
- Collections can be created/updated/deleted in database
- Files can be added/removed from collections
- Basic validation (size limits, file existence)

---

### Phase 2: Application Services (Week 2)
**Goal:** Business logic and collection templates

1. Implement `CollectionService` with validation logic
2. Create built-in collection templates
3. Implement import/export functionality (JSON manifest)
4. Add checksum verification for file integrity
5. Write integration tests

**Deliverables:**
- Collections can be exported as portable packages
- Collections can be imported from packages
- Template collections available for quick start
- Size validation and warnings

---

### Phase 3: UI - Collections Manager (Week 3)
**Goal:** Full-featured collections management dialog

1. Create `CollectionsManagerDialog` with split layout
2. Implement collection list with search/filter
3. Implement file list with add/remove/drag-drop
4. Add tags UI and filtering
5. Add RAG settings UI (chunk size/overlap)
6. Implement delete confirmation dialogs

**Deliverables:**
- Users can create and manage collections via UI
- Drag-drop files into collections
- Search and filter collections
- Visual size warnings

---

### Phase 4: UI - Quick Attach Integration (Week 4)
**Goal:** Seamless conversation integration

1. Create `CollectionAttachWidget` dropdown
2. Integrate widget into REPL widget toolbar
3. Implement attach/detach functionality
4. Show attached collections in file browser bar
5. Add collection badges with file counts

**Deliverables:**
- Collections can be attached to conversations with one click
- Attached collections visible in UI
- Collections persist across app restarts

---

### Phase 5: RAG Integration (Week 5)
**Goal:** Collections work with existing RAG pipeline

1. Implement `CollectionRAGHandler` (thin wrapper around existing `RAGPipeline`)
2. Add metadata tagging (collection_id, collection_name) to ingestion calls
3. Implement `load_collection_into_rag()` using `RAGPipeline.ingest_documents()`
4. Implement `unload_collection_from_rag()` using vector store metadata filtering
5. Add collection filtering to search results
6. Track collection-conversation associations in database

**Deliverables:**
- Attached collections automatically included in RAG context
- Embeddings tagged with collection metadata
- Source attribution shows collection name
- **NO new embedding service or vector store** - leverage existing infrastructure

---

### Phase 6: Advanced Features (Week 6)
**Goal:** Polish and power-user features

1. Implement collection duplication
2. Add collection statistics dashboard
3. Implement batch operations (attach multiple collections)
4. Add keyboard shortcuts (Ctrl+Shift+C for collections manager)
5. Implement collection auto-sync (watch for file changes)
6. Add collection sharing via URL/link

**Deliverables:**
- Power-user workflows enabled
- Collection statistics and insights
- File change detection and auto-reload

---

## File Structure

```
ghostman/
├── src/
│   ├── domain/
│   │   └── models/
│   │       └── collection.py                    # NEW
│   │
│   ├── application/
│   │   ├── collection_service.py                # NEW
│   │   └── collection_templates.py              # NEW
│   │
│   ├── infrastructure/
│   │   ├── conversation_management/
│   │   │   ├── migrations/
│   │   │   │   └── versions/
│   │   │   │       └── add_collections_tables.py  # NEW
│   │   │   └── repositories/
│   │   │       └── collection_repository.py     # NEW
│   │   │
│   │   ├── storage/
│   │   │   └── collection_storage.py            # NEW
│   │   │
│   │   └── rag_pipeline/
│   │       └── collection_rag_handler.py        # NEW
│   │
│   └── presentation/
│       ├── dialogs/
│       │   └── collections_manager_dialog.py    # NEW
│       │
│       └── widgets/
│           └── collection_attach_widget.py      # NEW
│
└── tests/
    ├── unit/
    │   ├── test_collection_repository.py        # NEW
    │   └── test_collection_service.py           # NEW
    │
    └── integration/
        └── test_collection_rag_integration.py   # NEW
```

---

## User Workflows

### Workflow 1: Create Collection from Scratch
1. User clicks "📚 Collections" → "Manage Collections"
2. Clicks "+ New Collection"
3. Enters name "Python Utils" and description
4. Adds tags: "python", "utilities"
5. Clicks "+ Add Files" and selects 12 Python files
6. Adjusts chunk size to 800 (optional)
7. Clicks "Save"
8. Collection appears in list

### Workflow 2: Use Template Collection
1. User clicks "+ New Collection"
2. Selects "Template: Python Project" from dropdown
3. System auto-populates with common Python file patterns
4. User adds their project directory
5. System automatically finds matching files
6. User reviews and saves

### Workflow 3: Attach Collection to Conversation
1. User opens conversation
2. Clicks "📚 Collections" dropdown in toolbar
3. Checks "Python Utils" collection
4. Collection badge appears showing "12 files attached"
5. Files automatically loaded into RAG
6. User queries: "What's in utils.py?"
7. AI responds with context from collection

### Workflow 4: Export Collection for Sharing
1. User opens Collections Manager
2. Selects "Python Utils" collection
3. Clicks "Export" button
4. Chooses output directory
5. System creates `collection_export_python_utils.zip`
6. Zip contains manifest.json + all files
7. User shares zip with colleague

### Workflow 5: Import Shared Collection
1. Colleague receives zip file
2. Opens Collections Manager
3. Clicks "📁 Import" button
4. Selects zip file
5. System validates manifest and files
6. Shows preview: "12 files, 45.2 MB, tags: python, utilities"
7. User confirms import
8. Collection available immediately

---

## Technical Considerations

### 1. File Path Handling
- **Absolute Paths:** Store absolute paths in database
- **Relative Paths:** Use relative paths in export manifests
- **Path Resolution:** On import, resolve paths relative to user's system
- **Missing Files:** Show warnings for missing/moved files
- **Symbolic Links:** Follow symlinks or store actual paths?

### 2. Performance Optimization
- **Lazy Loading:** Load file contents only when attached to conversation
- **Caching:** Cache collection metadata in memory
- **Async Processing:** Load large collections asynchronously
- **Progress Indicators:** Show progress when loading 100+ files
- **Batch Operations:** Use SQLAlchemy bulk operations

### 3. Data Integrity
- **Checksums:** Verify file integrity on load
- **File Watchers:** Optional file system watching for changes
- **Conflict Resolution:** Handle file modifications/deletions
- **Versioning:** Track collection versions for imports

### 4. Size Limits
- **Per-Collection Limit:** Default 500 MB (configurable)
- **Per-File Limit:** Inherit from existing file upload limit (50 MB)
- **Total Limit:** Warn when total collections exceed 5 GB
- **Warnings:** Show visual warnings at 80%, 90%, 100%

### 5. RAG Integration with Existing Pipeline
- **Vector Store Strategy:**
  - ✅ **Use existing FAISS vector store** (already implemented)
  - ✅ **No separate stores per collection** (inefficient, unnecessary)
  - ✅ **Tag embeddings with collection metadata** in existing store
  - ✅ **Filter by metadata** during retrieval
- **Embedding Reuse:**
  - If same file exists in multiple collections, **reuse existing embeddings**
  - Check file checksum to detect identical files
  - Only re-embed if file content changed
  - Saves API calls and processing time
- **Context Merging:**
  - When multiple collections attached, **merge retrieval results** from all
  - Deduplicate by document chunk ID
  - Preserve source attribution (collection_id in metadata)
- **Source Attribution:**
  - Track which collection provided which chunks via metadata
  - Display in UI: "Source: Python Utils collection / utils.py"
- **Chunk Settings:**
  - Per-collection chunk size/overlap **requires creating new RAGPipeline config**
  - Alternative: Store custom chunks separately with collection_id tag
  - Recommendation: Use global chunk settings for MVP, custom per-collection in Phase 6
- **Existing Infrastructure to Leverage:**
  - `RAGPipeline.ingest_documents()` - Batch file ingestion
  - `EmbeddingService` - Already handles caching, rate limiting
  - `FaissClient` - FAISS vector store with metadata support
  - `DocumentLoaderFactory` - Supports all file types
  - `TextSplitterFactory` - Configurable chunking

---

## Testing Strategy

### Unit Tests
- `test_collection_repository.py`: CRUD operations
- `test_collection_service.py`: Business logic, validation
- `test_collection_storage.py`: File handling, checksums
- `test_collection_templates.py`: Template creation

### Integration Tests
- `test_collection_rag_integration.py`: RAG pipeline integration
- `test_collection_import_export.py`: Import/export workflows
- `test_collection_conversation_integration.py`: Attach/detach workflows

### UI Tests (Manual)
- Collections Manager dialog interactions
- Drag-drop file uploads
- Collection attachment/detachment
- Search and filter functionality
- Size limit warnings

---

## Migration Strategy

### Database Migration
```python
# migrations/versions/add_collections_tables.py
def upgrade():
    # Create collections table
    op.create_table('collections', ...)

    # Create collection_files table
    op.create_table('collection_files', ...)

    # Create collection_tags table
    op.create_table('collection_tags', ...)

    # Create conversation_collections table
    op.create_table('conversation_collections', ...)

def downgrade():
    # Drop tables in reverse order
    op.drop_table('conversation_collections')
    op.drop_table('collection_tags')
    op.drop_table('collection_files')
    op.drop_table('collections')
```

### Settings Migration
Add to `DEFAULT_SETTINGS`:
```python
'collections': {
    'max_size_mb_per_collection': 500,
    'max_total_size_gb': 5,
    'enable_file_watching': False,
    'auto_load_on_attach': True,
    'show_collection_badges': True
}
```

---

## Success Criteria

### Minimum Viable Product (MVP)
- ✅ Users can create named collections
- ✅ Users can add/remove files from collections
- ✅ Users can attach collections to conversations
- ✅ Attached collections load into RAG automatically
- ✅ Collections persist across app restarts
- ✅ Basic import/export functionality works

### Full Feature Set
- ✅ Collections Manager UI with search/filter
- ✅ Quick-attach dropdown in conversation
- ✅ Template collections available
- ✅ Per-collection RAG settings
- ✅ Size limits and warnings
- ✅ Drag-drop file upload
- ✅ Collection statistics
- ✅ Keyboard shortcuts

### Polish & Performance
- ✅ Smooth UI with no lag on large collections
- ✅ Clear error messages and validation feedback
- ✅ Help documentation updated
- ✅ Unit test coverage >80%
- ✅ Integration tests for critical paths

---

## Risks & Mitigations

### Risk 1: Large Collections Performance
**Impact:** Loading 1000+ files could freeze UI
**Mitigation:**
- Implement async loading with progress bar
- Use pagination in file list (100 files per page)
- Lazy-load file contents only when needed
- Cache collection metadata

### Risk 2: File Path Portability
**Impact:** Exported collections may not work on different machines
**Mitigation:**
- Use relative paths in exports
- Provide path mapping dialog on import
- Validate all paths before loading
- Clear error messages for missing files

### Risk 3: RAG Context Pollution
**Impact:** Too many collections could dilute RAG quality
**Mitigation:**
- Limit to 5 collections per conversation (configurable)
- Show warning when approaching limit
- Allow users to prioritize collections
- Implement collection-specific retrieval filtering

### Risk 4: Database Migration Complexity
**Impact:** Complex schema could cause migration failures
**Mitigation:**
- Thorough testing on test database first
- Backup mechanism before migration
- Rollback capability (downgrade function)
- Clear migration logs

---

## Future Enhancements (Post-MVP)

1. **Smart Collections:** Auto-create collections based on file patterns
2. **Collection Sharing:** Share collections via cloud links
3. **Collection Versioning:** Track collection history
4. **Collection Merging:** Combine multiple collections
5. **File Deduplication:** Detect and handle duplicate files
6. **Collection Analytics:** Usage statistics, most-queried files
7. **Integration with Git:** Sync collections with Git repositories
8. **Cloud Backup:** Auto-backup collections to cloud storage
9. **Collaborative Collections:** Multi-user collection editing
10. **AI-Powered Suggestions:** Suggest relevant collections based on conversation

---

## Documentation Updates

### User-Facing
- Add "File Collections" section to help HTML
- Create video tutorial for collection workflows
- Update README with collections examples

### Developer-Facing
- Update CLAUDE.md with collections architecture
- Add collections to technical documentation
- Create API documentation for collection services

---

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | Week 1 | Data models, database, repository |
| Phase 2: Services | Week 2 | Business logic, import/export, templates |
| Phase 3: Collections Manager UI | Week 3 | Full management dialog |
| Phase 4: Quick Attach UI | Week 4 | Conversation integration |
| Phase 5: RAG Integration | Week 5 | Collections work with RAG |
| Phase 6: Advanced Features | Week 6 | Polish, statistics, shortcuts |
| **Total** | **6 weeks** | **Full feature set** |

---

## Open Questions

1. Should collections be conversation-specific or global (app-wide)?
   - **Recommendation:** Global collections, attachable to any conversation

2. How to handle file updates after collection creation?
   - **Recommendation:** Optional file watching + manual refresh button

3. Should we support nested collections (collections within collections)?
   - **Recommendation:** No for MVP, consider for future

4. What happens to conversations when a collection is deleted?
   - **Recommendation:** Detach automatically, show warning

5. Should collections support remote files (URLs, cloud storage)?
   - **Recommendation:** No for MVP, local files only

6. How to handle very large files (>50MB) in collections?
   - **Recommendation:** Respect existing file size limits, show error

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building the File Collections Manager feature. The phased approach allows for incremental development and testing, with each phase delivering tangible value. The MVP (Phases 1-4) can be completed in 4 weeks, with advanced features following in Phases 5-6.

The design prioritizes:
- **User Experience:** Intuitive UI with drag-drop, quick access
- **Performance:** Async loading, caching, lazy evaluation
- **Reliability:** Checksums, validation, error handling
- **Extensibility:** Template system, import/export, future enhancements
- **⭐ Architecture:** Leverage existing RAG infrastructure, avoid duplication

## Key Architectural Decision: Reuse Existing RAG Pipeline

**Problem:** How should collections integrate with the RAG (Retrieval-Augmented Generation) system?

**Solution:** Collections are a **metadata and organizational layer** on top of the existing RAG pipeline.

**Rationale:**
1. **Existing Pipeline is Complete:** `RAGPipeline` already handles document loading, chunking, embedding, and vector storage via FAISS
2. **Avoid Duplication:** No need for separate embedding services or vector stores
3. **Maintain Consistency:** All files use the same embedding model and chunking strategy
4. **Improve Efficiency:** Reuse embeddings for files that appear in multiple collections
5. **Simplify Code:** CollectionRAGHandler is a thin coordination layer, not a reimplementation

**Implementation:**
```python
# Collections just coordinate - don't duplicate
class CollectionRAGHandler:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline  # ✅ Reuse existing

    async def load_collection(self, collection_id: str):
        # Get files from database
        files = self.repo.get_collection_files(collection_id)

        # Use existing pipeline with metadata tagging
        await self.rag_pipeline.ingest_documents(
            sources=[f.file_path for f in files],
            metadata_override={'collection_id': collection_id}  # ✅ Tag only
        )
```

**Benefits:**
- ✅ Faster development (no RAG reimplementation)
- ✅ Lower maintenance burden (one pipeline to maintain)
- ✅ Better resource usage (shared embeddings cache)
- ✅ Consistent behavior across all file uploads
- ✅ Easier testing (leverage existing RAG tests)

**Next Steps:**
1. Review this plan with stakeholders
2. Validate RAG integration approach with existing codebase
3. Create detailed UI mockups
4. Set up development branch (collections) ✅ DONE
5. Begin Phase 1 implementation
