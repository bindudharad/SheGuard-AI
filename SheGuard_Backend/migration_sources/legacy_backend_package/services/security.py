import base64
import json
import hashlib
import hmac
import os
import secrets
import time


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150_000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode('utf-8')}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, _ = stored_hash.split("$", 2)
    except ValueError:
        return False
    return algorithm == "pbkdf2_sha256" and hmac.compare_digest(hash_password(password, salt), stored_hash)


def create_access_token(subject: str, expires_seconds: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": int(time.time()), "exp": int(time.time()) + expires_seconds}
    signing_input = f"{_b64_json(header)}.{_b64_json(payload)}"
    signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')}"


def verify_access_token(token: str) -> dict | None:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(_jwt_secret().encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
        if not hmac.compare_digest(expected, actual):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def _b64_json(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).decode("utf-8").rstrip("=")


def _jwt_secret() -> str:
    return os.environ.get("SHEGUARD_JWT_SECRET") or os.environ.get("SECRET_KEY") or "dev-only-change-this-secret"
