"""
Tests for APIToken model business logic.

Focuses on high-value testing of:
- record_usage() throttling logic (15-minute update interval)
- Database write efficiency (avoiding excessive updates)
"""
from datetime import timedelta
import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from tt.apps.api.models import APIToken
from tt.apps.common import datetimeproxy

logging.disable(logging.CRITICAL)

User = get_user_model()


class APITokenRecordUsageThrottlingTestCase(TestCase):
    """Test APIToken.record_usage() throttling behavior."""

    def setUp(self):
        """Create test user and token."""
        datetimeproxy.reset()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        self.token = APIToken.objects.create(
            user=self.user,
            name='Test Token',
            lookup_key='testkey1',
            api_token_hash='test_hash_value_1234567890abcdef1234567890abcdef12345678'
        )

    def tearDown(self):
        """Reset time after each test."""
        datetimeproxy.reset()

    # -------------------------------------------------------------------------
    # First Use Tests
    # -------------------------------------------------------------------------

    def test_record_usage_updates_when_last_used_at_is_none(self):
        """Test record_usage updates last_used_at on first use (None -> timestamp)."""
        # Verify initial state
        self.assertIsNone(self.token.last_used_at)

        # Record usage
        self.token.record_usage()

        # Refresh from database
        self.token.refresh_from_db()

        # Verify timestamp was set
        self.assertIsNotNone(self.token.last_used_at)

    # -------------------------------------------------------------------------
    # Throttling Tests - Updates After Interval
    # -------------------------------------------------------------------------

    def test_record_usage_updates_when_more_than_15_minutes_passed(self):
        """Test record_usage updates when >15 minutes since last update."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()
        initial_time = self.token.last_used_at

        # Advance time by 20 minutes
        datetimeproxy.increment(minutes=20)

        # Record usage again
        self.token.record_usage()
        self.token.refresh_from_db()

        # Verify timestamp was updated
        self.assertNotEqual(self.token.last_used_at, initial_time)

    def test_record_usage_updates_at_exact_15_minute_boundary(self):
        """Test record_usage updates at exactly >15 minutes (boundary test)."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()
        initial_time = self.token.last_used_at

        # Advance time by exactly 15 minutes + 1 second
        datetimeproxy.increment(minutes=15, seconds=1)

        # Record usage again
        self.token.record_usage()
        self.token.refresh_from_db()

        # Verify timestamp was updated (>15 minutes means update)
        self.assertNotEqual(self.token.last_used_at, initial_time)

    # -------------------------------------------------------------------------
    # Throttling Tests - No Updates Within Interval
    # -------------------------------------------------------------------------

    def test_record_usage_does_not_update_when_less_than_15_minutes_passed(self):
        """Test record_usage does NOT update when <15 minutes since last update."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()
        initial_time = self.token.last_used_at

        # Advance time by only 5 minutes
        datetimeproxy.increment(minutes=5)

        # Record usage again
        self.token.record_usage()
        self.token.refresh_from_db()

        # Verify timestamp was NOT updated
        self.assertEqual(self.token.last_used_at, initial_time)

    def test_record_usage_does_not_update_when_just_used(self):
        """Test record_usage does NOT update when just used (0 minutes ago)."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()
        initial_time = self.token.last_used_at

        # Record usage immediately (no time advancement)
        self.token.record_usage()
        self.token.refresh_from_db()

        # Verify timestamp was NOT updated
        self.assertEqual(self.token.last_used_at, initial_time)

    def test_record_usage_does_not_update_at_14_minutes_59_seconds(self):
        """Test record_usage does NOT update just before 15-minute threshold."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()
        initial_time = self.token.last_used_at

        # Advance time by 14 minutes 59 seconds (just under threshold)
        datetimeproxy.increment(minutes=14, seconds=59)

        # Record usage again
        self.token.record_usage()
        self.token.refresh_from_db()

        # Verify timestamp was NOT updated
        self.assertEqual(self.token.last_used_at, initial_time)

    # -------------------------------------------------------------------------
    # Database Write Efficiency Tests
    # -------------------------------------------------------------------------

    def test_record_usage_minimizes_database_writes(self):
        """Test record_usage avoids unnecessary DB writes within throttle interval."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()

        # Advance time by only 1 minute
        datetimeproxy.increment(minutes=1)

        # Mock save to count calls
        with patch.object(APIToken, 'save') as mock_save:
            self.token.record_usage()

            # save() should NOT be called when within throttle interval
            mock_save.assert_not_called()

    def test_record_usage_calls_save_when_update_needed(self):
        """Test record_usage calls save() when update is needed."""
        # Set initial last_used_at
        self.token.record_usage()
        self.token.refresh_from_db()

        # Advance time by 20 minutes
        datetimeproxy.increment(minutes=20)

        # Mock save to verify it's called
        with patch.object(APIToken, 'save') as mock_save:
            self.token.record_usage()

            # save() should be called once with update_fields
            mock_save.assert_called_once()
            call_kwargs = mock_save.call_args[1]
            self.assertEqual(call_kwargs.get('update_fields'), ['last_used_at'])

    def test_record_usage_uses_update_fields_optimization(self):
        """Test record_usage uses update_fields for efficient DB writes."""
        # First use (last_used_at is None)
        self.assertIsNone(self.token.last_used_at)

        with patch.object(APIToken, 'save') as mock_save:
            self.token.record_usage()

            # Verify save was called with update_fields
            mock_save.assert_called_once()
            call_kwargs = mock_save.call_args[1]
            self.assertIn('update_fields', call_kwargs)
            self.assertEqual(call_kwargs['update_fields'], ['last_used_at'])

    # -------------------------------------------------------------------------
    # Multiple Token Tests
    # -------------------------------------------------------------------------

    def test_record_usage_independent_per_token(self):
        """Test record_usage throttling is independent for each token."""
        # Create second token
        token2 = APIToken.objects.create(
            user=self.user,
            name='Second Token',
            lookup_key='testkey2',
            api_token_hash='test_hash_value_different1234567890abcdef1234567890abcdef'
        )

        # Record initial usage for both tokens
        self.token.record_usage()
        token2.record_usage()
        self.token.refresh_from_db()
        token2.refresh_from_db()

        token1_initial_time = self.token.last_used_at
        token2_initial_time = token2.last_used_at

        # Advance time by 10 minutes (within throttle for both)
        datetimeproxy.increment(minutes=10)

        # Update token2's last_used_at directly to simulate it being used 20 min ago
        token2.last_used_at = token2_initial_time - timedelta(minutes=10)
        token2.save()
        token2.refresh_from_db()
        token2_old_time = token2.last_used_at

        # Record usage for both
        self.token.record_usage()
        token2.record_usage()

        # Refresh both from database
        self.token.refresh_from_db()
        token2.refresh_from_db()

        # token1 should NOT be updated (within throttle - only 10 min passed)
        self.assertEqual(self.token.last_used_at, token1_initial_time)

        # token2 SHOULD be updated (beyond throttle - 20 min passed)
        self.assertNotEqual(token2.last_used_at, token2_old_time)

    # -------------------------------------------------------------------------
    # Configuration Tests
    # -------------------------------------------------------------------------

    def test_record_usage_constant_time_interval(self):
        """Test USAGE_UPDATE_INTERVAL is 15 minutes."""
        expected_interval = timedelta(minutes=15)
        self.assertEqual(APIToken.USAGE_UPDATE_INTERVAL, expected_interval)
