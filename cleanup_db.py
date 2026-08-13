import sqlite3

conn = sqlite3.connect("syncchat.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM users WHERE id=9")
conn.commit()

#cursor.execute("SELECT * FROM users WHERE id = 1")
#user = cursor.fetchone()
#print(user)

conn.close()

# SELECT * FROM users WHERE id = 1;
# DELETE FROM users WHERE id IN (1, 3, 5);
# DELETE FROM users WHERE username = 'john';
# DELETE FROM users WHERE id = 1;
# DELETE FROM messages

#DELETE FROM messages
#WHERE sender_id NOT IN (
#    SELECT id FROM users
#);