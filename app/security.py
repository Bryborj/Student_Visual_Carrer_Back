import hashlib
import hmac
import os

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
