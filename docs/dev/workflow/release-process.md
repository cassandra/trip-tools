# Release Process

## Release Overview

Releases follow structured branch workflow:
- Development work in feature branches
- Feature branches merged to `main` via PRs
- `release` branch serves as release branch
- Releases merge accumulated changes from `main` to `release`

## Prerequisites

- Direct repository access (core maintainers only)
- Local development environment configured
- All target changes merged into `main` branch

## Pre-Release Verification

1. **Confirm CI Status**: Ensure GitHub Actions pass on `main`
2. **Run Local Validation**: `make check`
3. **Review Recent Changes**: Check commits and merged PRs

## Release Steps

### 1. Prepare Main Branch

```bash
git checkout main
git pull origin main
```

### 2. Update Version Number and CHANGELOG.ms

```bash
# Edit TT_VERSION file with new version (no "-dev" suffix too)
# Add line to CHANGELOG.md file with short description
git add TT_VERSION  CHANGELOG.md
git commit -m "Bump version number to vX.X.X"
git push origin main
```

### 3. Merge to Release Branch

```bash
git checkout release
git pull origin release
git merge main
git push origin release
```

After changing to local `release`, it may be behind `origin/release` and should defintiely be behing both local `main` and `origin/main`. That is fine. When pulling in `origin/release`, it too will be behind `main`. That is normal as the release process is all about merging `main` into `origin/release`. 

Common Mistakes to Avoid:
  - NEVER make version changes directly on `release`
  - NEVER edit files after the merge to `release`
  - All changes on `release` must come from `main` via the merge

### 4. Create GitHub Release

Using GitHub CLI (preferred for automation):

```bash
gh release create vX.X.X --title "vX.X.X" --generate-notes --latest
```

Or via GitHub web interface:
1. Navigate to repository releases page
2. Click "Create a new release"
3. **Tag**: `vX.X.X` (create new)
4. **Target**: `release` branch
5. **Title**: Use tag name
6. **Description**: Use "Generate release notes"
7. **Settings**: Check "Set as latest release"
8. Click "Publish Release"

#### Check GitHub Actions

- Check that ZIP file was successfully built
- Check that Docker image was built.

### 5. Validate Install URL Works

Make sure that the published ZIP install link works and that it is at least 10MB in size and no more than 100MB in size.

Test the manual instalation ZIP file.
```bash
curl -L https://github.com/cassandra/home-information/releases/latest/download/home-information.zip -o home-information.zip
```

## 6. Cleanup

For safety, move back to `main` branch and get latest tags.
```bash
git checkout main
git fetch --tags

# Bump TT_VERSION file with next anticipatd version and a "-dev" suffix
git add TT_VERSION 
git commit -m "Bump version number to vX.X.X-dev"
git push origin main
```

This is where the automated release process ends.

## Post-Release Tasks (Manual)

### Refine Release

- Read and refine the release notes on the github page.
- Attach an image to the release

### Validate Install Script Works

Check github actions for completion of Docke rimage building.

Test the single-command installation script (this must be done manually):
```
DATE=`date '+%Y-%m-%d'`
mkdir ~/testing
cd ~/testing
mv ~/.hi ~/.hi-$DATE

curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/release/install.sh | bash
```

Best to try this on multiple types of machines.

### Post-Release Monitoring

**Critical**: Monitor the release for the first few hours after publication:
- Check GitHub Issues for user reports
- Monitor GitHub Discussions for problems

**If critical issues are discovered**, see [Rollback Process](rollback-process.md) for immediate response procedures.

### Docker Image Cleanup (Periodic)

**Every few releases**, clean up old Docker images to prevent clutter:
1. Go to: `https://github.com/cassandra/home-information/pkgs/container/home-information`
2. Review old versions and delete:
   - Versions older than 6 months (except major releases)
   - Keep at least 10 recent versions for rollback capability
   - Always keep `latest` and current stable version
3. This helps with storage management and reduces user confusion

## Version Bumping Criteria

**TBD** - Establish guidelines for:
- **Major version**: Breaking changes
- **Minor version**: New features (backward compatible)
- **Patch version**: Bug fixes (backward compatible)

## Rollback Procedures

**TBD** - Document rollback procedures:
- Revert problematic releases
- Communication protocols
- Post-rollback testing

## Notes

- **Changelog Management**: Generated from GitHub's automatic changelog
- **Deployment**: Releases distributed as downloadable packages
- **Quality Assurance**: Branch protection enforces tests and code quality

## Related Documentation
- Workflow guidelines: [Workflow Guidelines](workflow-guidelines.md)
- **[Rollback Process](rollback-process.md)** - Emergency rollback procedures for problematic releases
