# /conform Command

Apply project formatting conventions to Python code using a specialized formatting agent.

## Usage
```
/conform <target> [--check]
```

Where `<target>` can be:
- A Python filename: `services.py`
- A class name: `JournalPublishingService`
- A relative path: `tt/apps/journal/services.py`

Options:
- `--check`: Report violations without making changes

## Examples
```
/conform services.py
/conform JournalPublishingService
/conform tt/apps/journal/services.py --check
```

## Process

### Step 1: Locate Target
Find the target file using the provided identifier.

### Step 2: Read Formatting Rules
Read the formatting rules from: `docs/dev/shared/formatting-rules.md`

### Step 3: Launch Formatting Agent
Launch a `code-quality` sub-agent with this specific prompt:

```
You are a specialized code formatting agent. Your ONLY task is to apply formatting
rules to Python code. Do NOT change any logic, variable names, or functionality.

FORMATTING RULES:
[Include full contents of docs/dev/shared/formatting-rules.md]

TARGET FILE: [path]
MODE: [check|fix]

INSTRUCTIONS:
1. Read the target file carefully
2. Compare against each formatting rule
3. If MODE is "check":
   - List each violation with line number and rule violated
   - Show the current code and what it should be
   - Do NOT modify the file
4. If MODE is "fix":
   - Apply all formatting fixes
   - Use the Edit tool to make changes
   - Report each change made

CRITICAL CONSTRAINTS:
- ONLY change formatting, NEVER change logic
- NEVER rename variables or functions
- NEVER remove or add functionality
- NEVER change string content (only quote style)
- Preserve all comments (only formatting, not removal)
- When uncertain, leave code unchanged

Output format for check mode:
  Line 45: Rule 1 (Paren Spacing)
    Current:  result = calculate(x, y)
    Should be: result = calculate( x, y )

Output format for fix mode:
  Fixed Line 45: Added paren spacing in calculate() call
  Fixed Line 67-72: Aligned method signature parameters
  ...
  Summary: Applied 8 formatting fixes
```

### Step 4: Verify (fix mode only)
After fixes are applied:
1. Run `python -m py_compile <file>` to verify syntax
2. Run `make lint` to check for issues
3. If either fails, report the problem

## Implementation

When this command is invoked:

1. **Parse arguments** to get target and mode (check vs fix)

2. **Find the file**:
   ```
   Use Glob to find: **/<target>.py or **/<target>
   If multiple matches, ask user to clarify
   ```

3. **Read the formatting rules**:
   ```
   Read: docs/dev/shared/formatting-rules.md
   ```

4. **Read the target file**:
   ```
   Read the full contents of the target file
   ```

5. **Launch the formatting agent**:
   ```
   Use Task tool with subagent_type="code-quality"
   Include the formatting rules and target file content in the prompt
   Specify check or fix mode
   ```

6. **Report results**:
   - Check mode: Display list of violations
   - Fix mode: Display changes made and verification results

## Example Output

### Check Mode
```
Checking formatting in src/tt/apps/journal/services.py...

Found 5 formatting violations:

  Line 65: Rule 1 (Paren Spacing)
    Current:  should_include = str(entry.uuid) in selected_entry_uuids
    Should be: should_include = str( entry.uuid ) in selected_entry_uuids

  Line 68: Rule 1 (Paren Spacing) + Rule 2 (Kwarg Spacing)
    Current:  entry.save(update_fields=['include_in_publish'])
    Should be: entry.save( update_fields = ['include_in_publish'] )

  Line 88: Rule 1 (Paren Spacing) - EXCEPTION APPLIES
    Note: Single string argument, no change needed

Summary: 5 violations found (1 has exception, 4 need fixing)
```

### Fix Mode
```
Applying formatting to src/tt/apps/journal/services.py...

  Fixed Line 65: Added paren spacing in str() call
  Fixed Line 68: Added paren spacing and kwarg spacing in save() call
  Skipped Line 88: Single string argument exception applies

Verification:
  ✓ Syntax check passed
  ✓ Lint check passed

Summary: Applied 2 formatting fixes
```

## Error Handling

- **File not found**: Report error and suggest using Glob to find
- **Syntax error in file**: Report error, do not attempt formatting
- **Multiple matches**: Ask user to specify full path
- **Verification fails**: Report what failed, suggest manual review

## Related Commands
- `/review` - Full code review (not just formatting)
- `/commit` - Commit after formatting changes
- `/fixtests` - Fix tests if formatting broke something

## Notes

- This command focuses ONLY on formatting
- It will not fix logical issues, remove comments, or refactor code
- The formatting rules are defined in `docs/dev/shared/formatting-rules.md`
- Update that file to change formatting conventions
