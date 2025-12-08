/**
 * Tests for the Chrome extension authorization flow with mock server.
 *
 * Tests the extension's behavior when receiving tokens and validating with the server.
 * Uses a Python mock server with profile-controlled responses.
 *
 * IMPORTANT: Extensions require chromium.launchPersistentContext() to work properly.
 * Regular Playwright contexts cannot load Chrome extensions.
 */
const { test: base, expect, chromium, request: apiRequest } = require( '@playwright/test' );
const path = require( 'path' );
const {
    setExtensionStorage,
    getExtensionAuthState,
    waitForExtensionState,
} = require( './fixtures/extension-helpers' );

// Extension path (resolved from this file's location)
const extensionPath = path.resolve( __dirname, '../../../tools/chrome' );

// Mock server URL
const MOCK_SERVER_URL = 'http://localhost:6779';

// Test page URL - matches extension's content_scripts pattern
const TEST_PAGE_URL = `${MOCK_SERVER_URL}/user/extensions/`;

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
    // Add a request fixture for API calls to the mock server
    request: async ({}, use) => {
        const requestContext = await apiRequest.newContext({
            baseURL: MOCK_SERVER_URL,
        });
        await use( requestContext );
        await requestContext.dispose();
    },
});

test.describe( 'Extension Authorization Flow', () => {

    test.beforeEach( async ({ context, request }) => {
        // Wait for extension service worker to be ready
        await waitForServiceWorker( context );

        // Configure extension to use mock server
        await setExtensionStorage( context, {
            tt_serverUrl: MOCK_SERVER_URL
        });

        // Reset to default profile
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });
    });

    test( 'valid token authorizes extension', async ({ page, request }) => {
        // Set profile for successful auth
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });

        // Navigate to test page
        await page.goto( TEST_PAGE_URL );

        // Wait for extension content script to load
        await waitForExtensionState( page, 'tt-ext-not-authorized' );

        // Send token to extension via test helper
        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_abcdefghijklmnopqrstuvwxyz' );
        });

        // Wait for ack from extension
        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Verify ack indicates success - this confirms extension validated token with server
        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack ).not.toBeNull();
        expect( ack.payload.success ).toBe( true );
        expect( ack.payload.error ).toBeNull();
    });

    test( 'invalid token is rejected with 401', async ({ page, context, request }) => {
        // Set profile for 401 unauthorized
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_401' }
        });

        await page.goto( TEST_PAGE_URL );
        await waitForExtensionState( page, 'tt-ext-not-authorized' );

        // Send token
        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_invalidtokenvalue' );
        });

        // Wait for ack (should indicate failure)
        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack.payload.success ).toBe( false );
        expect( ack.payload.error ).toBeTruthy();

        // Verify no token stored in extension
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'not_authorized' );
        expect( state.tt_apiToken ).toBeUndefined();
    });

    test( 'server error is handled gracefully', async ({ page, context, request }) => {
        // Set profile for 500 server error
        await request.post( '/__test__/profile', {
            data: { profile: 'server_error' }
        });

        await page.goto( TEST_PAGE_URL );
        await waitForExtensionState( page, 'tt-ext-not-authorized' );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validformattoken' );
        });

        // Wait for ack
        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Extension should report failure
        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack.payload.success ).toBe( false );
        expect( ack.payload.error ).toBeTruthy();

        // Verify extension is not authorized
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'not_authorized' );
    });

    test( 'network timeout is handled', async ({ page, request }) => {
        // Set profile for timeout (10s delay)
        await request.post( '/__test__/profile', {
            data: { profile: 'timeout' }
        });

        await page.goto( TEST_PAGE_URL );
        await waitForExtensionState( page, 'tt-ext-not-authorized' );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validformattoken' );
        });

        // Wait for ack with extended timeout (extension has 5s timeout)
        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 15000 } );

        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack.payload.success ).toBe( false );
    });

    test( 'malformed token is rejected without API call', async ({ page, context }) => {
        // No profile change needed - should fail before making request

        await page.goto( TEST_PAGE_URL );
        await waitForExtensionState( page, 'tt-ext-not-authorized' );

        // Send malformed token (doesn't start with tt_)
        await page.evaluate( () => {
            window.sendTokenToExtension( 'invalid_format_token' );
        });

        // Wait for ack
        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 5000 } );

        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack.payload.success ).toBe( false );

        // Verify no token stored
        const state = await getExtensionAuthState( context );
        expect( state.tt_apiToken ).toBeUndefined();
    });

    test( 'token with wrong format is rejected', async ({ page }) => {
        await page.goto( TEST_PAGE_URL );
        await waitForExtensionState( page, 'tt-ext-not-authorized' );

        // Send token with wrong structure (tt_ prefix but wrong format)
        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_tooshort' );
        });

        // Wait for ack
        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 5000 } );

        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack.payload.success ).toBe( false );
    });

});

/**
 * Waits for the extension service worker to be registered.
 * Must be called after creating a persistent context with the extension loaded.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @param {number} [timeout=10000] - Maximum wait time in ms
 */
async function waitForServiceWorker( context, timeout = 10000 ) {
    const startTime = Date.now();

    while ( ( Date.now() - startTime ) < timeout ) {
        const workers = context.serviceWorkers();
        const ttWorker = workers.find( w => w.url().includes( 'service-worker.js' ) );
        if ( ttWorker ) {
            return ttWorker;
        }
        await new Promise( resolve => setTimeout( resolve, 200 ) );
    }

    throw new Error(
        `Extension service worker not found after ${timeout}ms. ` +
        'Ensure the extension is loaded correctly.'
    );
}
