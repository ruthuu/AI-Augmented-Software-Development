const MONTH_ABBREVIATIONS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
]

// "2026-11-10" -> "10 Nov 2026" using a fixed month list, so the result never depends on locale.
export function formatDate(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate)
  if (!match) {
    return isoDate
  }
  const month = Number(match[2])
  if (month < 1 || month > 12) {
    return isoDate
  }
  return `${match[3]} ${MONTH_ABBREVIATIONS[month - 1]} ${match[1]}`
}
