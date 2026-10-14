import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def hash_email(email: str) -> str:
    """Calcula el hash SHA-256 anónimo del correo electrónico institucional."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def hash_password(password: str, salt: str | None = None) -> str:
    """
    Genera un hash de contraseña usando PBKDF2 sha512 (10,000 iteraciones, 64 bytes).
    Compatible 100% con la implementación original en Node.js crypto.pbkdf2Sync.
    """
    if salt is None:
        salt = os.urandom(16).hex()
    derived = hashlib.pbkdf2_hmac(
        "sha512",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        10000,
        dklen=64
    ).hex()
    return f"{salt}:{derived}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica si la contraseña coincide con el hash guardado (formato salt:hash)."""
    if not stored_hash or ":" not in stored_hash:
        return False
    parts = stored_hash.split(":", 1)
    if len(parts) != 2:
        return False
    salt, original_hash = parts
    derived = hashlib.pbkdf2_hmac(
        "sha512",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        10000,
        dklen=64
    ).hex()
    return hmac.compare_digest(derived, original_hash)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Genera un token JWT firmado para la sesión de un usuario."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decodifica y valida un token JWT. Retorna None si es inválido o expiró."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
