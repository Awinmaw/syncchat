import sqlite3

conn = sqlite3.connect("syncchat.db")

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE messages ADD COLUMN duration FLOAT;
""")

conn.commit()
conn.close()

print("media_url column added successfully")

# ALTER TABLE recent_chats
# ADD COLUMN cleared_message_id INTEGER DEFAULT 0;

# ALTER TABLE messages 
# ADD COLUMN public_seen INTEGER DEFAULT 0

# ALTER TABLE users ADD COLUMN last_seen DATETIME;