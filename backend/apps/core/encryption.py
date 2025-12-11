import hashlib
import logging
import warnings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import nacl.secret
import nacl.utils
from nacl.exceptions import CryptoError

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Manages encryption keys and operations using LibSodium (PyNacl).
    
    Implements Envelope Encryption:
    - Master Key (KEK): Stored in environment (settings.ENCRYPTION_KEY).
    - Data Key (DEK): Generated per entity, encrypted by KEK.
    
    Security:
    - In production (DEBUG=False), ENCRYPTION_KEY must be explicitly set
    - In development (DEBUG=True), falls back to SECRET_KEY with a warning
    - KEK is cached after first load for performance
    """
    
    _kek = None

    @classmethod
    def get_kek(cls):
        """
        Lazy load KEK (Key Encryption Key) from settings.
        
        Security:
        - Production: Requires ENCRYPTION_KEY env var, fails loudly if missing
        - Development: Falls back to SECRET_KEY with deprecation warning
        
        Returns:
            bytes: 32-byte encryption key
            
        Raises:
            ImproperlyConfigured: If ENCRYPTION_KEY is missing in production
        """
        if cls._kek is None:
            key_hex = getattr(settings, 'ENCRYPTION_KEY', None)
            
            if not key_hex:
                # No explicit ENCRYPTION_KEY configured
                if not settings.DEBUG:
                    # PRODUCTION: Fail loudly - this is a critical security requirement
                    raise ImproperlyConfigured(
                        "ENCRYPTION_KEY must be set in production. "
                        "This key protects all encrypted secrets in the database. "
                        "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
                    )
                else:
                    # DEVELOPMENT: Allow fallback with warning
                    warnings.warn(
                        "ENCRYPTION_KEY not set. Using SECRET_KEY as fallback. "
                        "DO NOT USE IN PRODUCTION - set ENCRYPTION_KEY environment variable.",
                        UserWarning,
                        stacklevel=2
                    )
                    logger.warning(
                        "Using SECRET_KEY as encryption key fallback. "
                        "This is insecure and should only be used in development."
                    )
                    key_material = settings.SECRET_KEY.encode()
                    cls._kek = hashlib.sha256(key_material).digest()
            else:
                # ENCRYPTION_KEY is set - parse it
                cls._kek = cls._parse_key(key_hex)
                logger.info("Encryption key loaded successfully")
                
        return cls._kek

    @classmethod
    def _parse_key(cls, key_value: str) -> bytes:
        """
        Parse the encryption key from various formats.
        
        Supports:
        - 64-character hex string (32 bytes)
        - Any other string (will be hashed to 32 bytes)
        
        Args:
            key_value: The key string from settings
            
        Returns:
            bytes: 32-byte key
        """
        # Try to parse as hex first (preferred format)
        try:
            key_bytes = bytes.fromhex(key_value)
            if len(key_bytes) == 32:
                return key_bytes
            else:
                logger.warning(
                    f"ENCRYPTION_KEY hex is {len(key_bytes)} bytes, expected 32. "
                    "Key will be hashed to correct length."
                )
                return hashlib.sha256(key_bytes).digest()
        except ValueError:
            # Not valid hex, hash the raw string
            logger.warning(
                "ENCRYPTION_KEY is not valid hex. Key will be hashed. "
                "For best security, use a 64-character hex string."
            )
            return hashlib.sha256(key_value.encode()).digest()

    @classmethod
    def reset_kek(cls):
        """
        Reset the cached KEK. Useful for testing.
        
        WARNING: Only use in tests. In production, this could cause
        data to become unreadable if the KEK changes.
        """
        cls._kek = None

    @classmethod
    def generate_dek(cls) -> bytes:
        """Generate a random 32-byte Data Encryption Key"""
        return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

    @classmethod
    def encrypt_dek(cls, dek: bytes) -> bytes:
        """Encrypt the DEK using the KEK (Key Wrapping)"""
        kek = cls.get_kek()
        box = nacl.secret.SecretBox(kek)
        # Encrypt returns ciphertext with nonce prepended (PyNacl default behavior usually?)
        # SecretBox.encrypt returns EncryptedMessage which contains nonce
        encrypted = box.encrypt(dek)
        return encrypted # bytes (nonce + ciphertext + MAC)

    @classmethod
    def decrypt_dek(cls, encrypted_dek: bytes) -> bytes:
        """Decrypt the DEK using the KEK"""
        kek = cls.get_kek()
        box = nacl.secret.SecretBox(kek)
        try:
            dek = box.decrypt(encrypted_dek)
            return dek
        except CryptoError:
            raise ValueError("Failed to decrypt DEK. Invalid KEK or corrupted data.")

    @classmethod
    def encrypt_value(cls, value: str, dek: bytes) -> bytes:
        """Encrypt a string value using the provided DEK"""
        box = nacl.secret.SecretBox(dek)
        # Value must be bytes
        value_bytes = value.encode('utf-8')
        encrypted = box.encrypt(value_bytes)
        return encrypted
        
    @classmethod
    def decrypt_value(cls, encrypted_value: bytes, dek: bytes) -> str:
        """Decrypt a value using the provided DEK"""
        box = nacl.secret.SecretBox(dek)
        try:
            plaintext = box.decrypt(encrypted_value)
            return plaintext.decode('utf-8')
        except CryptoError:
             raise ValueError("Failed to decrypt value. Invalid DEK or corrupted data.")
