#!/bin/bash
#
# Build browser extension for production release.
# Creates packages for all supported browsers ready for store submission.
#
# Usage: ./deploy/build-extension.sh
#
# Reads version info from EXT_VERSION file.
# Outputs to dist/:
#   - chrome-extension-{version}.zip
#   - firefox-extension-{version}.xpi
#

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EXT_VERSION_FILE="$PROJECT_ROOT/EXT_VERSION"
EXT_SOURCE_DIR="$PROJECT_ROOT/tools/extension/src"
EXT_MANIFEST_DIR="$PROJECT_ROOT/tools/extension"
DIST_DIR="$PROJECT_ROOT/dist"

# Read version info from EXT_VERSION
if [ ! -f "$EXT_VERSION_FILE" ]; then
    echo "ERROR: EXT_VERSION file not found at $EXT_VERSION_FILE"
    exit 1
fi

source "$EXT_VERSION_FILE"

if [ -z "$VERSION" ]; then
    echo "ERROR: VERSION not set in EXT_VERSION"
    exit 1
fi

if [ -z "$MIN_SERVER_VERSION" ]; then
    echo "ERROR: MIN_SERVER_VERSION not set in EXT_VERSION"
    exit 1
fi

# VERSION is the full version string (e.g., "ext-v0.1.0" or "ext-v0.1.0-dev")
# VERSION_NAME is the display version (same as VERSION)
# MANIFEST_VERSION is browser-compatible:
#   - Strip "ext-v" prefix
#   - If "-dev" suffix: replace with ".999" (e.g., "0.1.0.999")
#   - If no "-dev": use as-is (e.g., "0.1.0")
VERSION_NAME="$VERSION"
MANIFEST_VERSION="${VERSION#ext-v}"
if [[ "$MANIFEST_VERSION" == *"-dev"* ]]; then
    MANIFEST_VERSION="${MANIFEST_VERSION%-dev}.999"
fi

echo "=== Building Browser Extensions ==="
echo "  Version: $VERSION_NAME"
echo "  Manifest Version: $MANIFEST_VERSION"
echo "  Min Server Version: $MIN_SERVER_VERSION"
echo ""

# Warn if building a dev version
if [[ "$VERSION" == *"-dev"* ]]; then
    echo "WARNING: Building a development version ($VERSION_NAME)"
    echo "         For production release, remove '-dev' suffix from EXT_VERSION"
    echo ""
fi

# Clean previous builds (hardcoded paths for safety - rm -rf is dangerous)
echo "Cleaning previous builds..."
/bin/rm -rf "$PROJECT_ROOT/dist/chrome-extension"
/bin/rm -rf "$PROJECT_ROOT/dist/firefox-extension"
/bin/rm -f "$PROJECT_ROOT/dist"/chrome-extension-*.zip
/bin/rm -f "$PROJECT_ROOT/dist"/firefox-extension-*.xpi

# Create dist directory
mkdir -p "$DIST_DIR"

#
# Build for a specific browser
# Args: $1 = browser name (chrome or firefox)
#
build_for_browser() {
    local browser="$1"
    local ext_dist_dir="$DIST_DIR/$browser-extension"

    echo "--- Building for $browser ---"

    # Create browser-specific dist directory
    mkdir -p "$ext_dist_dir"

    # Copy source files
    echo "  Copying extension files..."
    cp -r "$EXT_SOURCE_DIR"/* "$ext_dist_dir"/

    # Remove the manifest symlink and copy the appropriate manifest
    /bin/rm -f "$ext_dist_dir/manifest.json"
    echo "  Copying $browser manifest..."
    cp "$EXT_MANIFEST_DIR/manifest.$browser.json" "$ext_dist_dir/manifest.json"

    # Update manifest.json - version
    echo "  Updating manifest.json..."
    sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$MANIFEST_VERSION\"/" "$ext_dist_dir/manifest.json"

    # Chrome-specific: update version_name
    if [ "$browser" = "chrome" ]; then
        sed -i.bak "s/\"version_name\": \"[^\"]*\"/\"version_name\": \"$VERSION_NAME\"/" "$ext_dist_dir/manifest.json"
    fi

    /bin/rm -f "$ext_dist_dir/manifest.json.bak"

    # Update constants.js - version and IS_DEVELOPMENT
    echo "  Updating constants.js..."
    sed -i.bak "s/EXTENSION_VERSION: '[^']*'/EXTENSION_VERSION: '$VERSION_NAME'/" "$ext_dist_dir/shared/constants.js"
    sed -i.bak "s/IS_DEVELOPMENT: true/IS_DEVELOPMENT: false/" "$ext_dist_dir/shared/constants.js"
    /bin/rm -f "$ext_dist_dir/shared/constants.js.bak"

    # Create archive file
    echo "  Creating archive..."

    if [ "$browser" = "firefox" ]; then
        # Firefox uses .xpi (which is just a zip with different extension)
        local output_file="$browser-extension-$VERSION_NAME.xpi"
    else
        local output_file="$browser-extension-$VERSION_NAME.zip"
    fi

    # Zip from inside the extension directory so manifest.json is at the root
    cd "$ext_dist_dir"
    zip -rq "$DIST_DIR/$output_file" .

    echo "  Output: $DIST_DIR/$output_file"
    echo ""
}

# Build for all browsers
build_for_browser "chrome"
build_for_browser "firefox"

echo "=== Build Complete ==="
echo ""
ls -lh "$DIST_DIR"/chrome-extension-*.zip "$DIST_DIR"/firefox-extension-*.xpi 2>/dev/null || true
