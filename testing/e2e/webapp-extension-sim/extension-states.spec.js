/**
 * Tests for the three extension visibility states on the Extensions page.
 *
 * The page shows different UI based on body CSS classes set by the extension:
 * - No class: Extension not installed (default)
 * - tt-ext-not-authorized: Extension installed but not authorized
 * - tt-ext-authorized: Extension installed and authorized
 */
const { test, expect } = require( '@playwright/test' );
const { loginUser } = require( './fixtures/auth' );
const {
    EXT_STATE_CLASS_AUTHORIZED,
    EXT_STATE_CLASS_NOT_AUTHORIZED,
    simulateExtensionInstalled,
    simulateExtensionNotInstalled
} = require( './fixtures/extension-mock' );

// CSS visibility classes from TtConst
const EXT_SHOW_NOT_INSTALLED_CLASS = 'tt-ext-show-not-installed';
const EXT_SHOW_NOT_AUTHORIZED_CLASS = 'tt-ext-show-not-authorized';
const EXT_SHOW_AUTHORIZED_CLASS = 'tt-ext-show-authorized';

test.describe( 'Extension States on Extensions Page', () => {

    test.beforeEach( async ({ page }) => {
        await loginUser( page );
        await page.goto( '/user/extensions/' );
    });

    test( 'shows not-installed state when no extension classes present', async ({ page }) => {
        // Ensure no extension classes on body (default state)
        await simulateExtensionNotInstalled( page );

        // Not-installed elements should be visible
        const notInstalledEl = page.locator( `.${ EXT_SHOW_NOT_INSTALLED_CLASS }` );
        await expect( notInstalledEl.first() ).toBeVisible();

        // Not-authorized elements should be hidden
        const notAuthorizedEl = page.locator( `.${ EXT_SHOW_NOT_AUTHORIZED_CLASS }` );
        await expect( notAuthorizedEl.first() ).toBeHidden();

        // Authorized elements should be hidden
        const authorizedEl = page.locator( `.${ EXT_SHOW_AUTHORIZED_CLASS }` );
        await expect( authorizedEl.first() ).toBeHidden();
    });

    test( 'shows not-authorized state when extension installed but not authorized', async ({ page }) => {
        // Simulate extension adding not-authorized class
        await simulateExtensionInstalled( page, false );

        // Verify body has the class
        await expect( page.locator( 'body' ) ).toHaveClass( new RegExp( EXT_STATE_CLASS_NOT_AUTHORIZED ) );

        // Not-authorized elements should be visible
        const notAuthorizedEl = page.locator( `.${ EXT_SHOW_NOT_AUTHORIZED_CLASS }` );
        await expect( notAuthorizedEl.first() ).toBeVisible();

        // Not-installed elements should be hidden
        const notInstalledEl = page.locator( `.${ EXT_SHOW_NOT_INSTALLED_CLASS }` );
        await expect( notInstalledEl.first() ).toBeHidden();

        // Authorized elements should be hidden
        const authorizedEl = page.locator( `.${ EXT_SHOW_AUTHORIZED_CLASS }` );
        await expect( authorizedEl.first() ).toBeHidden();
    });

    test( 'shows authorized state when extension installed and authorized', async ({ page }) => {
        // Simulate extension adding authorized class
        await simulateExtensionInstalled( page, true );

        // Verify body has the class
        await expect( page.locator( 'body' ) ).toHaveClass( new RegExp( EXT_STATE_CLASS_AUTHORIZED ) );

        // Authorized elements should be visible
        const authorizedEl = page.locator( `.${ EXT_SHOW_AUTHORIZED_CLASS }` );
        await expect( authorizedEl.first() ).toBeVisible();

        // Not-installed elements should be hidden
        const notInstalledEl = page.locator( `.${ EXT_SHOW_NOT_INSTALLED_CLASS }` );
        await expect( notInstalledEl.first() ).toBeHidden();

        // Not-authorized elements should be hidden
        const notAuthorizedEl = page.locator( `.${ EXT_SHOW_NOT_AUTHORIZED_CLASS }` );
        await expect( notAuthorizedEl.first() ).toBeHidden();
    });

    test( 'authorize form is visible in not-authorized state', async ({ page }) => {
        await simulateExtensionInstalled( page, false );

        // The authorize button/form should be visible
        const authorizeButton = page.locator( 'button[type="submit"]' ).filter({ hasText: /authorize/i });
        await expect( authorizeButton ).toBeVisible();
    });

});
