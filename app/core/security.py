import hmac
import hashlib
from typing import Optional


def verify_signature(secret: str, signature: str, payload: bytes, algo: str = "sha256") -> bool:
    if not secret or not signature:
        return False
    digestmod = hashlib.sha256 if algo == "sha256" else hashlib.sha1
    expected = hmac.new(secret.encode(), payload, digestmod).hexdigest()
    # GitHub format: sha256=...
    provided = signature.split("=")[-1]
    return hmac.compare_digest(expected, provided)


def constant_time_equals(first: Optional[str], second: Optional[str]) -> bool:
    if not first or not second:
        return False
    return hmac.compare_digest(first, second)
