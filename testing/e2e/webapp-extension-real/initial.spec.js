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
const { loginUser, DEFAULT_TEST_EMAIL } = require( '../webapp-extension-sim/fixtures/auth' );

// Extension path (resolved from this file's location)
const extensionPath = path.resolve( __dirname, '../../../tools/extension/src' );

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

    test( 'extension authorization happy path', async ({ context, page }) => {
        // Step 1: Login to Django server
        await page.goto( DJANGO_URL + '/testing/signin/' );
        await page.fill( 'input[name="email"]', DEFAULT_TEST_EMAIL );
        await page.fill( 'input[name="password"]', 'e2e-test-password' );
        await page.click( 'button[type="submit"]' );
        await page.waitForURL( /.*dashboard.*/ );

        // Step 2: Open extension options page and configure server URL
        const extensionId = await getExtensionId( context );
        const optionsUrl = `chrome-extension://${extensionId}/options/options.html`;

        const optionsPage = await context.newPage();
        await optionsPage.goto( optionsUrl );

        // Configure extension to use test server URL (port 6778)
        // The extension defaults to port 6777, but our test server runs on 6778
        await optionsPage.evaluate( ( url ) => {
            return new Promise( ( resolve ) => {
                chrome.storage.local.set( { 'tt_serverUrl': url }, resolve );
            });
        }, DJANGO_URL );

        // Verify shows "not authorized" state
        await expect( optionsPage.locator( '#tt-options-auth-not-authorized' ) ).toBeVisible();

        // Step 3: Click Authorize button - this opens new tab to server
        const [ serverExtPage ] = await Promise.all([
            context.waitForEvent( 'page' ),
            optionsPage.click( '#tt-options-authorize-btn' ),
        ]);

        // Wait for the server extensions page to load
        await serverExtPage.waitForLoadState( 'domcontentloaded' );

        // Step 4: Wait for extension content script to detect and set body class
        // The content script sets tt-ext-not-authorized when extension is detected but not authorized
        await serverExtPage.waitForSelector( 'body.tt-ext-not-authorized', { timeout: 10000 } );

        // Verify the "Authorize Extension" button is visible on server page
        const serverAuthBtn = serverExtPage.locator( 'form[data-async="true"] button[type="submit"]' );
        await expect( serverAuthBtn ).toBeVisible();

        // Step 5: Click Authorize on server page
        await serverAuthBtn.click();

        // Wait for the auth success indicator to appear
        // The server renders extension_authorize_result.html with token data
        // Then the extension receives it via postMessage and acknowledges
        // Note: The async form replaces part of the DOM, element ID is tt-ext-auth-success
        await serverExtPage.waitForSelector( '#tt-ext-auth-success:not(.d-none)', { timeout: 10000 } );

        // Step 6: Verify extension is now authorized
        // Reload the options page to see updated state
        await optionsPage.reload();

        // Verify authorized section is now visible
        await expect( optionsPage.locator( '#tt-options-auth-authorized' ) ).toBeVisible();

        // Verify email is displayed
        const emailDisplay = optionsPage.locator( '#tt-options-auth-email' );
        await expect( emailDisplay ).toHaveText( DEFAULT_TEST_EMAIL );

        // Step 7: Verify server shows token in table
        await serverExtPage.goto( DJANGO_URL + '/user/extensions/' );
        await serverExtPage.waitForLoadState( 'domcontentloaded' );

        // The token table should show a "Chrome Extension" token
        const tokenTable = serverExtPage.locator( '#tt-ext-api-token-table' );
        await expect( tokenTable ).toBeVisible();
        await expect( tokenTable ).toContainText( 'Chrome Extension' );
    });

});
