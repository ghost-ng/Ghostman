import sqlite3

conn = sqlite3.connect('ghostman_conversations.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM conversations')
print(f'Total conversations: {cursor.fetchone()[0]}')
cursor.execute('SELECT id, title, status FROM conversations ORDER BY created_at DESC LIMIT 10')
rows = cursor.fetchall()
print('\nRecent conversations:')
for row in rows:
    print(f'  {row[0][:8]}... - {row[1]} - Status: {row[2]}')
conn.close()
