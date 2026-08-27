
import sqlite3
import base64
import hashlib
import hmac

conn = sqlite3.connect('sheguard.db')
c = conn.cursor()
c.execute('SELECT password_hash FROM users WHERE phone_number=?', ('9999999999',))
row = c.fetchone()
stored = row[0]
conn.close()

parts = stored.split(chr(36), 2)
salt = parts[1]
stored_digest = parts[2]

# Try decoding the stored digest and compare raw bytes
stored_bytes = base64.urlsafe_b64decode(stored_digest + '=' * (-len(stored_digest) % 4))
print('Stored bytes length:', len(stored_bytes))
print('Stored bytes:', stored_bytes.hex())

# Also try standard b64
stored_bytes2 = base64.b64decode(stored_digest + '=' * (-len(stored_digest) % 4))
print('Stored bytes (std):', stored_bytes2.hex())

