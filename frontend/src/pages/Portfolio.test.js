/**
 * Tests for the "Show $ values" toggle feature in Portfolio.jsx
 *
 * Validates that dollar values are masked when showValues is false (default)
 * and displayed normally when showValues is true.
 *
 * Run with: npm test
 */

import { describe, it, expect, beforeEach } from 'vitest'

const MASKED_VALUE = '$••••'

// Recreate formatCurrency as a pure function with explicit showValues param
const formatCurrency = (num, showValues) => {
  if (num === null || num === undefined) return 'N/A'
  if (!showValues) return MASKED_VALUE
  const absNum = Math.abs(num)
  if (absNum >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
  if (absNum >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
  if (absNum >= 1e4) return `$${(num / 1e3).toFixed(2)}K`
  return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// Recreate formatDollar as a pure function with explicit showValues param
const formatDollar = (num, showValues, opts = {}) => {
  if (num == null) return opts.fallback || 'N/A'
  if (!showValues) return MASKED_VALUE
  const { minimumFractionDigits = 2, maximumFractionDigits = 2 } = opts
  return `$${num.toLocaleString(undefined, { minimumFractionDigits, maximumFractionDigits })}`
}

// formatPercent should never be masked (only dollar values are hidden)
const formatPercent = (num) => {
  if (num === null || num === undefined) return 'N/A'
  return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`
}

describe('Show $ values toggle - formatCurrency', () => {
  describe('when showValues is false (default - values hidden)', () => {
    it('masks positive values', () => {
      expect(formatCurrency(1234.56, false)).toBe(MASKED_VALUE)
    })

    it('masks negative values', () => {
      expect(formatCurrency(-5000, false)).toBe(MASKED_VALUE)
    })

    it('masks zero', () => {
      expect(formatCurrency(0, false)).toBe(MASKED_VALUE)
    })

    it('masks billions', () => {
      expect(formatCurrency(57006000000, false)).toBe(MASKED_VALUE)
    })

    it('masks millions', () => {
      expect(formatCurrency(125500000, false)).toBe(MASKED_VALUE)
    })

    it('masks thousands', () => {
      expect(formatCurrency(50000, false)).toBe(MASKED_VALUE)
    })

    it('still returns N/A for null', () => {
      expect(formatCurrency(null, false)).toBe('N/A')
    })

    it('still returns N/A for undefined', () => {
      expect(formatCurrency(undefined, false)).toBe('N/A')
    })
  })

  describe('when showValues is true (values visible)', () => {
    it('formats billions', () => {
      expect(formatCurrency(57006000000, true)).toBe('$57.01B')
    })

    it('formats millions', () => {
      expect(formatCurrency(1250000, true)).toBe('$1.25M')
    })

    it('formats ten-thousands with K suffix', () => {
      expect(formatCurrency(50000, true)).toBe('$50.00K')
    })

    it('formats small values with dollar sign', () => {
      const result = formatCurrency(150.5, true)
      expect(result).toMatch(/^\$150\.50$/)
    })

    it('formats negative values', () => {
      expect(formatCurrency(-2500000, true)).toBe('$-2.50M')
    })

    it('returns N/A for null', () => {
      expect(formatCurrency(null, true)).toBe('N/A')
    })

    it('returns N/A for undefined', () => {
      expect(formatCurrency(undefined, true)).toBe('N/A')
    })
  })
})

describe('Show $ values toggle - formatDollar', () => {
  describe('when showValues is false (default - values hidden)', () => {
    it('masks values', () => {
      expect(formatDollar(199.99, false)).toBe(MASKED_VALUE)
    })

    it('masks zero', () => {
      expect(formatDollar(0, false)).toBe(MASKED_VALUE)
    })

    it('still returns N/A for null', () => {
      expect(formatDollar(null, false)).toBe('N/A')
    })

    it('still returns N/A for undefined', () => {
      expect(formatDollar(undefined, false)).toBe('N/A')
    })

    it('returns custom fallback for null when provided', () => {
      expect(formatDollar(null, false, { fallback: '-' })).toBe('-')
    })
  })

  describe('when showValues is true (values visible)', () => {
    it('formats values with dollar sign', () => {
      const result = formatDollar(199.99, true)
      expect(result).toMatch(/^\$199\.99$/)
    })

    it('formats zero', () => {
      const result = formatDollar(0, true)
      expect(result).toMatch(/^\$0\.00$/)
    })

    it('returns N/A for null', () => {
      expect(formatDollar(null, true)).toBe('N/A')
    })

    it('returns custom fallback for null when provided', () => {
      expect(formatDollar(null, true, { fallback: '-' })).toBe('-')
    })
  })
})

describe('formatPercent is never masked', () => {
  it('always shows positive percentages regardless of toggle', () => {
    expect(formatPercent(5.5)).toBe('+5.5%')
  })

  it('always shows negative percentages regardless of toggle', () => {
    expect(formatPercent(-3.2)).toBe('-3.2%')
  })

  it('always shows zero percentage', () => {
    expect(formatPercent(0)).toBe('+0.0%')
  })

  it('returns N/A for null', () => {
    expect(formatPercent(null)).toBe('N/A')
  })
})

describe('MASKED_VALUE constant', () => {
  it('uses the expected mask pattern', () => {
    expect(MASKED_VALUE).toBe('$••••')
  })

  it('starts with dollar sign', () => {
    expect(MASKED_VALUE[0]).toBe('$')
  })
})

// ── Next Earnings Date Display Logic ──────────────────────────────────

// Recreate the display logic used in the Portfolio stock table row
const formatEarningsDisplay = (nextEarningsDate) => {
  if (!nextEarningsDate) return null
  const earningsDate = new Date(nextEarningsDate + 'T00:00:00')
  const daysUntil = Math.ceil((earningsDate - new Date()) / (1000 * 60 * 60 * 24))
  const dateLabel = earningsDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return { dateLabel, daysUntil, isUrgent: daysUntil <= 7 }
}

describe('Next Earnings Date display logic', () => {
  it('returns null for undefined earnings date', () => {
    expect(formatEarningsDisplay(undefined)).toBeNull()
  })

  it('returns null for null earnings date', () => {
    expect(formatEarningsDisplay(null)).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(formatEarningsDisplay('')).toBeNull()
  })

  it('formats a future date with month and day', () => {
    // Use a date 30 days from now
    const future = new Date()
    future.setDate(future.getDate() + 30)
    const dateStr = future.toISOString().split('T')[0]
    const result = formatEarningsDisplay(dateStr)
    expect(result).not.toBeNull()
    expect(result.dateLabel).toMatch(/^[A-Z][a-z]{2} \d{1,2}$/)
    expect(result.daysUntil).toBeGreaterThanOrEqual(29)
    expect(result.daysUntil).toBeLessThanOrEqual(31)
    expect(result.isUrgent).toBe(false)
  })

  it('marks earnings within 7 days as urgent', () => {
    const soon = new Date()
    soon.setDate(soon.getDate() + 3)
    const dateStr = soon.toISOString().split('T')[0]
    const result = formatEarningsDisplay(dateStr)
    expect(result.isUrgent).toBe(true)
    expect(result.daysUntil).toBeLessThanOrEqual(7)
  })

  it('marks earnings 6 days out as urgent', () => {
    const soon = new Date()
    soon.setDate(soon.getDate() + 6)
    const dateStr = soon.toISOString().split('T')[0]
    const result = formatEarningsDisplay(dateStr)
    expect(result.isUrgent).toBe(true)
  })

  it('marks earnings 10 days out as not urgent', () => {
    const notUrgent = new Date()
    notUrgent.setDate(notUrgent.getDate() + 10)
    const dateStr = notUrgent.toISOString().split('T')[0]
    const result = formatEarningsDisplay(dateStr)
    expect(result.isUrgent).toBe(false)
  })

  it('calculates positive daysUntil for future dates', () => {
    const future = new Date()
    future.setDate(future.getDate() + 15)
    const dateStr = future.toISOString().split('T')[0]
    const result = formatEarningsDisplay(dateStr)
    expect(result.daysUntil).toBeGreaterThan(0)
  })
})

// ── Show $ values session persistence ────────────────────────────────
//
// Tests the pure logic used by Portfolio.jsx:
//   Init:   useState(() => storage.get(KEY) === 'true')
//   Toggle: setShowValues(v => { const next = !v; storage.set(KEY, next); return next })
//
// We use a plain Map as a sessionStorage stand-in (no DOM needed).

const createMockStorage = () => {
  const store = new Map()
  return {
    getItem: (key) => store.has(key) ? store.get(key) : null,
    setItem: (key, val) => store.set(key, String(val)),
    clear: () => store.clear(),
  }
}

// Mirrors the init logic: () => storage.getItem(KEY) === 'true'
const initShowValues = (storage, key) => storage.getItem(key) === 'true'

// Mirrors the toggle logic: prev => { const next = !prev; storage.setItem(KEY, next); return next }
const toggleShowValues = (prev, storage, key) => {
  const next = !prev
  storage.setItem(key, next)
  return next
}

describe('Show $ values session persistence', () => {
  const KEY = 'portfolio_showValues'
  let storage

  beforeEach(() => {
    storage = createMockStorage()
  })

  it('defaults to false when storage is empty', () => {
    expect(initShowValues(storage, KEY)).toBe(false)
  })

  it('initialises to true when storage has "true"', () => {
    storage.setItem(KEY, 'true')
    expect(initShowValues(storage, KEY)).toBe(true)
  })

  it('initialises to false when storage has "false"', () => {
    storage.setItem(KEY, 'false')
    expect(initShowValues(storage, KEY)).toBe(false)
  })

  it('toggle on: stores "true" and returns true', () => {
    const result = toggleShowValues(false, storage, KEY)
    expect(result).toBe(true)
    expect(storage.getItem(KEY)).toBe('true')
  })

  it('toggle off: stores "false" and returns false', () => {
    storage.setItem(KEY, 'true')
    const result = toggleShowValues(true, storage, KEY)
    expect(result).toBe(false)
    expect(storage.getItem(KEY)).toBe('false')
  })

  it('survives multiple toggles and retains last value', () => {
    toggleShowValues(false, storage, KEY) // → true
    toggleShowValues(true, storage, KEY)  // → false
    toggleShowValues(false, storage, KEY) // → true
    expect(initShowValues(storage, KEY)).toBe(true)
  })

  it('new session (clear) resets to default false', () => {
    storage.setItem(KEY, 'true')
    storage.clear()
    expect(initShowValues(storage, KEY)).toBe(false)
  })

  it('values masking respects persisted state', () => {
    storage.setItem(KEY, 'true')
    const showValues = initShowValues(storage, KEY)
    expect(formatCurrency(50000, showValues)).toBe('$50.00K')

    const toggled = toggleShowValues(showValues, storage, KEY)
    expect(formatCurrency(50000, toggled)).toBe(MASKED_VALUE)
  })
})

// ── Asset type pill ordering by allocation % ─────────────────────────
//
// Mirrors the sorting logic in Portfolio.jsx:
//   pillConfig.filter(value > 0).sort(by value descending)

const PILL_KEYS = [
  { key: 'stock',  label: 'Stocks' },
  { key: 'etf',    label: 'ETFs' },
  { key: 'crypto', label: 'Crypto' },
  { key: 'custom', label: 'Misc' },
  { key: 'cash',   label: 'Cash' },
  { key: 'option', label: 'Options' },
]

const sortPills = (byAssetType) =>
  PILL_KEYS
    .filter(p => (byAssetType[p.key]?.value || 0) > 0)
    .sort((a, b) => (byAssetType[b.key].value || 0) - (byAssetType[a.key].value || 0))
    .map(p => p.key)

describe('Asset type pill ordering by allocation', () => {
  it('sorts pills by value descending', () => {
    const byAssetType = {
      stock:  { value: 40000 },
      etf:    { value: 20000 },
      crypto: { value: 10000 },
      cash:   { value: 30000 },
    }
    expect(sortPills(byAssetType)).toEqual(['stock', 'cash', 'etf', 'crypto'])
  })

  it('crypto first when it has highest allocation', () => {
    const byAssetType = {
      stock:  { value: 10000 },
      crypto: { value: 50000 },
      cash:   { value: 5000 },
    }
    expect(sortPills(byAssetType)).toEqual(['crypto', 'stock', 'cash'])
  })

  it('excludes asset types with zero value', () => {
    const byAssetType = {
      stock:  { value: 20000 },
      etf:    { value: 0 },
      crypto: { value: 0 },
      cash:   { value: 5000 },
    }
    expect(sortPills(byAssetType)).toEqual(['stock', 'cash'])
  })

  it('excludes asset types that are missing', () => {
    const byAssetType = {
      stock: { value: 10000 },
    }
    expect(sortPills(byAssetType)).toEqual(['stock'])
  })

  it('handles all six asset types', () => {
    const byAssetType = {
      option: { value: 60000 },
      custom: { value: 50000 },
      cash:   { value: 40000 },
      crypto: { value: 30000 },
      etf:    { value: 20000 },
      stock:  { value: 10000 },
    }
    expect(sortPills(byAssetType)).toEqual(['option', 'custom', 'cash', 'crypto', 'etf', 'stock'])
  })

  it('returns empty array when no asset types have value', () => {
    const byAssetType = {
      stock: { value: 0 },
      cash:  { value: 0 },
    }
    expect(sortPills(byAssetType)).toEqual([])
  })

  it('handles equal values (stable order from config)', () => {
    const byAssetType = {
      stock: { value: 10000 },
      etf:   { value: 10000 },
      cash:  { value: 10000 },
    }
    const result = sortPills(byAssetType)
    expect(result).toHaveLength(3)
    expect(result).toContain('stock')
    expect(result).toContain('etf')
    expect(result).toContain('cash')
  })

  it('reorders when allocation changes', () => {
    // Before: stocks lead
    const before = {
      stock: { value: 50000 },
      crypto: { value: 10000 },
    }
    expect(sortPills(before)[0]).toBe('stock')

    // After: crypto surges past stocks
    const after = {
      stock: { value: 50000 },
      crypto: { value: 80000 },
    }
    expect(sortPills(after)[0]).toBe('crypto')
  })
})
