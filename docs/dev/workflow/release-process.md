# Release Process

## Release Overview

Trip Tools uses a structured release workflow for deploying to production:
- Development work in feature branches
- Feature branches merged to `main` via PRs
- `release` branch serves as production release branch
- Releases merge accumulated changes from `main` to `release`
- Deployment happens directly to DigitalOcean droplet

**Target Environment:** DigitalOcean production droplet at triptools.net

## Prerequisites

- Direct repository access (core maintainers only)
- Local development environment configured
- All target changes merged into `main` branch
- SSH access to production droplet configured
- Docker running locally (checked automatically by make targets)
- Make targets operational (`make docker-build`, `make deploy-prod`)

## Release Workflow

The release process consists of 8 phases with extensive validation at each step.

### Phase 1: Pre-Flight Checks

**Purpose:** Verify system is in correct state before starting release

**Actions:**
```bash
# 1. Verify on main branch
git branch --show-current
# Expected: main

# 2. Verify working directory is clean
git status
# Expected: "nothing to commit, working tree clean"

# 3. Verify synced with origin
git fetch origin
git status
# Expected: "Your branch is up to date with 'origin/main'"

# 4. Check for temporary debugging code
grep -rn --include="*.py" -iE "breakpoint|True.or|False.and|zzz" src/custom src/tt
# Expected: No output (no debugging code found)
# If found, remove before proceeding

# 5. Run lint checks
make lint
# Expected: No output (all checks pass)

# 6. Run test suite
make test
# Expected: All tests pass

# 7. Preview commits since last release
git log --oneline $(git describe --tags --abbrev=0)..HEAD
# Review what will be included in this release
```

**Validation Checklist:**
- [ ] On `main` branch
- [ ] Working directory clean (no uncommitted changes)
- [ ] Local main synced with origin/main
- [ ] No temporary debugging code (breakpoint, True or, False and, zzz)
- [ ] `make lint` passes with no output
- [ ] `make test` passes all tests
- [ ] Commits reviewed and appropriate for release

**Common Issues:**
- **Uncommitted changes**: Commit or stash before proceeding
- **Out of sync**: Pull latest changes from origin
- **Debugging code found**: Remove all breakpoint(), True or, False and, zzz markers before releasing
- **Tests failing**: Fix tests before releasing
- **Wrong branch**: Switch to main before starting

### Phase 2: Version Management

**Purpose:** Update version number for release

**Actions:**
```bash
# 1. Check current version
cat TT_VERSION
# Example: v0.0.1-dev

# 2. Determine new version
# - Remove -dev suffix for release
# - Follow semantic versioning (vX.Y.Z)
# - MAJOR: Breaking changes
# - MINOR: New features (backward compatible)
# - PATCH: Bug fixes (backward compatible)

# 3. Update TT_VERSION file
# Edit to new version (e.g., v0.0.1)
echo "v0.0.1" > TT_VERSION
```

**Version Format:**
- **Development:** `vX.Y.Z-dev` (e.g., v0.0.1-dev)
- **Release:** `vX.Y.Z` (e.g., v0.0.1)

**Validation Checklist:**
- [ ] Version format is `vX.Y.Z` (no -dev suffix)
- [ ] Version follows semantic versioning
- [ ] Version is higher than previous release
- [ ] TT_VERSION file updated correctly

**Common Issues:**
- **Forgot to remove -dev**: Release version must not have -dev suffix
- **Wrong version number**: Verify major/minor/patch is correct
- **Invalid format**: Must start with 'v' and follow vX.Y.Z pattern

### Phase 3: Changelog Update

**Purpose:** Document what changed in this release

**Actions:**
```bash
# 1. Open CHANGELOG.md for editing
# Add new entry at the top of the list

# Example:
# - v0.0.1 : Initial release with trip journal and travelog features

# 2. Keep entry concise but meaningful
# - Focus on user-visible changes
# - Use present tense
# - Be specific but brief (one line preferred)
```

**Changelog Entry Guidelines:**
- Start with version number: `- vX.Y.Z : `
- Brief description (aim for single line)
- Focus on features, not implementation details
- Use clear, user-friendly language

**Example Entries:**
```markdown
- v0.0.2 : Added email notifications for trip updates
- v0.0.1 : Initial release with trip journal and travelog features
```

**Validation Checklist:**
- [ ] CHANGELOG.md updated with new version
- [ ] Entry is clear and concise
- [ ] Version matches TT_VERSION
- [ ] Entry format follows existing pattern

**Common Issues:**
- **Too verbose**: Keep it to one line if possible
- **Too vague**: Be specific about what changed
- **Wrong version**: Must match TT_VERSION exactly

### Phase 4: Commit Version Bump

**Purpose:** Commit version and changelog changes to main

**Actions:**
```bash
# 1. Stage version files
git add TT_VERSION CHANGELOG.md

# 2. Verify staged changes
git diff --cached
# Check that only TT_VERSION and CHANGELOG.md are staged

# 3. Commit with standard message and **WITHOUT** any attributions.
git commit -m "Bump version to v0.0.1"

# 4. Push to origin/main
git push origin main

# 5. Verify push succeeded
git status
# Expected: "Your branch is up to date with 'origin/main'"
```

**Commit Message Format:**
```
Bump version to vX.Y.Z
```

**Validation Checklist:**
- [ ] Only TT_VERSION and CHANGELOG.md staged
- [ ] Commit message follows format
- [ ] Push to origin/main succeeded
- [ ] No other uncommitted changes

**Common Issues:**
- **Extra files staged**: Only version files should be committed
- **Push failed**: Check network, credentials, or branch protection
- **Typo in commit message**: Use exact format

**Rollback If Needed:**
```bash
# If commit made but not pushed:
git reset --soft HEAD~1

# If pushed but need to undo:
git revert HEAD
git push origin main
```

### Phase 5: Merge to Release Branch

**Purpose:** Merge main into release branch for deployment

**Actions:**
```bash
# 1. Switch to release branch
git checkout release

# 2. Pull latest from origin/release
git pull origin release
# Note: Release will be behind main - this is expected

# 3. Merge main into release
git merge main
# Should be fast-forward merge

# 4. Verify merge succeeded
git log --oneline -3
# Should show version bump commit at top

# 5. Push to origin/release
git push origin release

# 6. Verify push succeeded
git status
# Expected: "Your branch is up to date with 'origin/release'"
```

**Branch Strategy Notes:**
- Release branch is **always behind** main until releases
- Main contains latest development work
- Release contains only released versions
- **NEVER** make changes directly on release
- **ALWAYS** merge from main to release

**Validation Checklist:**
- [ ] On release branch
- [ ] Pulled latest origin/release
- [ ] Merge from main succeeded
- [ ] Push to origin/release succeeded
- [ ] No merge conflicts

**Common Issues:**
- **Merge conflicts**: Should be rare; resolve carefully or abort and investigate
- **Not fast-forward**: Indicates release has commits not in main (BAD)
- **Push failed**: Check credentials or branch protection

**Common Mistakes to Avoid:**
- ❌ NEVER edit files directly on release branch
- ❌ NEVER commit version changes on release
- ❌ NEVER make changes after merge to release
- ✅ ALL changes must come from main via merge

**Rollback If Needed:**
```bash
# If merge not pushed yet:
git merge --abort  # or
git reset --hard origin/release

# If pushed but need to undo:
# This is complex - contact team lead
```

### Phase 6: Tag the Release

**Purpose:** Create git tag for version tracking

**Actions:**
```bash
# 1. Create annotated tag (still on release branch)
git tag -a v0.0.1 -m "Release v0.0.1"

# 2. Verify tag created
git tag -l "v0.0.1"
# Should show: v0.0.1

# 3. View tag details
git show v0.0.1
# Shows tag info and commit details

# 4. Push tag to origin
git push origin v0.0.1

# 5. Verify tag on remote
git ls-remote --tags origin | grep v0.0.1
```

**Tag Format:**
- Tag name: `vX.Y.Z` (matches version exactly)
- Tag message: `Release vX.Y.Z`
- Always use annotated tags (`-a` flag)

**Validation Checklist:**
- [ ] Tag created on release branch
- [ ] Tag name matches version
- [ ] Tag is annotated (not lightweight)
- [ ] Tag pushed to origin
- [ ] Tag visible on remote

**Common Issues:**
- **Tag already exists**: Delete old tag if needed (`git tag -d vX.Y.Z`)
- **Lightweight tag**: Must use `-a` for annotated tag
- **Wrong branch**: Tag should be on release branch

**Rollback If Needed:**
```bash
# Delete local tag
git tag -d v0.0.1

# Delete remote tag (if pushed)
git push origin :refs/tags/v0.0.1
```

### Phase 7: Build and Deploy

**Purpose:** Build Docker image and deploy to production

**⚠️ CRITICAL:** This phase deploys to PRODUCTION. Execute each step separately with validation.

**Step 1: Build Docker Image**
```bash
# Precondition: On release branch with tag created
git branch --show-current
# Expected: release

# Build Docker image
make docker-build

# Verify build succeeded
docker images | grep tt
# Should show: tt  vX.X.X  and tt  latest
```

**Validation:**
- [ ] Docker build completed without errors
- [ ] Image tagged with correct version
- [ ] Image also tagged as 'latest'

**Step 2: Save and Prepare Image**
```bash
# Precondition: Docker build succeeded
docker images tt:$(cat TT_VERSION)
# Should show the image exists

# Save image to tar.gz (this will take 1 to 2 minutes given the size)
make docker-push

# Verify tar.gz created
ls -lh /tmp/tt-docker-image-*.tar.gz
# Should show file ~100-500MB in size
```

**Validation:**
- [ ] Image saved to /tmp/tt-docker-image-vX.X.X.tar.gz
- [ ] File size is reasonable (100-500MB)
- [ ] No errors during save process

**Step 3: Deploy to Production**
```bash
# Precondition: Image tar.gz exists locally
test -f /tmp/tt-docker-image-$(cat TT_VERSION).tar.gz && echo "Image ready" || echo "ERROR: Image not found"

# CONFIRM WITH USER BEFORE PROCEEDING
# Display warning:
echo "⚠️  PRODUCTION DEPLOYMENT ⚠️"
echo "About to deploy version $(cat TT_VERSION) to triptools.net"
echo "This will:"
echo "  - Copy environment file to droplet"
echo "  - Transfer Docker image (~200-400MB)"
echo "  - Restart services (brief downtime)"
echo ""
read -p "Proceed with deployment? (yes/no): " confirm

# If user confirms, deploy
if [ "$confirm" = "yes" ]; then
    make deploy-prod
else
    echo "Deployment cancelled"
    exit 1
fi

# Monitor output for:
# - "Copying environment file to droplet..."
# - "Copying Docker image to droplet..."
# - "Loading image and restarting services on droplet..."
# - "Deployment complete!"
```

**What `make deploy-prod` Does:**

1. **Check Docker running:**
   - Verifies Docker daemon is running locally (fails fast with clear error if not)

2. **Copy environment file:**
   - Converts `.private/env/production.sh` to docker-compose format (if needed)
   - SCPs to droplet: `/opt/triptools/triptools.env`

3. **Transfer Docker image:**
   - SCPs tar.gz to droplet: `/tmp/`

4. **Load and restart:**
   - SSHs to droplet
   - Loads Docker image from tar.gz
   - Runs `docker-compose --env-file triptools.env down`
   - Runs `docker-compose --env-file triptools.env up -d`
   - Cleans up temp files (local and remote)

**Validation Checklist:**
- [ ] docker-build succeeded
- [ ] docker-push created tar.gz file
- [ ] User confirmed deployment
- [ ] Environment file copied successfully
- [ ] Docker image copied successfully
- [ ] Image loaded on droplet
- [ ] Services restarted successfully
- [ ] "Deployment complete!" message shown
- [ ] No errors in output

**Common Issues:**
- **Docker not running**: Start Docker locally and retry (`make deploy-prod` checks this automatically)
- **Docker build fails**: Check Dockerfile syntax or dependencies
- **Image too large**: Check for unnecessary files in Docker context
- **SCP transfer fails**: Check SSH credentials or network connectivity
- **Droplet SSH fails**: Verify droplet is running and accessible
- **docker-compose fails**: Check triptools.env file or docker-compose.yml syntax
- **Services won't start**: Check Docker logs on droplet

**Monitoring Deployment:**
```bash
# After deployment, verify site is up (may need to wait a little):
curl -I https://triptools.net
# Should return 200 OK (will may code 502 initially when it is starting)

# Check health endpoint:
curl https://triptools.net/health
# Should return JSON with status information including current version to check

# Check Docker container status on droplet:
ssh root@triptools.net "docker ps"
# Should show tt container running
```

**Rollback If Needed:**
See "Rollback Procedures" section below for emergency rollback steps.

### Phase 8: Post-Release Cleanup

**Purpose:** Prepare main branch for next development cycle

**Actions:**
```bash
# 1. Switch back to main branch
git checkout main

# 2. Fetch latest tags
git fetch --tags

# 3. Determine next version
# Current: v0.0.1
# Next dev: v0.0.2-dev
# (Increment patch by default)

# 4. Update TT_VERSION
echo "v0.0.2-dev" > TT_VERSION

# 5. Commit version bump **WITHOUT** any attributions.
git add TT_VERSION
git commit -m "Bump version to v0.0.2-dev"

# 6. Push to origin/main
git push origin main

# 7. Verify clean state
git status
# Expected: clean working directory
```

**Next Version Guidelines:**
- **Default**: Increment patch + add `-dev` (v0.0.1 → v0.0.2-dev)
- **Planning minor**: Use next minor + `-dev` (v0.0.1 → v0.1.0-dev)
- **Planning major**: Use next major + `-dev` (v0.0.1 → v1.0.0-dev)

**Validation Checklist:**
- [ ] Back on main branch
- [ ] TT_VERSION has -dev suffix
- [ ] Version higher than release
- [ ] Commit message follows format
- [ ] Pushed to origin/main
- [ ] Working directory clean

**Common Issues:**
- **Forgot -dev suffix**: Dev versions must have -dev
- **Wrong version**: Should be next anticipated version

**Release Process Complete!**

## Post-Release Tasks (Manual)

### Immediate Validation (Within 1 Hour)

1. **Verify site accessibility:**
   ```bash
   curl -I https://triptools.net
   # Should return 200 OK
   ```

2. **Test critical user flows:**
   - User login
   - Create/edit trip
   - Upload images
   - View travelogs

3. **Check application logs:**
   ```bash
   ssh root@triptools.net "docker logs tt"
   # Look for errors or warnings
   ```

4. **Monitor error rates:**
   - Check Django admin for error logs
   - Watch for user reports

### Post-Release Monitoring (First 24 Hours)

- Monitor application logs for errors
- Watch for user-reported issues
- Check system resources (CPU, memory, disk)
- Verify background tasks running (if any)

### If Issues Discovered

See "Rollback Procedures" section below.

## Rollback Procedures

### Emergency Rollback

If critical issues discovered after deployment:

1. **Identify last working version:**
   ```bash
   git tag -l | tail -5
   # Find previous release tag
   ```

2. **Rollback on droplet:**
   ```bash
   ssh root@triptools.net
   cd /opt/triptools

   # Use previous image version
   docker-compose down
   # Edit .env or docker-compose.yml to use previous version
   docker-compose up -d
   ```

3. **Verify rollback:**
   ```bash
   curl -I https://triptools.net
   # Check site is responding
   ```

4. **Communicate rollback:**
   - Update team on status
   - Document issue for investigation
   - Plan fix for next release

### Post-Rollback Actions

1. **Investigate root cause** of failure
2. **Create hotfix branch** if needed
3. **Test fix thoroughly** before next release
4. **Update release process** if process improvement needed

## Version Numbering Guidelines

Trip Tools follows **Semantic Versioning** (semver):

**Format:** `vMAJOR.MINOR.PATCH[-dev]`

**When to increment:**

- **MAJOR (v1.0.0):** Breaking changes
  - Database schema changes requiring migration
  - API changes breaking compatibility
  - Major feature rewrites

- **MINOR (v0.1.0):** New features (backward compatible)
  - New user-facing features
  - New API endpoints
  - Significant enhancements

- **PATCH (v0.0.1):** Bug fixes (backward compatible)
  - Bug fixes
  - Security patches
  - Minor improvements

**Development versions:**
- Always have `-dev` suffix (e.g., v0.0.2-dev)
- Used on main branch between releases

## Common Mistakes to Avoid

1. **Making changes directly on release branch**
   - ❌ Never edit files on release
   - ✅ Always make changes on main and merge

2. **Forgetting to remove -dev suffix**
   - ❌ Releasing with v0.0.1-dev
   - ✅ Release version must be v0.0.1

3. **Skipping pre-flight checks**
   - ❌ Releasing with failing tests
   - ✅ Always run make check before releasing

4. **Not confirming deployment**
   - ❌ Auto-deploying to production
   - ✅ Always get explicit user confirmation

5. **Forgetting post-release cleanup**
   - ❌ Leaving main at v0.0.1
   - ✅ Bump to v0.0.2-dev after release

## Troubleshooting

### "Working directory not clean"

**Problem:** Uncommitted changes block release

**Solution:**
```bash
git status
# Review uncommitted changes
git stash  # or commit them
```

### "Tests failing"

**Problem:** `make test` fails

**Solution:**
- Fix failing tests before releasing
- Don't skip this check
- Tests must pass for release

### "Merge conflict on release branch"

**Problem:** Release branch has diverged from main

**Solution:**
- **This should not happen** - investigate why
- Release should only have commits from main
- Consult team lead before resolving

### "Deployment failed"

**Problem:** `make release-prod` fails

**Solution:**
1. Check error message for specific failure
2. Don't retry blindly - understand the issue
3. Fix root cause (network, credentials, Docker, etc.)
4. May need to rollback if partially deployed

### "Site down after deployment"

**Problem:** Site not responding after deploy

**Solution:**
1. **Immediate:** Execute rollback procedure
2. Check Docker container status
3. Review application logs
4. Investigate root cause offline
5. Fix and re-release

## Related Documentation

- [Workflow Guidelines](workflow-guidelines.md)
- [Testing Guidelines](../testing/testing-guidelines.md)
- [Deployment Infrastructure](../infrastructure/deployment.md)

## Notes

- **No GitHub Releases:** Trip Tools is a hosted web app, not a downloadable application, so GitHub releases are not used
- **Direct Deployment:** Deployment happens directly to DigitalOcean, not via GitHub Actions
- **Manual Process:** Release requires maintainer with SSH access and local deployment setup
- **Safety First:** Extensive validation at each step prevents bad releases
