const test = require("node:test")
const assert = require("node:assert/strict")

const { totalCart, priceAfterDiscount, formatCartSummary } = require("../src/cart")

test("totalCart multiplies price by quantity", () => {
  assert.equal(
    totalCart([
      { price: 10, quantity: 2 },
      { price: 5, quantity: 3 },
    ]),
    35,
  )
})

test("priceAfterDiscount applies the percent discount", () => {
  assert.equal(priceAfterDiscount(100, 20), 80)
  assert.equal(priceAfterDiscount(250, 10), 225)
})

test("formatCartSummary returns subtotal, discounted total, and item count", () => {
  assert.deepEqual(
    formatCartSummary(
      [
        { price: 20, quantity: 2 },
        { price: 10, quantity: 1 },
      ],
      20,
    ),
    {
      subtotal: 50,
      total: 40,
      itemCount: 3,
    },
  )
})
