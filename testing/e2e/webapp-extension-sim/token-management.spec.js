/**
 * Tests for extension token table management.
 *
 * Tests the token list display and disconnect functionality.
 * These tests run serially to avoid database conflicts from parallel token creation.
 */
const { test, expect } = require( '@playwright/test' );
const { loginUser } = require( './fixtures/auth' );
const {
    simulateExtensionInstalled,
    setupPostMessageMock
} = require( './fixtures/extension-mock' );

test.describe( 'Extension Token Management', () => {
    // Run serially to avoid unique constraint violations on token names
    test.describe.configure({ mode: 'serial' });

    test.beforeEach( async ({ page }) => {
        await loginUser( page );
    });

    test( 'token appears in table after creation', async ({ page }) => {
        await page.goto( '/user/extensions/' );
        await simulateExtensionInstalled( page, false );
        await setupPostMessageMock( page, { shouldSucceed: true, delay: 50 } );

        // Count existing token rows (exclude empty message row via data-empty-row attribute)
        const tokenRows = page.locator( 'table tbody tr:not([data-empty-row])' );
        const initialCount = await tokenRows.count();

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for success
        const successEl = page.locator( '#tt-ext-auth-success' );
        await expect( successEl ).toBeVisible( { timeout: 5000 } );

        // Refresh the page to see the token in the table
        await page.reload();

        // There should be one more token row than before
        await expect( tokenRows ).toHaveCount( initialCount + 1, { timeout: 5000 } );
    });

    test( 'token table shows token name with platform', async ({ page }) => {
        await page.goto( '/user/extensions/' );
        await simulateExtensionInstalled( page, false );
        await setupPostMessageMock( page, { shouldSucceed: true, delay: 50 } );

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for success
        const successEl = page.locator( '#tt-ext-auth-success' );
        await expect( successEl ).toBeVisible( { timeout: 5000 } );

        // Refresh to see table
        await page.reload();

        // Token name should contain "Chrome Extension"
        const tokenNameCell = page.locator( 'table tbody tr td' ).first();
        await expect( tokenNameCell ).toContainText( 'Chrome Extension' );
    });

    test( 'disconnect button is present for each token', async ({ page }) => {
        await page.goto( '/user/extensions/' );
        await simulateExtensionInstalled( page, false );
        await setupPostMessageMock( page, { shouldSucceed: true, delay: 50 } );

        // Wait for authorize button to be visible and click
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
        await authorizeButton.click();

        // Wait for success
        const successEl = page.locator( '#tt-ext-auth-success' );
        await expect( successEl ).toBeVisible( { timeout: 5000 } );

        // Refresh to see table
        await page.reload();

        // Each token row should have a disconnect button/link
        const disconnectButton = page.locator( 'a, button' ).filter({ hasText: /disconnect/i });
        await expect( disconnectButton.first() ).toBeVisible();
    });

});
