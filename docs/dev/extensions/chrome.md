# Chrome Extension Development

## Running in Development Mode

1. Open Chrome and navigate to `chrome://extensions`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select the `tools/chrome/` directory
5. Click **Details**
6. Enable **Pin to toolbar**

The extension icon will appear in the toolbar. Click it to open the popup.

### Development vs Production

The extension displays visual cues in development mode:

- **Coral header** (instead of teal)
- **Version shows "(DEV)"** suffix

This is controlled by `TT.CONFIG.IS_DEVELOPMENT` in `tools/chrome/shared/constants.js`.

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
