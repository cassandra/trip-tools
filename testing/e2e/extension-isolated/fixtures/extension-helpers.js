/**
 * Extension helper utilities for extension-real tests.
 *
 * Provides functions to interact with extension storage and state.
 * Uses chrome.storage APIs via page.evaluate() in extension context.
 */

/**
 * Gets the extension ID by finding the service worker.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @returns {Promise<string>} The extension ID
 */
async function getExtensionId( context ) {
    // First, try to get it from service workers
    const workers = context.serviceWorkers();
    const ttWorker = workers.find( w => w.url().includes( 'service-worker.js' ) );
    if ( ttWorker ) {
        return new URL( ttWorker.url() ).host;
    }

    // Fallback: Navigate to a host_permissions page to trigger content script
    // which will wake up the service worker
    let page = context.pages()[0];
    if ( !page ) {
        page = await context.newPage();
    }

    // Navigate to a matching host to trigger extension
    await page.goto( 'http://localhost:6779/user/extensions/' );
    await page.waitForTimeout( 1000 );

    // Try again to get service worker
    const maxWait = 10000;
    const startTime = Date.now();
    let serviceWorker;

    while ( !serviceWorker && ( Date.now() - startTime ) < maxWait ) {
        const allWorkers = context.serviceWorkers();
        serviceWorker = allWorkers.find( w => w.url().includes( 'service-worker.js' ) );
        if ( !serviceWorker ) {
            await new Promise( resolve => setTimeout( resolve, 200 ) );
        }
    }

    if ( !serviceWorker ) {
        throw new Error(
            'Extension service worker not found. ' +
            'Ensure the extension is loaded and host_permissions match the test URL.'
        );
    }

    return new URL( serviceWorker.url() ).host;
}

/**
 * Sets extension storage values directly.
 * Uses the service worker directly to avoid triggering auth checks from options/popup pages.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @param {Object} values - Key-value pairs to set in storage
 */
async function setExtensionStorage( context, values ) {
    const extensionId = await getExtensionId( context );
    const optionsPage = await context.newPage();

    await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );
    // Wait for auth check to complete before setting storage
    await optionsPage.waitForTimeout( 500 );
    await optionsPage.evaluate( ( vals ) => {
        return new Promise( resolve => {
            chrome.storage.local.set( vals, resolve );
        });
    }, values );

    await optionsPage.close();
}

/**
 * Gets the current extension auth state from storage.
 * Uses the options page to access storage.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @returns {Promise<Object>} Object containing tt_authState, tt_apiToken, tt_userEmail
 */
async function getExtensionAuthState( context ) {
    const extensionId = await getExtensionId( context );
    const optionsPage = await context.newPage();

    await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );
    // Wait for auth check to complete before reading storage
    await optionsPage.waitForTimeout( 500 );
    const state = await optionsPage.evaluate( () => {
        return new Promise( resolve => {
            chrome.storage.local.get(
                ['tt_authState', 'tt_apiToken', 'tt_userEmail', 'tt_serverUrl'],
                resolve
            );
        });
    });

    await optionsPage.close();
    return state;
}

/**
 * Clears extension storage to reset state between tests.
 * Uses the options page to access storage.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 */
async function clearExtensionStorage( context ) {
    const extensionId = await getExtensionId( context );
    const optionsPage = await context.newPage();

    await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );
    await optionsPage.waitForTimeout( 500 );
    await optionsPage.evaluate( () => {
        return new Promise( resolve => {
            chrome.storage.local.clear( resolve );
        });
    });

    await optionsPage.close();
}

/**
 * Waits for extension to add auth state class to body.
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {string} expectedClass - Class to wait for ('tt-ext-authorized' or 'tt-ext-not-authorized')
 * @param {number} [timeout=10000] - Maximum wait time in ms
 */
async function waitForExtensionState( page, expectedClass, timeout = 10000 ) {
    await page.waitForFunction(
        ( cls ) => document.body.classList.contains( cls ),
        expectedClass,
        { timeout }
    );
}

/**
 * Triggers an auth status check by navigating to a test page.
 * The content script will send an auth status request to the service worker.
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {string} [testPageUrl='http://localhost:6779/user/extensions/'] - Test page URL
 * @returns {Promise<Object>} Object with authState from the page's body class
 */
async function triggerAuthCheck( page, testPageUrl = 'http://localhost:6779/user/extensions/' ) {
    await page.goto( testPageUrl );

    // Wait for extension content script to set body class
    await page.waitForFunction(
        () => document.body.classList.contains( 'tt-ext-authorized' ) ||
              document.body.classList.contains( 'tt-ext-not-authorized' ),
        { timeout: 10000 }
    );

    const bodyClasses = await page.evaluate( () => document.body.className );
    return {
        isAuthorized: bodyClasses.includes( 'tt-ext-authorized' ),
        isNotAuthorized: bodyClasses.includes( 'tt-ext-not-authorized' ),
        bodyClasses,
    };
}

/**
 * Sends a disconnect request to the extension service worker.
 * Uses chrome.runtime.sendMessage from an extension page context.
 *
 * @param {import('@playwright/test').BrowserContext} context - Playwright browser context
 * @returns {Promise<Object>} Response from the service worker
 */
async function sendDisconnect( context ) {
    const extensionId = await getExtensionId( context );
    const optionsPage = await context.newPage();

    await optionsPage.goto( `chrome-extension://${extensionId}/options/options.html` );
    await optionsPage.waitForTimeout( 500 );

    const response = await optionsPage.evaluate( () => {
        return new Promise( ( resolve ) => {
            chrome.runtime.sendMessage(
                { type: 'tt_disconnect', data: {} },
                ( response ) => {
                    resolve( response );
                }
            );
        });
    });

    await optionsPage.close();
    return response;
}

module.exports = {
    getExtensionId,
    setExtensionStorage,
    getExtensionAuthState,
    clearExtensionStorage,
    waitForExtensionState,
    triggerAuthCheck,
    sendDisconnect,
};
