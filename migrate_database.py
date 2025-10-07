"""
Migration script to create chat_metadata table and migrate existing chats
Run this once to upgrade your database
"""

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

def migrate_database():
    print("🔄 Starting database migration...")
    
    # Connect to database
    conn = sqlite3.connect('chatbot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Create chat_metadata table
    print("📋 Creating chat_metadata table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_metadata (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if there are existing threads to migrate
    checkpointer = SqliteSaver(conn=conn)
    all_threads = set()
    
    print("🔍 Scanning for existing threads...")
    for checkpoint in checkpointer.list(None):
        thread_id = checkpoint.config['configurable']['thread_id']
        all_threads.add(thread_id)
    
    print(f"📊 Found {len(all_threads)} existing threads")
    
    if all_threads:
        print("⚠️  IMPORTANT: Existing chats will be assigned to a default 'legacy' user")
        print("   They will NOT be visible in new user sessions")
        
        response = input("Do you want to proceed? (yes/no): ")
        
        if response.lower() == 'yes':
            legacy_user_id = "legacy-user-00000000"
            
            for thread_id in all_threads:
                # Create a generic summary for old chats
                summary = f"Chat {str(thread_id)[:8]}..."
                
                # Insert into metadata table
                cursor.execute('''
                    INSERT OR IGNORE INTO chat_metadata (thread_id, user_id, summary)
                    VALUES (?, ?, ?)
                ''', (thread_id, legacy_user_id, summary))
            
            conn.commit()
            print(f"✅ Migrated {len(all_threads)} threads to legacy user")
            print(f"   Legacy User ID: {legacy_user_id}")
        else:
            print("❌ Migration cancelled")
    else:
        print("✨ No existing threads found. Database is ready!")
    
    conn.close()
    print("✅ Migration complete!")

if __name__ == "__main__":
    migrate_database()