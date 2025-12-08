/**
 * Initial integration tests for webapp + real extension.
 *
 * These tests verify basic functionality with the real Chrome extension
 * loaded against the real Django server.
 *
 * IMPORTANT: Extensions require chromium.launchPersistentContext() to work properly.
 */
const { test: base, expect, chromium } = require( '@playwright/test' );
const path = require( 'path' );
const { getExtensionId, waitForServiceWorker } = require( './fixtures/extension-helpers' );

// Extension path (resolved from this file's location)
const extensionPath = path.resolve( __dirname, '../../../tools/chrome' );

// Django server URL
const DJANGO_URL = 'http://localhost:6778';

// Create a test fixture that uses persistent context for extension loading
const test = base.extend({
    // Override context to use launchPersistentContext (required for extensions)
    context: async ({}, use) => {
        const userDataDir = `/tmp/test-user-data-${Date.now()}`;
        const context = await chromium.launchPersistentContext( userDataDir, {
            headless: false,
            args: [
                `--disable-extensions-except=${extensionPath}`,
                `--load-extension=${extensionPath}`,
            ],
        });
        await use( context );
        await context.close();
    },
    // Override page to use the persistent context's page
    page: async ({ context }, use) => {
        const page = context.pages()[0] || await context.newPage();
        await use( page );
    },
});

test.describe( 'Initial Integration Tests', () => {

    test.beforeEach( async ({ context }) => {
        // Wait for extension service worker to be ready
        await waitForServiceWorker( context );
    });

    test( 'home page loads with sign-in button for anonymous user', async ({ page }) => {
        await page.goto( DJANGO_URL + '/' );

        // Check page loads successfully
        await expect( page ).toHaveTitle( /Trip Tools/ );

        // Anonymous users should see sign-in button
        const signInButton = page.locator( 'a:has-text("Sign In")' );
        await expect( signInButton ).toBeVisible();
    });

    test( 'extension options page shows not connected', async ({ context }) => {
        const extensionId = await getExtensionId( context );
        const optionsUrl = `chrome-extension://${extensionId}/options/options.html`;

        const page = await context.newPage();
        await page.goto( optionsUrl );

        // Verify options page loads with title
        await expect( page.locator( 'h1' ) ).toHaveText( 'Trip Tools Extension - Options' );

        // Verify shows "not authorized" state (not hidden)
        const notAuthorizedSection = page.locator( '#tt-options-auth-not-authorized' );
        await expect( notAuthorizedSection ).toBeVisible();

        // Verify "Authorize Extension" button is present
        const authorizeBtn = page.locator( '#tt-options-authorize-btn' );
        await expect( authorizeBtn ).toBeVisible();
        await expect( authorizeBtn ).toHaveText( 'Authorize Extension' );
    });

});
