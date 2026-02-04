import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  Info,
  Loader2,
  BarChart3,
  PieChart,
  Brain,
  History,
  ChevronUp,
  ChevronDown,
  ExternalLink,
  Building2,
  Banknote,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Calendar,
  Newspaper,
  UserCheck,
  Landmark,
  Shield,
  Star,
  RefreshCw,
} from 'lucide-react'
import { financialsApi, watchlistApi } from '../services/api'
import PriceChart from '../components/charts/PriceChart'

// Format large numbers
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

// Helper component for metric rows in 4Q comparison table
const MetricRow = ({ label, quarters, field, format, color, colorCode }) => {
  const formatValue = (val) => {
    if (val === null || val === undefined) return 'N/A'
    switch (format) {
      case 'currency':
        return formatNumber(val)
      case 'percent':
        return `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`
      case 'marginPercent':
        return `${val.toFixed(1)}%`
      case 'eps':
        return `$${val.toFixed(2)}`
      case 'number':
        return val.toLocaleString()
      default:
        return val
    }
  }

  const getColor = (val) => {
    if (color) return `text-${color}-400`
    if (colorCode && val !== null && val !== undefined) {
      return val >= 0 ? 'text-emerald-400' : 'text-red-400'
    }
    return ''
  }

  return (
    <tr className="hover:bg-slate-700/20">
      <td className="py-2 px-2 text-slate-300">{label}</td>
      {quarters.map((q, i) => (
        <td key={i} className={`text-right py-2 px-2 font-medium ${getColor(q[field])}`}>
          {formatValue(q[field])}
        </td>
      ))}
    </tr>
  )
}

// Metric Card Component
function MetricCard({ label, value, subValue, icon: Icon, trend, color = 'blue' }) {
  const colorClasses = {
    blue: 'from-blue-500/20 to-blue-500/5 border-blue-500/30',
    green: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30',
    yellow: 'from-yellow-500/20 to-yellow-500/5 border-yellow-500/30',
    red: 'from-red-500/20 to-red-500/5 border-red-500/30',
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} border rounded-xl p-4`}>
      <div className="flex items-start justify-between mb-2">
        <span className="text-slate-400 text-sm">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-slate-500" />}
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      {subValue && (
        <div className={`text-sm flex items-center gap-1 ${
          trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400'
        }`}>
          {trend === 'up' && <ArrowUpRight className="w-3 h-3" />}
          {trend === 'down' && <ArrowDownRight className="w-3 h-3" />}
          {subValue}
        </div>
      )}
    </div>
  )
}

export default function CompanyAnalysis() {
  const { symbol } = useParams()
  const navigate = useNavigate()

  // Overview data (loads instantly)
  const [overview, setOverview] = useState(null)
  const [overviewLoading, setOverviewLoading] = useState(true)
  const [overviewError, setOverviewError] = useState(null)

  // Expanded sections
  const [activeSection, setActiveSection] = useState('price') // Chart open by default
  const [sectionData, setSectionData] = useState({})
  const [sectionLoading, setSectionLoading] = useState({})

  // Deep Insights (LLM-powered comprehensive analysis)
  const [deepInsights, setDeepInsights] = useState(null)
  const [deepInsightsLoading, setDeepInsightsLoading] = useState(false)
  const [deepInsightsExpanded, setDeepInsightsExpanded] = useState(false)

  // Revenue Drivers view mode
  const [revenueView, setRevenueView] = useState('quarterly') // 'quarterly', 'annual', '4q'

  // Price chart period
  const [chartPeriod, setChartPeriod] = useState('1y')

  // Market Feed (news, insider, senate trades)
  const [marketFeed, setMarketFeed] = useState(null)
  const [marketFeedLoading, setMarketFeedLoading] = useState(false)

  // Refresh state
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Watchlist state
  const [inWatchlist, setInWatchlist] = useState(false)
  const [watchlistLoading, setWatchlistLoading] = useState(false)

  // Image error state
  const [imageError, setImageError] = useState(false)

  // Load overview and chart on mount
  useEffect(() => {
    setImageError(false) // Reset image error on symbol change
    loadOverview()
    loadMarketFeed()
    loadPriceChart()
    checkWatchlistStatus()
  }, [symbol])

  // Check if stock is in watchlist
  const checkWatchlistStatus = async () => {
    try {
      const response = await watchlistApi.getStatus(symbol)
      setInWatchlist(response.data.inWatchlist)
    } catch (err) {
      console.error('Failed to check watchlist status:', err)
    }
  }

  // Toggle watchlist status
  const toggleWatchlist = async () => {
    if (watchlistLoading) return

    setWatchlistLoading(true)
    try {
      if (inWatchlist) {
        await watchlistApi.remove(symbol)
        setInWatchlist(false)
      } else {
        await watchlistApi.add(symbol)
        setInWatchlist(true)
      }
    } catch (err) {
      console.error('Failed to toggle watchlist:', err)
    } finally {
      setWatchlistLoading(false)
    }
  }

  // Load price chart data
  const loadPriceChart = async () => {
    setSectionLoading(prev => ({ ...prev, price: true }))
    try {
      const pRes = await financialsApi.getPriceHistory(symbol, chartPeriod)
      setSectionData(prev => ({ ...prev, price: pRes.data.prices }))
    } catch (err) {
      console.error('Failed to load price chart:', err)
    } finally {
      setSectionLoading(prev => ({ ...prev, price: false }))
    }
  }

  const loadMarketFeed = async () => {
    setMarketFeedLoading(true)
    try {
      const response = await financialsApi.getMarketFeed(symbol)
      setMarketFeed(response.data)
    } catch (err) {
      console.error('Failed to load market feed:', err)
    } finally {
      setMarketFeedLoading(false)
    }
  }

  const loadOverview = async () => {
    setOverviewLoading(true)
    setOverviewError(null)
    try {
      const response = await financialsApi.getOverview(symbol)
      setOverview(response.data)
    } catch (err) {
      setOverviewError(err.response?.data?.detail || 'Failed to load data')
    } finally {
      setOverviewLoading(false)
    }
  }

  // Refresh all data by clearing cache and reloading
  const handleRefresh = async () => {
    if (isRefreshing) return

    setIsRefreshing(true)
    try {
      // Clear all cache for this symbol
      await financialsApi.clearCache(symbol)

      // Reset deep insights state
      setDeepInsights(null)
      setDeepInsightsExpanded(false)

      // Reset section data
      setSectionData({})

      // Reload all data
      await Promise.all([
        loadOverview(),
        loadMarketFeed(),
        loadPriceChart()
      ])
    } catch (err) {
      console.error('Failed to refresh data:', err)
    } finally {
      setIsRefreshing(false)
    }
  }

  // Load price chart data on demand
  const loadSection = async (section) => {
    if (activeSection === section) {
      setActiveSection(null)
      return
    }

    setActiveSection(section)

    // Check if we already have data for this period
    const cacheKey = `${section}_${chartPeriod}`
    if (sectionData[cacheKey]) {
      setSectionData(prev => ({ ...prev, [section]: prev[cacheKey] }))
      return
    }

    setSectionLoading(prev => ({ ...prev, [section]: true }))

    try {
      const pRes = await financialsApi.getPriceHistory(symbol, chartPeriod)
      setSectionData(prev => ({
        ...prev,
        [section]: pRes.data.prices,
        [cacheKey]: pRes.data.prices // Cache by period too
      }))
    } catch (err) {
      console.error(`Failed to load ${section}:`, err)
    } finally {
      setSectionLoading(prev => ({ ...prev, [section]: false }))
    }
  }

  // Handle chart period change
  const handlePeriodChange = async (newPeriod) => {
    if (newPeriod === chartPeriod) return

    setChartPeriod(newPeriod)
    setSectionLoading(prev => ({ ...prev, price: true }))

    try {
      const pRes = await financialsApi.getPriceHistory(symbol, newPeriod)
      setSectionData(prev => ({
        ...prev,
        price: pRes.data.prices
      }))
    } catch (err) {
      console.error('Failed to load price data:', err)
    } finally {
      setSectionLoading(prev => ({ ...prev, price: false }))
    }
  }

  // Load Deep Insights (LLM-powered comprehensive analysis)
  const loadDeepInsights = async (forceRefresh = false) => {
    if (deepInsightsLoading) return

    setDeepInsightsLoading(true)
    setDeepInsightsExpanded(true)

    try {
      const response = await financialsApi.getDeepInsights(symbol, forceRefresh)
      setDeepInsights(response.data)
    } catch (err) {
      console.error('Failed to load deep insights:', err)
      setDeepInsights({ error: err.response?.data?.detail || 'Failed to generate deep insights' })
    } finally {
      setDeepInsightsLoading(false)
    }
  }

  // Loading state
  if (overviewLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500 mb-4" />
        <p className="text-slate-400">Loading {symbol}...</p>
      </div>
    )
  }

  // Error state
  if (overviewError) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold mb-2">Unable to Load Data</h2>
        <p className="text-slate-400 mb-4 text-center max-w-md">{overviewError}</p>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            Go Back
          </button>
          <button
            onClick={loadOverview}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const { profile, price, latestQuarter, balanceSheet, cashFlow, earnings, revenuePillars, nextEarnings, quarterlyComparison, analystRatings } = overview

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            title="Back to Dashboard"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing || overviewLoading}
            className={`p-2 hover:bg-slate-800 rounded-lg transition-colors ${
              isRefreshing ? 'opacity-50 cursor-wait' : ''
            }`}
            title="Refresh all data (clears cache)"
          >
            <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex items-center gap-3">
            {profile.image && !imageError ? (
              <img
                src={profile.image}
                alt={symbol}
                className="w-12 h-12 rounded-lg object-contain bg-white p-1"
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-slate-700 flex items-center justify-center text-slate-400 text-lg font-bold">
                {symbol?.slice(0, 2)}
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold">{profile.name}</h1>
                <button
                  onClick={toggleWatchlist}
                  disabled={watchlistLoading}
                  className={`p-1.5 rounded-lg transition-all ${
                    inWatchlist
                      ? 'text-yellow-500 hover:bg-yellow-500/20'
                      : 'text-slate-400 hover:bg-slate-700 hover:text-yellow-500'
                  } ${watchlistLoading ? 'opacity-50 cursor-wait' : ''}`}
                  title={inWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
                >
                  <Star className={`w-5 h-5 ${inWatchlist ? 'fill-yellow-500' : ''}`} />
                </button>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <span>{symbol}</span>
                <span>•</span>
                <span>{profile.sector}</span>
                <span>•</span>
                <span>{profile.industry}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stock Price */}
        <div className="text-right">
          <div className="text-3xl font-bold">${price.current?.toFixed(2)}</div>

          {/* Day Change */}
          <div className={`flex items-center justify-end gap-1 ${
            price.change >= 0 ? 'text-emerald-400' : 'text-red-400'
          }`}>
            {price.change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            <span>${Math.abs(price.change || 0).toFixed(2)}</span>
            <span>({formatPercent(price.changePercent)})</span>
          </div>

          {/* MoM and YoY Changes */}
          <div className="flex items-center justify-end gap-3 mt-1 text-sm">
            <div className={`flex items-center gap-1 ${
              price.momChangePercent >= 0 ? 'text-emerald-400/80' : 'text-red-400/80'
            }`}>
              <span className="text-slate-500">1M:</span>
              <span>{price.momChangePercent !== null && price.momChangePercent !== undefined
                ? `${price.momChangePercent >= 0 ? '+' : ''}${price.momChangePercent?.toFixed(1)}%`
                : 'N/A'}</span>
            </div>
            <div className={`flex items-center gap-1 ${
              price.yoyChangePercent >= 0 ? 'text-emerald-400/80' : 'text-red-400/80'
            }`}>
              <span className="text-slate-500">1Y:</span>
              <span>{price.yoyChangePercent !== null && price.yoyChangePercent !== undefined
                ? `${price.yoyChangePercent >= 0 ? '+' : ''}${price.yoyChangePercent?.toFixed(1)}%`
                : 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">Market Cap</span>
          <span className="float-right font-medium">{formatNumber(price.marketCap, 2)}</span>
        </div>
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">52W Range</span>
          <span className="float-right font-medium text-xs">{price.range52Week}</span>
        </div>
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">Employees</span>
          <span className="float-right font-medium">{parseInt(profile.employees || 0).toLocaleString()}</span>
        </div>
        {nextEarnings && (
          <div className="bg-gradient-to-r from-purple-500/20 to-purple-500/5 border border-purple-500/30 rounded-lg px-4 py-2 flex items-center justify-between">
            <span className="text-purple-400 flex items-center gap-1">
              <Calendar className="w-3 h-3" /> Next Earnings
            </span>
            <span className="font-medium">
              {(() => {
                const [year, month, day] = nextEarnings.date.split('-').map(Number)
                const d = new Date(year, month - 1, day) // Parse as local date
                const monthName = d.toLocaleDateString('en-US', { month: 'long' })
                const suffix = day === 1 || day === 21 || day === 31 ? 'st' : day === 2 || day === 22 ? 'nd' : day === 3 || day === 23 ? 'rd' : 'th'
                return `${monthName} ${day}${suffix}`
              })()}
              <span className="text-slate-400 text-xs ml-1">({nextEarnings.daysUntil}d)</span>
            </span>
          </div>
        )}
        <button
          onClick={() => loadSection('price')}
          disabled={sectionLoading.price}
          className={`rounded-lg px-4 py-2 flex items-center gap-2 transition-all ${
            activeSection === 'price'
              ? 'bg-gradient-to-r from-blue-500/20 to-blue-500/5 border border-blue-500/30 text-blue-400'
              : 'bg-slate-800/50 border border-slate-700 text-slate-300 hover:border-slate-600 hover:bg-slate-700'
          } ${sectionLoading.price ? 'opacity-50 cursor-wait' : ''}`}
        >
          {sectionLoading.price ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <TrendingUp className="w-3 h-3" />
          )}
          <span>Chart</span>
        </button>
      </div>

      {/* Price Chart - Expanded below Quick Stats */}
      {activeSection === 'price' && sectionData.price && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <PriceChart
            key={`${chartPeriod}-${sectionData.price?.length}`}
            data={sectionData.price}
            period={chartPeriod}
            onPeriodChange={handlePeriodChange}
            loading={sectionLoading.price}
          />
        </div>
      )}

      {/* Analyst Ratings Section */}
      {analystRatings && (analystRatings.consensus || analystRatings.priceTarget) && (
        <div className="bg-gradient-to-r from-slate-800 to-slate-800/50 rounded-xl p-5 border border-slate-700">
          <div className="flex items-center gap-2 mb-4">
            <Star className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-semibold">Analyst Ratings</h2>
            {analystRatings.totalAnalysts > 0 && (
              <span className="text-xs text-slate-400 ml-1">
                ({analystRatings.totalAnalysts} analysts)
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Consensus Rating */}
            {analystRatings.consensus && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">Consensus</span>
                  <span className={`text-lg font-bold ${
                    analystRatings.consensus.rating === 'Strong Buy' ? 'text-teal-400' :
                    analystRatings.consensus.rating === 'Buy' ? 'text-emerald-400' :
                    analystRatings.consensus.rating === 'Hold' ? 'text-yellow-400' :
                    analystRatings.consensus.rating === 'Sell' ? 'text-orange-400' :
                    'text-red-400'
                  }`}>
                    {analystRatings.consensus.rating}
                  </span>
                </div>

                {/* Rating Bar */}
                <div className="flex gap-1 h-8">
                  {analystRatings.consensus.strongBuy > 0 && (
                    <div
                      className="bg-teal-500 rounded-l flex items-center justify-center text-xs font-medium"
                      style={{ flex: analystRatings.consensus.strongBuy }}
                      title={`Strong Buy: ${analystRatings.consensus.strongBuy}`}
                    >
                      {analystRatings.consensus.strongBuy > 2 && analystRatings.consensus.strongBuy}
                    </div>
                  )}
                  {analystRatings.consensus.buy > 0 && (
                    <div
                      className="bg-emerald-500 flex items-center justify-center text-xs font-medium"
                      style={{ flex: analystRatings.consensus.buy }}
                      title={`Buy: ${analystRatings.consensus.buy}`}
                    >
                      {analystRatings.consensus.buy > 2 && analystRatings.consensus.buy}
                    </div>
                  )}
                  {analystRatings.consensus.hold > 0 && (
                    <div
                      className="bg-yellow-500 flex items-center justify-center text-xs font-medium text-slate-900"
                      style={{ flex: analystRatings.consensus.hold }}
                      title={`Hold: ${analystRatings.consensus.hold}`}
                    >
                      {analystRatings.consensus.hold > 2 && analystRatings.consensus.hold}
                    </div>
                  )}
                  {analystRatings.consensus.sell > 0 && (
                    <div
                      className="bg-orange-500 flex items-center justify-center text-xs font-medium"
                      style={{ flex: analystRatings.consensus.sell }}
                      title={`Sell: ${analystRatings.consensus.sell}`}
                    >
                      {analystRatings.consensus.sell > 2 && analystRatings.consensus.sell}
                    </div>
                  )}
                  {analystRatings.consensus.strongSell > 0 && (
                    <div
                      className="bg-red-500 rounded-r flex items-center justify-center text-xs font-medium"
                      style={{ flex: analystRatings.consensus.strongSell }}
                      title={`Strong Sell: ${analystRatings.consensus.strongSell}`}
                    >
                      {analystRatings.consensus.strongSell > 2 && analystRatings.consensus.strongSell}
                    </div>
                  )}
                </div>

                {/* Legend */}
                <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-teal-500" />
                    Strong Buy ({analystRatings.consensus.strongBuy})
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    Buy ({analystRatings.consensus.buy})
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-yellow-500" />
                    Hold ({analystRatings.consensus.hold})
                  </span>
                  {(analystRatings.consensus.sell > 0 || analystRatings.consensus.strongSell > 0) && (
                    <>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-orange-500" />
                        Sell ({analystRatings.consensus.sell})
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-red-500" />
                        Strong Sell ({analystRatings.consensus.strongSell})
                      </span>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Price Target */}
            {analystRatings.priceTarget && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">Price Target</span>
                  <div className="text-right">
                    <span className="text-lg font-bold">${analystRatings.priceTarget.consensus?.toFixed(2)}</span>
                    <span className={`ml-2 text-sm font-medium ${
                      analystRatings.priceTarget.upside >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      ({analystRatings.priceTarget.upside >= 0 ? '+' : ''}{analystRatings.priceTarget.upside?.toFixed(1)}%)
                    </span>
                  </div>
                </div>

                {/* Price Range Bar */}
                <div className="relative">
                  <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                    <span>${analystRatings.priceTarget.low?.toFixed(0)}</span>
                    <span>${analystRatings.priceTarget.high?.toFixed(0)}</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full relative">
                    <div className="absolute h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full left-0 right-0" />
                    {analystRatings.priceTarget.current && analystRatings.priceTarget.low && analystRatings.priceTarget.high && (
                      <div
                        className="absolute w-3 h-3 bg-white rounded-full border-2 border-slate-900 -top-0.5"
                        style={{
                          left: `${Math.min(100, Math.max(0,
                            ((analystRatings.priceTarget.current - analystRatings.priceTarget.low) /
                            (analystRatings.priceTarget.high - analystRatings.priceTarget.low)) * 100
                          ))}%`,
                          transform: 'translateX(-50%)',
                        }}
                        title={`Current: $${analystRatings.priceTarget.current?.toFixed(2)}`}
                      />
                    )}
                  </div>
                  <div className="text-center text-xs text-slate-400 mt-1">
                    Current: ${analystRatings.priceTarget.current?.toFixed(2)}
                  </div>
                </div>

                {/* Price Target Details */}
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="bg-slate-700/50 rounded-lg p-2">
                    <div className="text-slate-400">Low</div>
                    <div className="font-medium">${analystRatings.priceTarget.low?.toFixed(0)}</div>
                  </div>
                  <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-2">
                    <div className="text-blue-400">Median</div>
                    <div className="font-medium text-blue-400">${analystRatings.priceTarget.median?.toFixed(0)}</div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-2">
                    <div className="text-slate-400">High</div>
                    <div className="font-medium">${analystRatings.priceTarget.high?.toFixed(0)}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Smart Insights Section */}
      {overview?.smartInsights && (overview.smartInsights.warnings?.length > 0 || overview.smartInsights.positives?.length > 0) && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-500" />
              Smart Insights
              {overview.smartInsights.summary?.highSeverityCount > 0 && (
                <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-red-500/20 text-red-400">
                  {overview.smartInsights.summary.highSeverityCount} Critical
                </span>
              )}
            </h2>
            <button
              onClick={() => loadDeepInsights(false)}
              disabled={deepInsightsLoading}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-50 disabled:cursor-wait rounded-lg text-sm font-medium transition-all"
            >
              {deepInsightsLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Brain className="w-4 h-4" />
              )}
              {deepInsightsLoading ? 'Analyzing...' : 'Deep Analysis'}
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Warnings Column */}
            <div>
              {overview.smartInsights.warnings?.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-slate-400 flex items-center gap-1">
                    <AlertTriangle className="w-4 h-4 text-amber-500" /> Key Concerns
                  </h3>
                  {overview.smartInsights.warnings.map((warning, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border ${
                        warning.severity === 'high'
                          ? 'bg-red-500/10 border-red-500/30'
                          : warning.severity === 'medium'
                          ? 'bg-amber-500/10 border-amber-500/30'
                          : 'bg-slate-700/50 border-slate-600'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <AlertCircle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                          warning.severity === 'high' ? 'text-red-400' : 'text-amber-400'
                        }`} />
                        <div>
                          <div className={`font-medium text-sm ${
                            warning.severity === 'high' ? 'text-red-400' : 'text-amber-400'
                          }`}>
                            {warning.title}
                          </div>
                          <div className="text-xs text-slate-400 mt-1">{warning.message}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {overview.smartInsights.warnings?.length === 0 && (
                <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-medium text-sm">No major concerns identified</span>
                  </div>
                </div>
              )}
            </div>

            {/* Metrics & Positives Column */}
            <div className="space-y-4">
              {/* Positives */}
              {overview.smartInsights.positives?.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-slate-400 flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-emerald-500" /> Strengths
                  </h3>
                  {overview.smartInsights.positives.map((positive, i) => (
                    <div key={i} className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                      <div className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-emerald-400" />
                        <div>
                          <div className="font-medium text-sm text-emerald-400">{positive.title}</div>
                          <div className="text-xs text-slate-400 mt-1">{positive.message}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Key Metrics */}
              {overview.smartInsights.keyMetrics?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-1">
                    <Info className="w-4 h-4" /> Key Metrics
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    {overview.smartInsights.keyMetrics.map((metric, i) => (
                      <div key={i} className="p-2 rounded-lg bg-slate-700/50 border border-slate-600">
                        <div className="text-xs text-slate-400">{metric.name}</div>
                        <div className={`font-semibold ${
                          metric.interpretation === 'good' ? 'text-emerald-400' :
                          metric.interpretation === 'concern' ? 'text-red-400' : 'text-slate-300'
                        }`}>
                          {metric.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Deep Insights Panel (LLM-powered) */}
      {(deepInsightsLoading || deepInsights) && (
        <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 rounded-xl border border-purple-500/30 overflow-hidden">
          {/* Header */}
          <div
            className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/30 transition-colors"
            onClick={() => setDeepInsightsExpanded(!deepInsightsExpanded)}
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Deep Analysis</h2>
                <p className="text-xs text-slate-400">LLM-powered insights for {profile?.industry || 'this company'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {deepInsights?.cached && (
                <span className="text-xs px-2 py-1 rounded-full bg-slate-700 text-slate-400">
                  Cached
                </span>
              )}
              {deepInsightsLoading ? (
                <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
              ) : (
                <button className="p-1 hover:bg-slate-700 rounded">
                  {deepInsightsExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              )}
            </div>
          </div>

          {/* Loading State */}
          {deepInsightsLoading && deepInsightsExpanded && (
            <div className="px-6 pb-6">
              <div className="flex items-center gap-3 text-slate-400">
                <div className="animate-pulse flex space-x-4 w-full">
                  <div className="flex-1 space-y-4 py-1">
                    <div className="h-4 bg-slate-700 rounded w-3/4"></div>
                    <div className="space-y-3">
                      <div className="h-4 bg-slate-700 rounded"></div>
                      <div className="h-4 bg-slate-700 rounded w-5/6"></div>
                    </div>
                  </div>
                </div>
              </div>
              <p className="text-sm text-slate-400 mt-4">
                Analyzing comprehensive financial data with LLM... This may take 15-30 seconds.
              </p>
            </div>
          )}

          {/* Error State */}
          {deepInsights?.error && deepInsightsExpanded && (
            <div className="px-6 pb-6">
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <div className="flex items-center gap-2 text-red-400">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-medium">Analysis Failed</span>
                </div>
                <p className="text-sm text-slate-400 mt-2">{deepInsights.error}</p>
                <button
                  onClick={() => loadDeepInsights(true)}
                  className="mt-3 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg text-sm text-red-400 transition-colors"
                >
                  Retry Analysis
                </button>
              </div>
            </div>
          )}

          {/* Insights Content */}
          {deepInsights?.insights && deepInsightsExpanded && !deepInsightsLoading && (
            <div className="px-6 pb-6 space-y-6">
              {/* Industry Context */}
              {deepInsights.insights.industryContext && (
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-purple-400 mb-2 flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Industry Context: {deepInsights.insights.industryContext.industry}
                  </h3>
                  <p className="text-sm text-slate-300 mb-3">{deepInsights.insights.industryContext.whatMatters}</p>
                  {deepInsights.insights.industryContext.keyKPIs?.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {deepInsights.insights.industryContext.keyKPIs.map((kpi, i) => (
                        <span key={i} className="px-2 py-1 text-xs bg-purple-500/20 text-purple-300 rounded-full">
                          {kpi}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Simple Explanation - For New Investors */}
              {deepInsights.insights.beginnerExplanation && (
                <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-blue-400 mb-2 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    Simple Explanation (For New Investors)
                  </h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {deepInsights.insights.beginnerExplanation}
                  </p>
                </div>
              )}

              {/* Operational Insights */}
              {deepInsights.insights.operationalInsights?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4" />
                    Operational Insights
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {deepInsights.insights.operationalInsights.map((insight, i) => (
                      <div key={i} className="bg-slate-800/50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{insight.metric}</span>
                          {insight.trend && (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              insight.trend.toLowerCase().includes('up') || insight.trend.includes('+')
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : insight.trend.toLowerCase().includes('down') || insight.trend.includes('-')
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-slate-600 text-slate-400'
                            }`}>
                              {insight.trend}
                            </span>
                          )}
                        </div>
                        <div className="text-lg font-bold text-white mb-1">{insight.value}</div>
                        <p className="text-xs text-slate-400">{insight.interpretation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Deep Dive Section */}
              {deepInsights.insights.deepDive && (
                <div>
                  <h3 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Deep Dive Analysis
                  </h3>
                  <div className="space-y-3">
                    {deepInsights.insights.deepDive.revenueQuality && (
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <h4 className="text-xs font-medium text-slate-400 mb-1">Revenue Quality</h4>
                        <p className="text-sm text-slate-300">{deepInsights.insights.deepDive.revenueQuality}</p>
                      </div>
                    )}
                    {deepInsights.insights.deepDive.marginAnalysis && (
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <h4 className="text-xs font-medium text-slate-400 mb-1">Margin Analysis</h4>
                        <p className="text-sm text-slate-300">{deepInsights.insights.deepDive.marginAnalysis}</p>
                      </div>
                    )}
                    {deepInsights.insights.deepDive.cashFlowHealth && (
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <h4 className="text-xs font-medium text-slate-400 mb-1">Cash Flow Health</h4>
                        <p className="text-sm text-slate-300">{deepInsights.insights.deepDive.cashFlowHealth}</p>
                      </div>
                    )}
                    {deepInsights.insights.deepDive.balanceSheetStrength && (
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <h4 className="text-xs font-medium text-slate-400 mb-1">Balance Sheet Strength</h4>
                        <p className="text-sm text-slate-300">{deepInsights.insights.deepDive.balanceSheetStrength}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Hidden Insights */}
              {deepInsights.insights.hiddenInsights?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Hidden Insights (What Others Miss)
                  </h3>
                  <div className="space-y-3">
                    {deepInsights.insights.hiddenInsights.map((insight, i) => (
                      <div key={i} className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                        <div className="font-medium text-sm text-amber-300 mb-1">{insight.finding}</div>
                        <p className="text-xs text-slate-400 mb-2">{insight.significance}</p>
                        {insight.actionable && (
                          <div className="flex items-center gap-1 text-xs text-amber-400">
                            <Target className="w-3 h-3" />
                            <span>{insight.actionable}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risks & Opportunities */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Risks */}
                {deepInsights.insights.risks?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      Key Risks
                    </h3>
                    <div className="space-y-2">
                      {deepInsights.insights.risks.map((risk, i) => (
                        <div key={i} className={`p-3 rounded-lg border ${
                          risk.severity === 'HIGH'
                            ? 'bg-red-500/10 border-red-500/30'
                            : 'bg-slate-800/50 border-slate-700'
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-sm">{risk.risk}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              risk.severity === 'HIGH'
                                ? 'bg-red-500/20 text-red-400'
                                : risk.severity === 'MEDIUM'
                                ? 'bg-amber-500/20 text-amber-400'
                                : 'bg-slate-600 text-slate-400'
                            }`}>
                              {risk.severity}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{risk.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Opportunities */}
                {deepInsights.insights.opportunities?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Opportunities
                    </h3>
                    <div className="space-y-2">
                      {deepInsights.insights.opportunities.map((opp, i) => (
                        <div key={i} className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3">
                          <div className="font-medium text-sm text-emerald-300 mb-1">{opp.opportunity}</div>
                          <p className="text-xs text-slate-400">{opp.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Refresh Button */}
              <div className="flex justify-end">
                <button
                  onClick={() => loadDeepInsights(true)}
                  disabled={deepInsightsLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg text-sm transition-colors"
                >
                  <History className="w-4 h-4" />
                  Refresh Analysis
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Latest Quarter Section */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-500" />
            Latest Quarter ({latestQuarter.period})
          </h2>
          {latestQuarter.reportedDate && (
            <span className="text-sm text-slate-400 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              Reported: {new Date(latestQuarter.reportedDate).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
              })}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Revenue"
            value={formatNumber(latestQuarter.revenue)}
            subValue={latestQuarter.grossMargin ? `${latestQuarter.grossMargin}% margin` : null}
            icon={DollarSign}
            color="blue"
          />
          <MetricCard
            label="Net Income"
            value={formatNumber(latestQuarter.netIncome)}
            subValue={`${latestQuarter.netMargin}% margin`}
            icon={Banknote}
            color="green"
          />
          <MetricCard
            label="EPS"
            value={`$${latestQuarter.eps?.toFixed(2) || 'N/A'}`}
            subValue={earnings.beat !== null ? (earnings.beat ? 'Beat estimates' : 'Missed estimates') : null}
            trend={earnings.beat ? 'up' : earnings.beat === false ? 'down' : null}
            icon={Target}
            color={earnings.beat ? 'green' : earnings.beat === false ? 'red' : 'purple'}
          />
          <MetricCard
            label="Operating Margin"
            value={`${latestQuarter.operatingMargin}%`}
            icon={PieChart}
            color="yellow"
          />
        </div>
      </div>

      {/* Balance Sheet & Cash Flow */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Wallet className="w-5 h-5 text-emerald-500" />
            Balance Sheet
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-slate-400">Cash & Investments</span>
              <span className="font-medium text-emerald-400">{formatNumber(balanceSheet.totalCash)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Total Debt</span>
              <span className="font-medium text-red-400">{formatNumber(balanceSheet.totalDebt)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Total Assets</span>
              <span className="font-medium">{formatNumber(balanceSheet.totalAssets)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Shareholder Equity</span>
              <span className="font-medium">{formatNumber(balanceSheet.shareholderEquity)}</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-purple-500" />
            Cash Flow (Quarterly)
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-slate-400">Operating Cash Flow</span>
              <span className="font-medium text-emerald-400">{formatNumber(cashFlow.operatingCashFlow)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Free Cash Flow</span>
              <span className="font-medium text-emerald-400">{formatNumber(cashFlow.freeCashFlow)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">CapEx</span>
              <span className="font-medium text-yellow-400">{formatNumber(Math.abs(cashFlow.capex || 0))}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Buybacks</span>
              <span className="font-medium text-blue-400">{formatNumber(Math.abs(cashFlow.stockBuyback || 0))}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Revenue Drivers Section - with view toggle */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <PieChart className="w-5 h-5 text-blue-500" />
            Revenue Drivers
          </h2>

          {/* View Toggle Pills */}
          <div className="flex gap-2">
            <button
              onClick={() => setRevenueView('quarterly')}
              className={`px-3 py-1.5 text-sm rounded-full transition-all ${
                revenueView === 'quarterly'
                  ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
                  : 'bg-slate-700 border border-slate-600 text-slate-400 hover:border-slate-500'
              }`}
            >
              Quarterly
            </button>
            <button
              onClick={() => setRevenueView('annual')}
              className={`px-3 py-1.5 text-sm rounded-full transition-all ${
                revenueView === 'annual'
                  ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
                  : 'bg-slate-700 border border-slate-600 text-slate-400 hover:border-slate-500'
              }`}
            >
              Annual Segments
            </button>
            <button
              onClick={() => setRevenueView('4q')}
              className={`px-3 py-1.5 text-sm rounded-full transition-all ${
                revenueView === '4q'
                  ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
                  : 'bg-slate-700 border border-slate-600 text-slate-400 hover:border-slate-500'
              }`}
            >
              4Q Comparison
            </button>
          </div>
        </div>

        {/* Quarterly View - Latest quarter with YoY comparison */}
        {revenueView === 'quarterly' && quarterlyComparison?.latest && (
          <div>
            <div className="text-sm text-slate-400 mb-4">
              {quarterlyComparison.latest.period}
              {quarterlyComparison.yoyComparison && (
                <span className="ml-2 text-slate-500">vs {quarterlyComparison.yoyComparison.previousPeriod}</span>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="text-slate-400 text-sm mb-1">Revenue</div>
                <div className="text-xl font-bold">{formatNumber(quarterlyComparison.latest.revenue)}</div>
                {quarterlyComparison.yoyComparison?.revenueChange != null && (
                  <div className={`text-sm mt-1 ${quarterlyComparison.yoyComparison.revenueChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {quarterlyComparison.yoyComparison.revenueChange >= 0 ? '+' : ''}{quarterlyComparison.yoyComparison.revenueChange}% YoY
                  </div>
                )}
              </div>

              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="text-slate-400 text-sm mb-1">Gross Profit</div>
                <div className="text-xl font-bold">{formatNumber(quarterlyComparison.latest.grossProfit)}</div>
                <div className="text-sm text-slate-500">{quarterlyComparison.latest.grossMargin}% margin</div>
              </div>

              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="text-slate-400 text-sm mb-1">Net Income</div>
                <div className="text-xl font-bold">{formatNumber(quarterlyComparison.latest.netIncome)}</div>
                {quarterlyComparison.yoyComparison?.netIncomeChange != null && (
                  <div className={`text-sm mt-1 ${quarterlyComparison.yoyComparison.netIncomeChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {quarterlyComparison.yoyComparison.netIncomeChange >= 0 ? '+' : ''}{quarterlyComparison.yoyComparison.netIncomeChange}% YoY
                  </div>
                )}
              </div>

              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="text-slate-400 text-sm mb-1">EPS</div>
                <div className="text-xl font-bold">${quarterlyComparison.latest.eps?.toFixed(2) || 'N/A'}</div>
                {quarterlyComparison.yoyComparison?.epsChange != null && (
                  <div className={`text-sm mt-1 ${quarterlyComparison.yoyComparison.epsChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {quarterlyComparison.yoyComparison.epsChange >= 0 ? '+' : ''}{quarterlyComparison.yoyComparison.epsChange}% YoY
                  </div>
                )}
              </div>
            </div>

            {/* Margins Bar */}
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="bg-slate-700/20 rounded-lg p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-400 text-sm">Gross Margin</span>
                  <span className="text-emerald-400 font-medium">{quarterlyComparison.latest.grossMargin}%</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${quarterlyComparison.latest.grossMargin}%` }} />
                </div>
              </div>
              <div className="bg-slate-700/20 rounded-lg p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-400 text-sm">Operating Margin</span>
                  <span className="text-blue-400 font-medium">{quarterlyComparison.latest.operatingMargin}%</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${Math.min(quarterlyComparison.latest.operatingMargin, 100)}%` }} />
                </div>
              </div>
              <div className="bg-slate-700/20 rounded-lg p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-400 text-sm">Net Margin</span>
                  <span className="text-purple-400 font-medium">{quarterlyComparison.latest.netMargin}%</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2">
                  <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${Math.min(quarterlyComparison.latest.netMargin, 100)}%` }} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Annual Segments View - Product and Geographic breakdown */}
        {revenueView === 'annual' && revenuePillars && (revenuePillars.products?.length > 0 || revenuePillars.geographies?.length > 0) && (
          <div>
            <div className="text-sm text-slate-400 mb-4">
              FY{revenuePillars.products?.[0]?.fiscalYear || revenuePillars.geographies?.[0]?.fiscalYear || ''}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Product Segments */}
              {revenuePillars.products?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-3">By Product</h3>
                  <div className="space-y-2">
                    {revenuePillars.products.map((product, i) => (
                      <div key={i} className="bg-slate-700/30 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{product.name}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm">{formatNumber(product.revenue)}</span>
                            {product.yoyChange !== undefined && (
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                product.trend === 'up'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : product.trend === 'down'
                                  ? 'bg-red-500/20 text-red-400'
                                  : 'bg-slate-600 text-slate-400'
                              }`}>
                                {product.yoyChange > 0 ? '+' : ''}{product.yoyChange}%
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="w-full bg-slate-600 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${
                              product.trend === 'up' ? 'bg-emerald-500' :
                              product.trend === 'down' ? 'bg-red-500' : 'bg-blue-500'
                            }`}
                            style={{ width: `${product.share}%` }}
                          />
                        </div>
                        <div className="text-xs text-slate-500 mt-1">{product.share}% of revenue</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Geographic Segments */}
              {revenuePillars.geographies?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-3">By Geography</h3>
                  <div className="space-y-2">
                    {revenuePillars.geographies.map((geo, i) => (
                      <div key={i} className="bg-slate-700/30 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{geo.name}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm">{formatNumber(geo.revenue)}</span>
                            {geo.yoyChange !== undefined && (
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                geo.trend === 'up'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : geo.trend === 'down'
                                  ? 'bg-red-500/20 text-red-400'
                                  : 'bg-slate-600 text-slate-400'
                              }`}>
                                {geo.yoyChange > 0 ? '+' : ''}{geo.yoyChange}%
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="w-full bg-slate-600 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${
                              geo.trend === 'up' ? 'bg-emerald-500' :
                              geo.trend === 'down' ? 'bg-red-500' : 'bg-blue-500'
                            }`}
                            style={{ width: `${geo.share}%` }}
                          />
                        </div>
                        <div className="text-xs text-slate-500 mt-1">{geo.share}% of revenue</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Annual Segments - No data fallback */}
        {revenueView === 'annual' && (!revenuePillars || (revenuePillars.products?.length === 0 && revenuePillars.geographies?.length === 0)) && (
          <div className="text-center text-slate-500 py-8">
            <PieChart className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No segment data available for this company</p>
          </div>
        )}

        {/* 4Q Comparison View - Categorized Table */}
        {revenueView === '4q' && quarterlyComparison?.quarters?.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-2 text-slate-400 font-medium">Metric</th>
                  {quarterlyComparison.quarters.map((q, i) => (
                    <th key={i} className="text-right py-3 px-2 text-slate-400 font-medium">{q.period}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {/* Section A: Growth & Profitability */}
                <tr className="bg-emerald-500/10">
                  <td colSpan={5} className="py-2 px-2 text-emerald-400 font-semibold text-xs uppercase tracking-wide">
                    A. Growth & Profitability
                  </td>
                </tr>
                <MetricRow label="Revenue" quarters={quarterlyComparison.quarters} field="revenue" format="currency" />
                <MetricRow label="Revenue QoQ" quarters={quarterlyComparison.quarters} field="revenueQoQ" format="percent" colorCode />
                <MetricRow label="Gross Profit" quarters={quarterlyComparison.quarters} field="grossProfit" format="currency" />
                <MetricRow label="Operating Income" quarters={quarterlyComparison.quarters} field="operatingIncome" format="currency" />
                <MetricRow label="Net Income" quarters={quarterlyComparison.quarters} field="netIncome" format="currency" />
                <MetricRow label="EPS" quarters={quarterlyComparison.quarters} field="eps" format="eps" />
                <MetricRow label="Gross Margin" quarters={quarterlyComparison.quarters} field="grossMargin" format="marginPercent" color="emerald" />
                <MetricRow label="Operating Margin" quarters={quarterlyComparison.quarters} field="operatingMargin" format="marginPercent" color="blue" />
                <MetricRow label="Net Margin" quarters={quarterlyComparison.quarters} field="netMargin" format="marginPercent" color="purple" />

                {/* Section B: Cost Structure */}
                <tr className="bg-orange-500/10">
                  <td colSpan={5} className="py-2 px-2 text-orange-400 font-semibold text-xs uppercase tracking-wide">
                    B. Cost Structure
                  </td>
                </tr>
                <MetricRow label="Cost of Revenue" quarters={quarterlyComparison.quarters} field="costOfRevenue" format="currency" />
                <MetricRow label="COGS % of Revenue" quarters={quarterlyComparison.quarters} field="cogsPercent" format="marginPercent" />
                <MetricRow label="R&D Expense" quarters={quarterlyComparison.quarters} field="rdExpense" format="currency" />
                <MetricRow label="SG&A Expense" quarters={quarterlyComparison.quarters} field="sgaExpense" format="currency" />
                <MetricRow label="Total Operating Expenses" quarters={quarterlyComparison.quarters} field="totalOpex" format="currency" />

                {/* Section C: Cash Flow */}
                <tr className="bg-cyan-500/10">
                  <td colSpan={5} className="py-2 px-2 text-cyan-400 font-semibold text-xs uppercase tracking-wide">
                    C. Cash Flow
                  </td>
                </tr>
                <MetricRow label="Operating Cash Flow" quarters={quarterlyComparison.quarters} field="operatingCashFlow" format="currency" />
                <MetricRow label="Free Cash Flow" quarters={quarterlyComparison.quarters} field="freeCashFlow" format="currency" />
                <MetricRow label="CapEx" quarters={quarterlyComparison.quarters} field="capex" format="currency" />

                {/* Section D: Balance Sheet & Liquidity */}
                <tr className="bg-blue-500/10">
                  <td colSpan={5} className="py-2 px-2 text-blue-400 font-semibold text-xs uppercase tracking-wide">
                    D. Balance Sheet & Liquidity
                  </td>
                </tr>
                <MetricRow label="Cash & Equivalents" quarters={quarterlyComparison.quarters} field="cash" format="currency" />
                <MetricRow label="Total Debt" quarters={quarterlyComparison.quarters} field="totalDebt" format="currency" />
                <MetricRow label="Short-Term Debt" quarters={quarterlyComparison.quarters} field="shortTermDebt" format="currency" />
                <MetricRow label="Long-Term Debt" quarters={quarterlyComparison.quarters} field="longTermDebt" format="currency" />
                <MetricRow label="Net Debt" quarters={quarterlyComparison.quarters} field="netDebt" format="currency" />
                <MetricRow label="Interest Expense" quarters={quarterlyComparison.quarters} field="interestExpense" format="currency" />

                {/* Section E: Efficiency & Dilution */}
                <tr className="bg-pink-500/10">
                  <td colSpan={5} className="py-2 px-2 text-pink-400 font-semibold text-xs uppercase tracking-wide">
                    E. Efficiency & Dilution
                  </td>
                </tr>
                <MetricRow label="Stock-Based Comp" quarters={quarterlyComparison.quarters} field="stockBasedComp" format="currency" />
                <MetricRow label="SBC % of Revenue" quarters={quarterlyComparison.quarters} field="sbcPercent" format="marginPercent" />
                <MetricRow label="Headcount" quarters={quarterlyComparison.quarters} field="headcount" format="number" />
                <MetricRow label="Revenue per Employee" quarters={quarterlyComparison.quarters} field="revenuePerEmployee" format="currency" />

                {/* Section F: Leading Indicators */}
                <tr className="bg-violet-500/10">
                  <td colSpan={5} className="py-2 px-2 text-violet-400 font-semibold text-xs uppercase tracking-wide">
                    F. Leading Indicators
                  </td>
                </tr>
                <MetricRow label="Deferred Revenue" quarters={quarterlyComparison.quarters} field="deferredRevenue" format="currency" />
              </tbody>
            </table>
          </div>
        )}

        {/* 4Q Comparison - No data fallback */}
        {revenueView === '4q' && (!quarterlyComparison?.quarters || quarterlyComparison.quarters.length === 0) && (
          <div className="text-center text-slate-500 py-8">
            <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No quarterly comparison data available</p>
          </div>
        )}
      </div>

      {/* Market Feed - Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - News */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Newspaper className="w-5 h-5 text-blue-500" />
            Latest News
          </h2>

          {marketFeedLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : marketFeed?.news?.length > 0 ? (
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
              {marketFeed.news.map((item, i) => (
                <a
                  key={i}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block bg-slate-700/30 rounded-lg p-3 hover:bg-slate-700/50 transition-colors"
                >
                  <div className="flex gap-3">
                    {item.image && (
                      <img
                        src={item.image}
                        alt=""
                        className="w-16 h-16 rounded object-cover flex-shrink-0"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm line-clamp-2 mb-1">{item.title}</h3>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>{item.publisher}</span>
                        <span>•</span>
                        <span>{new Date(item.publishedDate).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <div className="text-center text-slate-500 py-8">
              <Newspaper className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No recent news available</p>
            </div>
          )}
        </div>

        {/* Right Column - Senate & Insider Trades */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Landmark className="w-5 h-5 text-purple-500" />
            Political & Insider Trading
          </h2>

          {marketFeedLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
            </div>
          ) : (
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
              {/* Senate Trades */}
              {marketFeed?.senateTrades?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-1">
                    <Landmark className="w-3 h-3" /> Senate Trades
                  </h3>
                  <div className="space-y-2">
                    {marketFeed.senateTrades.slice(0, 5).map((trade, i) => (
                      <a
                        key={i}
                        href={trade.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block bg-slate-700/30 rounded-lg p-3 hover:bg-slate-700/50 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">
                            {trade.firstName} {trade.lastName}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            trade.type === 'Sale' || trade.type === 'Sell'
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-emerald-500/20 text-emerald-400'
                          }`}>
                            {trade.type}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400">
                          <span>{trade.district}</span>
                          <span className="mx-1">•</span>
                          <span>{trade.amount}</span>
                          <span className="mx-1">•</span>
                          <span>{trade.transactionDate}</span>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Insider Trades */}
              {marketFeed?.insiderTrades?.length > 0 && (
                <div className={marketFeed?.senateTrades?.length > 0 ? 'mt-4 pt-4 border-t border-slate-700' : ''}>
                  <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-1">
                    <UserCheck className="w-3 h-3" /> Insider Trades
                  </h3>
                  <div className="space-y-2">
                    {marketFeed.insiderTrades.slice(0, 5).map((trade, i) => (
                      <a
                        key={i}
                        href={trade.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block bg-slate-700/30 rounded-lg p-3 hover:bg-slate-700/50 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{trade.reportingName}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            trade.transactionType?.includes('Sale') || trade.transactionType?.startsWith('S-')
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-emerald-500/20 text-emerald-400'
                          }`}>
                            {trade.transactionType?.includes('Sale') || trade.transactionType?.startsWith('S-') ? 'Sale' :
                             trade.transactionType?.includes('Purchase') || trade.transactionType?.startsWith('P-') ? 'Purchase' :
                             trade.transactionType?.includes('Award') || trade.transactionType?.startsWith('A-') ? 'Award' :
                             trade.transactionType?.startsWith('M-') ? 'Exercise' :
                             trade.formType === '3' ? 'Initial' : 'Award'}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400">
                          {trade.securitiesTransacted > 0 && (
                            <>
                              <span>{trade.securitiesTransacted.toLocaleString()} shares</span>
                              <span className="mx-1">•</span>
                            </>
                          )}
                          {trade.price > 0 && (
                            <>
                              <span>${trade.price.toFixed(2)}</span>
                              <span className="mx-1">•</span>
                            </>
                          )}
                          <span>{trade.filingDate}</span>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {(!marketFeed?.senateTrades?.length && !marketFeed?.insiderTrades?.length) && (
                <div className="text-center text-slate-500 py-8">
                  <Landmark className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No recent trading activity</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Company Description */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-slate-500" />
          About {profile.name}
        </h2>
        <p className="text-slate-400 text-sm leading-relaxed line-clamp-4">
          {profile.description}
        </p>
        {profile.website && (
          <a
            href={profile.website}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-3 text-blue-400 hover:text-blue-300 text-sm"
          >
            Visit Website <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </div>
  )
}
