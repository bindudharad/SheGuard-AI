
import sqlite3
from app.services.security import hash_password

conn = sqlite3.connect('sheguard.db')
c = conn.cursor()

# Update the password for user 9999999999 to a known hash
new_hash = hash_password('password123')
print('New hash:', new_hash)

c.execute('UPDATE users SET password_hash=? WHERE phone_number=?', (new_hash, '9999999999'))
conn.commit()
conn.close()
print('Updated')

