from app.services.security import verify_password
import sqlite3
conn = sqlite3.connect('sheguard.db')
cursor = conn.cursor()
cursor.execute(\
SELECT
password_hash
FROM
users
WHERE
phone_number
=
9999999999
\)
result = cursor.fetchone()
conn.close()
print('Hash:', result[0])
print('Verify password123:', verify_password('password123', result[0]))
