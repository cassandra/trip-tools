import logging

from django.contrib.auth import get_user_model
from django.urls import reverse

from tt.apps.api.models import APIToken
from tt.apps.user.extension_service import ExtensionTokenService
from tt.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)

User = get_user_model()


class TestExtensionsHomeView(SyncViewTestCase):
    """Tests for ExtensionsHomeView - the extensions management page."""

    def test_get_requires_login(self):
        """Test that unauthenticated users are redirected to signin."""
        url = reverse('user_extensions')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_get_authenticated_user(self):
        """Test that authenticated users can access the page."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'user/pages/extensions.html')

    def test_context_contains_extension_tokens(self):
        """Test that context includes extension tokens list."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.get(url)

        self.assertIn('extension_tokens', response.context)
        self.assertIsInstance(response.context['extension_tokens'], list)

    def test_context_contains_account_page(self):
        """Test that context includes account page info for sidebar."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.get(url)

        self.assertIn('account_page', response.context)


class TestExtensionsHomeViewPost(SyncViewTestCase):
    """Tests for ExtensionsHomeView POST - creates tokens for extension auth."""

    def test_post_requires_login(self):
        """Test that unauthenticated users are redirected to signin."""
        url = reverse('user_extensions')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/user/signin', response.url)

    def test_post_creates_token(self):
        """Test that POST creates an API token."""
        self.client.force_login(self.user)
        initial_count = APIToken.objects.filter(user=self.user).count()

        url = reverse('user_extensions')
        response = self.client.post(url)

        self.assertSuccessResponse(response)
        final_count = APIToken.objects.filter(user=self.user).count()
        self.assertEqual(final_count, initial_count + 1)

    def test_post_returns_json_response(self):
        """Test that POST returns JSON with fragment HTML for antinode.js."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url)

        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('insert', data)
        self.assertIn('auth-form-area', data['insert'])

    def test_post_response_contains_token_str(self):
        """Test that POST response HTML includes the token string."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url)

        data = response.json()
        html = data['insert']['auth-form-area']
        # Token should be in the data-token attribute
        self.assertIn('data-token="tt_', html)

    def test_post_response_contains_token_name(self):
        """Test that POST response HTML includes the token name."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url)

        data = response.json()
        html = data['insert']['auth-form-area']
        # Token name should include the prefix
        self.assertIn(ExtensionTokenService.TOKEN_NAME_PREFIX, html)

    def test_platform_passed_through_form(self):
        """Test that platform from POST data is used in token name."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url, {'platform': 'Windows'})

        self.assertSuccessResponse(response)
        data = response.json()
        html = data['insert']['auth-form-area']
        self.assertIn('Windows', html)

    def test_multiple_posts_create_unique_tokens(self):
        """Test that multiple POSTs create tokens with unique names."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')

        # Create first token
        self.client.post(url)

        # Create second token
        response2 = self.client.post(url)
        data = response2.json()
        html = data['insert']['auth-form-area']

        # Second token name should have "(2)" suffix
        self.assertIn('(2)', html)


class TestExtensionTokenService(SyncViewTestCase):
    """Tests for ExtensionTokenService - token name generation and management."""

    def test_generate_token_name_format(self):
        """Test that generated name follows expected format."""
        name = ExtensionTokenService.generate_token_name(self.user)

        # Should start with prefix
        self.assertTrue(name.startswith(ExtensionTokenService.TOKEN_NAME_PREFIX))
        # Should contain month/year format (e.g., "Dec 2025")
        import re
        self.assertTrue(re.search(r'[A-Z][a-z]{2} \d{4}', name))

    def test_generate_token_name_with_platform(self):
        """Test that platform is included in token name."""
        name = ExtensionTokenService.generate_token_name(self.user, platform='macOS')

        self.assertIn('macOS', name)

    def test_generate_token_name_collision_handling(self):
        """Test that collisions are handled by appending suffix."""
        # Create first token
        name1 = ExtensionTokenService.generate_token_name(self.user)
        ExtensionTokenService.create_extension_token(self.user)

        # Generate second name - should get (2) suffix
        name2 = ExtensionTokenService.generate_token_name(self.user)

        self.assertNotEqual(name1, name2)
        self.assertTrue(name2.endswith('(2)'))

    def test_create_extension_token(self):
        """Test that create_extension_token returns valid token data."""
        token_data = ExtensionTokenService.create_extension_token(self.user)

        self.assertIsNotNone(token_data.api_token)
        self.assertIsNotNone(token_data.api_token_str)
        self.assertTrue(token_data.api_token_str.startswith('tt_'))

    def test_get_extension_tokens_empty(self):
        """Test getting extension tokens when none exist."""
        tokens = ExtensionTokenService.get_extension_tokens(self.user)

        self.assertEqual(len(tokens), 0)

    def test_get_extension_tokens_returns_only_extension_tokens(self):
        """Test that only tokens with extension prefix are returned."""
        from tt.apps.api.services import APITokenService

        # Create a regular token (not extension)
        APITokenService.create_token(self.user, 'My Custom Token')

        # Create an extension token
        ExtensionTokenService.create_extension_token(self.user)

        tokens = ExtensionTokenService.get_extension_tokens(self.user)

        # Should only return the extension token
        self.assertEqual(len(tokens), 1)
        self.assertTrue(tokens[0].name.startswith(ExtensionTokenService.TOKEN_NAME_PREFIX))

    def test_get_extension_tokens_ordering(self):
        """Test that extension tokens are returned in reverse chronological order."""
        # Create two tokens
        ExtensionTokenService.create_extension_token(self.user, platform='First')
        ExtensionTokenService.create_extension_token(self.user, platform='Second')

        tokens = ExtensionTokenService.get_extension_tokens(self.user)

        self.assertEqual(len(tokens), 2)
        # Most recent should be first
        self.assertIn('Second', tokens[0].name)
        self.assertIn('First', tokens[1].name)

    def test_name_generation_includes_date(self):
        """Test that token name includes month and year format."""
        import re

        name = ExtensionTokenService.generate_token_name(self.user)

        # Should contain a month-year pattern like "Dec 2025"
        self.assertTrue(re.search(r'[A-Z][a-z]{2} \d{4}', name))
