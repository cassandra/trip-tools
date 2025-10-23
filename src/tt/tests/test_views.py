import logging
from unittest.mock import patch

from django.urls import reverse

from tt.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestStartView(SyncViewTestCase):
    """
    Tests for StartView - demonstrates synchronous HTML view testing.
    This view renders a template for first-time users when no locations exist.
    """

    def test_start_view_renders_template_when_no_locations(self):        
        url = reverse('start')
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'pages/start.html')


class TestHealthView(SyncViewTestCase):
    """
    Tests for HealthView - demonstrates health check endpoint testing.
    This view returns JSON with system health status.
    """

    @patch('tt.views.do_healthcheck')
    def test_health_check_healthy(self, mock_healthcheck):
        """Test health check when system is healthy."""
        mock_healthcheck.return_value = {
            'is_healthy': True,
            'database': 'ok',
            'redis': 'ok',
            'subsystems': []
        }

        url = reverse('health')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertTrue(data['status']['is_healthy'])

    @patch('tt.views.do_healthcheck')
    def test_health_check_unhealthy(self, mock_healthcheck):
        """Test health check when system is unhealthy."""
        mock_healthcheck.return_value = {
            'is_healthy': False,
            'database': 'error',
            'redis': 'ok',
            'error_message': 'Database connection failed'
        }

        url = reverse('health')
        response = self.client.get(url)

        # Should return 500 when unhealthy
        self.assertServerErrorResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertFalse(data['status']['is_healthy'])

    def test_health_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('health')
        response = self.client.post(url)

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)
