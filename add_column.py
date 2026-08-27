import sqlite3

conn = sqlite3.connect("syncchat.db")

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE messages
ADD COLUMN reply_to_message_id INTEGER;
""")

conn.commit()
conn.close()

print("reply_to_message_id column added successfully")

# ALTER TABLE recent_chats
# ADD COLUMN cleared_message_id INTEGER DEFAULT 0;

# ALTER TABLE messages 
# ADD COLUMN public_seen INTEGER DEFAULT 0

# ALTER TABLE users ADD COLUMN last_seen DATETIME;