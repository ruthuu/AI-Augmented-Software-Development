import { describe, expect, it } from 'vitest'
import { formatDate } from './formatDate'

describe('formatDate', () => {
  it.each([
    ['2026-11-10', '10 Nov 2026'],
    ['2026-01-05', '05 Jan 2026'],
    ['2000-01-01', '01 Jan 2000'],
    ['2025-12-31', '31 Dec 2025'],
    ['2024-02-29', '29 Feb 2024'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatDate(input)).toBe(expected)
  })

  it('returns the input unchanged when it is not an ISO date', () => {
    expect(formatDate('abc')).toBe('abc')
  })
})
