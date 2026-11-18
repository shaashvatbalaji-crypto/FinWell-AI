
from pwdlib import PasswordHash

# Initialize Argon2id password hasher
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Generate a secure Argon2id password hash."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password cannot be empty.")

    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    if not isinstance(password, str) or not isinstance(hashed_password, str):
        return False

    if not password or not hashed_password:
        return False

    return password_hasher.verify(password, hashed_password)
