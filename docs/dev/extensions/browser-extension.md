# Browser Extension Development

## Directory Structure

```
tools/extension/
  manifest.chrome.json   # Chrome-specific manifest (authoritative)
  manifest.firefox.json  # Firefox-specific manifest (authoritative)
  src/                   # Shared source code
    manifest.json        # Symlink → ../manifest.chrome.json (not in git)
    background/
    content/
    popup/
    options/
    shared/
    adapters/
    styles/
    images/
```

## Initial Setup

The `src/manifest.json` file is not tracked in git. Create a symlink to the Chrome manifest:

```bash
cd tools/extension/src
ln -s ../manifest.chrome.json manifest.json
```

This symlink allows loading the extension directly from `src/` for development.

## Running in Chrome (Development Mode)

1. Ensure the manifest symlink exists (see Initial Setup above)
2. Open Chrome and navigate to `chrome://extensions`
3. Enable **Developer mode** (toggle in top right)
4. Click **Load unpacked**
5. Select the `tools/extension/src/` directory
6. Click **Details**
7. Enable **Pin to toolbar**

The extension icon will appear in the toolbar. Click it to open the popup.

## Running in Firefox (Development Mode)

Firefox requires a different manifest due to MV3 differences (event pages vs service workers, no ports in match patterns).

### Switch to Firefox Manifest

```bash
cd tools/extension/src
rm manifest.json
ln -s ../manifest.firefox.json manifest.json
```

### Load in Firefox

1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on...**
3. Navigate to `tools/extension/src/` and select `manifest.json`

### Switch Back to Chrome Manifest

After Firefox testing, restore the Chrome symlink:

```bash
cd tools/extension/src
rm manifest.json
ln -s ../manifest.chrome.json manifest.json
```

**Important:** E2E tests use Chrome and expect the Chrome manifest. Always restore the Chrome symlink after Firefox testing.

**Note:** Firefox has limitations with localhost content scripts - port numbers in match patterns don't work. The Firefox manifest is configured to work around this.

### Development vs Production

The extension displays visual cues in development mode:

- **Coral header** (instead of teal)
- **Version shows "(DEV)"** suffix

This is controlled by `TT.CONFIG.IS_DEVELOPMENT` in `tools/extension/src/shared/constants.js`.

### Reloading Changes

After modifying extension files:

- **JavaScript/CSS changes**: Click the refresh icon on the extension card at `chrome://extensions`
- **manifest.json changes**: Remove and re-load the extension

### Debugging

- **Popup**: Right-click the popup and select "Inspect"
- **Service worker**: Click "Service Worker" link on the extension card at `chrome://extensions`
- **Debug panel**: Visible when Developer Mode is enabled (see Options)

## Options

The extension has a two-tier options structure:

### Quick Options (Slide-in Panel)

Access via the gear icon in the popup header. Slides in from the right with frequently-used settings (placeholder for now). Click "All Options" at the bottom to access the full options page.

### Full Options Page

Access via "All Options" link in the quick options panel. Contains all settings including:

**Developer Mode** - Enables the Developer Settings section with:

- **Server URL**: API endpoint for Trip Tools backend (defaults based on `IS_DEVELOPMENT`)
- **Debug Panel**: Show/hide debug panel in popup (defaults to enabled when Developer Mode is turned on)

In development builds, Developer Mode defaults to enabled. In production builds, it defaults to disabled but can be enabled by users who need it.

## Authorization

The extension authenticates with triptools.net using API tokens.

### Authorization Flow

1. User clicks "Authorize" in extension popup or options page
2. Browser opens `/user/extensions/authorize/` on triptools.net
3. User clicks "Authorize Extension" button (async POST via antinode.js)
4. Server creates API token, returns fragment with token in data attribute
5. Page JavaScript sends token to extension via `postMessage`
6. Extension content script receives token, forwards to service worker
7. Service worker validates token with `/api/v1/me/`, stores on success
8. Extension sends ack back to page, which shows success/failure

### Token Validation

The service worker validates tokens on demand (debounced):
- When popup opens
- When options page opens
- When content script queries auth state

If validation fails:
- **401**: Token revoked → clear auth state, show "Not connected"
- **Network error**: Keep cached auth, show "Offline"
- **5xx error**: Keep cached auth, show "Server error"
- **Timeout**: Keep cached auth, show "Connection timeout"

### Disconnect

Disconnect deletes the token on the server before clearing local state. Requires network connectivity.

## Extension State on triptools.net Pages

Content scripts add CSS classes to `<body>` indicating extension state. Pages use visibility classes to show/hide content based on state.

### Body State Classes

Added by `triptools-state.js` content script:

| Class | Meaning |
|-------|---------|
| `tt-ext-authorized` | Extension installed and authorized |
| `tt-ext-not-authorized` | Extension installed but not authorized |
| *(neither)* | Extension not installed |

### Visibility Classes

Use these on elements to control visibility:

| Class | Visible When |
|-------|--------------|
| `tt-ext-show-authorized` | Extension authorized |
| `tt-ext-show-not-authorized` | Extension installed but not authorized |
| `tt-ext-show-not-installed` | Extension not installed (default state) |

Example:
```html
<div class="tt-ext-show-authorized">Welcome back!</div>
<div class="tt-ext-show-not-authorized">Please authorize the extension.</div>
<div class="tt-ext-show-not-installed">Install our browser extension.</div>
```

### Synced Constants

These values are defined in both:
- Server: `TtConst` in `src/tt/environment/constants.py`
- Extension: `TT.SERVER_SYNC` in `tools/extension/src/shared/constants.js`

Variable names are identical for searchability. CSS rules are in `src/tt/static/css/main.css`.
