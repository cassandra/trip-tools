---
allowed-tools: Bash, Read, Edit, Write, TodoWrite, Grep, Glob, AskUserQuestion
description: Execute the complete release process from main to release
model: claude-sonnet-4-20250514
argument-hint: [version] (e.g., 0.0.2)
---

Execute the complete Trip Tools release process for version **$1** following the authoritative workflow in `docs/dev/workflow/release-process.md`.

## Release Requirements

**CRITICAL**: This process deploys to PRODUCTION at triptools.net. Follow all validation steps carefully.

### Execution Guidelines

1. **Read the authoritative documentation first:**
   - Open `docs/dev/workflow/release-process.md`
   - Understand all phases and their validation requirements
   - Note the specific commands and expected outputs

2. **Use TodoWrite to plan the workflow:**
   - Create tasks for each phase defined in the documentation
   - Track progress through all phases
   - Mark phases complete only after validation succeeds

3. **Follow the exact process:**
   - Execute each phase in order
   - Run all validation checks as specified
   - STOP immediately on any failure
   - Provide rollback guidance if errors occur

4. **Get user confirmation before deployment:**
   - Build and Deploy phase requires explicit user confirmation
   - Display warning about production deployment
   - Execute docker-build, docker-push, and deploy-prod separately with validation between each
   - Wait for user approval before running `make deploy-prod`

5. **Validate at each step:**
   - Check pre-conditions before each phase
   - Verify outputs match expected results
   - Confirm successful completion before proceeding

### Critical Requirements

- **Single source of truth:** Follow `docs/dev/workflow/release-process.md` exactly
- **No shortcuts:** Complete all pre-flight checks and validations
- **User confirmation:** Required before production deployment
- **Error handling:** Stop on failure, provide rollback guidance
- **Version argument:** Use version `$1` throughout the process

### Version Information

- **Version to release:** $1
- **Target branch:** release
- **Source branch:** main
- **Deployment target:** DigitalOcean production droplet (triptools.net)

Begin by reading `docs/dev/workflow/release-process.md` and creating a TodoWrite task list for all phases defined there.
