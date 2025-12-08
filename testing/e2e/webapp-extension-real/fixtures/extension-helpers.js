/**
 * Helper utilities for webapp-extension-real tests.
 *
 * Provides functions to interact with the Chrome extension in tests.
 */

/**
 * Gets the extension ID by finding the service worker.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @returns {Promise<string>} The extension ID
 */
async function getExtensionId( context ) {
    const maxWait = 10000;
    const startTime = Date.now();

    while ( ( Date.now() - startTime ) < maxWait ) {
        const workers = context.serviceWorkers();
        const ttWorker = workers.find( w => w.url().includes( 'service-worker.js' ) );
        if ( ttWorker ) {
            return new URL( ttWorker.url() ).host;
        }
        await new Promise( resolve => setTimeout( resolve, 200 ) );
    }

    throw new Error(
        'Extension service worker not found. ' +
        'Ensure the extension is loaded correctly.'
    );
}

/**
 * Waits for the extension service worker to be registered.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @param {number} [timeout=10000] - Maximum wait time in ms
 * @returns {Promise<import('@playwright/test').Worker>} The service worker
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

module.exports = {
    getExtensionId,
    waitForServiceWorker,
};
