#!/usr/bin/env python3
"""
Debug script to check conversation files in the database.
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_conversation_files():
    """Check what files are stored in the conversation database."""
    
    # Find the database file
    db_paths = [
        Path.home() / "AppData" / "Roaming" / "Ghostman" / "db" / "conversations.db",
        project_root / "ghostman.db",
        Path.home() / "AppData" / "Roaming" / "Ghostman" / "ghostman.db",
        project_root / "data" / "ghostman.db"
    ]
    
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("❌ No database file found. Checked paths:")
        for path in db_paths:
            print(f"   - {path}")
        return
    
    print(f"📁 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tables in database: {tables}")
        
        if 'conversations' not in tables:
            print("❌ No conversations table found")
            return
        
        if 'conversation_files' not in tables:
            print("❌ No conversation_files table found")
            return
        
        # Check conversations
        cursor.execute("SELECT id, title, status, created_at FROM conversations ORDER BY created_at DESC LIMIT 10;")
        conversations = cursor.fetchall()
        print(f"\n📝 Recent conversations ({len(conversations)}):")
        for conv in conversations:
            print(f"   {conv[0][:8]}... | {conv[1]} | {conv[2]} | {conv[3]}")
        
        # Check conversation files
        cursor.execute("SELECT conversation_id, filename, file_id, processing_status, is_enabled, upload_timestamp FROM conversation_files ORDER BY upload_timestamp DESC LIMIT 20;")
        files = cursor.fetchall()
        print(f"\n📎 Files in database ({len(files)}):")
        if files:
            for file_info in files:
                conv_id_short = file_info[0][:8] if file_info[0] else "None"
                print(f"   {conv_id_short}... | {file_info[1]} | {file_info[2]} | {file_info[3]} | enabled={file_info[4]} | {file_info[5]}")
        else:
            print("   No files found in database!")
        
        # Check file counts per conversation
        cursor.execute("""
            SELECT c.id, c.title, COUNT(cf.id) as file_count
            FROM conversations c 
            LEFT JOIN conversation_files cf ON c.id = cf.conversation_id 
            WHERE cf.is_enabled = 1 
            GROUP BY c.id, c.title 
            HAVING file_count > 0
            ORDER BY file_count DESC;
        """)
        conv_file_counts = cursor.fetchall()
        print(f"\n📊 Conversations with files ({len(conv_file_counts)}):")
        for conv in conv_file_counts:
            conv_id_short = conv[0][:8] if conv[0] else "None"
            print(f"   {conv_id_short}... | {conv[1]} | {conv[2]} files")
        
        # Check for any files that might have wrong conversation_id
        cursor.execute("SELECT DISTINCT conversation_id FROM conversation_files;")
        file_conv_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT id FROM conversations;")
        existing_conv_ids = [row[0] for row in cursor.fetchall()]
        
        orphaned_files = [fid for fid in file_conv_ids if fid not in existing_conv_ids]
        if orphaned_files:
            print(f"\n⚠️ Found {len(orphaned_files)} orphaned files (conversation doesn't exist):")
            for orphan_id in orphaned_files[:5]:  # Show first 5
                print(f"   {orphan_id[:8]}...")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def check_current_conversation():
    """Check what the current conversation is set to."""
    try:
        from ghostman.src.infrastructure.settings import get_settings_manager
        settings = get_settings_manager()
        current_conv = settings.get("conversation.current_id")
        print(f"\n🎯 Current conversation ID: {current_conv}")
        
        if current_conv:
            # Check files for current conversation
            db_path = None
            db_paths = [
                Path.home() / "AppData" / "Roaming" / "Ghostman" / "db" / "conversations.db",
                project_root / "ghostman.db",
                Path.home() / "AppData" / "Roaming" / "Ghostman" / "ghostman.db",
                project_root / "data" / "ghostman.db"
            ]
            
            for path in db_paths:
                if path.exists():
                    db_path = path
                    break
            
            if db_path:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT filename, file_id, processing_status FROM conversation_files WHERE conversation_id = ? ORDER BY upload_timestamp DESC;", (current_conv,))
                files = cursor.fetchall()
                print(f"📎 Files for current conversation ({len(files)}):")
                for file_info in files:
                    print(f"   {file_info[0]} | {file_info[1]} | {file_info[2]}")
                conn.close()
        
    except Exception as e:
        print(f"❌ Error checking current conversation: {e}")

if __name__ == "__main__":
    print("🔍 CONVERSATION FILES DEBUG REPORT")
    print("=" * 50)
    check_conversation_files()
    check_current_conversation()
    print("\n✅ Debug complete")