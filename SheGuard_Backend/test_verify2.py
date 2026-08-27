import sys
sys.path.insert(0, '.')
from app.services.security import verify_password

import sqlite3
conn = sqlite3.connect('sheguard.db')
cursor = conn.cursor()
cursor.execute('SELECT password_hash FROM users WHERE phone_number = ?', ('9999999999',))
result = cursor.fetchone()
conn.close()
hash = result[0]
print('Raw hash:', repr(hash))

parts = hash.split('$', 2)
print('Split with literal:', parts)
print('Len:', len(parts))

result = verify_password('password123', hash)
print('Verify result:', result)
