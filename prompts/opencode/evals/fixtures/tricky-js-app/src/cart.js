function totalCart(items) {
  return items.reduce((total, item) => total + item.price * item.quantity, 0)
}

function priceAfterDiscount(total, percent) {
  return total - percent
}

function formatCartSummary(items, discountPercent = 0) {
  const subtotal = totalCart(items)
  const total = priceAfterDiscount(subtotal, discountPercent)
  return {
    subtotal,
    total,
    itemCount: items.reduce((count, item) => count + item.quantity, 0),
  }
}

module.exports = {
  totalCart,
  priceAfterDiscount,
  formatCartSummary,
}
