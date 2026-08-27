
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

# Use chr(36) which is dollar sign
parts = stored.split(chr(36), 2)
print('Parts:', parts)

salt = parts[1]
stored_digest = parts[2]

for iterations in [100000, 150000, 200000, 50000, 10000, 1000]:
    digest = hashlib.pbkdf2_hmac('sha256', 'password123'.encode('utf-8'), salt.encode('utf-8'), iterations)
    computed = base64.urlsafe_b64encode(digest).decode('utf-8')
    if computed == stored_digest:
        print('Match found at iterations=' + str(iterations))
        break
    else:
        print('iterations=' + str(iterations) + ': ' + computed[:20] + '... != ' + stored_digest[:20] + '...')

