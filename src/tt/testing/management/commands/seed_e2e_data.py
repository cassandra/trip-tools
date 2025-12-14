"""
Management command to seed test data for E2E testing.

This command creates a known test user that Playwright tests can use
to authenticate via the /testing/signin/ endpoint.

Usage:
    ./src/manage.py seed_e2e_data

The command is idempotent - running it multiple times is safe.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command( BaseCommand ):
    help = 'Seed test data for E2E testing with Playwright'

    # Default test user credentials
    # These should match the values in testing/e2e/extension-simulation/fixtures/auth.js
    DEFAULT_TEST_EMAIL = 'e2e-test@example.com'
    DEFAULT_TEST_FIRST_NAME = 'E2E'
    DEFAULT_TEST_LAST_NAME = 'TestUser'

    def add_arguments( self, parser ):
        parser.add_argument(
            '--email',
            default=self.DEFAULT_TEST_EMAIL,
            help=f'Email for test user (default: {self.DEFAULT_TEST_EMAIL})'
        )
        parser.add_argument(
            '--first-name',
            default=self.DEFAULT_TEST_FIRST_NAME,
            help=f'First name for test user (default: {self.DEFAULT_TEST_FIRST_NAME})'
        )
        parser.add_argument(
            '--last-name',
            default=self.DEFAULT_TEST_LAST_NAME,
            help=f'Last name for test user (default: {self.DEFAULT_TEST_LAST_NAME})'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output messages'
        )

    def handle( self, *args, **options ):
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR( 'This command only runs in DEBUG mode' )
            )
            return

        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']
        quiet = options['quiet']

        User = get_user_model()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'email_verified': True,
            }
        )

        if not created:
            # Update existing user to ensure consistent state
            user.first_name = first_name
            user.last_name = last_name
            user.email_verified = True
            user.is_active = True
            user.save()

        if not quiet:
            action = 'Created' if created else 'Updated'
            password = getattr( settings, 'E2E_TEST_PASSWORD', '(not set)' )
            self.stdout.write(
                self.style.SUCCESS( f'{action} E2E test user: {email}' )
            )
            self.stdout.write( '' )
            self.stdout.write( 'E2E test targets (servers start automatically):' )
            self.stdout.write( '  make test-e2e                    - Run all E2E tests' )
            self.stdout.write( '  make test-e2e-webapp-extension-none  - Webapp without extension' )
            self.stdout.write( '  make test-e2e-webapp-extension-sim   - Webapp with simulated extension' )
            self.stdout.write( '  make test-e2e-extension-isolated     - Extension with mock server' )
            self.stdout.write( '  make test-e2e-webapp-extension-real  - Webapp with real extension' )
            self.stdout.write( '' )
            self.stdout.write( 'Test signin endpoint: /testing/signin/' )
            self.stdout.write( f'Test password: {password}' )
