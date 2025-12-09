"""
Tests for health check endpoint.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestHealthCheckView:
    """Test cases for health check endpoint."""
    
    def test_health_check_success(self):
        """Test health check returns 200 when healthy."""
        client = APIClient()
        response = client.get('/api/v1/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'healthy'
        assert response.data['service'] == 'ConfigMat Public API'
        assert response.data['version'] == 'v1'
        assert 'timestamp' in response.data
        assert response.data['database'] == 'connected'
    
    def test_health_check_no_auth_required(self):
        """Test health check doesn't require authentication."""
        client = APIClient()
        # No credentials provided
        response = client.get('/api/v1/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'healthy'
    
    def test_health_check_response_structure(self):
        """Test health check response has correct structure."""
        client = APIClient()
        response = client.get('/api/v1/health/')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check all required fields are present
        required_fields = ['status', 'service', 'version', 'timestamp', 'database']
        for field in required_fields:
            assert field in response.data, f"Missing field: {field}"
    
    def test_health_check_content_type(self):
        """Test health check returns JSON content type."""
        client = APIClient()
        response = client.get('/api/v1/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/json'
    
    def test_health_check_multiple_calls(self):
        """Test health check can be called multiple times."""
        client = APIClient()
        
        # Make multiple calls
        for _ in range(5):
            response = client.get('/api/v1/health/')
            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'healthy'
