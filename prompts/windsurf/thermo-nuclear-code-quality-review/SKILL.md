---
name: thermo-nuclear-code-quality-review
description: Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth
---

## /thermo-nuclear-code-quality-review - Deep Code Quality Audit

When asked for a thermo-nuclear code quality review, thermonuclear review, deep code quality audit, or especially harsh maintainability review:

1. Perform a deep code quality audit of the current branch's changes
2. Rethink how to structure / implement the changes to meaningfully improve code quality without impacting behavior
3. Be ambitious about structural simplification - search for "code judo" moves that delete complexity
4. Do not let a PR push a file from under 1k lines to over 1k lines without strong justification
5. Do not allow random spaghetti growth - flag new ad-hoc conditionals in unrelated flows
6. Bias toward cleaning the design, not just accepting working code
7. Prefer direct, boring, maintainable code over hacky or magical code
8. Push hard on type and boundary cleanliness
9. Keep logic in the canonical layer and reuse existing helpers
10. Treat unnecessary sequential orchestration and non-atomic updates as design smells

Key questions:
- Is there a "code judo" move that would make this dramatically simpler?
- Can this be reframed so fewer concepts, branches, or helper layers are needed?
- Did the diff add branching complexity where a better abstraction should exist?
- Did a previously cohesive module become more coupled or harder to scan?
- Did this change enlarge a file past a healthy size boundary?
- Is this abstraction actually earning its keep, or is it just a wrapper?

Flag aggressively:
- Files crossing 1000 lines due to the PR
- New conditionals bolted onto unrelated code paths
- Feature-specific logic leaking into general-purpose modules
- Generic "magic" handling that hides simple structure
- Thin wrappers or identity abstractions without simplifying anything
- Unnecessary casts, any, unknown, or optional params
- Copy-pasted logic instead of extracted helpers
- Bespoke helpers where the codebase already has a canonical utility
- Logic added in the wrong layer/package
- Sequential async flow where independent work could run in parallel

Output priorities:
1. Structural code-quality regressions
2. Missed opportunities for dramatic simplification / code-judo
3. Spaghetti / branching complexity increases
4. Boundary / abstraction / type-contract problems
5. File-size and decomposition concerns
6. Modularity and abstraction issues
7. Legibility and maintainability concerns

Approval bar: no structural regression, no missed simplification opportunity, no unjustified file-size explosion, no spaghetti-growth, no hacky abstractions, no boundary leaks, no canonical-helper duplication.

Be direct, serious, and demanding about quality.
