import sys
sys.path.insert(0, '.')
import hashlib
import base64
import hmac

password = 'password123'
stored_hash = 'pbkdf2_sha256='

# Manual verification
parts = stored_hash.split('$', 2)
print('Parts:', parts)
print('Len:', len(parts))
algorithm, salt, stored_digest = parts
print('Algorithm:', algorithm)
print('Salt:', salt)
print('Stored digest:', stored_digest)

digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 150_000)
computed_digest = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
print('Computed digest:', computed_digest)
print('Match:', hmac.compare_digest(computed_digest, stored_digest))
