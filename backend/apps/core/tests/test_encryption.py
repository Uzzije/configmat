from django.test import SimpleTestCase, override_settings
from apps.core.encryption import KeyManager


@override_settings(ENCRYPTION_KEY='a' * 64)
class EncryptionTests(SimpleTestCase):
    """Tests for encryption operations using a test encryption key."""
    
    def setUp(self):
        # Reset the cached KEK before each test to ensure clean state
        KeyManager.reset_kek()
    
    def test_dek_generation_and_wrapping(self):
        # 1. Generate DEK
        dek = KeyManager.generate_dek()
        self.assertEqual(len(dek), 32)

        # 2. Encrypt DEK (Wrap)
        encrypted_dek = KeyManager.encrypt_dek(dek)
        # 3. Decrypt DEK (Unwrap)
        unwrapped_dek = KeyManager.decrypt_dek(encrypted_dek)
        
        self.assertEqual(dek, unwrapped_dek)

    def test_value_encryption(self):
        dek = KeyManager.generate_dek()
        original_text = "super_secret_password_123"
        
        # Encrypt
        encrypted = KeyManager.encrypt_value(original_text, dek)
        self.assertNotEqual(encrypted, original_text.encode())
        
        # Decrypt
        decrypted = KeyManager.decrypt_value(encrypted, dek)
        self.assertEqual(decrypted, original_text)

    def test_different_deks_produce_different_ciphertexts(self):
        dek1 = KeyManager.generate_dek()
        dek2 = KeyManager.generate_dek()
        text = "same_text"
        
        c1 = KeyManager.encrypt_value(text, dek1)
        c2 = KeyManager.encrypt_value(text, dek2)
        
        self.assertNotEqual(c1, c2)
        
        # Also even with same DEK, nonce ensures different ciphertext (PyNacl random nonce)
        c3 = KeyManager.encrypt_value(text, dek1)
        self.assertNotEqual(c1, c3)
