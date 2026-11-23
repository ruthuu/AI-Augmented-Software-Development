// Works on the decimal text only; a money string is never converted to a number.
export function formatMoney(amount: string | null | undefined): string {
  if (amount === null || amount === undefined) {
    return ''
  }
  const negative = amount.startsWith('-')
  const unsigned = negative ? amount.slice(1) : amount
  const [whole, fraction] = unsigned.split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const decimals = fraction === undefined ? '' : `.${fraction}`
  return `${negative ? '-' : ''}₹${grouped}${decimals}`
}
