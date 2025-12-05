---
allowed-tools: Bash, Read, Write, TodoWrite, Grep, Glob, AskUserQuestion
description: Design planning and HTML mockup creation for GitHub issues
model: claude-sonnet-4-20250514
argument-hint: [issue-number]
---

Design planning and HTML mockup creation for GitHub issue #$1:

## Design Phase Process

This command creates an HTML mockup and STOPS for review. Documentation is created only after explicit mockup approval.

### Phase 1: Research and Mockup (this session)

1. **Use TodoWrite to plan design phases** - Track design workflow steps
   - Read `docs/CLAUDE.md` for AI-specific guidance and development philosophy
   - Follow design workflow in `docs/dev/workflow/design-workflow.md`
   - Focus on well-factored design solutions

2. **Read GitHub issue completely** - Understand design requirements:
   - Use `gh issue view $1` to read issue description and all comments
   - Identify visual and UX requirements
   - Understand user needs and interaction goals
   - Note any existing design discussion or wireframes

3. **Orient to design task context** - Review relevant codebase:
   - Search for existing similar UI components or patterns
   - Review current styling and design patterns
   - Understand technical constraints and framework capabilities
   - Identify reusable components or templates

4. **Create design decision questions** - Before starting mockups:
   - What are the key layout and visual hierarchy decisions?
   - What interaction patterns should be used?
   - How should this integrate with existing UI patterns?
   - What are the responsive design requirements?
   - What accessibility considerations need addressing?
   - Are there specific branding or style guidelines to follow?
   - What are the performance constraints for the design?

5. **Ask clarifying questions** - Get design direction before mockup creation:
   - Present the design decision questions for clarification
   - Understand priorities and constraints
   - Clarify any ambiguous UX requirements
   - Confirm target user experience goals

6. **Create HTML mockup** - After design decisions are clarified:
   - Build interactive HTML mockup in `data/design/issue-$1/mockup.html`
   - Use existing CSS patterns and component styles where possible
   - Focus on layout, interaction patterns, and visual hierarchy
   - Make mockup interactive to demonstrate user flows
   - Ensure mockup works across different screen sizes

7. **STOP AND PRESENT MOCKUP FOR REVIEW**:
   - Tell the user: "HTML mockup created at `data/design/issue-$1/mockup.html`"
   - Summarize key design choices made in the mockup
   - Ask user to review the mockup in their browser
   - **DO NOT proceed to documentation until user explicitly approves**
   - Wait for user feedback - they may request changes or approve

### Phase 2: Documentation (only after mockup approval)

Only proceed with these steps when user explicitly confirms mockup is finalized:

8. **Create interaction documentation** - After mockup approval:
   - Document in `data/design/issue-$1/interaction-patterns.md`
   - Specify user interaction flows and behaviors
   - Define component states and transitions
   - Document accessibility patterns and requirements
   - Specify responsive behavior across breakpoints

9. **Create design summary** - Comprehensive deliverable:
   - Document in `data/design/issue-$1/design-summary.md`
   - Summarize key design decisions and rationale
   - Document component specifications
   - Include implementation guidance for developers
   - Note any dependencies or technical requirements

10. **Post design deliverables to GitHub issue** - Share for review:
    - **NEVER** Use references to locally stored files in GitHub comments: this does not scale.
    - **ALWAYS** post full content to GitHub as comments and attachements.
    - Attach HTML mockup file to GitHub issue
    - Post interaction patterns as issue comment
    - Post design summary as issue comment
    - Mark as ready for stakeholder review and approval

**Design Workflow Integration:**
- Creates deliverables in `data/design/issue-{number}/` (git ignored)
- Separates design phase from implementation phase
- Provides comprehensive design specifications for implementation
- Follows design patterns established in project

**Design Phase Goals:**
- Create visual and interactive specifications
- Resolve UX and design decisions before implementation
- Provide clear guidance for implementation phase
- Enable design review and approval process

**Key Design Principles:**
- Iterate and finalize HTML mock before interaction docs
- Make design decisions explicit and documented
- Focus on user experience and interaction patterns
- Ensure consistency with existing design system

**Design Target:** GitHub issue #$1
**Output:** HTML mockup (Phase 1) → interaction documentation + design summary (Phase 2)

**IMPORTANT:** This command stops after creating the mockup. Documentation is only created after explicit user approval of the mockup design.

Begin Phase 1: Research and mockup creation now.
