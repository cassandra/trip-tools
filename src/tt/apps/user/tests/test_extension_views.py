import logging
import re

from django.contrib.auth import get_user_model
from django.urls import reverse

from tt.apps.api.enums import TokenType
from tt.apps.api.models import APIToken
from tt.apps.user.extension_service import ExtensionTokenService
from tt.environment.constants import TtConst
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

    def test_context_contains_api_token_list(self):
        """Test that context includes extension tokens list."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.get(url)

        self.assertIn('api_token_list', response.context)
        self.assertIsInstance(response.context['api_token_list'], list)

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

    def test_post_returns_json_insert_response(self):
        """Test that POST returns JSON with insert directives for antinode.js."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('insert', data)
        # Should include auth result and token table updates
        self.assertIn(TtConst.EXT_AUTH_RESULT_ID, data['insert'])
        self.assertIn(TtConst.EXT_API_TOKEN_TABLE_ID, data['insert'])

    def test_post_response_contains_token_str(self):
        """Test that POST response JSON includes the token string."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url)

        data = response.json()
        auth_html = data['insert'][TtConst.EXT_AUTH_RESULT_ID]
        # Token should be in the data-token attribute
        self.assertIn('data-token="tt_', auth_html)

    def test_post_response_contains_token_name(self):
        """Test that POST response JSON includes the token name."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url)

        data = response.json()
        auth_html = data['insert'][TtConst.EXT_AUTH_RESULT_ID]
        # Token name should include "Extension" suffix
        self.assertIn('Extension', auth_html)

    def test_browser_passed_through_form(self):
        """Test that browser from POST data is used in token name."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url, {'browser': 'Firefox'})

        self.assertSuccessResponse(response)
        data = response.json()
        auth_html = data['insert'][TtConst.EXT_AUTH_RESULT_ID]
        self.assertIn('Firefox Extension', auth_html)

    def test_invalid_browser_falls_back_to_default(self):
        """Test that invalid browser value is ignored and falls back to default."""
        self.client.force_login(self.user)

        url = reverse('user_extensions')
        response = self.client.post(url, {'browser': 'EvilBrowser<script>'})

        self.assertSuccessResponse(response)
        data = response.json()
        auth_html = data['insert'][TtConst.EXT_AUTH_RESULT_ID]
        # Should use default browser name, not the injected value
        self.assertNotIn('EvilBrowser', auth_html)
        self.assertIn('Browser Extension', auth_html)

    def test_multiple_posts_create_unique_tokens(self):
        """Test that multiple POSTs create tokens with unique names."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')

        # Create first token
        self.client.post(url)

        # Create second token
        response2 = self.client.post(url)
        data = response2.json()
        auth_html = data['insert'][TtConst.EXT_AUTH_RESULT_ID]

        # Second token name should have "(2)" suffix
        self.assertIn('(2)', auth_html)


class TestExtensionTokenService(SyncViewTestCase):
    """Tests for ExtensionTokenService - token name generation and management."""

    def test_generate_token_name_format(self):
        """Test that generated name follows expected format."""
        name = ExtensionTokenService.generate_token_name(self.user)

        # Should use default browser when none provided
        self.assertTrue(name.startswith(f'{ExtensionTokenService.DEFAULT_BROWSER} Extension'))
        # Should contain month/year format (e.g., "Dec 2025")
        self.assertTrue(re.search(r'[A-Z][a-z]{2} \d{4}', name))

    def test_generate_token_name_with_browser(self):
        """Test that browser is included in token name."""
        name = ExtensionTokenService.generate_token_name(self.user, browser='Chrome')

        self.assertTrue(name.startswith('Chrome Extension'))

    def test_generate_token_name_with_various_browsers(self):
        """Test that various valid browsers are correctly used in token names."""
        for browser in ['Firefox', 'Safari', 'Edge', 'Brave', 'Opera', 'Vivaldi']:
            name = ExtensionTokenService.generate_token_name(self.user, browser=browser)
            self.assertTrue(name.startswith(f'{browser} Extension'), f'Failed for {browser}')

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
        """Test that only tokens with token_type=EXTENSION are returned."""
        from tt.apps.api.services import APITokenService

        # Create a regular token (not extension)
        APITokenService.create_token( self.user, 'My Custom Token' )

        # Create an extension token
        ExtensionTokenService.create_extension_token( self.user )

        tokens = ExtensionTokenService.get_extension_tokens( self.user )

        # Should only return the extension token
        self.assertEqual( len( tokens ), 1 )
        self.assertEqual( tokens[0].token_type, TokenType.EXTENSION )

    def test_create_extension_token_sets_token_type(self):
        """Test that created extension token has token_type=EXTENSION."""
        token_data = ExtensionTokenService.create_extension_token( self.user )

        self.assertEqual( token_data.api_token.token_type, TokenType.EXTENSION )

    def test_get_extension_tokens_ordering(self):
        """Test that extension tokens are returned in reverse chronological order."""
        # Create two tokens with different browsers
        ExtensionTokenService.create_extension_token(self.user, browser='Chrome')
        ExtensionTokenService.create_extension_token(self.user, browser='Firefox')

        tokens = ExtensionTokenService.get_extension_tokens(self.user)

        self.assertEqual(len(tokens), 2)
        # Most recent should be first
        self.assertIn('Firefox', tokens[0].name)
        self.assertIn('Chrome', tokens[1].name)

    def test_name_generation_includes_date(self):
        """Test that token name includes month and year format."""
        name = ExtensionTokenService.generate_token_name(self.user)

        # Should contain a month-year pattern like "Dec 2025"
        self.assertTrue(re.search(r'[A-Z][a-z]{2} \d{4}', name))


class TestExtensionsHomeViewTemplateStructure(SyncViewTestCase):
    """Tests that verify DOM elements required for JavaScript hooks exist."""

    def test_auth_result_container_exists(self):
        """Test that the auth result container element exists in GET response."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        expected_id = TtConst.EXT_AUTH_RESULT_ID
        self.assertIn(f'id="{expected_id}"', html)

    def test_post_response_has_token_data_element(self):
        """Test that POST response has element with token data ID and data-token attr."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.post(url)

        # Response is JSON with escaped HTML in insert directives
        content = response.content.decode('utf-8')
        expected_id = TtConst.EXT_TOKEN_DATA_ELEMENT_ID
        # In JSON, quotes are escaped as \"
        self.assertIn(f'id=\\"{expected_id}\\"', content)
        self.assertIn('data-token=\\"tt_', content)

    def test_post_response_has_pending_element(self):
        """Test that POST response has the pending state element."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.post(url)

        # Response is JSON with escaped HTML in insert directives
        content = response.content.decode('utf-8')
        expected_id = TtConst.EXT_AUTH_PENDING_ID
        self.assertIn(f'id=\\"{expected_id}\\"', content)

    def test_post_response_has_success_element(self):
        """Test that POST response has the success state element."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.post(url)

        # Response is JSON with escaped HTML in insert directives
        content = response.content.decode('utf-8')
        expected_id = TtConst.EXT_AUTH_SUCCESS_ID
        self.assertIn(f'id=\\"{expected_id}\\"', content)

    def test_post_response_has_failure_element(self):
        """Test that POST response has the failure/fallback state element."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.post(url)

        # Response is JSON with escaped HTML in insert directives
        content = response.content.decode('utf-8')
        expected_id = TtConst.EXT_AUTH_FAILURE_ID
        self.assertIn(f'id=\\"{expected_id}\\"', content)


class TestExtensionStateVisibilityClasses(SyncViewTestCase):
    """Tests that verify CSS visibility classes are present for state switching."""

    def test_show_not_installed_class_present(self):
        """Test that page has element with not-installed visibility class."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        expected_class = TtConst.EXT_SHOW_NOT_INSTALLED_CLASS
        self.assertIn(f'class="{expected_class}"', html)

    def test_show_not_authorized_class_present(self):
        """Test that page has element with not-authorized visibility class."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        expected_class = TtConst.EXT_SHOW_NOT_AUTHORIZED_CLASS
        # Class may be combined with other classes or ID, so check for the class name
        self.assertIn(expected_class, html)

    def test_show_authorized_class_present(self):
        """Test that page has element with authorized visibility class."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        expected_class = TtConst.EXT_SHOW_AUTHORIZED_CLASS
        self.assertIn(f'class="{expected_class}"', html)


class TestExtensionTokenTableRendering(SyncViewTestCase):
    """Tests for conditional token table rendering."""

    def test_token_table_has_no_token_rows_when_empty(self):
        """Test that token table has no data rows when no tokens exist."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        # Table container exists
        self.assertIn(f'id="{TtConst.EXT_API_TOKEN_TABLE_ID}"', html)
        # No delete links present - use reverse with placeholder to get URL pattern base
        delete_url_base = reverse('user_api_token_delete', kwargs={'lookup_key': 'PLACEHOLDER'})
        delete_url_base = delete_url_base.replace('PLACEHOLDER', '')
        self.assertNotIn(delete_url_base, html)

    def test_token_table_has_token_rows_when_tokens_exist(self):
        """Test that token table has data rows when tokens exist."""
        self.client.force_login(self.user)
        # Create an extension token
        token_data = ExtensionTokenService.create_extension_token(self.user)

        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        # Table should contain a delete link with the token's lookup_key
        delete_url = reverse('user_api_token_extension_disconnect', kwargs={'lookup_key': token_data.api_token.lookup_key})
        self.assertIn(delete_url, html)

    def test_token_row_contains_lookup_key_for_delete(self):
        """Test that token rows have delete links with lookup_key."""
        self.client.force_login(self.user)
        token_data = ExtensionTokenService.create_extension_token(self.user)
        lookup_key = token_data.api_token.lookup_key

        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        # Delete link should contain the lookup_key
        self.assertIn(lookup_key, html)

    def test_token_row_displays_token_name(self):
        """Test that token rows display the token name."""
        self.client.force_login(self.user)
        ExtensionTokenService.create_extension_token(self.user, browser='Vivaldi')

        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        # Token name should contain the browser
        self.assertIn('Vivaldi Extension', html)


class TestJavaScriptConstantsInjection(SyncViewTestCase):
    """Tests that verify TtConst JavaScript object is available."""

    def test_ttconst_object_in_page(self):
        """Test that TtConst JavaScript object is defined in page."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        # TtConst should be defined in a script tag
        self.assertIn('TtConst', html)

    def test_extension_postmessage_constants_in_page(self):
        """Test that extension postMessage type constants are in page."""
        self.client.force_login(self.user)
        url = reverse('user_extensions')
        response = self.client.get(url)

        html = response.content.decode('utf-8')
        # The postMessage types should be present (used in inline script)
        self.assertIn(TtConst.EXT_POSTMESSAGE_DATA_TYPE, html)
        self.assertIn(TtConst.EXT_POSTMESSAGE_ACK_TYPE, html)
