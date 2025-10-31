import logging
from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from custom.models import CustomUser
from django.http import HttpResponse
from django.test import RequestFactory

from tt.apps.user.middleware import AuthenticationMiddleware
from tt.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAuthenticationMiddleware(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse('success'))
        self.middleware = AuthenticationMiddleware(self.get_response)
        
        self.authenticated_user = CustomUser.objects.create_user(
            email='auth@example.com',
            password='authpass'
        )

    def test_middleware_initialization(self):
        """Test AuthenticationMiddleware initializes correctly."""
        middleware = AuthenticationMiddleware(self.get_response)
        
        self.assertEqual(middleware.get_response, self.get_response)
        
        # Verify exempt URL names are defined
        expected_exempt_urls = {
            'admin',
            'manifest',
            'notify_email_unsubscribe',
            'user_signin',
            'user_signin_magic_code',
            'user_signin_magic_link',
        }
        self.assertEqual(middleware.EXEMPT_VIEW_URL_NAMES, expected_exempt_urls)

    def test_middleware_bypasses_when_user_authenticated(self):
        """Test middleware bypasses when user is already authenticated."""
        request = self.factory.get('/some-protected-path')
        request.user = self.authenticated_user
        
        with patch('tt.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='protected_view', app_name='main')
            
            response = self.middleware(request)
            
            # Should call get_response directly without authentication check
            self.get_response.assert_called_once_with(request)
            self.assertEqual(response, self.get_response.return_value)

    def test_middleware_allows_admin_app_access(self):
        """Test middleware allows access to admin app without authentication."""
        request = self.factory.get('/admin/some-admin-path')
        request.user = AnonymousUser()
        
        with patch('tt.apps.user.middleware.resolve') as mock_resolve:
            mock_resolve.return_value = Mock(url_name='admin_view', app_name='admin')
            
            response = self.middleware(request)
            
            # Should call get_response directly for admin app
            self.get_response.assert_called_once_with(request)
            self.assertEqual(response, self.get_response.return_value)

    def test_middleware_allows_exempt_signin_urls(self):
        """Test middleware allows access to exempt signin URLs."""
        exempt_urls = [
            'user_signin',
            'user_signin_magic_code', 
            'user_signin_magic_link'
        ]
        
        for url_name in exempt_urls:
            with self.subTest(url_name=url_name):
                request = self.factory.get(f'/{url_name}')
                request.user = AnonymousUser()
                
                with patch('tt.apps.user.middleware.resolve') as mock_resolve:
                    mock_resolve.return_value = Mock(url_name=url_name, app_name='user')
                    
                    response = self.middleware(request)
                    
                    # Should call get_response directly for exempt URLs
                    self.get_response.assert_called_once_with(request)
                    self.assertEqual(response, self.get_response.return_value)
                    
                # Reset mock for next iteration
                self.get_response.reset_mock()

    def test_middleware_exempt_urls_are_comprehensive(self):
        """Test middleware exempt URLs cover all necessary authentication endpoints."""
        exempt_urls = self.middleware.EXEMPT_VIEW_URL_NAMES
        
        # Verify critical authentication URLs are exempt
        self.assertIn('user_signin', exempt_urls)
        self.assertIn('user_signin_magic_code', exempt_urls)
        self.assertIn('user_signin_magic_link', exempt_urls)
        self.assertIn('admin', exempt_urls)
        
        # Verify the set is not empty and contains strings
        self.assertTrue(len(exempt_urls) > 0)
        self.assertTrue(all(isinstance(url, str) for url in exempt_urls))
