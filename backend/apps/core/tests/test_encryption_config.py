"""
Tests for encryption key configuration safety.

These tests ensure that the encryption system fails loudly in production
when misconfigured, rather than silently falling back to insecure defaults.
"""

import pytest
import warnings
from unittest.mock import patch
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


class TestEncryptionConfiguration:
    """Tests for encryption key configuration safety."""
    
    def _reset_key_manager(self):
        """Reset the cached KEK to force re-initialization."""
        from apps.core.encryption import KeyManager
        KeyManager.reset_kek()
    
    @override_settings(DEBUG=False, ENCRYPTION_KEY=None)
    def test_missing_key_in_production_raises_error(self):
        """
        Production without ENCRYPTION_KEY must fail loudly.
        
        This is a critical security requirement - we should never silently
        fall back to using SECRET_KEY for encryption in production.
        """
        from apps.core.encryption import KeyManager
        self._reset_key_manager()
        
        with pytest.raises(ImproperlyConfigured) as exc_info:
            KeyManager.get_kek()
        
        assert "ENCRYPTION_KEY must be set" in str(exc_info.value)
        assert "production" in str(exc_info.value).lower()
    
    @override_settings(DEBUG=True, ENCRYPTION_KEY=None)
    def test_missing_key_in_debug_warns(self):
        """
        Debug mode should warn but not fail when ENCRYPTION_KEY is missing.
        
        This allows developers to run the app locally without configuring
        encryption, but makes it clear this is not safe for production.
        """
        from apps.core.encryption import KeyManager
        self._reset_key_manager()
        
        with pytest.warns(UserWarning, match="DO NOT USE IN PRODUCTION"):
            key = KeyManager.get_kek()
        
        assert key is not None
        assert len(key) == 32
    
    @override_settings(ENCRYPTION_KEY='a' * 64)
    def test_valid_hex_key_works(self):
        """Valid hex ENCRYPTION_KEY should work correctly."""
        from apps.core.encryption import KeyManager
        self._reset_key_manager()
        
        key = KeyManager.get_kek()
        
        assert key is not None
        assert len(key) == 32
        assert key == bytes.fromhex('a' * 64)
    
    @override_settings(ENCRYPTION_KEY='short')
    def test_short_key_is_hashed(self):
        """Keys that aren't 32 bytes should be hashed to correct length."""
        from apps.core.encryption import KeyManager
        self._reset_key_manager()
        
        key = KeyManager.get_kek()
        
        # Should be hashed to 32 bytes
        assert len(key) == 32
    
    @override_settings(ENCRYPTION_KEY='b' * 64)
    def test_key_is_cached(self):
        """KEK should be cached after first retrieval."""
        from apps.core.encryption import KeyManager
        self._reset_key_manager()
        
        key1 = KeyManager.get_kek()
        key2 = KeyManager.get_kek()
        
        # Should be the same object (cached)
        assert key1 is key2
    
    @override_settings(ENCRYPTION_KEY='a' * 64)
    def test_different_keys_produce_different_encrypted_deks(self):
        """Different KEKs should produce different encrypted DEKs."""
        from apps.core.encryption import KeyManager
        
        # Generate a DEK
        dek = KeyManager.generate_dek()
        
        # Encrypt with first KEK
        KeyManager.reset_kek()
        encrypted1 = KeyManager.encrypt_dek(dek)
        
        # Change key and encrypt again
        from django.test import override_settings as os2
        with os2(ENCRYPTION_KEY='b' * 64):
            KeyManager.reset_kek()
            encrypted2 = KeyManager.encrypt_dek(dek)
        
        # Same DEK should produce different ciphertext with different KEKs
        assert encrypted1 != encrypted2
    
    @override_settings(ENCRYPTION_KEY='a' * 64)
    def test_wrong_kek_cannot_decrypt_dek(self):
        """DEK encrypted with one KEK should not decrypt with another."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        
        # Encrypt with first KEK
        KeyManager.reset_kek()
        encrypted_dek = KeyManager.encrypt_dek(dek)
        
        # Try to decrypt with different KEK
        from django.test import override_settings as os2
        with os2(ENCRYPTION_KEY='b' * 64):
            KeyManager.reset_kek()
            
            with pytest.raises(ValueError, match="Failed to decrypt DEK"):
                KeyManager.decrypt_dek(encrypted_dek)


class TestEncryptionOperations:
    """Tests for encryption/decryption operations."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Values should decrypt to their original plaintext."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        original = "super_secret_api_key_12345"
        
        encrypted = KeyManager.encrypt_value(original, dek)
        decrypted = KeyManager.decrypt_value(encrypted, dek)
        
        assert decrypted == original
    
    def test_encrypted_value_differs_from_plaintext(self):
        """Encrypted values should not resemble plaintext."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        plaintext = "visible_secret"
        
        encrypted = KeyManager.encrypt_value(plaintext, dek)
        
        # Encrypted should be bytes, not contain plaintext
        assert isinstance(encrypted, bytes)
        assert plaintext.encode() not in encrypted
    
    def test_same_plaintext_different_ciphertext(self):
        """Same plaintext encrypted twice should produce different ciphertext (due to nonce)."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        plaintext = "same_value"
        
        encrypted1 = KeyManager.encrypt_value(plaintext, dek)
        encrypted2 = KeyManager.encrypt_value(plaintext, dek)
        
        # Random nonces mean different ciphertext each time
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same value
        assert KeyManager.decrypt_value(encrypted1, dek) == plaintext
        assert KeyManager.decrypt_value(encrypted2, dek) == plaintext
    
    def test_unicode_values_supported(self):
        """Encryption should handle unicode characters."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        unicode_value = "密码 🔐 пароль"
        
        encrypted = KeyManager.encrypt_value(unicode_value, dek)
        decrypted = KeyManager.decrypt_value(encrypted, dek)
        
        assert decrypted == unicode_value
    
    def test_empty_string_encryption(self):
        """Empty strings should encrypt and decrypt correctly."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        
        encrypted = KeyManager.encrypt_value("", dek)
        decrypted = KeyManager.decrypt_value(encrypted, dek)
        
        assert decrypted == ""
    
    def test_large_value_encryption(self):
        """Large values should encrypt correctly."""
        from apps.core.encryption import KeyManager
        
        dek = KeyManager.generate_dek()
        large_value = "x" * 100000  # 100KB
        
        encrypted = KeyManager.encrypt_value(large_value, dek)
        decrypted = KeyManager.decrypt_value(encrypted, dek)
        
        assert decrypted == large_value

