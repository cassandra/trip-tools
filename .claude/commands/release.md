---
allowed-tools: Bash, Read, Edit, TodoWrite, Grep, Glob
description: Execute the complete release process from main to release
model: claude-sonnet-4-20250514
argument-hint: [version] (e.g., 1.2.3)
---

Execute our complete release process following `docs/dev/workflow/release-process.md`:

## Release for version $1

I need to execute our standardized release process with the following requirements:

1. **Use TodoWrite to plan all release steps** - Break down the entire process into trackable tasks
2. **Pre-release verification** - Verify CI status, run `make check`, review recent changes
3. **Version management** - Update TT_VERSION file to `$1` and update CHANGELOG.md
4. **Git workflow** - Merge main to release following our branch strategy
5. **GitHub release** - Create release using `gh` CLI with auto-generated notes
6. **Validation** - Check build artifacts, ZIP file size, and download URLs
7. **Cleanup** - Version bump to next dev version and return to main
8. **Post-release guidance** - Provide monitoring checklist and next steps

**Critical requirements:**
- Follow exact process in `docs/dev/workflow/release-process.md`
- Handle errors gracefully with rollback guidance
- Verify all prerequisites before starting
- Validate each step before proceeding
- Use TodoWrite tool throughout for progress tracking

**Version to release:** $1
**Target branch:** release
**Source branch:** main

Begin the release process now.
