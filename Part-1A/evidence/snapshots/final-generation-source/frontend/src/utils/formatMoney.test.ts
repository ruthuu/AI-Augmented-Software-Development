import { describe, expect, it } from 'vitest'
import { formatMoney } from './formatMoney'

describe('formatMoney', () => {
  it.each([
    ['10000.00', '₹10,000.00'],
    ['0.01', '₹0.01'],
    ['9999999.99', '₹9,999,999.99'],
    ['99999999.99', '₹99,999,999.99'],
    ['250.50', '₹250.50'],
    ['0.00', '₹0.00'],
    ['999.99', '₹999.99'],
    ['1000.00', '₹1,000.00'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatMoney(input)).toBe(expected)
  })

  it('works on the text only: a value a number cannot hold exactly stays exact', () => {
    expect(formatMoney('12345678901234567.89')).toBe('₹12,345,678,901,234,567.89')
  })

  it('returns an empty string for a missing value', () => {
    expect(formatMoney(null)).toBe('')
    expect(formatMoney(undefined)).toBe('')
  })
})
