import base64, hashlib, hmac

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hmac_sign_hex(key_b64: str, msg: bytes) -> str:
    if not key_b64:
        # deterministic fallback for local dev; DO NOT use in prod
        key = b"dev-insecure-key"
    else:
        key = base64.b64decode(key_b64)
    return hmac.new(key, msg, hashlib.sha256).hexdigest()
