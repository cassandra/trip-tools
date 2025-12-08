const { defineConfig, devices } = require( '@playwright/test' );
const path = require( 'path' );

// Absolute path to the Chrome extension
const extensionPath = path.resolve( __dirname, '../../tools/chrome' );

module.exports = defineConfig({
  testDir: '.',
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,

  // Single worker to avoid database conflicts between parallel tests
  // All tests share the same database, so parallel execution causes race conditions
  workers: 1,

  // Reporter configuration
  reporter: process.env.CI ? 'github' : 'html',

  projects: [
    {
      name: 'webapp-extension-none',
      testDir: './webapp-extension-none',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'webapp-extension-sim',
      testDir: './webapp-extension-sim',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'extension-isolated',
      testDir: './extension-isolated',
      use: {
        // Headed mode required for Chrome extensions
        headless: false,
        // Use port 6779 to match mock server
        baseURL: 'http://localhost:6779',
        launchOptions: {
          args: [
            `--disable-extensions-except=${extensionPath}`,
            `--load-extension=${extensionPath}`,
          ],
        },
      },
    },
    {
      name: 'webapp-extension-real',
      testDir: './webapp-extension-real',
      use: {
        // Headed mode required for Chrome extensions
        headless: false,
        // Use port 6778 to match Django server
        baseURL: 'http://localhost:6778',
        launchOptions: {
          args: [
            `--disable-extensions-except=${extensionPath}`,
            `--load-extension=${extensionPath}`,
          ],
        },
      },
    },
  ],

  // Web servers for different test suites
  // Note: Only servers needed for the selected project(s) will start
  webServer: [
    {
      // Django server for webapp-extension-none, webapp-extension-sim, and webapp-extension-real tests
      command: './setup-db.sh && cd ../../src && DJANGO_SETTINGS_MODULE=tt.settings.e2e python manage.py runserver 6778',
      url: 'http://localhost:6778',
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      // Mock server for extension-isolated tests
      // Serves test pages and provides profile-controlled API responses
      command: 'cd ../mock_server && python server.py --port 6779',
      url: 'http://localhost:6779/__test__/health',
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],

  // Shared settings for all projects
  use: {
    baseURL: 'http://localhost:6778',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
