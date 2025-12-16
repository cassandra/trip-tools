# End-to-End Testing with Playwright

This document covers the E2E testing infrastructure for Trip Tools using Playwright.

## Prerequisites

- **Node.js 20.x** (LTS) - See [Dependencies](../Dependencies.md#nodejs) for installation instructions
- **npm** - Comes with Node.js

When working in the E2E testing directory, use nvm to ensure the correct Node.js version:
```bash
cd testing/e2e
nvm use          # Reads version from .nvmrc
```

## Setup

First-time setup:
```bash
make test-e2e-install
make test-e2e-seed
```

This installs npm dependencies, downloads Chromium for Playwright, and seeds the database with test user data.

## Running Tests

### All E2E Tests
```bash
make test-e2e
```

### By Test Category

| Make Target | Description |
|-------------|-------------|
| `make test-e2e-webapp-extension-none` | Web app only (no extension) |
| `make test-e2e-webapp-extension-sim` | Web app with simulated extension |
| `make test-e2e-extension-isolated` | Extension with mock server |
| `make test-e2e-webapp-extension-real` | Full integration (Django + real extension) |

### Interactive Mode

Run tests with browser visible:
```bash
cd testing/e2e
~/.nvm/nvm.sh
nvm use 
npm run test:headed
```

### View Test Report

After running tests:
```bash
cd testing/e2e
~/.nvm/nvm.sh
nvm use 
npm run report
```

## Test Organization

```
testing/
├── e2e/
│   ├── webapp-extension-none/     # Web app tests (no extension)
│   │   └── *.spec.js
│   ├── webapp-extension-sim/      # Web app tests with simulated extension
│   │   ├── fixtures/
│   │   │   ├── auth.js            # Login helpers
│   │   │   └── extension-mock.js  # Extension simulation utilities
│   │   └── *.spec.js
│   ├── extension-isolated/        # Extension tests with mock server
│   │   ├── fixtures/
│   │   │   └── extension-helpers.js  # Extension storage/state helpers
│   │   └── *.spec.js
│   ├── webapp-extension-real/     # Full integration tests
│   │   ├── fixtures/
│   │   │   └── extension-helpers.js  # Extension ID/service worker helpers
│   │   └── *.spec.js
│   └── playwright.config.js
└── mock_server/                   # Python mock server for extension-isolated tests
    ├── server.py                  # HTTP server with profile-controlled responses
    ├── profiles.py                # Response profiles (success, 401, 500, etc.)
    └── test_pages/                # Static HTML pages for testing
```

## Test Categories

### Naming Convention

| Test Suite | Server | Extension | Purpose |
|------------|--------|-----------|---------|
| `webapp-extension-none` | Real Django | None | Web app pages with no extension interaction |
| `webapp-extension-sim` | Real Django | Simulated | Web app extension pages (authorization UI) |
| `extension-isolated` | Mock Python | Real Chrome | Extension behavior in isolation |
| `webapp-extension-real` | Real Django | Real Chrome | Full integration |

### 1. Web App Tests (`webapp-extension-none/`)

Standard E2E tests for the Django web application with no extension involvement:
- Page loading and rendering
- Navigation flows

Uses Django server on port 6778.

### 2. Web App + Simulated Extension (`webapp-extension-sim/`)

Test web app pages that interact with the browser extension using simulated extension behavior:
- postMessage communication between page and extension
- CSS class injection for extension state visibility
- Token delivery on authorization pages

Uses Django server on port 6778. Fixtures simulate extension without loading it.

### 3. Extension Isolated (`extension-isolated/`)

Test the Chrome extension loaded in a real browser, isolated from the production server:
- Service worker message handling
- Chrome storage operations
- Content script behavior
- Authorization flow with mock server
- Server error handling and recovery

**Key characteristics:**
- Uses **mock server** (port 6779) instead of Django
- Requires **headed mode** - extensions don't work headless
- Uses `chromium.launchPersistentContext()` for extension support
- Tests extension storage state directly via helpers

### 4. Full Integration (`webapp-extension-real/`)

Test the real Chrome extension against the real Django server:
- End-to-end authorization flow
- Extension-webapp interaction
- Full user journeys

**Key characteristics:**
- Uses **Django server** (port 6778) - real backend
- Requires **headed mode** - extensions don't work headless
- Uses `chromium.launchPersistentContext()` for extension support
- Combines Django auth with real extension behavior

## Mock Server

The `testing/mock_server/` provides profile-controlled API responses for `extension-isolated` tests.

### Profiles

Profiles define how the mock server responds to API calls. See `profiles.py` for the full list:

| Profile | `/api/v1/me/` Response | Use Case |
|---------|------------------------|----------|
| `ext_auth_success` | 200 with user info | Normal authorization |
| `ext_auth_401` | 401 Unauthorized | Invalid/revoked token |
| `server_error` | 500 Internal Error | Server issues |
| `timeout` | 10s delay | Network timeout |
| `rate_limit` | 429 Too Many Requests | Rate limiting |
| `bad_gateway` | 502 Bad Gateway | Proxy/gateway errors |

### Changing Profiles at Runtime

Tests can change the active profile via POST:
```javascript
await request.post('/__test__/profile', {
    data: { profile: 'ext_auth_401' }
});
```

### Test Pages

Static HTML pages in `test_pages/` simulate triptools.net pages for extension testing. These include the JavaScript needed for extension-page communication.

## Test Data

Tests requiring Django authentication need a seeded database:

```bash
make test-e2e-seed
```

This creates:
- **Test user:** `e2e-test@example.com`

The command is idempotent and safe to run multiple times.

### Test Authentication

E2E tests authenticate via a special endpoint only available in DEBUG mode:

- **Endpoint:** `/testing/signin/`
- **Password:** Configured in `settings.E2E_TEST_PASSWORD`

This bypasses the magic code email flow for automated testing.

## Writing Tests

### Basic Test Structure

```javascript
const { test, expect } = require('@playwright/test');

test('should display page content', async ({ page }) => {
    await page.goto('/some-page/');
    await expect(page.locator('h1')).toContainText('Expected Title');
});
```

### Extension Simulation Fixtures

For testing pages that interact with the browser extension:

```javascript
const { simulateExtensionInstalled, setupPostMessageMock } = require('./fixtures/extension-mock');

test('extension authorization flow', async ({ page }) => {
    await page.goto('/user/extensions/');

    // Simulate extension present but not authorized
    await simulateExtensionInstalled(page, false);

    // Mock extension responding to postMessage
    await setupPostMessageMock(page, { shouldSucceed: true });

    // ... trigger authorization and verify
});
```

### Extension Isolated Helpers

For `extension-isolated` tests, use helpers to interact with extension storage:

```javascript
const {
    setExtensionStorage,
    getExtensionAuthState,
    getExtensionId
} = require('./fixtures/extension-helpers');

test('extension stores auth state', async ({ context, page }) => {
    // Set extension storage directly
    await setExtensionStorage(context, {
        tt_serverUrl: 'http://localhost:6779',
    });

    // ... perform actions

    // Verify storage state
    const state = await getExtensionAuthState(context);
    expect(state.tt_authState).toBe('authorized');
});
```

## Configuration

The Playwright configuration is in `testing/e2e/playwright.config.js`.

Key settings:
- **Ports**: Django on 6778, Mock server on 6779
- **workers**: 1 (avoids database conflicts)
- **timeout**: 30 seconds per test
- **retries**: 2 in CI, 0 locally

### Web Servers

Playwright automatically starts the required servers:
- **Django** (`webapp-extension-none`, `webapp-extension-sim`, `webapp-extension-real`): port 6778
- **Mock server** (`extension-isolated`): port 6779

## Running Specific Tests

All commands run from `testing/e2e/`:

```bash
# Run a specific test file
npx playwright test webapp-extension-none/home.spec.js

# Run tests matching a name pattern
npx playwright test --grep "sign-in button" --project=webapp-extension-none

# Re-run only failed tests from last run
npx playwright test --last-failed

# Combine: specific file in specific project
npx playwright test extension-isolated/authorization-flow.spec.js --project=extension-isolated
```

## Debugging Tests

All commands run from `testing/e2e/`:

```bash
# UI mode - Interactive runner with time-travel debugging (recommended)
npx playwright test --ui --project=webapp-extension-none

# Debug mode - Pause at each step with Playwright Inspector
PWDEBUG=1 npx playwright test --project=webapp-extension-none

# Headed mode - Watch browser as tests run
npx playwright test --headed --project=webapp-extension-none

# Trace viewer - Step through recorded test run
npx playwright test --project=webapp-extension-none --trace on
npx playwright show-trace test-results/<test-folder>/trace.zip
```

Note: Traces are already captured on test failures (`trace: 'on-first-retry'` in config).

## Troubleshooting

### Django Server Issues

If tests fail to connect to the server:
1. Check if port 6778 is in use: `lsof -i :6778`
2. Manually start server: `DJANGO_SETTINGS_MODULE=tt.settings.e2e ./src/manage.py runserver 6778`

### Extension Tests Failing

Extension-isolated tests require:
- Headed mode (cannot run headless)
- Chrome browser (not Firefox/WebKit)
- Valid extension at `tools/extension/src/`

### Service Worker Not Found

If extension tests fail with "service worker not found":
- Ensure the extension has valid `manifest.json`
- Check `host_permissions` in manifest match test URLs
- The test navigates to trigger service worker activation

### Missing Node.js

See [Dependencies](../Dependencies.md#nodejs) for Node.js installation instructions using nvm.
