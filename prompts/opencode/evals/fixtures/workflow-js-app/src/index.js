const { createWorkflowEngine } = require("./workflow")

const engine = createWorkflowEngine()
engine.createRun({ id: "demo", queue: "default" })

console.log(`workflow engine ready: ${engine.getRun("demo").status}`)
