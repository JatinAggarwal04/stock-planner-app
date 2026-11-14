import { describe, expect, it } from 'vitest'
import { formatters } from './formatters'

describe('formatters', () => {
  it('formats rupees', () => {
    expect(formatters.currency(1234567.891)).toBe('₹12,34,567.89')
    expect(formatters.currency(null)).toBe('₹0.00')
  })

  it('formats lakhs and crores', () => {
    expect(formatters.compactNumber(25000000)).toBe('2.50Cr')
    expect(formatters.compactNumber(250000)).toBe('2.50L')
    expect(formatters.compactNumber(2500)).toBe('2.50K')
    expect(formatters.compactNumber(25)).toBe('25.00')
  })

  it('formats signed percentages', () => {
    expect(formatters.percentage(1.234)).toBe('+1.23%')
    expect(formatters.percentage(-1.5, 1)).toBe('-1.5%')
    expect(formatters.percentage(undefined)).toBe('0.00%')
  })
})
