
import sqlite3
from app.services.security import hash_password

conn = sqlite3.connect('sheguard.db')
c = conn.cursor()

# Update passwords for test users
users_to_update = [
    ('1111111111', 'password123'),
    ('2222222222', 'password123'),
    ('5550000000', 'password123'),
    ('5550000001', 'password123'),
    ('5550000002', 'password123'),
    ('7770000000', 'password123'),
    ('7770000001', 'password123'),
    ('7770000002', 'password123'),
    ('7770000003', 'password123'),
    ('7770000004', 'password123'),
    ('8880000000', 'password123'),
    ('8880000001', 'password123'),
    ('8880000002', 'password123'),
    ('3333333333', 'password123'),
    ('9111111111', 'password123'),
    ('9222222222', 'password123'),
    ('9333333333', 'password123'),
    ('9999999998', 'password123'),
]

for phone, pwd in users_to_update:
    new_hash = hash_password(pwd)
    c.execute('UPDATE users SET password_hash=? WHERE phone_number=?', (new_hash, phone))
    print(f'Updated {phone}')

conn.commit()
conn.close()
print('All updated')

