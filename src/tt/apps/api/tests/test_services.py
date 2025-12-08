"""
Tests for API token service business logic.

Focuses on high-value testing of:
- Token creation and format validation
- Authentication logic and security (constant-time comparison)
- Hash verification
- Usage tracking integration
"""
import hashlib
import logging
import secrets
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.api.enums import TokenType
from tt.apps.api.models import APIToken
from tt.apps.api.services import APITokenService

logging.disable(logging.CRITICAL)

User = get_user_model()


class APITokenServiceTestCase(TestCase):
    """Test APITokenService business logic and security."""

    def setUp(self):
        """Create test user for token operations."""
        from tt.apps.common import datetimeproxy
        datetimeproxy.reset()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )

    def tearDown(self):
        """Reset time after test."""
        from tt.apps.common import datetimeproxy
        datetimeproxy.reset()

    # -------------------------------------------------------------------------
    # Token Creation Tests
    # -------------------------------------------------------------------------

    def test_create_token_generates_valid_format(self):
        """Test create_token generates token with correct tt_{lookup_key}_{secret_key} format."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Verify token string format
        self.assertTrue(result.api_token_str.startswith('tt_'))
        parts = result.api_token_str.split('_', 2)
        self.assertEqual(len(parts), 3, 'Token should have format tt_{lookup_key}_{secret_key}')
        self.assertEqual(parts[0], 'tt')

        # Verify lookup key length (8 chars)
        lookup_key = parts[1]
        self.assertEqual(len(lookup_key), 8)

        # Verify secret key exists and is substantial
        secret_key = parts[2]
        self.assertGreater(len(secret_key), 20, 'Secret key should be substantial length')

    def test_create_token_stores_hashed_not_plaintext(self):
        """Test create_token stores hashed token, never plaintext."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Verify database record exists
        db_token = APIToken.objects.get(pk=result.api_token.pk)

        # Verify plaintext token is NOT stored in database
        self.assertNotEqual(db_token.api_token_hash, result.api_token_str)

        # Verify stored value is a hash (SHA256 hex is 64 chars)
        self.assertEqual(len(db_token.api_token_hash), 64)

        # Verify hash matches what we expect
        expected_hash = hashlib.sha256(result.api_token_str.encode()).hexdigest()
        self.assertEqual(db_token.api_token_hash, expected_hash)

    def test_create_token_stores_correct_lookup_key(self):
        """Test create_token extracts and stores correct lookup_key."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Extract lookup_key from token string
        parts = result.api_token_str.split('_', 2)
        lookup_key_from_token = parts[1]

        # Verify it matches database record
        self.assertEqual(result.api_token.lookup_key, lookup_key_from_token)

    def test_create_token_stores_user_and_name(self):
        """Test create_token stores correct user and token name."""
        token_name = 'Chrome Extension'
        result = APITokenService.create_token(self.user, token_name)

        # Verify database record has correct associations
        db_token = APIToken.objects.get(pk=result.api_token.pk)
        self.assertEqual(db_token.user, self.user)
        self.assertEqual(db_token.name, token_name)

    def test_create_token_generates_unique_tokens(self):
        """Test create_token generates unique tokens each time."""
        result1 = APITokenService.create_token(self.user, 'Token 1')
        result2 = APITokenService.create_token(self.user, 'Token 2')

        # Tokens should be different
        self.assertNotEqual(result1.api_token_str, result2.api_token_str)
        self.assertNotEqual(result1.api_token.lookup_key, result2.api_token.lookup_key)
        self.assertNotEqual(result1.api_token.api_token_hash, result2.api_token.api_token_hash)

    # -------------------------------------------------------------------------
    # Authentication Tests - Valid Tokens
    # -------------------------------------------------------------------------

    def test_authenticate_returns_user_for_valid_token(self):
        """Test authenticate returns user for valid token."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Authenticate with valid token
        authenticated_user = APITokenService.authenticate(result.api_token_str)

        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user, self.user)

    def test_authenticate_calls_record_usage_on_success(self):
        """Test authenticate calls record_usage() on successful authentication."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Mock record_usage to verify it's called
        with patch.object(APIToken, 'record_usage') as mock_record_usage:
            authenticated_user = APITokenService.authenticate(result.api_token_str)

            # Verify record_usage was called
            self.assertIsNotNone(authenticated_user)
            mock_record_usage.assert_called_once()

    # -------------------------------------------------------------------------
    # Authentication Tests - Invalid Tokens
    # -------------------------------------------------------------------------

    def test_authenticate_returns_none_for_invalid_token(self):
        """Test authenticate returns None for token with wrong secret."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Create invalid token by changing secret portion
        parts = result.api_token_str.split('_', 2)
        invalid_token = f"tt_{parts[1]}_wrongsecret123456789012345678901234567890"

        authenticated_user = APITokenService.authenticate(invalid_token)

        self.assertIsNone(authenticated_user)

    def test_authenticate_returns_none_for_wrong_prefix(self):
        """Test authenticate returns None for token without tt_ prefix."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Remove tt_ prefix
        invalid_token = result.api_token_str[3:]  # Remove 'tt_'

        authenticated_user = APITokenService.authenticate(invalid_token)

        self.assertIsNone(authenticated_user)

    def test_authenticate_returns_none_for_wrong_format_missing_parts(self):
        """Test authenticate returns None for malformed token (wrong number of parts)."""
        # Token with only 2 parts instead of 3
        malformed_token = 'tt_onlyonepart'

        authenticated_user = APITokenService.authenticate(malformed_token)

        self.assertIsNone(authenticated_user)

    def test_authenticate_returns_none_for_empty_token(self):
        """Test authenticate returns None for empty token string."""
        authenticated_user = APITokenService.authenticate('')

        self.assertIsNone(authenticated_user)

    def test_authenticate_returns_none_for_none_token(self):
        """Test authenticate returns None for None token."""
        authenticated_user = APITokenService.authenticate(None)

        self.assertIsNone(authenticated_user)

    def test_authenticate_returns_none_for_nonexistent_lookup_key(self):
        """Test authenticate returns None when lookup_key doesn't exist in database."""
        # Create token with format that looks valid but doesn't exist
        fake_token = f"tt_notexist_{secrets.token_urlsafe(30)}"

        authenticated_user = APITokenService.authenticate(fake_token)

        self.assertIsNone(authenticated_user)

    # -------------------------------------------------------------------------
    # Security Tests
    # -------------------------------------------------------------------------

    def test_authenticate_uses_constant_time_comparison(self):
        """Test authenticate uses secrets.compare_digest for timing attack protection."""
        result = APITokenService.create_token(self.user, 'Test Token')

        # Mock secrets.compare_digest to verify it's being used
        with patch('tt.apps.api.services.secrets.compare_digest', wraps=secrets.compare_digest) as mock_compare:
            mock_compare.return_value = True  # Force success

            authenticated_user = APITokenService.authenticate(result.api_token_str)

            # Verify compare_digest was called
            self.assertIsNotNone(authenticated_user)
            mock_compare.assert_called_once()

            # Verify it was called with the hash values
            call_args = mock_compare.call_args[0]
            self.assertEqual(len(call_args), 2)
            # Both arguments should be 64-char SHA256 hashes
            self.assertEqual(len(call_args[0]), 64)
            self.assertEqual(len(call_args[1]), 64)

    def test_hash_algorithm_produces_consistent_results(self):
        """Test _hash_api_token_str produces consistent SHA256 hashes."""
        token_str = 'tt_testkey1_testsecret123456789012345678901234567890'

        hash1 = APITokenService._hash_api_token_str(token_str)
        hash2 = APITokenService._hash_api_token_str(token_str)

        # Hashes should be identical for same input
        self.assertEqual(hash1, hash2)

        # Should be valid SHA256 hex (64 chars)
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))

    # -------------------------------------------------------------------------
    # Multiple Tokens Tests
    # -------------------------------------------------------------------------

    def test_authenticate_works_with_multiple_tokens_same_user(self):
        """Test authenticate correctly handles multiple tokens for same user."""
        result1 = APITokenService.create_token(self.user, 'Token 1')
        result2 = APITokenService.create_token(self.user, 'Token 2')

        # Both tokens should authenticate correctly
        user1 = APITokenService.authenticate(result1.api_token_str)
        user2 = APITokenService.authenticate(result2.api_token_str)

        self.assertEqual(user1, self.user)
        self.assertEqual(user2, self.user)

    def test_authenticate_works_with_multiple_users(self):
        """Test authenticate correctly handles tokens from different users."""
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass123'
        )

        result1 = APITokenService.create_token(self.user, 'User 1 Token')
        result2 = APITokenService.create_token(user2, 'User 2 Token')

        # Each token should return its own user
        authenticated_user1 = APITokenService.authenticate(result1.api_token_str)
        authenticated_user2 = APITokenService.authenticate(result2.api_token_str)

        self.assertEqual(authenticated_user1, self.user)
        self.assertEqual(authenticated_user2, user2)
        self.assertNotEqual(authenticated_user1, authenticated_user2)

    # -------------------------------------------------------------------------
    # Token Limit Tests
    # -------------------------------------------------------------------------

    def test_user_token_count_returns_zero_for_new_user(self):
        """Test user_token_count returns 0 for user with no tokens."""
        count = APITokenService.user_token_count( self.user )
        self.assertEqual( count, 0 )

    def test_user_token_count_returns_correct_count(self):
        """Test user_token_count returns accurate count after creating tokens."""
        APITokenService.create_token( self.user, 'Token 1' )
        APITokenService.create_token( self.user, 'Token 2' )
        APITokenService.create_token( self.user, 'Token 3' )

        count = APITokenService.user_token_count( self.user )
        self.assertEqual( count, 3 )

    def test_can_create_token_returns_true_under_limit(self):
        """Test can_create_token returns True when user is under token limit."""
        # User has no tokens, should be able to create
        self.assertTrue( APITokenService.can_create_token( self.user ) )

        # Create a few tokens, still under limit
        for i in range( 5 ):
            APITokenService.create_token( self.user, f'Token {i}' )

        self.assertTrue( APITokenService.can_create_token( self.user ) )

    def test_can_create_token_returns_false_at_limit(self):
        """Test can_create_token returns False when user is at token limit."""
        # Create tokens up to the limit
        for i in range( APITokenService.MAX_TOKENS_PER_USER ):
            APITokenService.create_token( self.user, f'Token {i}' )

        # Should not be able to create more
        self.assertFalse( APITokenService.can_create_token( self.user ) )

    def test_can_create_token_respects_max_tokens_per_user_constant(self):
        """Test MAX_TOKENS_PER_USER constant is reasonable and respected."""
        # Verify the constant exists and is sensible
        self.assertIsInstance( APITokenService.MAX_TOKENS_PER_USER, int )
        self.assertGreater( APITokenService.MAX_TOKENS_PER_USER, 0 )
        self.assertLessEqual( APITokenService.MAX_TOKENS_PER_USER, 1000 )

    # -------------------------------------------------------------------------
    # Token Type Tests
    # -------------------------------------------------------------------------

    def test_create_token_defaults_to_standard_type(self):
        """Test create_token defaults to STANDARD token type."""
        result = APITokenService.create_token( self.user, 'Test Token' )

        self.assertEqual( result.api_token.token_type, TokenType.STANDARD )

    def test_create_token_with_explicit_standard_type(self):
        """Test create_token with explicit STANDARD type."""
        result = APITokenService.create_token(
            self.user,
            'Test Token',
            token_type = TokenType.STANDARD,
        )

        self.assertEqual( result.api_token.token_type, TokenType.STANDARD )

    def test_create_token_with_extension_type(self):
        """Test create_token with EXTENSION type."""
        result = APITokenService.create_token(
            self.user,
            'Extension Token',
            token_type = TokenType.EXTENSION,
        )

        self.assertEqual( result.api_token.token_type, TokenType.EXTENSION )

    def test_token_type_persists_in_database(self):
        """Test that token_type is correctly stored and retrieved from database."""
        result = APITokenService.create_token(
            self.user,
            'Extension Token',
            token_type = TokenType.EXTENSION,
        )

        # Refresh from database
        db_token = APIToken.objects.get( pk = result.api_token.pk )

        self.assertEqual( db_token.token_type, TokenType.EXTENSION )

    # -------------------------------------------------------------------------
    # name_exists() Tests
    # -------------------------------------------------------------------------

    def test_name_exists_returns_true_when_name_exists(self):
        """Test name_exists returns True when token name exists for user."""
        APITokenService.create_token( self.user, 'My Token' )

        self.assertTrue( APITokenService.name_exists( self.user, 'My Token' ) )

    def test_name_exists_returns_false_when_name_does_not_exist(self):
        """Test name_exists returns False when token name doesn't exist."""
        self.assertFalse( APITokenService.name_exists( self.user, 'Nonexistent Token' ) )

    def test_name_exists_only_checks_current_user(self):
        """Test name_exists only checks tokens for the specified user."""
        user2 = User.objects.create_user(
            email = 'user2@example.com',
            password = 'testpass123'
        )
        APITokenService.create_token( user2, 'Shared Name' )

        # Same name should not exist for self.user
        self.assertFalse( APITokenService.name_exists( self.user, 'Shared Name' ) )

    # -------------------------------------------------------------------------
    # get_token_by_lookup_key() Tests
    # -------------------------------------------------------------------------

    def test_get_token_by_lookup_key_returns_token_when_found(self):
        """Test get_token_by_lookup_key returns token when exactly one match."""
        result = APITokenService.create_token( self.user, 'Test Token' )
        lookup_key = result.api_token.lookup_key

        token, error = APITokenService.get_token_by_lookup_key( self.user, lookup_key )

        self.assertIsNotNone( token )
        self.assertIsNone( error )
        self.assertEqual( token.pk, result.api_token.pk )

    def test_get_token_by_lookup_key_returns_error_when_not_found(self):
        """Test get_token_by_lookup_key returns error when no match."""
        token, error = APITokenService.get_token_by_lookup_key( self.user, 'nonexist' )

        self.assertIsNone( token )
        self.assertEqual( error, 'Token not found' )

    def test_get_token_by_lookup_key_returns_error_for_other_users_token(self):
        """Test get_token_by_lookup_key doesn't return another user's token."""
        user2 = User.objects.create_user(
            email = 'user2@example.com',
            password = 'testpass123'
        )
        result = APITokenService.create_token( user2, 'Other User Token' )

        # Try to get user2's token as self.user
        token, error = APITokenService.get_token_by_lookup_key(
            self.user,
            result.api_token.lookup_key,
        )

        self.assertIsNone( token )
        self.assertEqual( error, 'Token not found' )

    def test_get_token_by_lookup_key_sanitizes_input(self):
        """Test get_token_by_lookup_key sanitizes lookup_key input."""
        result = APITokenService.create_token( self.user, 'Test Token' )
        lookup_key = result.api_token.lookup_key

        # Add whitespace to lookup_key - should still work after sanitization
        token, error = APITokenService.get_token_by_lookup_key(
            self.user,
            f'  {lookup_key}  ',
        )

        self.assertIsNotNone( token )
        self.assertIsNone( error )

    def test_get_token_by_lookup_key_returns_error_on_duplicates(self):
        """Test get_token_by_lookup_key returns error when duplicates found."""
        result = APITokenService.create_token( self.user, 'Test Token' )
        lookup_key = result.api_token.lookup_key

        # Manually create a duplicate (should never happen normally)
        APIToken.objects.create(
            user = self.user,
            name = 'Duplicate Token',
            lookup_key = lookup_key,
            api_token_hash = 'different_hash_12345678901234567890123456789012345678901234567890123456',
        )

        token, error = APITokenService.get_token_by_lookup_key( self.user, lookup_key )

        self.assertIsNone( token )
        self.assertEqual( error, 'Unable to process token. Please contact support.' )

    # -------------------------------------------------------------------------
    # delete_token() Tests
    # -------------------------------------------------------------------------

    def test_delete_token_deletes_token_when_found(self):
        """Test delete_token successfully deletes token."""
        result = APITokenService.create_token( self.user, 'To Delete' )
        lookup_key = result.api_token.lookup_key

        success, error = APITokenService.delete_token( self.user, lookup_key )

        self.assertTrue( success )
        self.assertIsNone( error )
        self.assertFalse( APIToken.objects.filter( lookup_key = lookup_key ).exists() )

    def test_delete_token_returns_error_when_not_found(self):
        """Test delete_token returns error when token doesn't exist."""
        success, error = APITokenService.delete_token( self.user, 'nonexist' )

        self.assertFalse( success )
        self.assertEqual( error, 'Token not found' )

    def test_delete_token_refuses_when_duplicates_exist(self):
        """Test delete_token refuses to delete when duplicates exist."""
        result = APITokenService.create_token( self.user, 'Test Token' )
        lookup_key = result.api_token.lookup_key

        # Manually create a duplicate
        APIToken.objects.create(
            user = self.user,
            name = 'Duplicate Token',
            lookup_key = lookup_key,
            api_token_hash = 'different_hash_12345678901234567890123456789012345678901234567890123456',
        )

        success, error = APITokenService.delete_token( self.user, lookup_key )

        self.assertFalse( success )
        self.assertEqual( error, 'Unable to process token. Please contact support.' )
        # Both tokens should still exist
        self.assertEqual( APIToken.objects.filter( lookup_key = lookup_key ).count(), 2 )

    def test_delete_token_does_not_delete_other_users_token(self):
        """Test delete_token doesn't delete another user's token."""
        user2 = User.objects.create_user(
            email = 'user2@example.com',
            password = 'testpass123'
        )
        result = APITokenService.create_token( user2, 'Other User Token' )

        success, error = APITokenService.delete_token(
            self.user,
            result.api_token.lookup_key,
        )

        self.assertFalse( success )
        self.assertEqual( error, 'Token not found' )
        # Token should still exist
        self.assertTrue( APIToken.objects.filter( pk = result.api_token.pk ).exists() )

    # -------------------------------------------------------------------------
    # list_tokens() Tests
    # -------------------------------------------------------------------------

    def test_list_tokens_returns_all_tokens_when_no_filter(self):
        """Test list_tokens returns all tokens when no type filter."""
        APITokenService.create_token( self.user, 'Standard 1', TokenType.STANDARD )
        APITokenService.create_token( self.user, 'Extension 1', TokenType.EXTENSION )
        APITokenService.create_token( self.user, 'Standard 2', TokenType.STANDARD )

        tokens = APITokenService.list_tokens( self.user )

        self.assertEqual( tokens.count(), 3 )

    def test_list_tokens_filters_by_standard_type(self):
        """Test list_tokens returns only STANDARD tokens when filtered."""
        APITokenService.create_token( self.user, 'Standard 1', TokenType.STANDARD )
        APITokenService.create_token( self.user, 'Extension 1', TokenType.EXTENSION )
        APITokenService.create_token( self.user, 'Standard 2', TokenType.STANDARD )

        tokens = APITokenService.list_tokens( self.user, TokenType.STANDARD )

        self.assertEqual( tokens.count(), 2 )
        for token in tokens:
            self.assertEqual( token.token_type, TokenType.STANDARD )

    def test_list_tokens_filters_by_extension_type(self):
        """Test list_tokens returns only EXTENSION tokens when filtered."""
        APITokenService.create_token( self.user, 'Standard 1', TokenType.STANDARD )
        APITokenService.create_token( self.user, 'Extension 1', TokenType.EXTENSION )
        APITokenService.create_token( self.user, 'Extension 2', TokenType.EXTENSION )

        tokens = APITokenService.list_tokens( self.user, TokenType.EXTENSION )

        self.assertEqual( tokens.count(), 2 )
        for token in tokens:
            self.assertEqual( token.token_type, TokenType.EXTENSION )

    def test_list_tokens_orders_by_created_at_descending(self):
        """Test list_tokens returns tokens ordered by created_at descending."""
        import datetime
        import pytz
        from tt.apps.common import datetimeproxy

        datetimeproxy.set( datetime.datetime( 2024, 1, 1, tzinfo = pytz.UTC ) )
        APITokenService.create_token( self.user, 'First Token' )

        datetimeproxy.set( datetime.datetime( 2024, 1, 2, tzinfo = pytz.UTC ) )
        APITokenService.create_token( self.user, 'Second Token' )

        datetimeproxy.set( datetime.datetime( 2024, 1, 3, tzinfo = pytz.UTC ) )
        APITokenService.create_token( self.user, 'Third Token' )

        tokens = list( APITokenService.list_tokens( self.user ) )

        self.assertEqual( tokens[0].name, 'Third Token' )
        self.assertEqual( tokens[1].name, 'Second Token' )
        self.assertEqual( tokens[2].name, 'First Token' )

    def test_list_tokens_only_returns_current_users_tokens(self):
        """Test list_tokens only returns tokens for specified user."""
        user2 = User.objects.create_user(
            email = 'user2@example.com',
            password = 'testpass123'
        )
        APITokenService.create_token( self.user, 'My Token' )
        APITokenService.create_token( user2, 'Other Token' )

        tokens = APITokenService.list_tokens( self.user )

        self.assertEqual( tokens.count(), 1 )
        self.assertEqual( tokens.first().name, 'My Token' )

    def test_list_tokens_returns_empty_queryset_for_user_with_no_tokens(self):
        """Test list_tokens returns empty queryset for user with no tokens."""
        tokens = APITokenService.list_tokens( self.user )

        self.assertEqual( tokens.count(), 0 )
