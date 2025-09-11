#!/usr/bin/env python3
"""
Clean up orphaned files from deleted conversations.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def cleanup_orphaned_files():
    """Clean up files from deleted conversations."""
    try:
        from ghostman.src.infrastructure.conversation_management.integration.conversation_manager import ConversationManager
        
        print("🧹 Starting Orphaned Files Cleanup")
        print("=" * 50)
        
        # Initialize conversation manager
        conversation_manager = ConversationManager()
        if not conversation_manager.initialize():
            print("❌ Failed to initialize conversation manager")
            return
        
        # Get active conversations
        conversations = await conversation_manager.list_conversations(limit=5, include_deleted=False)
        if not conversations:
            print("❌ No active conversations found")
            return
        
        print(f"📝 Found {len(conversations)} active conversations:")
        for conv in conversations:
            print(f"   {conv.id[:8]}... | {conv.title} | {conv.status.value}")
        
        # Use the first active conversation as target
        target_conv = conversations[0]
        print(f"\n🎯 Target conversation: {target_conv.title} ({target_conv.id[:8]}...)")
        
        # Reassign orphaned files
        conv_service = conversation_manager.conversation_service
        if conv_service:
            reassigned_count = await conv_service.reassign_orphaned_files_to_conversation(target_conv.id)
            
            if reassigned_count > 0:
                print(f"✅ Successfully reassigned {reassigned_count} orphaned files to '{target_conv.title}'")
                
                # Show files now in target conversation
                files = await conv_service.get_conversation_files(target_conv.id, enabled_only=False)
                print(f"\n📎 Files now in target conversation ({len(files)}):")
                for file_info in files:
                    status = file_info.get('processing_status', 'unknown')
                    enabled = file_info.get('is_enabled', False)
                    print(f"   {file_info['filename']} | {status} | enabled={enabled}")
            else:
                print("ℹ️ No orphaned files found to reassign")
        
        print("\n🎉 Cleanup completed!")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main cleanup function."""
    print("🔧 ORPHANED FILES CLEANUP UTILITY")
    print("This will move files from deleted conversations to active ones")
    print()
    
    asyncio.run(cleanup_orphaned_files())

if __name__ == "__main__":
    main()