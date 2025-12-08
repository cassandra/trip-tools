/**
 * Authentication helpers for E2E testing.
 *
 * Uses the test-only /testing/signin/ endpoint which is only available
 * when Django is running with DEBUG=True (tt.testing app installed).
 */

// Default test password - must match settings.E2E_TEST_PASSWORD
const E2E_TEST_PASSWORD = 'e2e-test-password';

// Default test user - created by: ./src/manage.py seed_e2e_data
const DEFAULT_TEST_EMAIL = 'e2e-test@example.com';

/**
 * Logs in a user via the E2E test signin endpoint.
 *
 * This endpoint only exists in DEBUG mode and accepts a shared test password
 * instead of the magic code flow.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} [email=DEFAULT_TEST_EMAIL] - User email address
 * @param {string} [password=E2E_TEST_PASSWORD] - Test password
 */
async function loginUser( page, email = DEFAULT_TEST_EMAIL, password = E2E_TEST_PASSWORD ) {
    await page.goto( '/testing/signin/' );

    await page.fill( 'input[name="email"]', email );
    await page.fill( 'input[name="password"]', password );
    await page.click( 'button[type="submit"]' );

    // Wait for redirect after successful login
    await page.waitForURL( /.*dashboard.*/ );
}

/**
 * Logs out the current user by navigating to signout.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
async function logoutUser( page ) {
    await page.goto( '/user/signout/' );
    // The signout page may require confirmation - click the button if present
    const confirmButton = page.locator( 'button[type="submit"]' );
    if ( await confirmButton.isVisible() ) {
        await confirmButton.click();
    }
}

/**
 * Checks if user is currently logged in.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<boolean>} True if logged in
 */
async function isLoggedIn( page ) {
    // Check for presence of dashboard link or user menu
    const dashboardLink = page.locator( 'a[href*="dashboard"]' );
    return await dashboardLink.isVisible().catch( () => false );
}

module.exports = {
    E2E_TEST_PASSWORD,
    DEFAULT_TEST_EMAIL,
    loginUser,
    logoutUser,
    isLoggedIn
};
