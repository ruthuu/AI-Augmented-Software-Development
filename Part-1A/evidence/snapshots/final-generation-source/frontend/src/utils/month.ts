const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

export function isValidMonth(value: string): boolean {
  const match = /^(\d{4})-(\d{2})$/.exec(value)
  if (!match) {
    return false
  }
  const year = Number(match[1])
  const month = Number(match[2])
  return year >= 1 && month >= 1 && month <= 12
}

export function monthOf(isoDate: string): string {
  return isoDate.slice(0, 7)
}

export function formatMonth(month: string): string {
  if (!isValidMonth(month)) {
    return month
  }
  return `${MONTH_NAMES[Number(month.slice(5)) - 1]} ${month.slice(0, 4)}`
}
