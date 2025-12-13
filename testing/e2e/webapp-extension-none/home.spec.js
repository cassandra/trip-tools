const { test, expect } = require( '@playwright/test' );

test.describe( 'Home Page', () => {

    test( 'should load and display sign-in button for anonymous users', async ({ page }) => {
        await page.goto( '/' );

        // Check page loads successfully
        await expect( page ).toHaveTitle( /Trip Tools/ );

        // Anonymous users should see sign-in button, not dashboard
        const signInButton = page.locator( 'a:has-text("Sign In")' );
        await expect( signInButton ).toBeVisible();

        const dashboardButton = page.locator( 'a:has-text("Dashboard")' );
        await expect( dashboardButton ).not.toBeVisible();
    });

});
