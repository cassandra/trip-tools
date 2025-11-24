---
allowed-tools: Bash, Read, TodoWrite, Task
description: Prepare code on current branch for PR with quality checks and analysis
model: claude-sonnet-4-20250514
argument-hint:
---

Prepare code on a feature branch for a PR by reviewing changes against our quality standards:

## Code Review Preparation Process

Execute comprehensive review preparation:

1. **Use TodoWrite to plan review preparation** - Track all quality checks
   - Read `docs/CLAUDE.md` for AI behavior patterns and quality standards
   - Use sub-agent coordination for expert analysis

2. **Run mandatory quality checks** - Both must pass:
   ```bash
   # Run full test suite (must pass)
   make test
   ```
   ```bash
   # Run code quality check (must pass with no output)
   make lint
   ```
   **CRITICAL**: Address any failures before proceeding

3. **Generate change summary** - Document what was modified by looking at all commits in this branch since it branched from `main`:
   ```bash
   # Show all commits on current branch
   git log --oneline --graph -100
   ```

3a. **CRITICAL** Analyze all commits to pick out most important work and ignore commits that were relatively minor or branch-only cleanups.  We want to focus on the major work that will go onto the main branch.
   ```
   # Show diff against main branch
   git diff main...HEAD

   # Show changed files
   git diff --name-only main...HEAD
   ```
   
4. **Use specialized review agents** - Get expert analysis from relevant sub-agents:
   - **Use Task tool with code-quality agent**: Review test coverage and quality
   - **Use Task tool with test-engineer agent**: Review test coverage and quality
   - **Use Task tool with domain-expert agent**: Analyze business logic changes
   - **Use Task tool with backend-dev agent**: Review Django patterns (if applicable)
   - **Use Task tool with frontend-dev agent**: Review template/UI changes (if applicable)

5. **Identify potential issues** - Look for:
   - Code quality concerns
   - Security vulnerabilities
   - Performance implications
   - Breaking changes
   - Missing tests
   - Documentation gaps

6. **Create review checklist** - Generate actionable items:
   - Code quality improvements needed
   - Test coverage gaps to address
   - Documentation updates required
   - Security considerations
   - Performance optimizations
   - Breaking change documentation

7. **Generate review summary** - Provide comprehensive overview:
   - Summary of changes made
   - Key components modified
   - Business impact assessment
   - Quality metrics (tests passing, lint clean)
   - Potential risks or concerns
   - Reviewer guidance and focus areas

**Review preparation goals:**
- Ensure code meets our quality standards
- Identify potential issues before PR creation
- Provide comprehensive change documentation
- Generate reviewer guidance

**Current branch:** [Will be determined from git status]

Begin review preparation now.
