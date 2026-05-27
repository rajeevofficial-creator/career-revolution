"""
Security utilities for Career Revolution.
Handles symmetric encryption/decryption of sensitive credential data
using the Fernet (AES-128-CBC + HMAC) scheme from the `cryptography` library.
"""

import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def get_fernet() -> Fernet:
    """
    Returns a Fernet instance, initializing it from the environment or
    auto-generating and persisting a key to .env on first use.
    """
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "CREDENTIAL_ENCRYPTION_KEY is not set in the .env file. "
            "Add it before storing or retrieving any credentials."
        )

    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise RuntimeError(f"Invalid CREDENTIAL_ENCRYPTION_KEY: {e}")

    return _fernet


def _write_key_to_env(key: str):
    """Appends the encryption key to the .env file in the project root."""
    try:
        # Find .env relative to this file (app/utils/ -> root)
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(root, ".env")
        with open(env_path, "a") as f:
            f.write(f"\n# Auto-generated encryption key for credential storage\n")
            f.write(f"CREDENTIAL_ENCRYPTION_KEY={key}\n")
        logger.info(f"Encryption key written to: {env_path}")
    except Exception as e:
        logger.error(f"Could not write encryption key to .env: {e}")


def encrypt_value(plaintext: str) -> str:
    """
    Encrypts a plaintext string and returns a base64-encoded ciphertext string.
    Returns empty string if input is empty/None.
    """
    if not plaintext:
        return ""
    f = get_fernet()
    encrypted_bytes = f.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypts a Fernet-encrypted ciphertext string and returns the plaintext.
    Returns empty string if input is empty/None or decryption fails.
    """
    if not ciphertext:
        return ""
    try:
        f = get_fernet()
        decrypted_bytes = f.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        logger.error("Decryption failed: InvalidToken — wrong key or corrupted data.")
        return ""
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return ""


def mask_password(plaintext: str) -> str:
    """Returns '••••••••' if the value is set, empty string otherwise."""
    return "••••••••" if plaintext else ""
