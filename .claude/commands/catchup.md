---
allowed-tools: Bash, Read, TodoWrite, Grep, Glob
description: Sync AI understanding with user-made code changes
model: claude-sonnet-4-20250514
argument-hint: [file-path...]
---

Catch up on user-made code changes to sync AI understanding with current codebase state:

## Purpose

When users make changes related to work AI agents have been doing, AI agents may have cached/outdated views of:
- Syntax and naming conventions
- Design decisions and architectural approaches
- Patterns and abstractions
- Responsibility boundaries

This command analyzes recent changes and extracts key takeaways for future AI work.

## Catchup Process

1. **Identify changes to analyze** - Determine scope based on arguments:

   **If file paths provided ($ARGUMENTS):**
   ```bash
   # Show diff for specific files
   git diff -- $ARGUMENTS
   git diff --staged -- $ARGUMENTS
   ```

   **If no arguments:**
   ```bash
   # Show all uncommitted changes (staged and unstaged)
   git diff
   git diff --staged
   ```

2. **Check for changes** - If no uncommitted changes exist:
   - Report "No uncommitted changes found"
   - Suggest: "Did you mean to specify a commit range? Try `/catchup HEAD~3` or commit after making changes."
   - Exit gracefully

3. **Read changed files** - For each modified file:
   - Read the current (post-change) version
   - Understand the full context of changes

4. **Analyze changes for key patterns** - Look for:
   - **Naming conventions**: Variable names, function names, class names used
   - **Code organization**: How responsibilities are divided
   - **Architectural patterns**: Design approaches, abstractions introduced
   - **Style choices**: Formatting, structure, comment patterns
   - **Business logic**: Domain-specific decisions and constraints
   - **Deviations from AI's prior approach**: What the user changed from AI-generated code

5. **Generate key takeaways** - Produce a concise bullet-point list:
   - Focus on actionable insights for future work
   - Highlight conventions to follow
   - Note design decisions to respect
   - Flag patterns to adopt in similar code
   - Keep each point brief and specific

## Output Format

```
## Catchup Summary

Analyzed N files with uncommitted changes.

### Key Takeaways

- **[Category]**: [Specific takeaway]
- **[Category]**: [Specific takeaway]
- ...

### Files Analyzed
- path/to/file1.py
- path/to/file2.js
```

## Example Output

```
## Catchup Summary

Analyzed 3 files with uncommitted changes.

### Key Takeaways

- **Naming**: Use `get_*` prefix for query methods, `compute_*` for calculations
- **Error handling**: Prefer early returns over nested conditionals
- **Imports**: Group by stdlib, third-party, local with blank lines between
- **Type hints**: Include return types on all public methods
- **Docstrings**: Use imperative mood, keep to one line when possible

### Files Analyzed
- src/tt/apps/journal/services.py
- src/tt/apps/journal/models.py
- src/tt/apps/journal/views.py
```

## Usage Examples

```
# Catch up on all uncommitted changes
/catchup

# Catch up on specific files
/catchup src/tt/apps/journal/services.py

# Catch up on a directory
/catchup src/tt/apps/journal/
```

## Critical Requirements

- **Read before analyzing**: Always read the full current file, not just the diff
- **Focus on patterns**: Extract generalizable conventions, not one-off fixes
- **Be concise**: Key takeaways should be scannable, not verbose
- **Be actionable**: Each takeaway should guide future code decisions
- **No judgment**: Report patterns neutrally without critiquing user choices

Begin catchup analysis now.
