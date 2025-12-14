---
allowed-tools: Bash, Read, Edit, Write, TodoWrite, Grep, Glob, AskUserQuestion, WebFetch
description: Execute the Chrome extension release process
model: claude-sonnet-4-20250514
argument-hint: [version] (e.g., 0.1.0)
---

Execute the Chrome extension release process for version **ext-v$1** following the authoritative workflow in `docs/dev/workflow/extension-release-process.md`.

## Release Requirements

**NOTE**: Phase 6 (Chrome Web Store submission) is a MANUAL step. This command will pause after Phase 5 and wait for user confirmation before proceeding to Phase 7.

### Execution Flow

**Automated Phases (1-5):**
1. Pre-Flight Checks - Branch, working directory, E2E tests
2. Verify Server Compatibility - Review changes, verify MIN_SERVER_VERSION accuracy, check production
3. Version Management - Update EXT_VERSION (remove -dev suffix)
4. Build Extension - Run make extension-build, verify output
5. Commit and Tag - Commit, tag, push (requires user confirmation before push)

**Manual Phase (6):**
- After Phase 5 completes, provide Chrome Web Store submission instructions
- Use AskUserQuestion to wait for user to confirm submission is complete
- Do NOT proceed to Phase 7 until user confirms

**Cleanup Phase (7):**
- Only after user confirms Chrome Web Store submission
- Bump version to next dev version (e.g., ext-v0.1.1-dev)
- Update EXT_VERSION, manifest.json, and constants.js
- Commit and push

### Execution Guidelines

1. **Read the authoritative documentation first:**
   - Open `docs/dev/workflow/extension-release-process.md`
   - Understand all phases and their validation requirements

2. **Use TodoWrite to plan the workflow:**
   - Create tasks for each phase defined in the documentation
   - Track progress through all phases
   - Mark phases complete only after validation succeeds

3. **User confirmation points:**
   - Phase 2: Confirm MIN_SERVER_VERSION is accurate after reviewing changes
   - Phase 5: Before pushing commit and tag
   - Phase 6→7: Must wait for Chrome Web Store submission to complete

4. **Validate at each step:**
   - Check pre-conditions before each phase
   - Verify outputs match expected results
   - STOP immediately on any failure

### Version Information

- **Version to release:** ext-v$1
- **EXT_VERSION format:** `VERSION=ext-v$1`
- **Git tag:** ext-v$1
- **Manifest version:** $1 (numeric only)
- **Output file:** dist/chrome-extension-ext-v$1.zip

### Critical Requirements

- **Single source of truth:** Follow `docs/dev/workflow/extension-release-process.md` exactly
- **No shortcuts:** Complete all validation checks
- **Mandatory pause:** Must wait for user confirmation after Phase 5 before Phase 7
- **Error handling:** Stop on failure, provide guidance

Begin by reading `docs/dev/workflow/extension-release-process.md` and creating a TodoWrite task list for all phases.
