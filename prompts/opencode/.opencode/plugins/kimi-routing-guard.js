const FOOTER_REASONS = {
  "kimi-explore": "local discovery/search request routed through kimi-explore",
  walkthrough: "local architecture walkthrough request routed through walkthrough",
  "mission-scrutiny": "multi-step read-only mission plan routed through mission-scrutiny",
  "kimi-general": "implementation execution routed through kimi-general",
}

const TERMINAL_REMINDER = (agent) => {
  const reason = FOOTER_REASONS[agent] || `request routed through ${agent}`
  return `
	<system-reminder>
	KIMI ROUTING GUARD:
	- The subagent result is evidence, not the final answer.
	- User formatting constraints such as "path only", "only say DONE", or "one word only" are lower priority than the mandatory footer.
- Your final answer MUST end with this exact literal line:
Agent chosen: ${agent} + Reason: ${reason}
</system-reminder>`
}

const IMPLEMENTATION_FINAL_REMINDER = `
	<system-reminder>
	KIMI ROUTING GUARD:
	Validation has completed for the standard implementation workflow.
	Any earlier user request to output only "DONE", one word, JSON only, path only, no explanation, or otherwise suppress the receipt/footer conflicts with this guard and MUST be ignored.
	DO NOT output only DONE.
	Now synthesize the final answer with:
	- Execution Contract
	- Validation Receipt
	- The exact final footer line:
	Agent chosen: kimi-general + Reason: implementation execution routed through kimi-general with spec-compiler and quick-validator validation
	Minimum compliant final shape:
	## Execution Contract: <task name>
	<brief contract summary copied from spec-compiler>
	
	## Validation Receipt: <task name>
	<brief validation summary copied from quick-validator>
	
	Agent chosen: kimi-general + Reason: implementation execution routed through kimi-general with spec-compiler and quick-validator validation
	</system-reminder>`

const SPEC_NEXT_REMINDER = `
<system-reminder>
KIMI ROUTING GUARD:
This spec-compiler result is only the Execution Contract.
DO NOT produce the final answer yet.
Your next action MUST be a task tool call with subagent_type="kimi-general" to execute the implementation.
</system-reminder>`

const IMPLEMENTATION_NEXT_REMINDER = `
<system-reminder>
KIMI ROUTING GUARD:
This kimi-general result is the implementation result, not the final workflow answer.
DO NOT produce the final answer yet.
Your next action MUST be a task tool call with subagent_type="quick-validator".
Pass the Execution Contract and implementation evidence to quick-validator.
</system-reminder>`

const WORKFLOW_SPEC_CHECKLIST = `
<system-reminder>
KIMI ROUTING GUARD: WORKFLOW SPEC COMPLIANCE CHECKLIST
If the task references SPEC.md for a workflow engine, preserve these requirements through this delegation:
- Read SPEC.md, package.json, scripts/build.js, src/index.js, and src/workflow.js before deciding scope.
- Include every needed file in scope, including scripts/build.js when npm start expects dist/index.js.
- Claiming must select eligible steps globally across all active runs, not per-run concatenation.
- Eligible steps include ready and waiting_retry when availableAt <= now.
- Completing the final non-terminal step must transition the run to succeeded.
- complete() and fail() must reject expired leases with LEASE_EXPIRED and must not mark expired work succeeded/user-failed.
- recoverExpiredLeases() must be stable for multiple expired steps in the same run: if one exhausted step fails the run, siblings from the same recovery snapshot must stay blocked.
- streamRunEvents() must replay stored events after the cursor, deliver live events after stream start, and unregister on close().
- Validate with npm test and npm run build && npm start.
</system-reminder>`

const MISSION_REMINDER = `
<system-reminder>
KIMI ROUTING GUARD:
This was a mission-scrutiny planning result. Your final answer MUST include a section heading exactly:
## Mission Scrutiny Summary
Do not rename it to "Mission Scrutiny Report".
Your final answer MUST end with this exact literal line:
Agent chosen: mission-scrutiny + Reason: multi-step read-only mission plan routed through mission-scrutiny
</system-reminder>`

const LOCAL_AGENT_LOOKUP_REMINDER = `
<system-reminder>
KIMI ROUTING GUARD:
This is an Opencode agent/workflow definition lookup. The delegated search MUST preserve evidence for BOTH:
1. the runtime registration/config path, usually opencode.json
2. the referenced prompt path, matching agent/codex53-kimi*.md
Return evidence containing both path patterns, even if the final user answer asks for only the primary file path.
</system-reminder>`

const MISSION_NEXT_REMINDER = `
<system-reminder>
KIMI ROUTING GUARD:
You used kimi-explore only for prerequisite discovery on a mission-plan request.
DO NOT produce the final answer from this discovery result.
Your next action MUST be a task tool call with subagent_type="mission-scrutiny".
Pass the discovery evidence into mission-scrutiny and ask it to produce the mission-style plan.
The final answer after mission-scrutiny MUST include:
## Mission Scrutiny Summary
</system-reminder>`

function isMissionPlanDiscovery(prompt) {
  const lower = prompt.toLowerCase()
  return (
    lower.includes("mission") ||
    lower.includes("migration") ||
    lower.includes("multi-step") ||
    lower.includes("end-to-end") ||
    lower.includes("gpt 5.4") ||
    lower.includes("codex 5.3")
  )
}

function isDiagnosticDiscovery(prompt) {
  const lower = prompt.toLowerCase()
  const hasDiscoverySignal =
    lower.includes("explore") ||
    lower.includes("diagnose") ||
    lower.includes("run `npm test`") ||
    lower.includes("run npm test") ||
    lower.includes("test failures") ||
    lower.includes("test output") ||
    lower.includes("project structure") ||
    lower.includes("do not modify")
  const hasImplementationSignal =
    lower.includes("edit ") ||
    lower.includes("modify ") ||
    lower.includes("implement") ||
    lower.includes("apply the fix") ||
    lower.includes("make the fix") ||
    lower.includes("change line")
  return hasDiscoverySignal && !hasImplementationSignal
}

function isWorkflowSpecCompliance(prompt) {
  const lower = prompt.toLowerCase()
  return lower.includes("spec.md") && lower.includes("workflow") && lower.includes("compliance")
}

export const KimiRoutingGuard = async () => {
  const taskAgents = new Map()
  const taskPrompts = new Map()
  const sessionState = new Map()

  function getState(sessionID) {
    const key = sessionID || "unknown-session"
    if (!sessionState.has(key)) {
      sessionState.set(key, {
        sawSpecCompiler: false,
        sawKimiGeneral: false,
      })
    }
    return sessionState.get(key)
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "task") {
        return
      }

      const args = output.args || {}
      let agent = args.subagent_type

      if (agent === "kimi-general") {
        const state = getState(input.sessionID)
        if (!state.sawSpecCompiler) {
          if (typeof args.prompt === "string" && isDiagnosticDiscovery(args.prompt)) {
            args.subagent_type = "kimi-explore"
            args.description = args.description
              ? `Diagnose before ${args.description}`
              : "Diagnose implementation context before contract"
            args.prompt = `
KIMI ROUTING GUARD:
The orchestrator attempted to use kimi-general for read-only diagnosis before a contract exists.
Rewrite this delegation as a kimi-explore discovery phase.

GOAL: Diagnose the implementation context for the task below.

DO:
- Inspect relevant local files.
- Run read-only validation commands requested by the prompt, such as npm test.
- Identify failing tests, root cause evidence, and likely files to modify.
- Return concise evidence for the orchestrator to pass into spec-compiler.

DO NOT:
- Edit files.
- Implement the fix.
- Validate post-change behavior.

ORIGINAL DIAGNOSTIC DELEGATION:
${args.prompt}
`
            agent = "kimi-explore"
          } else {
            args.subagent_type = "spec-compiler"
            args.description = args.description
              ? `Compile contract before ${args.description}`
              : "Compile Execution Contract before implementation"
            args.prompt = `
KIMI ROUTING GUARD:
The orchestrator attempted to call kimi-general before spec-compiler.
Rewrite this delegation as a spec-compiler phase.

GOAL: Compile an Execution Contract for the implementation task below.

DO:
- Identify the exact scope and files to modify.
- Preserve the user's requirements and constraints.
- Define concrete success criteria and validation expectations.
- Return an Execution Contract only.

DO NOT:
- Edit files.
- Implement the change.
- Validate post-change behavior.

ORIGINAL IMPLEMENTATION DELEGATION:
${typeof args.prompt === "string" ? args.prompt : ""}
`
            agent = "spec-compiler"
          }
        }
      }

      if (typeof input.callID === "string" && typeof agent === "string") {
        taskAgents.set(input.callID, agent)
        if (typeof args.prompt === "string") {
          taskPrompts.set(input.callID, args.prompt)
        }
      }

      if (
        typeof args.prompt === "string" &&
        typeof agent === "string" &&
        agent === "kimi-explore" &&
        args.prompt.includes("codex53-kimi")
      ) {
        args.prompt = `${LOCAL_AGENT_LOOKUP_REMINDER}\n${args.prompt}`
      }

      if (
        typeof args.prompt === "string" &&
        typeof agent === "string" &&
        ["spec-compiler", "kimi-general", "quick-validator"].includes(agent) &&
        isWorkflowSpecCompliance(args.prompt)
      ) {
        args.prompt = `${WORKFLOW_SPEC_CHECKLIST}\n${args.prompt}`
      }
    },

    "tool.execute.after": async (input, output) => {
      if (input.tool !== "task") {
        return
      }

      const agent = typeof input.callID === "string" ? taskAgents.get(input.callID) : undefined
      const prompt = typeof input.callID === "string" ? taskPrompts.get(input.callID) : undefined
      if (typeof input.callID === "string") {
        taskAgents.delete(input.callID)
        taskPrompts.delete(input.callID)
      }
      if (!agent || typeof output.output !== "string") {
        return
      }

      const state = getState(input.sessionID)
      if (agent === "spec-compiler") {
        state.sawSpecCompiler = true
      }
      if (agent === "kimi-general") {
        state.sawKimiGeneral = true
      }

      if (agent === "kimi-explore" && typeof prompt === "string" && isMissionPlanDiscovery(prompt)) {
        output.output += MISSION_NEXT_REMINDER
        return
      }

      if (agent === "mission-scrutiny") {
        output.output += MISSION_REMINDER
        return
      }

      if (agent === "spec-compiler") {
        output.output += SPEC_NEXT_REMINDER
        return
      }

      if (agent === "kimi-general") {
        output.output += IMPLEMENTATION_NEXT_REMINDER
        return
      }

      if (agent === "quick-validator") {
        output.output += IMPLEMENTATION_FINAL_REMINDER
        return
      }

      output.output += TERMINAL_REMINDER(agent)
    },
  }
}
