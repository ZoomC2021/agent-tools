# PR Reviewer

Fetch all comments from a GitHub PR, summarize issues, address them, and update the PR.

## Workflow

1. **Get repository info**
   ```bash
   gh repo view --json owner,name
   ```

2. **Fetch PR comments**
   Ask for the PR number, then fetch all comments using `gh api graphql`.

3. **Identify reviewer types**
   Known bots:
   - `qodo-merge-pro[bot]` - Structured suggestions
   - `coderabbitai[bot]` - Detailed analysis
   - `gemini-code-assist[bot]` - Suggestions
   - `copilot[bot]` - Code suggestions
   - `sonarcloud[bot]` - Security/bugs

   Tag each comment as 🤖 Bot or 👤 Human.

4. **Summarize issues**
   Present a table:
   | # | File:Line | Reviewer | Type | Issue | Status |

   Group by:
   - 🔴 Blocking (changes requested, security)
   - 🟠 Suggestions (improvements)
   - 🟡 Nitpicks (style, minor)
   - 💬 Questions/Discussion

5. **Checkout PR branch**
   ```bash
   gh pr checkout {PR_NUMBER}
   ```

6. **Address each issue**
   - Read referenced files for full context
   - Make necessary code changes
   - For questions: prepare response comments
   - Skip resolved threads

   **Bot handling:**
   - Evaluate, don't blindly apply
   - Security issues: always investigate
   - Human feedback takes priority over bot suggestions

7. **Verify changes**
   Run type checking and build commands.

8. **Commit and push**
   ```bash
   git add -A
   git commit -m "Address PR review feedback"
   git push
   ```

9. **Report summary**
   ```
   ✅ Addressed: X issues (Y from bots, Z from humans)
   💬 Responded: N comments  
   ⏭️ Skipped: M (resolved/false positives)
   ```

## Notes

- Always preserve the original PR author's intent
- If an issue is unclear, ask for clarification instead of guessing
- Human feedback takes priority over bot suggestions when they conflict
- Security issues from any source should always be addressed
