/**
 * Tests for the extension authorization flow.
 *
 * Tests the complete cycle:
 * 1. User clicks "Authorize Extension" button
 * 2. Server creates token and returns HTML fragment
 * 3. JavaScript sends token via postMessage to extension
 * 4. Extension responds with acknowledgment
 * 5. UI updates to show success or failure
 */
const { test, expect } = require( '@playwright/test' );
const { loginUser } = require( './fixtures/auth' );
const {
    simulateExtensionInstalled,
    setupPostMessageMock,
    setupPostMessageNoResponse,
    getMockReceivedMessages
} = require( './fixtures/extension-mock' );

// DOM element IDs from TtConst
const EXT_TOKEN_DATA_ELEMENT_ID = 'extension-token-data';
const EXT_AUTH_PENDING_ID = 'tt-ext-auth-pending';
const EXT_AUTH_SUCCESS_ID = 'tt-ext-auth-success';
const EXT_AUTH_FAILURE_ID = 'tt-ext-auth-failure';

test.describe( 'Extension Authorization Flow', () => {

    test.beforeEach( async ({ page }) => {
        await loginUser( page );
        await page.goto( '/user/extensions/' );
        // Simulate extension installed but not authorized
        await simulateExtensionInstalled( page, false );
    });

    test( 'clicking authorize button submits form and receives token', async ({ page }) => {
        // Set up mock to capture postMessage
        await setupPostMessageMock( page, { shouldSucceed: true, delay: 50 } );

        // Wait for authorize button to be visible (after extension simulation applies CSS)
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for the token data element to appear (from POST response)
        const tokenElement = page.locator( `#${ EXT_TOKEN_DATA_ELEMENT_ID }` );
        await expect( tokenElement ).toBeAttached();

        // Verify token starts with tt_
        const token = await tokenElement.getAttribute( 'data-token' );
        expect( token ).toMatch( /^tt_/ );
    });

    test( 'successful authorization shows success message', async ({ page }) => {
        // Set up mock to respond with success
        await setupPostMessageMock( page, { shouldSucceed: true, delay: 50 } );

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for success element to become visible
        const successEl = page.locator( `#${ EXT_AUTH_SUCCESS_ID }` );
        await expect( successEl ).toBeVisible( { timeout: 5000 } );

        // Pending should be hidden
        const pendingEl = page.locator( `#${ EXT_AUTH_PENDING_ID }` );
        await expect( pendingEl ).toBeHidden();

        // Failure should be hidden
        const failureEl = page.locator( `#${ EXT_AUTH_FAILURE_ID }` );
        await expect( failureEl ).toBeHidden();
    });

    test( 'failed authorization shows fallback UI', async ({ page }) => {
        // Set up mock to respond with failure
        await setupPostMessageMock( page, { shouldSucceed: false, delay: 50, errorMessage: 'Token invalid' } );

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for failure element to become visible
        const failureEl = page.locator( `#${ EXT_AUTH_FAILURE_ID }` );
        await expect( failureEl ).toBeVisible( { timeout: 5000 } );

        // Pending should be hidden
        const pendingEl = page.locator( `#${ EXT_AUTH_PENDING_ID }` );
        await expect( pendingEl ).toBeHidden();

        // Success should be hidden
        const successEl = page.locator( `#${ EXT_AUTH_SUCCESS_ID }` );
        await expect( successEl ).toBeHidden();

        // Fallback should contain a token input for manual copy
        const tokenInput = failureEl.locator( 'input[readonly]' );
        await expect( tokenInput ).toBeVisible();
        const inputValue = await tokenInput.inputValue();
        expect( inputValue ).toMatch( /^tt_/ );
    });

    test( 'timeout shows fallback UI when extension does not respond', async ({ page }) => {
        // Set up mock that does NOT respond (simulates extension not handling message)
        await setupPostMessageNoResponse( page );

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for the 2-second timeout plus buffer
        // The page JavaScript has a 2000ms timeout before showing fallback
        const failureEl = page.locator( `#${ EXT_AUTH_FAILURE_ID }` );
        await expect( failureEl ).toBeVisible( { timeout: 5000 } );

        // Verify message was sent to extension
        const messages = await getMockReceivedMessages( page );
        expect( messages.length ).toBeGreaterThan( 0 );
        expect( messages[0].type ).toBe( 'tt_extension_data' );
        expect( messages[0].payload.action ).toBe( 'authorize' );
    });

    test( 'token sent via postMessage has correct format', async ({ page }) => {
        // Set up mock to capture the message
        await setupPostMessageMock( page, { shouldSucceed: true, delay: 50 } );

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for success (ensures message was processed)
        const successEl = page.locator( `#${ EXT_AUTH_SUCCESS_ID }` );
        await expect( successEl ).toBeVisible( { timeout: 5000 } );

        // Check the message that was sent
        const messages = await getMockReceivedMessages( page );
        expect( messages.length ).toBe( 1 );

        const msg = messages[0];
        expect( msg.type ).toBe( 'tt_extension_data' );
        expect( msg.payload ).toBeDefined();
        expect( msg.payload.action ).toBe( 'authorize' );
        expect( msg.payload.token ).toMatch( /^tt_[a-f0-9]{8}_/ );
    });

});
