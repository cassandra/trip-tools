import logging
from unittest.mock import patch

from django.urls import reverse

from tt.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestEnvironmentHomeView(SyncViewTestCase):
    """
    Tests for EnvironmentHomeView - demonstrates simple JSON API view testing.
    This view returns internal configuration data as JSON.
    """
    def test_get_config_data(self):
        """Test getting internal configuration data."""
        self.client.force_login(self.user)
        url = reverse('env_home')
        response = self.client.get(url)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)

        data = response.json()

        # Keys that should always be present
        common_keys = [
            'ALLOWED_HOSTS',
            'REDIS_HOST',
            'REDIS_PORT',
            'MEDIA_ROOT',
            'DEFAULT_FROM_EMAIL',
            'SERVER_EMAIL',
            'CORS_ALLOWED_ORIGINS',
            'CSP_DEFAULT_SRC',
            'CSP_CONNECT_SRC',
            'CSP_FRAME_SRC',
            'CSP_SCRIPT_SRC',
            'CSP_STYLE_SRC',
            'CSP_MEDIA_SRC',
            'CSP_IMG_SRC',
            'CSP_CHILD_SRC',
            'CSP_FONT_SRC',
        ]

        for key in common_keys:
            self.assertIn(key, data, f"Expected key '{key}' not found in config data")

        # Database config: either SQLite (DATABASES_NAME_PATH) or MySQL (full connection params)
        sqlite_key = 'DATABASES_NAME_PATH'
        mysql_keys = ['DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD']

        has_sqlite = sqlite_key in data and data[sqlite_key]
        has_mysql = all(key in data for key in mysql_keys)

        self.assertTrue(
            has_sqlite or has_mysql,
            f"Expected either '{sqlite_key}' or all of {mysql_keys} in config data"
        )

        # Email config: either API-based (EMAIL_API_KEY) or SMTP (full SMTP params)
        api_key = 'EMAIL_API_KEY'
        smtp_keys = ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_USE_TLS', 'EMAIL_USE_SSL']

        has_api_email = api_key in data
        has_smtp_email = all(key in data for key in smtp_keys)

        self.assertTrue(
            has_api_email or has_smtp_email,
            f"Expected either '{api_key}' or all of {smtp_keys} in config data"
        )

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        self.client.force_login(self.user)
        url = reverse('env_home')
        response = self.client.post(url)
        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    @patch('tt.environment.views.settings')
    def test_config_values_from_settings(self, mock_settings):
        """Test that config values are pulled from Django settings."""
        self.client.force_login(self.user)

        # Set mock values - ENV attributes
        mock_settings.ENV.environment_name = 'test'
        mock_settings.ENV.VERSION = '1.0.0'
        mock_settings.ENV.DATABASE_HOST = 'db.test.com'
        mock_settings.ENV.DATABASE_PORT = '3306'
        mock_settings.ENV.DATABASE_NAME = 'test_db'
        mock_settings.ENV.STORAGE_ENDPOINT_URL = 'https://storage.test.com'
        mock_settings.ENV.STORAGE_REGION_NAME = 'us-east-1'
        mock_settings.ENV.STORAGE_BUCKET_NAME = 'test-bucket'
        mock_settings.ENV.STORAGE_LOCATION_PREFIX = 'prefix'
        mock_settings.ENV.STORAGE_CUSTOM_DOMAIN = 'cdn.test.com'

        # Set mock values - direct settings attributes
        mock_settings.ALLOWED_HOSTS = ['test.example.com']
        mock_settings.REDIS_HOST = 'redis.test.com'
        mock_settings.REDIS_PORT = 6379
        mock_settings.DATABASES = {'default': {'NAME': '/test/db.sqlite3'}}
        mock_settings.MEDIA_ROOT = '/test/media'
        mock_settings.DEFAULT_FROM_EMAIL = 'test@example.com'
        mock_settings.SERVER_EMAIL = 'server@example.com'
        mock_settings.EMAIL_HOST = 'smtp.test.com'
        mock_settings.EMAIL_PORT = 587
        mock_settings.EMAIL_HOST_USER = 'testuser'
        mock_settings.EMAIL_USE_TLS = True
        mock_settings.EMAIL_USE_SSL = False
        mock_settings.CORS_ALLOWED_ORIGINS = ['http://test.com']
        mock_settings.CSP_DEFAULT_SRC = ["'self'"]
        mock_settings.CSP_CONNECT_SRC = ["'self'"]
        mock_settings.CSP_FRAME_SRC = ["'self'"]
        mock_settings.CSP_SCRIPT_SRC = ["'self'"]
        mock_settings.CSP_STYLE_SRC = ["'self'"]
        mock_settings.CSP_MEDIA_SRC = ["'self'"]
        mock_settings.CSP_IMG_SRC = ["'self'"]
        mock_settings.CSP_CHILD_SRC = ["'self'"]
        mock_settings.CSP_FONT_SRC = ["'self'"]

        url = reverse('env_home')
        response = self.client.get(url)
        self.assertSuccessResponse(response)

        data = response.json()
        self.assertEqual(data['ENVIRONMENT'], 'test')
        self.assertEqual(data['VERSION'], '1.0.0')
        self.assertEqual(data['ALLOWED_HOSTS'], ['test.example.com'])
        self.assertEqual(data['REDIS_HOST'], 'redis.test.com')
        self.assertEqual(data['EMAIL_USE_TLS'], True)
        self.assertEqual(data['EMAIL_USE_SSL'], False)
