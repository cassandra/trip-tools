# Browser Extension Release Process

## Release Overview

The browser extension follows its own release cycle, independent of but coordinated with the server application:

- Extension source code lives in `tools/extension/src/`
- Browser-specific manifests in `tools/extension/` (manifest.chrome.json, manifest.firefox.json)
- Version info stored in `EXT_VERSION` at project root
- Extension releases tagged with version name
- Built extensions submitted to Chrome Web Store and Firefox Add-ons

**Key Constraint:** Extension releases may depend on specific server API versions. The `MIN_SERVER_VERSION` in `EXT_VERSION` documents this dependency.

## Prerequisites

- Direct repository access (core maintainers only)
- Chrome Web Store developer account access
- All target changes merged into `main` branch
- Production server running at least `MIN_SERVER_VERSION`

## Version Files

**`EXT_VERSION`** (project root):
```
VERSION=ext-v0.1.0-dev
MIN_SERVER_VERSION=v0.3.0
```

- `VERSION`: Current extension version with `ext-v` prefix (matches git tags)
- `MIN_SERVER_VERSION`: Minimum server version required for this extension

**Version Format:**
- Uses `ext-v` prefix to match git tags and distinguish from server versions
- Chrome manifest requires numeric-only version, so build script handles conversion
- Development versions use `.999` suffix (fourth position) to be visibly distinct from releases

| Location | Dev Example | Release Example |
|----------|-------------|-----------------|
| EXT_VERSION | `ext-v0.1.0-dev` | `ext-v0.1.0` |
| Git tag | (none) | `ext-v0.1.0` |
| manifest.json `version` | `0.1.0.999` | `0.1.0` |
| manifest.json `version_name` | `ext-v0.1.0-dev` | `ext-v0.1.0` |
| constants.js `EXTENSION_VERSION` | `ext-v0.1.0-dev` | `ext-v0.1.0` |

**Files updated by build script in `dist1 directory before ZIP:**
- `manifest.json` - `version` (stripped) and `version_name` (full)
- `shared/constants.js` - `EXTENSION_VERSION` and `IS_DEVELOPMENT` flag

## Release Workflow

The release process consists of 7 phases.

### Phase 1: Pre-Flight Checks

**Purpose:** Verify system is ready for release

**Actions:**
```bash
# 1. Verify on main branch with clean working directory
git branch --show-current
# Expected: main

git status
# Expected: "nothing to commit, working tree clean"

# 2. Verify synced with origin
git fetch origin
git status
# Expected: "Your branch is up to date with 'origin/main'"

# 3. Run E2E tests
make test-e2e-extension-isolated
make test-e2e-webapp-extension-real
```

**Validation Checklist:**
- [ ] On `main` branch
- [ ] Working directory clean
- [ ] Local main synced with origin/main
- [ ] E2E tests pass (if applicable)

### Phase 2: Verify Server Compatibility

**Purpose:** Verify MIN_SERVER_VERSION is accurate and production server meets the requirement

**Actions:**
```bash
# 1. Review changes since last extension release
git log --oneline ext-v<last-release>..HEAD -- tools/extension/
# Examine what changed - do any changes depend on new server endpoints/fields?

# 2. Check current MIN_SERVER_VERSION
cat EXT_VERSION
# Ask yourself: Is this still accurate given the changes above?
# If extension now requires newer server features, update MIN_SERVER_VERSION first

# 3. Check production server version
curl -s https://triptools.net/health | grep version
# Verify production version >= MIN_SERVER_VERSION
```

**Verification Questions:**
- Do any extension changes since last release use new API endpoints?
- Do any changes depend on new response fields or server behavior?
- If yes to either: Is MIN_SERVER_VERSION updated to reflect this?

**Validation Checklist:**
- [ ] Reviewed changes since last release
- [ ] Confirmed MIN_SERVER_VERSION is accurate for these changes
- [ ] Production server version checked
- [ ] Production version >= MIN_SERVER_VERSION

**If MIN_SERVER_VERSION Needs Updating:**
- Update EXT_VERSION with correct MIN_SERVER_VERSION
- This becomes part of the release commit

**If Production Is Behind:**
- Deploy server first (see `release-process.md`)
- Then proceed with extension release

### Phase 3: Version Management

**Purpose:** Update version number for release

**Actions:**
```bash
# 1. Check current version
cat EXT_VERSION
# Example: VERSION=ext-v0.1.0-dev

# 2. Update EXT_VERSION - remove -dev suffix
# Edit EXT_VERSION to set release version:
#   VERSION=ext-v0.1.0
#   MIN_SERVER_VERSION=v0.3.0

# 3. Verify the update
cat EXT_VERSION
```

**Version Format:**
- **Development:** `ext-vX.Y.Z-dev` (e.g., ext-v0.1.0-dev)
- **Release:** `ext-vX.Y.Z` (e.g., ext-v0.1.0)

**Validation Checklist:**
- [ ] VERSION has no `-dev` suffix
- [ ] VERSION follows semantic versioning
- [ ] MIN_SERVER_VERSION is accurate

### Phase 4: Build Extension

**Purpose:** Create production-ready extension package

**Actions:**
```bash
# 1. Run the build script
make extension-build

# 2. Verify output
ls -la dist/
# Should show: chrome-extension-0.1.0.zip

# 3. Ensure script string replacements worked:
grep -e version dist/chrome-extension/manifest.json
# Should show proper version and version name

grep -e EXTENSION_VERSION -e IS_DEVELOPMENT dist/chrome-extension/shared/constants.js
# Should show proper version and development mode 'false'

# 4. Optionally test the built extension locally
#    - Open chrome://extensions/
#    - Enable Developer mode
#    - Load unpacked from dist/chrome-extension/
#    - Verify it works against production server
```

**What the Build Does:**
1. Copies `tools/extension/src/` to `dist/extension-{browser}/`
2. Copies the appropriate manifest (manifest.chrome.json or manifest.firefox.json)
3. Updates `manifest.json` with release version
4. Updates `constants.js`:
   - Sets `EXTENSION_VERSION` to release version
   - Sets `IS_DEVELOPMENT` to `false`
5. Creates `dist/extension-{browser}-{version}.zip` (or .xpi for Firefox)

**Validation Checklist:**
- [ ] Build completed without errors
- [ ] Zip file created at expected location
- [ ] Versions and IS_DEVELOPMENT all have correct settings
- [ ] (Optional) Local testing against production passed

### Phase 5: Commit and Tag

**Purpose:** Record the release in git

**Actions:**
```bash
# 1. Stage and commit version change
git add EXT_VERSION
git commit -m "Extension release ext-v0.1.0"

# 2. Create annotated tag
git tag -a ext-v0.1.0 -m "Extension release ext-v0.1.0"

# 3. Push commit and tag
git push origin main
git push origin ext-v0.1.0

# 4. Verify tag on remote
git ls-remote --tags origin | grep ext-v0.1.0
```

**Tag Format:**
- Tag name: `ext-vX.Y.Z` (e.g., `ext-v0.1.0`)
- Prefix distinguishes from server releases (`v0.3.0`)

**Validation Checklist:**
- [ ] EXT_VERSION committed
- [ ] Annotated tag created
- [ ] Pushed to origin/main
- [ ] Tag pushed to origin

### Phase 6: Submit to Chrome Web Store

**Purpose:** Publish extension to users

**Actions:**
1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Select the Trip Tools Extension (or create new if first release)
3. Upload `dist/chrome-extension-{version}.zip`
4. Fill in/update store listing:
   - Description
   - Screenshots
   - Privacy policy URL: `https://triptools.net/privacy`
5. Submit for review

**Chrome Web Store Notes:**
- Review typically takes 1-3 business days
- First submission may take longer
- Keep browser open to respond to any reviewer questions

**Validation Checklist:**
- [ ] Zip file uploaded
- [ ] Store listing complete
- [ ] Submitted for review
- [ ] Note submission date for tracking

### Phase 7: Post-Release Cleanup

**Purpose:** Prepare for next development cycle

**Actions:**
```bash
# 1. Determine next version
# Current: ext-v0.1.0
# Next dev: ext-v0.1.1-dev (patch) or ext-v0.2.0-dev (minor)

# 2. Update EXT_VERSION
# Edit to set next development version:
#   VERSION=ext-v0.1.1-dev
#   MIN_SERVER_VERSION=v0.3.0

# 3. Update tools/extension/manifest.chrome.json:
# Edit to set next development version:
#   "version": "0.1.1.999",
#   "version_name": "ext-v0.1.1-dev",

# 4. Update tools/extension/manifest.firefox.json:
# Edit to set next development version:
#   "version": "0.1.1.999",

# 5. Update tools/extension/src/shared/constants.js:
# Edit to set next development version:
#   EXTENSION_VERSION: 'ext-v0.1.1-dev',

# 6. Commit
git add EXT_VERSION tools/extension/manifest.*.json tools/extension/src/shared/constants.js
git commit -m "Bump extension version to ext-v0.1.1-dev"
git push origin main

# 7. Verify clean state
git status
# Expected: clean working directory
```

**Validation Checklist:**
- [ ] EXT_VERSION updated with `-dev` suffix
- [ ] manifest.json updated with next dev version
- [ ] constants.js updated with next dev version
- [ ] Committed and pushed
- [ ] Working directory clean

## Versioning Guidelines

### Extension Version (X.Y.Z)

- **MAJOR (X):** Breaking changes, major redesign
- **MINOR (Y):** New features, significant enhancements
- **PATCH (Z):** Bug fixes, minor improvements

### MIN_SERVER_VERSION

Update when the extension:
- Uses new API endpoints
- Requires new API response fields
- Depends on server-side behavior changes

Do NOT update when:
- Extension-only changes (UI, bug fixes)
- Using existing stable API endpoints

## Troubleshooting

### "Production server version too old"

**Problem:** MIN_SERVER_VERSION > production version

**Solution:**
1. Deploy server first (see `release-process.md`)
2. Then proceed with extension release

### "Build script fails"

**Problem:** `make extension-build` errors

**Solution:**
1. Check EXT_VERSION file exists and has correct format
2. Verify `tools/extension/src/` directory exists
3. Verify browser-specific manifest exists (manifest.chrome.json or manifest.firefox.json)
4. Check for syntax errors in source files

### "Chrome Web Store rejection"

**Problem:** Extension rejected during review

**Solution:**
1. Read rejection reason carefully
2. Common issues:
   - Missing privacy policy
   - Excessive permissions
   - Policy violations
3. Fix issues and resubmit

## Related Documentation

- [Server Release Process](release-process.md)
- [Browser Extension Development](../extensions/browser-extension.md)
- [E2E Testing](../testing/e2e-testing.md)
