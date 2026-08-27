
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

print('Stored digest:', stored_digest)
print('Length:', len(stored_digest))

# Try different base64 decodings
for pad in range(4):
    try:
        padded = stored_digest + '=' * pad
        decoded = base64.urlsafe_b64decode(padded)
        print(f'Pad {pad}: {decoded.hex()}')
    except Exception as e:
        print(f'Pad {pad}: Error - {e}')

# Also check the computed one
digest = hashlib.pbkdf2_hmac('sha256', 'password123'.encode('utf-8'), salt.encode('utf-8'), 150000)
computed = base64.urlsafe_b64encode(digest).decode('utf-8')
print('Computed:', computed)
print('Computed length:', len(computed))

computed_bytes = base64.urlsafe_b64decode(computed + '=' * (-len(computed) % 4))
print('Computed bytes:', computed_bytes.hex())

