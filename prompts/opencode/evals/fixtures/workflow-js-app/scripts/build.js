const fs = require("node:fs")
const path = require("node:path")

const root = path.resolve(__dirname, "..")
const dist = path.join(root, "dist")

fs.rmSync(dist, { force: true, recursive: true })
fs.mkdirSync(dist, { recursive: true })

fs.copyFileSync(path.join(root, "src", "workflow.js"), path.join(dist, "workflow.js"))
fs.copyFileSync(path.join(root, "src", "index.js"), path.join(dist, "server.js"))
