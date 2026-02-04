import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Star,
  TrendingUp,
  TrendingDown,
  Loader2,
  Trash2,
  RefreshCw,
  AlertCircle,
  Building2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { watchlistApi } from '../services/api'

export default function Watchlist() {
  const navigate = useNavigate()
  const [watchlist, setWatchlist] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [removingSymbol, setRemovingSymbol] = useState(null)
  const [failedImages, setFailedImages] = useState(new Set())
  const [groupByIndustry, setGroupByIndustry] = useState(true)
  const [collapsedIndustries, setCollapsedIndustries] = useState(new Set())

  useEffect(() => {
    loadWatchlist()
  }, [])

  const loadWatchlist = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await watchlistApi.getAll(true)
      setWatchlist(response.data.items || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load watchlist')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const response = await watchlistApi.getAll(true)
      setWatchlist(response.data.items || [])
    } catch (err) {
      console.error('Failed to refresh watchlist:', err)
    } finally {
      setRefreshing(false)
    }
  }

  const handleRemove = async (symbol, e) => {
    e.stopPropagation()
    setRemovingSymbol(symbol)
    try {
      await watchlistApi.remove(symbol)
      setWatchlist(prev => prev.filter(item => item.symbol !== symbol))
    } catch (err) {
      console.error('Failed to remove from watchlist:', err)
    } finally {
      setRemovingSymbol(null)
    }
  }

  const toggleIndustry = (industry) => {
    setCollapsedIndustries(prev => {
      const next = new Set(prev)
      if (next.has(industry)) {
        next.delete(industry)
      } else {
        next.add(industry)
      }
      return next
    })
  }

  const formatPercent = (num) => {
    if (num === null || num === undefined) return 'N/A'
    return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`
  }

  const getPercentColor = (num) => {
    if (num === null || num === undefined) return 'text-slate-400'
    return num >= 0 ? 'text-emerald-400' : 'text-red-400'
  }

  // Group watchlist by industry
  const groupedWatchlist = useMemo(() => {
    if (!groupByIndustry) return null

    const groups = {}
    watchlist.forEach(item => {
      const industry = item.industry || 'Other'
      if (!groups[industry]) {
        groups[industry] = []
      }
      groups[industry].push(item)
    })

    // Sort industries alphabetically, but put "Other" at the end
    const sortedIndustries = Object.keys(groups).sort((a, b) => {
      if (a === 'Other') return 1
      if (b === 'Other') return -1
      return a.localeCompare(b)
    })

    return sortedIndustries.map(industry => ({
      industry,
      items: groups[industry],
      totalValue: groups[industry].reduce((sum, item) => sum + (item.price || 0), 0),
    }))
  }, [watchlist, groupByIndustry])

  // Calculate industry summary stats
  const getIndustrySummary = (items) => {
    const avgDayChange = items.reduce((sum, item) => sum + (item.changePercent || 0), 0) / items.length
    return { avgDayChange, count: items.length }
  }

  // Render a stock row
  const renderStockRow = (item, showIndustry = false) => (
    <tr
      key={item.symbol}
      onClick={() => navigate(`/analysis/${item.symbol}`)}
      className="hover:bg-slate-700/30 cursor-pointer transition-colors"
    >
      {/* Company */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          {item.image && !failedImages.has(item.symbol) ? (
            <img
              src={item.image}
              alt={item.symbol}
              className="w-10 h-10 rounded-lg object-contain bg-white p-1"
              onError={() => {
                setFailedImages(prev => new Set([...prev, item.symbol]))
              }}
            />
          ) : (
            <div className="w-10 h-10 rounded-lg bg-slate-700 flex items-center justify-center text-slate-400 text-sm font-bold">
              {item.symbol?.slice(0, 2)}
            </div>
          )}
          <div>
            <div className="font-semibold">{item.symbol}</div>
            <div className="text-sm text-slate-400 truncate max-w-[200px]">
              {item.name || 'Unknown'}
            </div>
            {showIndustry && item.industry && (
              <div className="text-xs text-slate-500 truncate max-w-[200px]">
                {item.industry}
              </div>
            )}
          </div>
        </div>
      </td>

      {/* Price */}
      <td className="px-4 py-4 text-right">
        <div className="font-semibold">
          ${item.price?.toFixed(2) || 'N/A'}
        </div>
      </td>

      {/* 1D Change */}
      <td className="px-4 py-4 text-right">
        <div className={`flex items-center justify-end gap-1 ${getPercentColor(item.changePercent)}`}>
          {item.changePercent !== null && item.changePercent !== undefined && (
            item.changePercent >= 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )
          )}
          <span>{formatPercent(item.changePercent)}</span>
        </div>
      </td>

      {/* 1M Change */}
      <td className="px-4 py-4 text-right">
        <span className={getPercentColor(item.momChangePercent)}>
          {formatPercent(item.momChangePercent)}
        </span>
      </td>

      {/* 1Y Change */}
      <td className="px-4 py-4 text-right">
        <span className={getPercentColor(item.yoyChangePercent)}>
          {formatPercent(item.yoyChangePercent)}
        </span>
      </td>

      {/* Added date */}
      <td className="px-4 py-4 text-right text-sm text-slate-400">
        {item.addedAt ? new Date(item.addedAt).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        }) : 'N/A'}
      </td>

      {/* Remove button */}
      <td className="px-4 py-4 text-right">
        <button
          onClick={(e) => handleRemove(item.symbol, e)}
          disabled={removingSymbol === item.symbol}
          className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-slate-400 hover:text-red-400"
          title="Remove from watchlist"
        >
          {removingSymbol === item.symbol ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </td>
    </tr>
  )

  // Loading state
  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500 mb-4" />
        <p className="text-slate-400">Loading watchlist...</p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold mb-2">Unable to Load Watchlist</h2>
        <p className="text-slate-400 mb-4">{error}</p>
        <button
          onClick={loadWatchlist}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Star className="w-8 h-8 text-yellow-500 fill-yellow-500" />
          <div>
            <h1 className="text-2xl font-bold">Watchlist</h1>
            <p className="text-slate-400 text-sm">
              {watchlist.length} {watchlist.length === 1 ? 'stock' : 'stocks'} tracked
              {groupByIndustry && groupedWatchlist && ` across ${groupedWatchlist.length} industries`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Group by Industry toggle */}
          <button
            onClick={() => setGroupByIndustry(!groupByIndustry)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              groupByIndustry
                ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
                : 'bg-slate-700 border border-slate-600 text-slate-400 hover:border-slate-500'
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span className="hidden sm:inline">Group by Industry</span>
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={`flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors ${
              refreshing ? 'opacity-50 cursor-wait' : ''
            }`}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Empty state */}
      {watchlist.length === 0 && (
        <div className="bg-slate-800 rounded-xl p-12 border border-slate-700 text-center">
          <Star className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">No stocks in watchlist</h2>
          <p className="text-slate-400 mb-6">
            Add stocks to your watchlist by clicking the star icon on any company analysis page.
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Browse Stocks
          </button>
        </div>
      )}

      {/* Grouped by Industry view */}
      {watchlist.length > 0 && groupByIndustry && groupedWatchlist && (
        <div className="space-y-4">
          {groupedWatchlist.map(({ industry, items }) => {
            const isCollapsed = collapsedIndustries.has(industry)
            const summary = getIndustrySummary(items)

            return (
              <div key={industry} className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                {/* Industry Header */}
                <button
                  onClick={() => toggleIndustry(industry)}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {isCollapsed ? (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    )}
                    <Building2 className="w-5 h-5 text-blue-500" />
                    <span className="font-semibold text-lg">{industry}</span>
                    <span className="text-sm text-slate-400 bg-slate-700 px-2 py-0.5 rounded-full">
                      {summary.count} {summary.count === 1 ? 'stock' : 'stocks'}
                    </span>
                  </div>
                  <div className={`text-sm font-medium ${getPercentColor(summary.avgDayChange)}`}>
                    Avg: {formatPercent(summary.avgDayChange)}
                  </div>
                </button>

                {/* Stocks Table */}
                {!isCollapsed && (
                  <table className="w-full">
                    <thead>
                      <tr className="border-t border-slate-700 text-left bg-slate-900/50">
                        <th className="px-6 py-3 text-slate-400 font-medium text-sm">Company</th>
                        <th className="px-4 py-3 text-slate-400 font-medium text-sm text-right">Price</th>
                        <th className="px-4 py-3 text-slate-400 font-medium text-sm text-right">1D</th>
                        <th className="px-4 py-3 text-slate-400 font-medium text-sm text-right">1M</th>
                        <th className="px-4 py-3 text-slate-400 font-medium text-sm text-right">1Y</th>
                        <th className="px-4 py-3 text-slate-400 font-medium text-sm text-right">Added</th>
                        <th className="px-4 py-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {items.map((item) => renderStockRow(item, false))}
                    </tbody>
                  </table>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Flat list view */}
      {watchlist.length > 0 && !groupByIndustry && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700 text-left">
                <th className="px-6 py-4 text-slate-400 font-medium">Company</th>
                <th className="px-4 py-4 text-slate-400 font-medium text-right">Price</th>
                <th className="px-4 py-4 text-slate-400 font-medium text-right">1D</th>
                <th className="px-4 py-4 text-slate-400 font-medium text-right">1M</th>
                <th className="px-4 py-4 text-slate-400 font-medium text-right">1Y</th>
                <th className="px-4 py-4 text-slate-400 font-medium text-right">Added</th>
                <th className="px-4 py-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {watchlist.map((item) => renderStockRow(item, true))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
