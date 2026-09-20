import hashlib
from app.security import hash_email, hash_password, verify_password

def test_hash_email():
    email = "lobo.feroz@alumno.buap.mx"
    expected = hashlib.sha256(email.encode("utf-8")).hexdigest()
    assert hash_email(email) == expected
    # Asegurar case-insensitive y sin espacios
    assert hash_email("  Lobo.Feroz@ALUMNO.BUAP.MX  ") == expected

def test_password_hash_and_verify():
    password = "SuperSecretPassword2026!"
    stored = hash_password(password)
    assert ":" in stored
    assert verify_password(password, stored) is True
    assert verify_password("WrongPassword", stored) is False

def test_pbkdf2_nodejs_compatibility():
    # Simulación de un hash previamente generado por Node.js crypto.pbkdf2Sync('miPassword123', 'salt123456789012', 10000, 64, 'sha512')
    salt = "salt123456789012"
    password = "miPassword123"
    node_compatible_derived = hashlib.pbkdf2_hmac(
        "sha512",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        10000,
        dklen=64
    ).hex()
    node_stored_hash = f"{salt}:{node_compatible_derived}"

    assert verify_password(password, node_stored_hash) is True
    assert verify_password("otraPassword", node_stored_hash) is False
