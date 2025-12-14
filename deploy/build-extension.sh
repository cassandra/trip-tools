#!/bin/bash
#
# Build Chrome extension for production release.
# Creates a zip file ready for Chrome Web Store submission.
#
# Usage: ./deploy/build-extension.sh
#
# Reads version info from EXT_VERSION file.
# Outputs to dist/chrome-extension-{version}.zip
#

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EXT_VERSION_FILE="$PROJECT_ROOT/EXT_VERSION"
EXT_SOURCE_DIR="$PROJECT_ROOT/tools/chrome"
DIST_DIR="$PROJECT_ROOT/dist"
EXT_DIST_DIR="$DIST_DIR/chrome-extension"

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
# MANIFEST_VERSION is Chrome-compatible:
#   - Strip "ext-v" prefix
#   - If "-dev" suffix: replace with ".999" (e.g., "0.1.0.999")
#   - If no "-dev": use as-is (e.g., "0.1.0")
VERSION_NAME="$VERSION"
MANIFEST_VERSION="${VERSION#ext-v}"
if [[ "$MANIFEST_VERSION" == *"-dev"* ]]; then
    MANIFEST_VERSION="${MANIFEST_VERSION%-dev}.999"
fi

echo "=== Building Chrome Extension ==="
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

# Clean previous build (hardcoded paths for safety - rm -rf is dangerous)
echo "Cleaning previous build..."
/bin/rm -rf "$PROJECT_ROOT/dist/chrome-extension"
/bin/rm -f "$PROJECT_ROOT/dist"/chrome-extension-*.zip

# Create dist directory
mkdir -p "$EXT_DIST_DIR"

# Copy source files
echo "Copying extension files..."
cp -r "$EXT_SOURCE_DIR"/* "$EXT_DIST_DIR"/

# Update manifest.json - version (Chrome-compatible) and version_name (display)
echo "Updating manifest.json..."
sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$MANIFEST_VERSION\"/" "$EXT_DIST_DIR/manifest.json"
sed -i.bak "s/\"version_name\": \"[^\"]*\"/\"version_name\": \"$VERSION_NAME\"/" "$EXT_DIST_DIR/manifest.json"
/bin/rm -f "$EXT_DIST_DIR/manifest.json.bak"

# Update constants.js - version and IS_DEVELOPMENT
echo "Updating constants.js..."
sed -i.bak "s/EXTENSION_VERSION: '[^']*'/EXTENSION_VERSION: '$VERSION_NAME'/" "$EXT_DIST_DIR/shared/constants.js"
sed -i.bak "s/IS_DEVELOPMENT: true/IS_DEVELOPMENT: false/" "$EXT_DIST_DIR/shared/constants.js"
/bin/rm -f "$EXT_DIST_DIR/shared/constants.js.bak"

# Create zip file
echo "Creating zip file..."
cd "$DIST_DIR"
zip -rq "chrome-extension-$VERSION_NAME.zip" chrome-extension/

echo ""
echo "=== Build Complete ==="
echo "Output: $DIST_DIR/chrome-extension-$VERSION_NAME.zip"
echo ""
ls -lh "$DIST_DIR/chrome-extension-$VERSION_NAME.zip"
