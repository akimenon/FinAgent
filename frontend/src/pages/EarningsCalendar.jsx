import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, Loader2, Filter, Sparkles, Cpu, Car, Microscope, Building2 } from 'lucide-react'
import { financialsApi } from '../services/api'

// Stock category mappings
const CATEGORIES = {
  all: {
    label: 'All',
    icon: Calendar,
    color: 'slate',
    symbols: null, // null means show all
  },
  mag7: {
    label: 'MAG7',
    icon: Sparkles,
    color: 'blue',
    symbols: ['AAPL', 'AMZN', 'META', 'GOOGL', 'GOOG', 'MSFT', 'NVDA', 'TSLA'],
  },
  semiconductors: {
    label: 'Semiconductors',
    icon: Cpu,
    color: 'purple',
    symbols: ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ON', 'NXPI', 'ADI', 'MCHP', 'SWKS', 'QRVO', 'MPWR', 'SLAB', 'TSM', 'ASML'],
  },
  ev: {
    label: 'EV & Auto',
    icon: Car,
    color: 'green',
    symbols: ['TSLA', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'F', 'GM', 'TM', 'HMC', 'STLA', 'RACE', 'APTV', 'BWA', 'ALV', 'LEA', 'PLUG', 'CHPT', 'BLNK'],
  },
  biomedical: {
    label: 'Biomedical',
    icon: Microscope,
    color: 'pink',
    symbols: ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN', 'MRNA', 'BIIB', 'ILMN', 'ISRG', 'DXCM', 'ZBH', 'SYK', 'MDT', 'BSX', 'EW'],
  },
  finance: {
    label: 'Finance',
    icon: Building2,
    color: 'amber',
    symbols: ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'TFC', 'SCHW', 'BLK', 'SPGI', 'MCO', 'ICE', 'CME', 'V', 'MA', 'AXP', 'COF', 'DFS'],
  },
}

/**
 * Format large numbers in abbreviated format per CLAUDE.md
 */
function formatRevenue(value) {
  if (value == null) return '-'
  const num = Number(value)
  if (isNaN(num)) return '-'

  if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`
  if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
  if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`
  if (num >= 1e4) return `$${(num / 1e3).toFixed(0)}K`
  return `$${num.toLocaleString()}`
}

/**
 * Format date as "Mon, Jan 25"
 */
function formatDateHeader(dateStr) {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })
}

/**
 * Group earnings by date
 */
function groupByDate(earnings) {
  const groups = {}
  for (const earning of earnings) {
    const date = earning.date
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(earning)
  }
  return groups
}

/**
 * Get color classes for a category
 */
function getCategoryColors(colorName, isActive) {
  const colors = {
    slate: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/50' },
    blue: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/50' },
    purple: { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/50' },
    green: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/50' },
    pink: { bg: 'bg-pink-500/20', text: 'text-pink-400', border: 'border-pink-500/50' },
    amber: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/50' },
  }
  return colors[colorName] || colors.slate
}

export default function EarningsCalendar() {
  const navigate = useNavigate()
  const [earnings, setEarnings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeCategory, setActiveCategory] = useState('all')
  const [showOnlyWithEstimates, setShowOnlyWithEstimates] = useState(true)
  const [days, setDays] = useState(7)

  useEffect(() => {
    const fetchEarnings = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await financialsApi.getEarningsCalendar(days)
        setEarnings(response.data.earnings || [])
      } catch (err) {
        console.error('Failed to fetch earnings calendar:', err)
        setError('Failed to load earnings calendar')
      } finally {
        setLoading(false)
      }
    }

    fetchEarnings()
  }, [days])

  // Filter earnings based on category and estimate toggle
  const filteredEarnings = useMemo(() => {
    let result = earnings

    // Filter by estimates
    if (showOnlyWithEstimates) {
      result = result.filter(e => e.epsEstimate != null)
    }

    // Filter by category
    const category = CATEGORIES[activeCategory]
    if (category && category.symbols) {
      const symbolSet = new Set(category.symbols)
      result = result.filter(e => symbolSet.has(e.symbol))
    }

    return result
  }, [earnings, activeCategory, showOnlyWithEstimates])

  const groupedEarnings = useMemo(() => groupByDate(filteredEarnings), [filteredEarnings])
  const sortedDates = Object.keys(groupedEarnings).sort()

  const handleTickerClick = (symbol) => {
    navigate(`/analysis/${symbol}`)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-500/20 rounded-xl">
            <Calendar className="h-8 w-8 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Earnings Calendar</h1>
            <p className="text-slate-400">Upcoming earnings announcements</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Days selector */}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Next 7 days</option>
            <option value={14}>Next 14 days</option>
            <option value={30}>Next 30 days</option>
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-400">Filters</span>
        </div>

        {/* Category pills */}
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(CATEGORIES).map(([key, cat]) => {
            const Icon = cat.icon
            const isActive = activeCategory === key
            const colors = getCategoryColors(cat.color, isActive)

            return (
              <button
                key={key}
                onClick={() => setActiveCategory(key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all border ${
                  isActive
                    ? `${colors.bg} ${colors.text} ${colors.border}`
                    : 'bg-slate-700 hover:bg-slate-600 text-slate-300 border-transparent'
                }`}
              >
                <Icon className="w-4 h-4" />
                {cat.label}
              </button>
            )
          })}
        </div>

        {/* Toggle for estimates */}
        <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showOnlyWithEstimates}
            onChange={(e) => setShowOnlyWithEstimates(e.target.checked)}
            className="rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
          />
          Only show stocks with EPS estimates
        </label>
      </div>

      {/* Results count */}
      <div className="text-sm text-slate-400">
        Showing {filteredEarnings.length} earnings {activeCategory !== 'all' && `in ${CATEGORIES[activeCategory].label}`}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
        </div>
      ) : error ? (
        <div className="text-center py-20 text-red-400 bg-slate-800 rounded-xl border border-slate-700">
          {error}
        </div>
      ) : filteredEarnings.length === 0 ? (
        <div className="text-center py-20 text-slate-400 bg-slate-800 rounded-xl border border-slate-700">
          No earnings found for the selected filters
        </div>
      ) : (
        <div className="space-y-6">
          {sortedDates.map((date) => (
            <div key={date} className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              {/* Date header */}
              <div className="bg-slate-700/50 px-4 py-3 border-b border-slate-700">
                <h3 className="font-medium flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-slate-400" />
                  {formatDateHeader(date)}
                  <span className="text-slate-500 text-sm">({groupedEarnings[date].length} earnings)</span>
                </h3>
              </div>

              {/* Earnings table */}
              <div className="divide-y divide-slate-700/50">
                {groupedEarnings[date].map((earning, idx) => (
                  <div
                    key={`${earning.symbol}-${idx}`}
                    className="px-4 py-3 hover:bg-slate-700/30 transition-colors flex items-center justify-between gap-4"
                  >
                    {/* Left: Logo + Ticker + Company name */}
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {/* Company logo */}
                      {earning.logo ? (
                        <img
                          src={earning.logo}
                          alt={earning.symbol}
                          className="w-10 h-10 rounded-lg object-contain bg-white p-0.5 flex-shrink-0"
                          onError={(e) => { e.target.style.display = 'none' }}
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-slate-600 flex items-center justify-center text-xs font-bold text-slate-400 flex-shrink-0">
                          {earning.symbol.slice(0, 2)}
                        </div>
                      )}
                      {/* Ticker, name, and sector */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleTickerClick(earning.symbol)}
                            className="text-blue-400 font-semibold hover:text-blue-300 transition-colors"
                          >
                            {earning.symbol}
                          </button>
                          {earning.sector && (
                            <span className="px-2 py-0.5 text-xs rounded bg-slate-600/50 text-slate-400">
                              {earning.sector}
                            </span>
                          )}
                        </div>
                        {earning.companyName && (
                          <div className="text-slate-500 text-sm truncate">
                            {earning.companyName}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right: Revenue + EPS */}
                    <div className="flex items-center gap-6 text-sm flex-shrink-0">
                      <div className="text-right min-w-[100px] hidden sm:block">
                        <div className="text-slate-500 text-xs">Revenue Est.</div>
                        <div className="text-slate-300">{formatRevenue(earning.revenueEstimate)}</div>
                      </div>
                      <div className="text-right min-w-[70px]">
                        <div className="text-slate-500 text-xs">EPS Est.</div>
                        <div className="text-slate-300 font-medium">
                          {earning.epsEstimate != null ? `$${earning.epsEstimate.toFixed(2)}` : '-'}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

