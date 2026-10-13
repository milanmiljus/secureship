import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from config import settings


def generate_code() -> tuple[str, str]:
    """
    Generate a 6-digit verification code.
    Returns (plain_code, sha256_hash).
    We use SHA-256 for speed (bcrypt is too slow for a 6-digit code that
    already has a 10-minute expiry and 3-attempt limit).
    """
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    return code, code_hash


def verify_code(plain_code: str, stored_hash: str) -> bool:
    """Constant-time comparison of submitted code against stored hash."""
    submitted_hash = hashlib.sha256(plain_code.encode()).hexdigest()
    return secrets.compare_digest(submitted_hash, stored_hash)


def is_code_expired(sent_at: datetime) -> bool:
    """Check if the code has exceeded CODE_EXPIRY_MINUTES."""
    expiry = sent_at + timedelta(minutes=settings.CODE_EXPIRY_MINUTES)
    return datetime.now(timezone.utc) > expiry


def is_attempts_exceeded(attempt_count: int) -> bool:
    return attempt_count >= settings.MAX_CODE_ATTEMPTS
