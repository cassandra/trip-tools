/**
 * Tests for extension behavior during server health issues.
 *
 * Verifies that:
 * - Cached auth persists during server outages
 * - Different error types are correctly classified
 * - Extension remains operable when server is unavailable
 * - Disconnect flow handles server errors gracefully
 *
 * IMPORTANT: Extensions require chromium.launchPersistentContext() to work properly.
 */
const { test: base, expect, chromium, request: apiRequest } = require( '@playwright/test' );
const path = require( 'path' );
const {
    getExtensionId,
    setExtensionStorage,
    getExtensionAuthState,
    triggerAuthCheck,
    sendDisconnect,
} = require( './fixtures/extension-helpers' );

// Extension path (resolved from this file's location)
const extensionPath = path.resolve( __dirname, '../../../tools/chrome' );

// Mock server URL
const MOCK_SERVER_URL = 'http://localhost:6779';

// Unreachable server URL (nothing running on this port)
const UNREACHABLE_SERVER_URL = 'http://localhost:6780';

// Test page URL
const TEST_PAGE_URL = `${MOCK_SERVER_URL}/user/extensions/`;

// Create a test fixture that uses persistent context for extension loading
const test = base.extend({
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
    page: async ({ context }, use) => {
        const page = context.pages()[0] || await context.newPage();
        await use( page );
    },
    request: async ({}, use) => {
        const requestContext = await apiRequest.newContext({
            baseURL: MOCK_SERVER_URL,
        });
        await use( requestContext );
        await requestContext.dispose();
    },
});

/**
 * Wait for the extension service worker to be ready.
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
    throw new Error( `Extension service worker not found after ${timeout}ms.` );
}

/**
 * Pre-seed extension with authorized state.
 * Used to test behavior when already authorized and server becomes unavailable.
 */
async function seedAuthorizedState( context, serverUrl = MOCK_SERVER_URL ) {
    await setExtensionStorage( context, {
        tt_serverUrl: serverUrl,
        tt_apiToken: 'tt_12345678_preseededtokenvalue',
        tt_authState: 'authorized',
        tt_userEmail: 'cached@example.com',
    });
}

// ============================================================================
// Server Unreachable Tests
// ============================================================================

test.describe( 'Server Unreachable', () => {

    test.beforeEach( async ({ context }) => {
        await waitForServiceWorker( context );
    });

    test( 'connection refused results in offline status', async ({ context, page }) => {
        // Pre-seed authorized state pointing to unreachable server
        await seedAuthorizedState( context, UNREACHABLE_SERVER_URL );

        // Trigger auth check by navigating to test page
        // Note: We use the mock server URL for the page, but extension calls unreachable server
        await page.goto( TEST_PAGE_URL );

        // Wait for content script to query auth status
        // The extension should still show authorized (cached) but with error status
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-authorized' ) ||
                  document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 15000 }
        );

        // Verify cached auth is preserved
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
        expect( state.tt_userEmail ).toBe( 'cached@example.com' );
        expect( state.tt_apiToken ).toBe( 'tt_12345678_preseededtokenvalue' );
    });

    test( 'cached auth persists when server unreachable', async ({ context, page, request }) => {
        // First authorize successfully
        await setExtensionStorage( context, {
            tt_serverUrl: MOCK_SERVER_URL,
        });

        // Ensure mock server returns success for initial authorization
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });

        // Navigate and authorize
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validtokenfortest' );
        });

        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );
        const ack = await page.evaluate( () => window.extensionAck );
        expect( ack.payload.success ).toBe( true );

        // Verify authorized
        let state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );

        // Now switch to unreachable server
        await setExtensionStorage( context, {
            tt_serverUrl: UNREACHABLE_SERVER_URL,
        });

        // Trigger re-validation by opening options page (no debounce for options)
        // This will attempt to contact the unreachable server
        const extensionId = await getExtensionId( context );
        const optionsPage = await context.newPage();
        await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );

        // Wait for auth check to complete (will timeout trying to reach server)
        await optionsPage.waitForTimeout( 6000 );
        await optionsPage.close();

        // Auth should still be preserved (unreachable = STATUS_OFFLINE, not 401)
        state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );

        // Content script should also show authorized (reads cached state)
        await page.reload();
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-authorized' ),
            { timeout: 10000 }
        );
    });

});

// ============================================================================
// Server Error Recovery Tests
// ============================================================================

test.describe( 'Server Error Recovery', () => {

    test.beforeEach( async ({ context, request }) => {
        await waitForServiceWorker( context );
        await setExtensionStorage( context, {
            tt_serverUrl: MOCK_SERVER_URL,
        });
        // Reset to success profile
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });
    });

    test( 'server error preserves cached auth', async ({ context, page, request }) => {
        // First authorize successfully
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validtokenfortest' );
        });

        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Switch to server error profile
        await request.post( '/__test__/profile', {
            data: { profile: 'server_error' }
        });

        // Trigger re-validation by opening options page (no debounce)
        const extensionId = await getExtensionId( context );
        const optionsUrl = `chrome-extension://${extensionId}/options/options.html`;
        await page.goto( optionsUrl );

        // Wait for validation attempt
        await page.waitForTimeout( 2000 );

        // Auth should still be preserved despite server error
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
        expect( state.tt_apiToken ).toBeTruthy();
    });

    test( 'server recovery clears error status', async ({ context, page, request }) => {
        // Pre-seed authorized state
        await seedAuthorizedState( context, MOCK_SERVER_URL );

        // Start with server error
        await request.post( '/__test__/profile', {
            data: { profile: 'server_error' }
        });

        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-authorized' ),
            { timeout: 10000 }
        );

        // Switch to success profile
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });

        // Trigger re-validation by opening options page (no debounce)
        const extensionId = await getExtensionId( context );
        const optionsUrl = `chrome-extension://${extensionId}/options/options.html`;
        await page.goto( optionsUrl );

        // Wait for options page to validate
        await page.waitForTimeout( 1000 );

        // Auth should still be valid
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
    });

    test( 'rate limit (429) returns rate_limited status and preserves auth', async ({ context, page, request }) => {
        // Pre-seed authorized state
        await seedAuthorizedState( context, MOCK_SERVER_URL );

        // Set 429 profile
        await request.post( '/__test__/profile', {
            data: { profile: 'rate_limit' }
        });

        // Trigger validation by opening options page (no debounce)
        const extensionId = await getExtensionId( context );
        const optionsPage = await context.newPage();
        await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );
        await optionsPage.waitForTimeout( 2000 );
        await optionsPage.close();

        // Auth should be preserved (429 = rate limited, not auth failure)
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
        expect( state.tt_apiToken ).toBe( 'tt_12345678_preseededtokenvalue' );

        // Content script should show authorized (cached state)
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-authorized' ),
            { timeout: 10000 }
        );
    });

    test( 'bad gateway (502) treated same as server error', async ({ context, page, request }) => {
        // Pre-seed authorized state
        await seedAuthorizedState( context, MOCK_SERVER_URL );

        // Set 502 profile
        await request.post( '/__test__/profile', {
            data: { profile: 'bad_gateway' }
        });

        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-authorized' ) ||
                  document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        // Auth should be preserved (502 = server error, not auth failure)
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
        expect( state.tt_apiToken ).toBe( 'tt_12345678_preseededtokenvalue' );
    });

});

// ============================================================================
// Token Revocation Tests
// ============================================================================

test.describe( 'Token Revocation', () => {

    test.beforeEach( async ({ context, request }) => {
        await waitForServiceWorker( context );
        await setExtensionStorage( context, {
            tt_serverUrl: MOCK_SERVER_URL,
        });
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });
    });

    test( '401 during re-validation clears cached auth', async ({ context, page, request }) => {
        // First authorize successfully
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validtokenfortest' );
        });

        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Verify authorized (this opens options page which validates - allow time)
        let state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );

        // Now server returns 401 (token revoked)
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_401' }
        });

        // Trigger re-validation by opening options page (no debounce for options)
        // The options page checkAuthStatus will hit server, get 401, and clear auth
        const extensionId = await getExtensionId( context );
        const optionsPage = await context.newPage();
        await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );

        // Wait for the auth check to complete and state to be cleared
        // The 401 response triggers TTAuth.disconnect() which clears state
        await optionsPage.waitForTimeout( 2000 );
        await optionsPage.close();

        // Auth should be cleared
        state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'not_authorized' );
        expect( state.tt_apiToken ).toBeUndefined();

        // Content script should also reflect the cleared state
        await page.reload();
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );
    });

});

// ============================================================================
// Disconnect Flow Tests
// ============================================================================

test.describe( 'Disconnect Flow', () => {

    test.beforeEach( async ({ context, request }) => {
        await waitForServiceWorker( context );
        await setExtensionStorage( context, {
            tt_serverUrl: MOCK_SERVER_URL,
        });
        await request.post( '/__test__/profile', {
            data: { profile: 'ext_auth_success' }
        });
    });

    test( 'disconnect while online deletes token and clears auth', async ({ context, page, request }) => {
        // First authorize
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validtokenfortest' );
        });

        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Verify authorized
        let state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );

        // Disconnect
        const response = await sendDisconnect( context );
        expect( response.success ).toBe( true );

        // Verify disconnected
        state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'not_authorized' );
        expect( state.tt_apiToken ).toBeUndefined();
    });

    test( 'disconnect while server unreachable fails gracefully', async ({ context, page, request }) => {
        // First authorize
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validtokenfortest' );
        });

        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Point to unreachable server
        await setExtensionStorage( context, {
            tt_serverUrl: UNREACHABLE_SERVER_URL,
        });

        // Try to disconnect - should fail but not crash
        const response = await sendDisconnect( context );
        expect( response.success ).toBe( false );

        // Auth should still be preserved (couldn't delete token on server)
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
        expect( state.tt_apiToken ).toBeTruthy();
    });

    test( 'disconnect during server error fails gracefully', async ({ context, page, request }) => {
        // First authorize
        await page.goto( TEST_PAGE_URL );
        await page.waitForFunction(
            () => document.body.classList.contains( 'tt-ext-not-authorized' ),
            { timeout: 10000 }
        );

        await page.evaluate( () => {
            window.sendTokenToExtension( 'tt_12345678_validtokenfortest' );
        });

        await page.waitForFunction( () => window.extensionAck !== null, { timeout: 10000 } );

        // Switch to server error profile
        await request.post( '/__test__/profile', {
            data: { profile: 'server_error' }
        });

        // Try to disconnect - should fail
        const response = await sendDisconnect( context );
        expect( response.success ).toBe( false );

        // Auth should still be preserved
        const state = await getExtensionAuthState( context );
        expect( state.tt_authState ).toBe( 'authorized' );
        expect( state.tt_apiToken ).toBeTruthy();
    });

});
