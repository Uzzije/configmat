from rest_framework import authentication, exceptions
from .models import APIKey


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate requests using X-API-Key header.
    Format: X-API-Key: <32-char-key>
    """

    def authenticate(self, request):
        api_key_header = request.headers.get('X-API-Key')
        if not api_key_header:
            return None

        return self.authenticate_credentials(api_key_header)

    def authenticate_credentials(self, key):
        # Key format: <prefix>... (we don't store the full key, just hash)
        # But for lookup, we need to find the key first.
        # Since we don't store the key, we can't look it up directly by key.
        # We need to look up by prefix? No, that's not secure enough for lookup.
        # Wait, the model stores key_hash. We need to iterate? No, that's slow.
        # 
        # Better approach: The key provided by client should be the raw key.
        # We can't query by raw key.
        # 
        # Standard practice: API Key = "prefix.secret"
        # We store prefix and hash(secret).
        # Client sends "prefix.secret".
        # We lookup by prefix, then verify hash(secret).
        
        # Let's assume the key is just the 32 chars for now as per my serializer.
        # But wait, the serializer generated a 32 char key and stored the first 8 as prefix.
        # So we can use the first 8 chars of the provided key to lookup.
        
        if len(key) < 16:
            raise exceptions.AuthenticationFailed('Invalid API Key format')
            
        prefix = key[:16]
        
        try:
            api_key = APIKey.objects.get(key_prefix=prefix, revoked=False)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API Key')

        if not api_key.verify_key(key):
            raise exceptions.AuthenticationFailed('Invalid API Key')

        if api_key.revoked:
            raise exceptions.AuthenticationFailed('API Key revoked')

        # Update last used timestamp (async to avoid DB write on every read?)
        # For MVP, sync is fine, or use a background task if high volume.
        # api_key.last_used_at = timezone.now()
        # api_key.save(update_fields=['last_used_at'])

        return (api_key.created_by, api_key)
