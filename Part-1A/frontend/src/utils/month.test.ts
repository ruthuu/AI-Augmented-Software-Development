import { describe, expect, it } from 'vitest'
import { formatMonth, isValidMonth, monthOf } from './month'

describe('month helpers', () => {
  it('takes the month of a date string', () => {
    expect(monthOf('2026-11-12')).toBe('2026-11')
  })

  it('formats a month for display', () => {
    expect(formatMonth('2026-11')).toBe('November 2026')
    expect(formatMonth('2026-01')).toBe('January 2026')
  })

  it.each(['2026-11', '1999-12', '0001-01', '9999-12'])('accepts %s', (value) => {
    expect(isValidMonth(value)).toBe(true)
  })

  it.each(['2026-13', '2026-00', '26-11', '2026-1', 'abc', ''])('rejects %s', (value) => {
    expect(isValidMonth(value)).toBe(false)
  })
})
