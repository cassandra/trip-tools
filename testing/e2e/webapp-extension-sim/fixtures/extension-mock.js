/**
 * Extension simulation utilities for E2E testing.
 *
 * These functions simulate browser extension behavior by:
 * 1. Adding CSS classes to body that the extension normally adds
 * 2. Responding to postMessage events that the extension normally handles
 *
 * Constants must match TtConst values from src/tt/environment/constants.py
 */

const EXT_STATE_CLASS_AUTHORIZED = 'tt-ext-authorized';
const EXT_STATE_CLASS_NOT_AUTHORIZED = 'tt-ext-not-authorized';
const EXT_POSTMESSAGE_DATA_TYPE = 'tt_extension_data';
const EXT_POSTMESSAGE_ACK_TYPE = 'tt_extension_ack';

/**
 * Simulates extension installed state by adding body class.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {boolean} authorized - Whether to simulate authorized or not-authorized state
 */
async function simulateExtensionInstalled( page, authorized ) {
    const className = authorized
        ? EXT_STATE_CLASS_AUTHORIZED
        : EXT_STATE_CLASS_NOT_AUTHORIZED;
    await page.evaluate( ( cls ) => {
        document.body.classList.add( cls );
    }, className );
}

/**
 * Removes extension state classes from body (simulates extension not installed).
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
async function simulateExtensionNotInstalled( page ) {
    await page.evaluate( () => {
        document.body.classList.remove( 'tt-ext-authorized', 'tt-ext-not-authorized' );
    });
}

/**
 * Sets up a mock listener for postMessage events from the page.
 * Simulates extension responding to authorization token delivery.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Object} options - Configuration options
 * @param {boolean} [options.shouldSucceed=true] - Whether the mock should respond with success
 * @param {number} [options.delay=100] - Delay in ms before sending acknowledgment
 * @param {string|null} [options.errorMessage=null] - Error message to include on failure
 */
async function setupPostMessageMock( page, options = {} ) {
    const { shouldSucceed = true, delay = 100, errorMessage = null } = options;

    await page.evaluate( ({ success, delay, error, dataType, ackType }) => {
        window.__extensionMockReceived = [];

        window.addEventListener( 'message', function( event ) {
            if ( event.origin !== window.location.origin ) return;
            if ( !event.data || event.data.type !== dataType ) return;

            // Record the received message for test assertions
            window.__extensionMockReceived.push( event.data );

            // Simulate extension processing and responding
            setTimeout( function() {
                window.postMessage({
                    type: ackType,
                    payload: {
                        action: 'authorize',
                        success: success,
                        error: success ? null : ( error || 'Mock authorization failed' )
                    }
                }, window.location.origin );
            }, delay );
        });
    }, {
        success: shouldSucceed,
        delay: delay,
        error: errorMessage,
        dataType: EXT_POSTMESSAGE_DATA_TYPE,
        ackType: EXT_POSTMESSAGE_ACK_TYPE
    });
}

/**
 * Sets up a mock that does NOT respond to postMessage (simulates timeout).
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
async function setupPostMessageNoResponse( page ) {
    await page.evaluate( ({ dataType }) => {
        window.__extensionMockReceived = [];

        window.addEventListener( 'message', function( event ) {
            if ( event.origin !== window.location.origin ) return;
            if ( !event.data || event.data.type !== dataType ) return;

            // Record the received message but do NOT respond
            window.__extensionMockReceived.push( event.data );
        });
    }, { dataType: EXT_POSTMESSAGE_DATA_TYPE });
}

/**
 * Gets the messages received by the mock extension listener.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<Array>} Array of received message data objects
 */
async function getMockReceivedMessages( page ) {
    return await page.evaluate( () => {
        return window.__extensionMockReceived || [];
    });
}

module.exports = {
    EXT_STATE_CLASS_AUTHORIZED,
    EXT_STATE_CLASS_NOT_AUTHORIZED,
    EXT_POSTMESSAGE_DATA_TYPE,
    EXT_POSTMESSAGE_ACK_TYPE,
    simulateExtensionInstalled,
    simulateExtensionNotInstalled,
    setupPostMessageMock,
    setupPostMessageNoResponse,
    getMockReceivedMessages
};
