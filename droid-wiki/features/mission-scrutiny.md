# Mission scrutiny workflow

Front-load planning and milestone validation for long-running multi-step tasks.

## Purpose

The mission-scrutiny workflow adds structure to extended implementations:
1. Restates the actual goal and explicit exclusions
2. Breaks work into milestones with clear boundaries
3. Calls out dependencies, shared-risk areas, and re-plan points
4. Recommends validation cadence
5. Suggests the safest or highest-leverage first milestone

## When to use

Use mission-scrutiny when:
- Task spans multiple files or architectural layers
- Implementation requires validation checkpoints
- Risk of scope creep or unclear boundaries
- Cross-surface dependencies exist
- Multiple worker runs will be needed

## Output: Mission Scrutiny Report

The workflow produces a structured report:

### Goal Summary
- **Will Deliver**: Concise description of deliverables
- **Will Not Deliver**: Explicit exclusions to prevent scope creep

### Milestone Plan

| Milestone | Goal | Deliverables | Dependencies | Validation |
|-----------|------|--------------|--------------|------------|
| 1 | Foundation work | Core interfaces | None | Unit tests pass |
| 2 | Feature A | Implementation | Milestone 1 | Integration tests |
| 3 | Feature B | Implementation | Milestone 1 | E2E validation |

### Validation Cadence
- How often milestone validation runs
- What checks to perform at each checkpoint

### Major Risks

| Risk | Level | Why it matters | Mitigation |
|------|-------|----------------|------------|
| API breaking change | High | Impacts downstream consumers | Deprecation warnings first |
| External dependency | Medium | Could block work | Fallback implementation |

### Plan Review Trigger
Indicates whether a plan-review subagent should validate the plan before work begins:

- **REQUIRED**: When high risks exist or architectural uncertainty
- **OPTIONAL**: When the plan is straightforward and well-understood

### Recommended First Milestone
- Rationale for starting point selection

## Blocking conditions

The workflow may report BLOCKED when:
- Task is too underspecified to plan responsibly
- Milestone ordering depends on missing architectural decisions
- Requested scope is internally contradictory

## Usage

### OpenCode
```
/mission-scrutiny
```

## Available in

All 14 agent targets. See [Agent targets](../agent-targets/index.md).

## Related workflows

- [Milestone validator](milestone-validator.md) — Validate each milestone before proceeding
- [Spec compiler](spec-compiler.md) — Create execution contracts
- [Plan review](plan-review.md) — Binary validation of execution contracts
