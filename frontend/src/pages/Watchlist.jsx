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
  Plus,
  X,
  Briefcase,
} from 'lucide-react'
import { watchlistApi, portfolioApi } from '../services/api'

// Account presets for dropdown
const ACCOUNT_PRESETS = [
  'Fidelity',
  'Schwab',
  'Robinhood',
  'Coinbase',
  'Vanguard',
  'TD Ameritrade',
  'E*Trade',
  'Webull',
  'Interactive Brokers',
]

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

  // Add to portfolio modal state
  const [showPortfolioModal, setShowPortfolioModal] = useState(false)
  const [portfolioFormData, setPortfolioFormData] = useState({
    ticker: '',
    name: '',
    quantity: '',
    costBasis: '',
    accountName: '',
    customAccount: '',
  })
  const [portfolioFormError, setPortfolioFormError] = useState(null)
  const [addingToPortfolio, setAddingToPortfolio] = useState(false)

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
      next.has(industry) ? next.delete(industry) : next.add(industry)
      return next
    })
  }

  // Add to portfolio handlers
  const openPortfolioModal = (item, e) => {
    e.stopPropagation()
    setPortfolioFormData({
      ticker: item.symbol,
      name: item.name || item.symbol,
      quantity: '',
      costBasis: item.price?.toFixed(2) || '',
      accountName: '',
      customAccount: '',
    })
    setPortfolioFormError(null)
    setShowPortfolioModal(true)
  }

  const closePortfolioModal = () => {
    setShowPortfolioModal(false)
    setPortfolioFormError(null)
  }

  const handleAddToPortfolio = async (e) => {
    e.preventDefault()
    setPortfolioFormError(null)
    setAddingToPortfolio(true)

    const accountName =
      portfolioFormData.accountName === 'Other'
        ? portfolioFormData.customAccount
        : portfolioFormData.accountName

    if (!portfolioFormData.quantity || !portfolioFormData.costBasis || !accountName) {
      setPortfolioFormError('Please fill in all fields')
      setAddingToPortfolio(false)
      return
    }

    try {
      await portfolioApi.add({
        ticker: portfolioFormData.ticker,
        quantity: parseFloat(portfolioFormData.quantity),
        costBasis: parseFloat(portfolioFormData.costBasis),
        accountName,
      })
      closePortfolioModal()
    } catch (err) {
      setPortfolioFormError(err.response?.data?.detail || 'Failed to add to portfolio')
    } finally {
      setAddingToPortfolio(false)
    }
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
          {item.changePercent != null && item.changePercent >= 0 && <TrendingUp className="w-3 h-3" />}
          {item.changePercent != null && item.changePercent < 0 && <TrendingDown className="w-3 h-3" />}
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

      {/* Actions */}
      <td className="px-4 py-4 text-right">
        <div className="flex items-center justify-end gap-1">
          <button
            onClick={(e) => openPortfolioModal(item, e)}
            className="p-2 hover:bg-blue-500/20 rounded-lg transition-colors text-slate-400 hover:text-blue-400"
            title="Add to portfolio"
          >
            <Plus className="w-4 h-4" />
          </button>
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
        </div>
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

      {/* Add to Portfolio Modal */}
      {showPortfolioModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-blue-500" />
                <h2 className="text-lg font-semibold">Add to Portfolio</h2>
              </div>
              <button
                onClick={closePortfolioModal}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddToPortfolio} className="p-6 space-y-4">
              {portfolioFormError && (
                <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                  {portfolioFormError}
                </div>
              )}

              {/* Ticker (readonly) */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Stock
                </label>
                <div className="px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-300">
                  <span className="font-semibold">{portfolioFormData.ticker}</span>
                  <span className="text-slate-400 ml-2">{portfolioFormData.name}</span>
                </div>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Quantity
                </label>
                <input
                  type="number"
                  step="any"
                  value={portfolioFormData.quantity}
                  onChange={(e) =>
                    setPortfolioFormData({ ...portfolioFormData, quantity: e.target.value })
                  }
                  placeholder="e.g., 100"
                  className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500"
                  autoFocus
                />
              </div>

              {/* Cost Basis */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Cost Basis (per share)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                    $
                  </span>
                  <input
                    type="number"
                    step="any"
                    value={portfolioFormData.costBasis}
                    onChange={(e) =>
                      setPortfolioFormData({ ...portfolioFormData, costBasis: e.target.value })
                    }
                    placeholder="e.g., 150.50"
                    className="w-full pl-8 pr-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Pre-filled with current price. Adjust to your actual cost.
                </p>
              </div>

              {/* Account */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Account
                </label>
                <select
                  value={portfolioFormData.accountName}
                  onChange={(e) =>
                    setPortfolioFormData({ ...portfolioFormData, accountName: e.target.value })
                  }
                  className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500"
                >
                  <option value="">Select account...</option>
                  {ACCOUNT_PRESETS.map((account) => (
                    <option key={account} value={account}>
                      {account}
                    </option>
                  ))}
                  <option value="Other">Other</option>
                </select>
              </div>

              {/* Custom Account */}
              {portfolioFormData.accountName === 'Other' && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Custom Account Name
                  </label>
                  <input
                    type="text"
                    value={portfolioFormData.customAccount}
                    onChange={(e) =>
                      setPortfolioFormData({ ...portfolioFormData, customAccount: e.target.value })
                    }
                    placeholder="Enter account name"
                    className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              )}

              {/* Submit */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={closePortfolioModal}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingToPortfolio}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {addingToPortfolio && <Loader2 className="w-4 h-4 animate-spin" />}
                  Add to Portfolio
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
