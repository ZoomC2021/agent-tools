# Handoff Command

Generate a structured handoff context for continuing work in a new session.

## When to Use /handoff

Use the handoff command when:
- Context is getting too long and you want a fresh start
- Approaching the context window limit
- Switching to a different session or agent
- Need to pass work to another team member
- Want to checkpoint complex multi-step work

## Phased Workflow

### Phase 0: Validate Request

Check that meaningful context exists to handoff:
- Verify there is session history, file changes, or active work
- Confirm the workspace has been modified or tasks are in progress
- If no meaningful context exists, report: "No active work context to handoff"

### Phase 1: Gather Context

Collect all relevant information from the current session:

1. **Review session history** - understand the conversation flow and decisions made
2. **Check todos** - identify active, pending, and completed tasks
3. **Git status** - get current branch and uncommitted changes overview
4. **Git diff** - capture specific code changes made
5. **File exploration** - identify key files modified or created

Use tools to gather:
- `git status --short` for file change overview
- `git diff HEAD` for unstaged changes
- `git diff --cached` for staged changes
- File read for todo files or key documents

### Phase 2: Extract Context

Transform gathered information into first-person continuation context:

1. **What we were doing**: Summarize the original goal in 1-2 sentences
2. **What got done**: List completed work with file references
3. **Current state**: Describe exactly where we left off
4. **What's next**: Identify the immediate next step
5. **Blockers**: Note any issues that need resolution
6. **Decisions**: Capture key decisions made and their rationale

Write as if YOU were continuing the work - use first person perspective.

### Phase 3: Format Output

Structure the extracted context into the HANDOFF CONTEXT format:

```
HANDOFF CONTEXT
===============

USER REQUESTS (AS-IS)
---------------------
[Paste the original user request verbatim]

GOAL
----
[One-line summary of the task goal]

WORK COMPLETED
--------------
- [Item 1: description with file path]
- [Item 2: description with file path]
- [...]

CURRENT STATE
-------------
[Detailed description of where we left off, including file contents, test results, or pending operations]

PENDING TASKS
-------------
1. [Next immediate step]
2. [Subsequent step]
3. [...]

KEY FILES (max 10)
------------------
1. `path/to/file1` - [purpose in the current task]
2. `path/to/file2` - [purpose in the current task]
3. [...]

IMPORTANT DECISIONS
-------------------
- [Decision 1]: [rationale]
- [Decision 2]: [rationale]
- [...]

EXPLICIT CONSTRAINTS
--------------------
- [Constraint 1]
- [Constraint 2]
- [...]

CONTEXT FOR CONTINUATION
------------------------
[1-2 paragraph narrative explaining what needs to happen next, written as first-person continuation instructions]
```

### Phase 4: Provide Instructions

After generating the HANDOFF CONTEXT, provide clear continuation instructions:

1. Tell the user to copy the handoff context
2. Instruct them to start a new session
3. Explain how to use the handoff context (paste at start of new session)
4. Remind them to verify workspace state matches the handoff description

## Constraints

- Do NOT create new sessions programmatically
- Handoff is READ-ONLY analysis - do not modify files
- All file paths must be workspace-relative (no absolute paths)
- Never include secrets, API keys, or credentials
- Maximum 10 key files listed
- Keep handoff self-contained and continuation-ready
- Summarize code changes rather than pasting full diffs

## Output Example

```
HANDOFF CONTEXT
===============

USER REQUESTS (AS-IS)
---------------------
Add OAuth2 authentication to the API using JWT tokens

GOAL
----
Implement secure authentication flow for API endpoints

WORK COMPLETED
--------------
- Created auth middleware in `src/middleware/auth.js`
- Added JWT token generation in `src/utils/jwt.js`
- Implemented login endpoint in `src/routes/auth.js`

CURRENT STATE
-------------
Login endpoint is functional and returns valid JWT tokens. Token verification middleware is implemented but not yet integrated with protected routes. Tests pass for login but are pending for protected endpoint access.

PENDING TASKS
-------------
1. Integrate auth middleware with existing API routes
2. Add token refresh endpoint
3. Write tests for protected routes
4. Update API documentation

KEY FILES (max 10)
------------------
1. `src/middleware/auth.js` - JWT verification middleware
2. `src/utils/jwt.js` - Token generation utilities
3. `src/routes/auth.js` - Login/logout endpoints
4. `tests/auth.test.js` - Authentication tests

IMPORTANT DECISIONS
-------------------
- Using RS256 signing algorithm for production security
- Tokens expire after 1 hour with refresh token support
- Auth middleware will be opt-in per route (not global)

EXPLICIT CONSTRAINTS
--------------------
- Keep existing public endpoints accessible
- Don't break existing API contracts
- Follow existing error handling patterns

CONTEXT FOR CONTINUATION
------------------------
I need to integrate the auth middleware with the existing API routes. Start by identifying which routes need protection, then apply the middleware selectively. The auth middleware is ready to use - import it and apply to route definitions. After integration, implement the refresh token endpoint following the pattern established in the login endpoint. Finally, write comprehensive tests for the protected routes.
```
