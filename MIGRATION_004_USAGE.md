# Migration 004: File Collections Feature

## Overview

Migration 004 adds support for file collections in Ghostman, allowing users to create reusable sets of files that can be attached to multiple conversations for RAG context.

## Migration Details

**File:** `ghostman/src/infrastructure/conversation_management/migrations/versions/004_add_collections_tables.py`

**Revision ID:** 004
**Previous Revision:** 003
**Database:** SQLite (Windows AppData location)

## Tables Created

### 1. collections
Main table for storing file collection metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PRIMARY KEY | UUID identifier |
| name | String(200) | NOT NULL, UNIQUE | Collection name |
| description | Text | - | Optional description |
| created_at | DateTime | NOT NULL | Creation timestamp |
| updated_at | DateTime | NOT NULL | Last update timestamp |
| chunk_size | Integer | DEFAULT 1000 | RAG chunk size |
| chunk_overlap | Integer | DEFAULT 200 | RAG chunk overlap |
| is_template | Boolean | DEFAULT False | Template flag |
| max_size_mb | Integer | DEFAULT 500 | Max collection size |

**Indexes:**
- `idx_collections_name` on name
- `idx_collections_created_at` on created_at
- `idx_collections_is_template` on is_template

### 2. collection_files
Stores files within each collection.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PRIMARY KEY | UUID identifier |
| collection_id | String(36) | NOT NULL, FK | Reference to collections.id |
| file_path | String(1000) | NOT NULL | Original file path |
| file_name | String(500) | NOT NULL | File name |
| file_size | Integer | NOT NULL | File size in bytes |
| file_type | String(100) | - | MIME type or extension |
| added_at | DateTime | NOT NULL | When file was added |
| checksum | String(64) | NOT NULL | SHA256 hash |

**Foreign Keys:**
- collection_id → collections.id (CASCADE DELETE)

**Indexes:**
- `idx_collection_files_collection_id` on collection_id
- `idx_collection_files_checksum` on checksum

### 3. collection_tags
Tags for organizing collections.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| collection_id | String(36) | PRIMARY KEY (composite) | Reference to collections.id |
| tag | String(100) | PRIMARY KEY (composite) | Tag value |

**Foreign Keys:**
- collection_id → collections.id (CASCADE DELETE)

**Indexes:**
- `idx_collection_tags_collection_id` on collection_id

### 4. conversation_collections
Many-to-many relationship between conversations and collections.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| conversation_id | String(36) | PRIMARY KEY (composite) | Reference to conversations.id |
| collection_id | String(36) | PRIMARY KEY (composite) | Reference to collections.id |
| attached_at | DateTime | NOT NULL | When collection was attached |

**Foreign Keys:**
- conversation_id → conversations.id (CASCADE DELETE)
- collection_id → collections.id (CASCADE DELETE)

**Indexes:**
- `idx_conversation_collections_conversation` on conversation_id
- `idx_conversation_collections_collection` on collection_id

## Usage

### Apply Migration

```bash
cd ghostman/src/infrastructure/conversation_management
alembic upgrade head
```

This will upgrade the database to version 4, creating all four tables.

### Verify Migration Status

```bash
# Check current version
alembic current

# View migration history
alembic history

# Show detailed info
alembic show 004
```

### Rollback Migration

```bash
# Rollback to version 003
alembic downgrade 003

# Or rollback one step
alembic downgrade -1
```

## Database Location

The migration applies to the SQLite database at:
```
%APPDATA%\Ghostman\db\conversations.db
```

On Windows, this typically resolves to:
```
C:\Users\<username>\AppData\Roaming\Ghostman\db\conversations.db
```

## Schema Version

After applying this migration:
- Schema version in `schema_version` table: **4**
- Migration creates version 4
- Rollback reverts to version 3

## Data Relationships

```
collections (1) ──┬─→ (N) collection_files
                  ├─→ (N) collection_tags
                  └─→ (N) conversation_collections ←─ (N) conversations
```

**Key Relationships:**
1. One collection can have many files
2. One collection can have many tags
3. One collection can be attached to many conversations
4. One conversation can have many collections attached

**Cascade Deletes:**
- Deleting a collection removes all its files, tags, and conversation associations
- Deleting a conversation removes all its collection associations

## Migration Safety

**Safe Operations:**
- All table creations are atomic
- Foreign key constraints ensure referential integrity
- Indexes improve query performance
- CASCADE DELETE prevents orphaned records

**Rollback Safety:**
- Downgrade removes all tables and indexes cleanly
- Schema version correctly reverted
- No data loss for existing conversations (003 and earlier)

## Testing

A test script is available to validate the migration:

```bash
python test_migration_004.py
```

This script:
1. Creates a test database
2. Applies migration 004
3. Verifies all tables and indexes
4. Tests rollback to 003
5. Verifies cleanup

## Next Steps

After applying this migration, you can:

1. Create SQLAlchemy ORM models for the new tables
2. Implement repository classes for data access
3. Build UI components for collection management
4. Integrate with existing RAG pipeline
5. Add collection import/export functionality

## Notes

- All foreign keys use CASCADE DELETE for automatic cleanup
- Checksum field (SHA256) allows duplicate file detection
- is_template flag enables creating collection templates
- max_size_mb helps prevent oversized collections
- Composite primary keys on junction tables prevent duplicates
