import os
import secrets
import base64
from django.conf import settings
import nacl.secret
import nacl.utils
import nacl.encoding
from nacl.exceptions import CryptoError

class KeyManager:
    """
    Manages encryption keys and operations using LibSodium (PyNacl).
    Implements Envelope Encryption:
    - Master Key (KEK): Stored in environment (settings.ENCRYPTION_KEY).
    - Data Key (DEK): Generated per entity, encrypted by KEK.
    """
    
    _kek = None

    @classmethod
    def get_kek(cls):
        """Lazy load KEK from settings"""
        if cls._kek is None:
            # key string must be 32 bytes hex or base64?
            # Start with getting from env
            key_hex = getattr(settings, 'ENCRYPTION_KEY', None)
            if not key_hex:
                 # Fallback to SECRET_KEY (Insecure for prod but ok for dev/mvp if 32 bytes)
                 # SECRET_KEY might be any string. Hash it to get 32 bytes
                 import hashlib
                 key_material = settings.SECRET_KEY.encode()
                 key_digest = hashlib.sha256(key_material).digest()
                 cls._kek = key_digest
            else:
                 try:
                    cls._kek = bytes.fromhex(key_hex)
                 except ValueError:
                    # Maybe base64? For now assume hex as standard
                    cls._kek = key_hex.encode() # Incorrect if raw string
                    # Let's enforce 32 bytes or hash it
                    if len(cls._kek) != 32:
                         import hashlib
                         cls._kek = hashlib.sha256(cls._kek).digest()
        return cls._kek

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
