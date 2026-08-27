import sys
sys.path.insert(0, '.')
import hashlib
import base64
import hmac

# Get hash from DB
import sqlite3
conn = sqlite3.connect('sheguard.db')
cursor = conn.cursor()
cursor.execute('SELECT password_hash FROM users WHERE phone_number = ?', ('9999999999',))
result = cursor.fetchone()
conn.close()
hash = result[0]
print('Hash from DB:', repr(hash))

# Now manually run the verify_password logic
stored_hash = hash
password = 'password123'

# Split using chr(36) which is $
algorithm, salt, stored_digest = stored_hash.split(chr(36), 2)
print('After split with chr(36):')
print('  Algorithm:', repr(algorithm))
print('  Salt:', repr(salt))
print('  Stored digest:', repr(stored_digest))

if algorithm != 'pbkdf2_sha256':
    print('Algorithm mismatch!')
    exit()

digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 150_000)
computed_digest = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
print('Computed digest:', repr(computed_digest))
print('Match:', hmac.compare_digest(computed_digest, stored_digest))
