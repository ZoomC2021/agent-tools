const test = require("node:test")
const assert = require("node:assert/strict")

const { sum } = require("../src/math")

test("sum adds two numbers", () => {
  assert.equal(sum(2, 3), 5)
})
