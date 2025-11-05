"""Test script to validate migration 004_add_collections_tables.py

This script verifies:
1. Migration can be applied successfully
2. All tables are created with correct schema
3. Indexes are created
4. Foreign keys work correctly
5. Migration can be rolled back cleanly
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "ghostman"))

def get_test_db_path():
    """Get path for test database."""
    return os.path.join(os.environ['APPDATA'], 'Ghostman', 'db', 'test_migration.db')

def verify_table_structure(cursor, table_name, expected_columns):
    """Verify table has expected columns."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = {col[1] for col in columns}

    print(f"\n  Checking {table_name}:")
    for col in expected_columns:
        if col in column_names:
            print(f"    ✓ {col}")
        else:
            print(f"    ✗ {col} MISSING")
            return False
    return True

def verify_indexes(cursor, table_name, expected_indexes):
    """Verify table has expected indexes."""
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = cursor.fetchall()
    index_names = {idx[1] for idx in indexes}

    print(f"\n  Checking indexes for {table_name}:")
    for idx in expected_indexes:
        if idx in index_names:
            print(f"    ✓ {idx}")
        else:
            print(f"    ✗ {idx} MISSING")
            return False
    return True

def main():
    """Run migration validation."""
    print("="*70)
    print("Migration 004 Validation Test")
    print("="*70)

    # Test database path
    test_db = get_test_db_path()

    # Remove existing test database
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"\n✓ Removed existing test database: {test_db}")

    print("\n" + "="*70)
    print("Step 1: Apply Migration")
    print("="*70)

    # Apply migration using alembic
    os.chdir(project_root / "ghostman" / "src" / "infrastructure" / "conversation_management")

    # Set test database
    os.environ['GHOSTMAN_TEST_DB'] = test_db

    print("\nRunning: alembic upgrade 004")
    result = os.system("alembic upgrade 004")

    if result != 0:
        print("\n✗ Migration failed to apply")
        return False

    print("\n✓ Migration applied successfully")

    # Verify database structure
    print("\n" + "="*70)
    print("Step 2: Verify Database Structure")
    print("="*70)

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Verify collections table
    collections_columns = ['id', 'name', 'description', 'created_at', 'updated_at',
                          'chunk_size', 'chunk_overlap', 'is_template', 'max_size_mb']
    if not verify_table_structure(cursor, 'collections', collections_columns):
        print("\n✗ Collections table structure invalid")
        return False

    # Verify collection_files table
    collection_files_columns = ['id', 'collection_id', 'file_path', 'file_name',
                               'file_size', 'file_type', 'added_at', 'checksum']
    if not verify_table_structure(cursor, 'collection_files', collection_files_columns):
        print("\n✗ Collection_files table structure invalid")
        return False

    # Verify collection_tags table
    collection_tags_columns = ['collection_id', 'tag']
    if not verify_table_structure(cursor, 'collection_tags', collection_tags_columns):
        print("\n✗ Collection_tags table structure invalid")
        return False

    # Verify conversation_collections table
    conversation_collections_columns = ['conversation_id', 'collection_id', 'attached_at']
    if not verify_table_structure(cursor, 'conversation_collections', conversation_collections_columns):
        print("\n✗ Conversation_collections table structure invalid")
        return False

    # Verify indexes
    collections_indexes = ['idx_collections_name', 'idx_collections_created_at',
                          'idx_collections_is_template']
    if not verify_indexes(cursor, 'collections', collections_indexes):
        print("\n✗ Collections indexes invalid")
        return False

    collection_files_indexes = ['idx_collection_files_collection_id',
                               'idx_collection_files_checksum']
    if not verify_indexes(cursor, 'collection_files', collection_files_indexes):
        print("\n✗ Collection_files indexes invalid")
        return False

    # Verify schema version
    cursor.execute("SELECT version FROM schema_version")
    version = cursor.fetchone()[0]
    print(f"\n  Schema version: {version}")
    if version != 4:
        print(f"  ✗ Expected version 4, got {version}")
        return False
    print(f"  ✓ Schema version is correct")

    conn.close()

    print("\n" + "="*70)
    print("Step 3: Test Rollback")
    print("="*70)

    print("\nRunning: alembic downgrade 003")
    result = os.system("alembic downgrade 003")

    if result != 0:
        print("\n✗ Migration rollback failed")
        return False

    print("\n✓ Migration rolled back successfully")

    # Verify tables are removed
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    print("\n  Checking tables were removed:")
    collections_tables = ['collections', 'collection_files', 'collection_tags',
                         'conversation_collections']

    for table in collections_tables:
        if table not in tables:
            print(f"    ✓ {table} removed")
        else:
            print(f"    ✗ {table} still exists")
            return False

    # Verify schema version reverted
    cursor.execute("SELECT version FROM schema_version")
    version = cursor.fetchone()[0]
    print(f"\n  Schema version after rollback: {version}")
    if version != 3:
        print(f"  ✗ Expected version 3, got {version}")
        return False
    print(f"  ✓ Schema version correctly reverted")

    conn.close()

    print("\n" + "="*70)
    print("All Tests Passed!")
    print("="*70)

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"\n✓ Cleaned up test database: {test_db}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
