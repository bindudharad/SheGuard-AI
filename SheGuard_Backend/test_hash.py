import hashlib; import base64; import hmac; stored = 'pbkdf2_sha256-AKQCtpPFRLEf_VTFLwgTp4Po='; parts = stored.split('$', 2); print('Parts:', parts)
