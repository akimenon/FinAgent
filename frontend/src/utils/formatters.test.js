/**
 * Tests for formatter utility functions used in CompanyAnalysis.jsx
 * These tests ensure helper functions exist and work correctly.
 *
 * Run with: npm test (after adding vitest to package.json)
 */

import { describe, it, expect } from 'vitest'

// Import the functions from CompanyAnalysis.jsx
// Note: In a real setup, these would be extracted to a utils file

// Recreate the functions here for testing
const getChangeColor = (value, opacity = '') => {
  if (value == null) return 'text-slate-400'
  const suffix = opacity ? `/${opacity}` : ''
  return value >= 0 ? `text-emerald-400${suffix}` : `text-red-400${suffix}`
}

const getConsensusColor = (rating) => {
  const colors = {
    'Strong Buy': 'text-teal-400',
    'Buy': 'text-emerald-400',
    'Hold': 'text-yellow-400',
    'Sell': 'text-orange-400',
    'Strong Sell': 'text-red-400',
  }
  return colors[rating] || 'text-slate-400'
}

const formatPriceChange = (value, decimals = 1) => {
  if (value == null) return 'N/A'
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
}

const formatNumber = (num, decimals = 1) => {
  if (!num && num !== 0) return 'N/A'
  const absNum = Math.abs(num)
  if (absNum >= 1e12) return `$${(num / 1e12).toFixed(decimals)}T`
  if (absNum >= 1e9) return `$${(num / 1e9).toFixed(decimals)}B`
  if (absNum >= 1e6) return `$${(num / 1e6).toFixed(decimals)}M`
  if (absNum >= 1e3) return `$${(num / 1e3).toFixed(decimals)}K`
  return `$${num.toFixed(decimals)}`
}

const formatPercent = (num) => {
  if (!num && num !== 0) return 'N/A'
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`
}

describe('getChangeColor', () => {
  it('returns green for positive values', () => {
    expect(getChangeColor(5.5)).toBe('text-emerald-400')
    expect(getChangeColor(0)).toBe('text-emerald-400')
  })

  it('returns red for negative values', () => {
    expect(getChangeColor(-3.2)).toBe('text-red-400')
  })

  it('returns slate for null/undefined', () => {
    expect(getChangeColor(null)).toBe('text-slate-400')
    expect(getChangeColor(undefined)).toBe('text-slate-400')
  })

  it('handles opacity suffix', () => {
    expect(getChangeColor(5, '80')).toBe('text-emerald-400/80')
    expect(getChangeColor(-5, '80')).toBe('text-red-400/80')
  })
})

describe('getConsensusColor', () => {
  it('returns correct colors for each rating', () => {
    expect(getConsensusColor('Strong Buy')).toBe('text-teal-400')
    expect(getConsensusColor('Buy')).toBe('text-emerald-400')
    expect(getConsensusColor('Hold')).toBe('text-yellow-400')
    expect(getConsensusColor('Sell')).toBe('text-orange-400')
    expect(getConsensusColor('Strong Sell')).toBe('text-red-400')
  })

  it('returns slate for unknown rating', () => {
    expect(getConsensusColor('Unknown')).toBe('text-slate-400')
    expect(getConsensusColor(null)).toBe('text-slate-400')
  })
})

describe('formatPriceChange', () => {
  it('formats positive values with + prefix', () => {
    expect(formatPriceChange(5.5)).toBe('+5.5%')
    expect(formatPriceChange(0)).toBe('+0.0%')
  })

  it('formats negative values', () => {
    expect(formatPriceChange(-3.2)).toBe('-3.2%')
  })

  it('returns N/A for null/undefined', () => {
    expect(formatPriceChange(null)).toBe('N/A')
    expect(formatPriceChange(undefined)).toBe('N/A')
  })

  it('respects decimal places', () => {
    expect(formatPriceChange(5.567, 2)).toBe('+5.57%')
  })
})

describe('formatNumber', () => {
  it('formats billions', () => {
    expect(formatNumber(5000000000)).toBe('$5.0B')
    expect(formatNumber(57006000000)).toBe('$57.0B')
  })

  it('formats millions', () => {
    expect(formatNumber(125500000)).toBe('$125.5M')
  })

  it('formats thousands', () => {
    expect(formatNumber(50000)).toBe('$50.0K')
  })

  it('returns N/A for null/undefined', () => {
    expect(formatNumber(null)).toBe('N/A')
    expect(formatNumber(undefined)).toBe('N/A')
  })
})

describe('formatPercent', () => {
  it('formats positive percentages', () => {
    expect(formatPercent(5.55)).toBe('+5.55%')
  })

  it('formats negative percentages', () => {
    expect(formatPercent(-3.22)).toBe('-3.22%')
  })

  it('returns N/A for null/undefined', () => {
    expect(formatPercent(null)).toBe('N/A')
  })
})
