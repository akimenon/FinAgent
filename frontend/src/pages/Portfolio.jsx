import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Briefcase,
  TrendingUp,
  TrendingDown,
  Loader2,
  Trash2,
  RefreshCw,
  AlertCircle,
  Plus,
  X,
  Edit2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ArrowUpDown,
  DollarSign,
  PieChart,
  Activity,
  Lock,
  Wallet,
  Filter,
  Banknote,
  Camera,
  Check,
  Target,
  Eye,
  EyeOff,
  Calendar,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
} from 'recharts'
import { portfolioApi } from '../services/api'
import TickerSearch from '../components/search/TickerSearch'

// Miscellaneous investment category presets
const MISC_CATEGORIES = [
  '529 Plan',
  'Angel Investment',
  'Real Estate',
  'Private Equity',
  'Collectibles',
  'Other',
]

// Account presets for dropdown
const ACCOUNT_PRESETS = [
  'Fidelity',
  'Charles Schwab',
  'Robinhood',
  'Coinbase',
  'Coinbase Wallet',
  'Vanguard',
  'TD Ameritrade',
  'E*Trade',
  'Webull',
  'Interactive Brokers',
  'Kraken',
  'Ledger',
  'Wealthfront',
  'Chase',
  'Wells Fargo',
  'Bank of America',
]

// Asset type display config
const ASSET_TYPE_CONFIG = {
  stock: { label: 'Stocks', icon: TrendingUp, color: 'blue', activeChip: 'bg-blue-500/20 border-blue-500/50 text-blue-300' },
  etf: { label: 'ETFs', icon: PieChart, color: 'purple', activeChip: 'bg-purple-500/20 border-purple-500/50 text-purple-300' },
  crypto: { label: 'Crypto', icon: DollarSign, color: 'orange', activeChip: 'bg-orange-500/20 border-orange-500/50 text-orange-300' },
  custom: { label: 'Miscellaneous', icon: Wallet, color: 'teal', activeChip: 'bg-teal-500/20 border-teal-500/50 text-teal-300' },
  cash: { label: 'Cash', icon: Banknote, color: 'emerald', activeChip: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300' },
  option: { label: 'Options', icon: Target, color: 'rose', activeChip: 'bg-rose-500/20 border-rose-500/50 text-rose-300' },
}

export default function Portfolio() {
  const navigate = useNavigate()

  // PIN state — always start locked, verify with backend on mount
  const [unlocked, setUnlocked] = useState(false)
  const [pinRequired, setPinRequired] = useState(null) // null = checking, true/false = known
  const [pin, setPin] = useState(['', '', '', ''])
  const [pinError, setPinError] = useState('')
  const [pinLoading, setPinLoading] = useState(false)
  const pinRefs = [useRef(null), useRef(null), useRef(null), useRef(null)]

  const [portfolio, setPortfolio] = useState({ holdings: [], summary: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [snapshotting, setSnapshotting] = useState(false) // 'idle' | 'loading' | 'done'
  const [snapshotResult, setSnapshotResult] = useState(null)
  const [removingId, setRemovingId] = useState(null)
  const [collapsedSections, setCollapsedSections] = useState(new Set())
  const [sectionFilters, setSectionFilters] = useState({}) // { [assetType]: { type: 'account'|'ticker', value: string } }
  const [sectionSort, setSectionSort] = useState({}) // { [assetType]: { key: string, direction: 'asc'|'desc' } }
  const [showValues, setShowValues] = useState(() => sessionStorage.getItem('portfolio_showValues') === 'true')

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingHolding, setEditingHolding] = useState(null)
  const [addType, setAddType] = useState('holding') // 'holding' or 'cash'
  const [formData, setFormData] = useState({
    ticker: '',
    tickerName: '',
    quantity: '',
    costBasis: '',
    accountName: '',
    customAccount: '',
    optionType: 'call',
    strikePrice: '',
    expirationDate: '',
    underlyingTicker: '',
    optionPrice: '',
  })
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Performance state
  const [performance, setPerformance] = useState(null)
  const [selectedPeriod, setSelectedPeriod] = useState('1W')
  const [showAssetBreakdown, setShowAssetBreakdown] = useState(false)
  const [showPerformance, setShowPerformance] = useState(true)
  const [pieModalType, setPieModalType] = useState(null)

  // On mount: always check backend for PIN status
  useEffect(() => {
    portfolioApi.verifyPin('').then((res) => {
      if (!res.data.pinSet) {
        // No PIN configured — auto-unlock
        setUnlocked(true)
        setPinRequired(false)
      } else if (sessionStorage.getItem('portfolio_unlocked') === 'true') {
        // PIN exists but already verified this session
        setUnlocked(true)
        setPinRequired(true)
      } else {
        // PIN exists and not yet verified — show gate
        setPinRequired(true)
      }
    }).catch(() => {
      setPinRequired(true)
    })
  }, [])

  // Load data once unlocked
  useEffect(() => {
    if (unlocked) {
      loadPortfolio()
      loadPerformance()
    }
  }, [unlocked])

  const handlePinChange = useCallback((index, value) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) return

    const next = [...pin]
    next[index] = value
    setPin(next)
    setPinError('')

    if (value && index < 3) {
      // Auto-advance to next input
      pinRefs[index + 1].current?.focus()
    } else if (value && index === 3) {
      // Last digit entered — auto-submit
      const fullPin = next.join('')
      if (fullPin.length === 4) {
        setPinLoading(true)
        portfolioApi.verifyPin(fullPin).then((res) => {
          if (res.data.verified) {
            setUnlocked(true)
            sessionStorage.setItem('portfolio_unlocked', 'true')
          } else {
            setPinError('Incorrect PIN')
            setPin(['', '', '', ''])
            pinRefs[0].current?.focus()
          }
        }).catch(() => {
          setPinError('Failed to verify PIN')
        }).finally(() => {
          setPinLoading(false)
        })
      }
    }
  }, [pin])

  const handlePinKeyDown = useCallback((index, e) => {
    // Backspace: clear current and move back
    if (e.key === 'Backspace' && !pin[index] && index > 0) {
      pinRefs[index - 1].current?.focus()
    }
  }, [pin])

  const handlePinSubmit = useCallback(async (e) => {
    e?.preventDefault()
    const fullPin = pin.join('')
    if (fullPin.length !== 4) {
      setPinError('Please enter a 4-digit PIN')
      return
    }

    setPinLoading(true)
    setPinError('')
    try {
      const response = await portfolioApi.verifyPin(fullPin)
      if (response.data.verified) {
        setUnlocked(true)
        sessionStorage.setItem('portfolio_unlocked', 'true')
      } else {
        setPinError('Incorrect PIN')
        setPin(['', '', '', ''])
        pinRefs[0].current?.focus()
      }
    } catch {
      setPinError('Failed to verify PIN')
    } finally {
      setPinLoading(false)
    }
  }, [pin])

  const loadPortfolio = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await portfolioApi.getAll()
      setPortfolio(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load portfolio')
    } finally {
      setLoading(false)
    }
  }

  const loadPerformance = async () => {
    try {
      const response = await portfolioApi.getPerformance()
      setPerformance(response.data)
    } catch (err) {
      console.error('Failed to load performance:', err)
    }
  }

  // Re-fetch portfolio data without showing the full-page loading spinner
  const refreshPortfolio = async (forceRefresh = false) => {
    try {
      const response = await portfolioApi.getAll(forceRefresh)
      setPortfolio(response.data)
    } catch (err) {
      console.error('Failed to refresh portfolio:', err)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await Promise.all([refreshPortfolio(true), loadPerformance()])
    } catch (err) {
      console.error('Failed to refresh portfolio:', err)
    } finally {
      setRefreshing(false)
    }
  }

  const handleSnapshot = async () => {
    setSnapshotting(true)
    setSnapshotResult(null)
    try {
      const response = await portfolioApi.takeSnapshot(true)
      setSnapshotResult(response.data)
      // Refresh performance data since we just took a new snapshot
      await loadPerformance()
      // Brief success indicator
      setTimeout(() => {
        setSnapshotting(false)
        setSnapshotResult(null)
      }, 2000)
    } catch (err) {
      console.error('Failed to take snapshot:', err)
      setSnapshotting(false)
    }
  }

  const handleRemove = async (holdingId, e) => {
    e.stopPropagation()
    setRemovingId(holdingId)
    try {
      await portfolioApi.remove(holdingId)
      await refreshPortfolio()
    } catch (err) {
      console.error('Failed to remove holding:', err)
    } finally {
      setRemovingId(null)
    }
  }

  const toggleSection = (assetType) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev)
      next.has(assetType) ? next.delete(assetType) : next.add(assetType)
      return next
    })
  }

  const handleSort = (assetType, key) => {
    setSectionSort((prev) => {
      const current = prev[assetType]
      if (current?.key === key) {
        // Cycle: asc → desc → clear
        if (current.direction === 'asc') return { ...prev, [assetType]: { key, direction: 'desc' } }
        const next = { ...prev }
        delete next[assetType]
        return next
      }
      return { ...prev, [assetType]: { key, direction: 'asc' } }
    })
  }

  const sortHoldings = (holdings, assetType) => {
    const sort = sectionSort[assetType]
    if (!sort) return holdings
    const { key, direction } = sort
    const sorted = [...holdings].sort((a, b) => {
      let aVal = a[key]
      let bVal = b[key]
      // Handle nulls
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1
      // String comparison for text fields
      if (typeof aVal === 'string') return aVal.localeCompare(bVal)
      return aVal - bVal
    })
    return direction === 'desc' ? sorted.reverse() : sorted
  }

  const SortIcon = ({ assetType, column }) => {
    const sort = sectionSort[assetType]
    if (sort?.key !== column) return <ArrowUpDown className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
    return sort.direction === 'asc'
      ? <ChevronUp className="w-3 h-3 text-blue-400" />
      : <ChevronDown className="w-3 h-3 text-blue-400" />
  }

  // Form handlers
  const openAddModal = () => {
    setFormData({
      ticker: '',
      tickerName: '',
      quantity: '',
      costBasis: '',
      accountName: '',
      customAccount: '',
      optionType: 'call',
      strikePrice: '',
      expirationDate: '',
      underlyingTicker: '',
      optionPrice: '',
    })
    setFormError(null)
    setEditingHolding(null)
    setShowAddModal(true)
  }

  const openEditModal = (holding, e) => {
    e.stopPropagation()
    setFormData({
      ticker: holding.ticker,
      tickerName: holding.name || holding.ticker,
      quantity: holding.quantity.toString(),
      costBasis: holding.costBasis.toString(),
      accountName: ACCOUNT_PRESETS.includes(holding.accountName)
        ? holding.accountName
        : 'Other',
      customAccount: ACCOUNT_PRESETS.includes(holding.accountName)
        ? ''
        : holding.accountName,
      optionType: holding.optionType || 'call',
      strikePrice: holding.strikePrice?.toString() || '',
      expirationDate: holding.expirationDate || '',
      underlyingTicker: holding.underlyingTicker || '',
      optionPrice: holding.optionPrice?.toString() || '',
    })
    setFormError(null)
    setEditingHolding(holding)
    setShowAddModal(true)
  }

  const closeModal = () => {
    setShowAddModal(false)
    setEditingHolding(null)
    setFormError(null)
    setAddType('holding')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError(null)
    setSubmitting(true)

    const accountName =
      formData.accountName === 'Other'
        ? formData.customAccount
        : formData.accountName

    const isCash = addType === 'cash' && !editingHolding
    const isCashEdit = editingHolding?.assetType === 'cash'
    const isMisc = addType === 'misc' && !editingHolding
    const isMiscEdit = editingHolding?.assetType === 'custom'
    const isOption = addType === 'option' && !editingHolding
    const isOptionEdit = editingHolding?.assetType === 'option'

    if (isCash || isCashEdit) {
      if (!formData.costBasis || !accountName) {
        setFormError('Please fill in all fields')
        setSubmitting(false)
        return
      }
    } else if (isMisc || isMiscEdit) {
      const miscTicker = formData.ticker === 'Other' ? formData.tickerName : formData.ticker
      if (!miscTicker || !formData.costBasis || !accountName) {
        setFormError('Please fill in all fields')
        setSubmitting(false)
        return
      }
    } else if (isOption || isOptionEdit) {
      if (!formData.underlyingTicker || !formData.strikePrice || !formData.expirationDate || !formData.quantity || !formData.costBasis || !accountName) {
        setFormError('Please fill in all fields')
        setSubmitting(false)
        return
      }
    } else if (!formData.ticker || !formData.quantity || !formData.costBasis || !accountName) {
      setFormError('Please fill in all fields')
      setSubmitting(false)
      return
    }

    try {
      if (editingHolding) {
        // Update existing
        const updateData = {
          quantity: (isCashEdit || isMiscEdit) ? 1 : parseFloat(formData.quantity),
          costBasis: parseFloat(formData.costBasis),
          accountName,
        }
        if (isOptionEdit) {
          updateData.optionType = formData.optionType
          updateData.strikePrice = parseFloat(formData.strikePrice)
          updateData.expirationDate = formData.expirationDate
          updateData.underlyingTicker = formData.underlyingTicker.toUpperCase()
          if (formData.optionPrice) updateData.optionPrice = parseFloat(formData.optionPrice)
        }
        await portfolioApi.update(editingHolding.id, updateData)
      } else if (isCash) {
        // Add cash
        await portfolioApi.add({
          ticker: 'CASH',
          quantity: 1,
          costBasis: parseFloat(formData.costBasis),
          accountName,
          assetType: 'cash',
        })
      } else if (isMisc) {
        // Add miscellaneous investment
        const miscTicker = formData.ticker === 'Other' ? formData.tickerName : formData.ticker
        await portfolioApi.add({
          ticker: miscTicker.toUpperCase(),
          quantity: 1,
          costBasis: parseFloat(formData.costBasis),
          accountName,
          assetType: 'custom',
        })
      } else if (isOption) {
        // Add option
        const underlying = formData.underlyingTicker.toUpperCase()
        const strike = parseFloat(formData.strikePrice)
        const typeLabel = formData.optionType === 'call' ? 'C' : 'P'
        const syntheticTicker = `${underlying} ${Math.round(strike)}${typeLabel}`
        const addPayload = {
          ticker: syntheticTicker,
          quantity: parseFloat(formData.quantity),
          costBasis: parseFloat(formData.costBasis),
          accountName,
          assetType: 'option',
          optionType: formData.optionType,
          strikePrice: strike,
          expirationDate: formData.expirationDate,
          underlyingTicker: underlying,
        }
        if (formData.optionPrice) addPayload.optionPrice = parseFloat(formData.optionPrice)
        await portfolioApi.add(addPayload)
      } else {
        // Add new holding
        await portfolioApi.add({
          ticker: formData.ticker.toUpperCase(),
          quantity: parseFloat(formData.quantity),
          costBasis: parseFloat(formData.costBasis),
          accountName,
        })
      }
      closeModal()
      await refreshPortfolio()
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to save holding')
    } finally {
      setSubmitting(false)
    }
  }

  // Formatting helpers
  const MASKED_VALUE = '$••••'

  const formatCurrency = (num) => {
    if (num === null || num === undefined) return 'N/A'
    if (!showValues) return MASKED_VALUE
    const absNum = Math.abs(num)
    if (absNum >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
    if (absNum >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
    if (absNum >= 1e4) return `$${(num / 1e3).toFixed(2)}K`
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const formatDollar = (num, opts = {}) => {
    if (num == null) return opts.fallback || 'N/A'
    if (!showValues) return MASKED_VALUE
    const { minimumFractionDigits = 2, maximumFractionDigits = 2 } = opts
    return `$${num.toLocaleString(undefined, { minimumFractionDigits, maximumFractionDigits })}`
  }

  const formatPercent = (num) => {
    if (num === null || num === undefined) return 'N/A'
    return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`
  }

  const getGainLossColor = (num) => {
    if (num === null || num === undefined) return 'text-slate-400'
    return num >= 0 ? 'text-emerald-400' : 'text-red-400'
  }

  // Group holdings by asset type
  const groupedHoldings = useMemo(() => {
    const groups = { stock: [], etf: [], crypto: [], custom: [], cash: [], option: [] }
    portfolio.holdings.forEach((holding) => {
      const type = holding.assetType || 'stock'
      if (groups[type]) {
        groups[type].push(holding)
      }
    })
    return groups
  }, [portfolio.holdings])

  // PIN gate - still checking if PIN is required
  if (!unlocked && pinRequired === null) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500 mb-4" />
        <p className="text-slate-400">Loading...</p>
      </div>
    )
  }

  // PIN gate - PIN is required, show entry screen
  if (!unlocked && pinRequired) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 w-full max-w-sm text-center">
          <Lock className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Portfolio Locked</h2>
          <p className="text-slate-400 text-sm mb-6">
            Enter your 4-digit PIN to access your portfolio.
          </p>
          <form onSubmit={handlePinSubmit}>
            <div className="flex justify-center gap-3 mb-4">
              {pin.map((digit, i) => (
                <input
                  key={i}
                  ref={pinRefs[i]}
                  type="password"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handlePinChange(i, e.target.value)}
                  onKeyDown={(e) => handlePinKeyDown(i, e)}
                  className="w-12 h-14 text-center text-2xl font-bold bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500 transition-colors"
                  autoFocus={i === 0}
                />
              ))}
            </div>
            {pinError && (
              <p className="text-red-400 text-sm mb-4">{pinError}</p>
            )}
            <button
              type="submit"
              disabled={pinLoading || pin.join('').length !== 4}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {pinLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Unlock
            </button>
          </form>
        </div>
      </div>
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500 mb-4" />
        <p className="text-slate-400">Loading portfolio...</p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold mb-2">Unable to Load Portfolio</h2>
        <p className="text-slate-400 mb-4">{error}</p>
        <button
          onClick={loadPortfolio}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  const { summary } = portfolio

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Briefcase className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-2xl font-bold">Portfolio</h1>
              <p className="text-slate-400 text-sm">
                {portfolio.holdings.length}{' '}
                {portfolio.holdings.length === 1 ? 'holding' : 'holdings'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowValues((v) => { const next = !v; sessionStorage.setItem('portfolio_showValues', next); return next })}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors border ${
                showValues
                  ? 'bg-emerald-600/20 border-emerald-500/50 text-emerald-400 hover:bg-emerald-600/30'
                  : 'bg-slate-700 border-slate-600 text-slate-400 hover:bg-slate-600'
              }`}
              title={showValues ? 'Hide $ values' : 'Show $ values'}
            >
              {showValues ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              <span className="hidden sm:inline text-sm">{showValues ? 'Hide $' : 'Show $'}</span>
            </button>
            <button
              onClick={openAddModal}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Add Holding</span>
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
            <button
              onClick={handleSnapshot}
              disabled={snapshotting}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                snapshotResult
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 hover:bg-slate-600'
              } ${snapshotting && !snapshotResult ? 'opacity-50 cursor-wait' : ''}`}
              title="Take portfolio snapshot"
            >
              {snapshotting && !snapshotResult ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : snapshotResult ? (
                <Check className="w-4 h-4" />
              ) : (
                <Camera className="w-4 h-4" />
              )}
              <span className="hidden sm:inline">
                {snapshotResult ? 'Saved' : 'Snapshot'}
              </span>
            </button>
          </div>
        </div>

        {/* Asset Type Breakdown Pills — sorted by allocation % descending */}
        {summary && summary.totalValue > 0 && (() => {
          const pillConfig = [
            { key: 'stock',  label: 'Stocks',  Icon: TrendingUp,  pill: 'bg-blue-500/10 border-blue-500/30',     text: 'text-blue-400' },
            { key: 'etf',    label: 'ETFs',    Icon: PieChart,    pill: 'bg-purple-500/10 border-purple-500/30', text: 'text-purple-400' },
            { key: 'crypto', label: 'Crypto',  Icon: DollarSign,  pill: 'bg-orange-500/10 border-orange-500/30', text: 'text-orange-400' },
            { key: 'custom', label: 'Misc',    Icon: Wallet,      pill: 'bg-teal-500/10 border-teal-500/30',     text: 'text-teal-400' },
            { key: 'cash',   label: 'Cash',    Icon: Banknote,    pill: 'bg-emerald-500/10 border-emerald-500/30', text: 'text-emerald-400' },
            { key: 'option', label: 'Options', Icon: Target,      pill: 'bg-rose-500/10 border-rose-500/30',     text: 'text-rose-400' },
          ]
          const sorted = pillConfig
            .filter(p => (summary.byAssetType?.[p.key]?.value || 0) > 0)
            .sort((a, b) => (summary.byAssetType[b.key].value || 0) - (summary.byAssetType[a.key].value || 0))
          return (
            <div className="flex flex-wrap items-center gap-2">
              {sorted.map(({ key, label, Icon, pill, text }) => (
                <div key={key} className={`flex items-center gap-2 px-3 py-1.5 border rounded-full ${pill}`}>
                  <Icon className={`w-4 h-4 ${text}`} />
                  <span className={`text-sm font-medium ${text}`}>{label}</span>
                  <span className="text-sm text-slate-300">
                    {formatCurrency(summary.byAssetType[key].value)}
                  </span>
                  <span className="text-xs text-slate-400 bg-slate-700/50 px-1.5 py-0.5 rounded">
                    {((summary.byAssetType[key].value / summary.totalValue) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )
        })()}
      </div>

      {/* Summary Cards */}
      {summary && portfolio.holdings.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="text-sm text-slate-400 mb-1">Total Value</div>
            <div className="text-2xl font-bold">{formatCurrency(summary.totalValue)}</div>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="text-sm text-slate-400 mb-1">Total Cost</div>
            <div className="text-2xl font-bold">{formatCurrency(summary.totalCost)}</div>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="text-sm text-slate-400 mb-1">Gain/Loss</div>
            <div className={`text-2xl font-bold ${getGainLossColor(summary.totalGainLoss)}`}>
              {formatCurrency(summary.totalGainLoss)}
            </div>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="text-sm text-slate-400 mb-1">Return</div>
            <div className={`text-2xl font-bold flex items-center gap-2 ${getGainLossColor(summary.totalGainLossPercent)}`}>
              {summary.totalGainLossPercent >= 0 ? (
                <TrendingUp className="w-5 h-5" />
              ) : (
                <TrendingDown className="w-5 h-5" />
              )}
              {formatPercent(summary.totalGainLossPercent)}
            </div>
          </div>
        </div>
      )}

      {/* Weekly Performance Section */}
      {portfolio.holdings.length > 0 && performance?.periods && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div
            className="px-6 py-4 border-b border-slate-700 cursor-pointer hover:bg-slate-700/30 transition-colors"
            onClick={() => setShowPerformance((prev) => !prev)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {showPerformance ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
                <Activity className="w-5 h-5 text-blue-500" />
                <h2 className="text-lg font-semibold">Performance</h2>
              </div>
              {showPerformance && (
                <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1" onClick={(e) => e.stopPropagation()}>
                  {['1W', '1M', '3M', 'YTD'].map((period) => (
                    <button
                      key={period}
                      onClick={() => setSelectedPeriod(period)}
                      className={`px-3 py-1 text-sm rounded-md transition-colors ${
                        selectedPeriod === period
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {showPerformance && (() => {
            const periodData = performance.periods[selectedPeriod]
            if (!periodData) {
              return (
                <div className="px-6 py-8 text-center text-slate-400">
                  <p>No data for this period yet.</p>
                  <p className="text-sm mt-1">
                    Snapshots are taken daily when you open the app. Check back after a few days.
                  </p>
                </div>
              )
            }

            return (
              <div className="p-6 space-y-5">
                {/* Total Portfolio Change */}
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-slate-400">
                      Portfolio Change ({periodData.fromDate} - {periodData.toDate})
                    </div>
                    <div className={`text-2xl font-bold flex items-center gap-2 mt-1 ${getGainLossColor(periodData.change)}`}>
                      {periodData.change >= 0 ? (
                        <TrendingUp className="w-6 h-6" />
                      ) : (
                        <TrendingDown className="w-6 h-6" />
                      )}
                      {formatCurrency(periodData.change)}
                      <span className="text-lg">
                        ({formatPercent(periodData.changePercent)})
                      </span>
                    </div>
                  </div>
                  <div className="text-right text-sm text-slate-400">
                    <div>{formatCurrency(periodData.previousValue)}</div>
                    <div className="text-slate-500">to</div>
                    <div>{formatCurrency(periodData.currentValue)}</div>
                  </div>
                </div>

                {/* Portfolio Total Value Chart */}
                {performance.history && performance.history.length >= 2 && (() => {
                  const chartData = performance.history.map((s) => ({
                    date: s.date,
                    total: s.totalValue,
                    stocks: s.byAssetType?.stock?.value || 0,
                    etfs: s.byAssetType?.etf?.value || 0,
                    crypto: s.byAssetType?.crypto?.value || 0,
                    misc: s.byAssetType?.custom?.value || 0,
                    cash: s.byAssetType?.cash?.value || 0,
                    options: s.byAssetType?.option?.value || 0,
                  }))

                  const valueChange = chartData[chartData.length - 1].total - chartData[0].total
                  const isPositive = valueChange >= 0

                  const formatChartDate = (dateStr) => {
                    const d = new Date(dateStr + 'T00:00:00')
                    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                  }

                  const ChartTooltip = ({ active, payload, label }) => {
                    if (!active || !payload?.length) return null
                    return (
                      <div className="bg-slate-900 border border-slate-600 rounded-lg p-3 shadow-lg text-sm">
                        <p className="text-slate-400 text-xs mb-2">{formatChartDate(label)}</p>
                        {payload.map((entry) => (
                          <div key={entry.name} className="flex items-center justify-between gap-4">
                            <span style={{ color: entry.color }}>{entry.name}</span>
                            <span className="text-white font-medium">{formatCurrency(entry.value)}</span>
                          </div>
                        ))}
                      </div>
                    )
                  }

                  const hasBreakdownData = chartData.some(
                    (d) => d.stocks > 0 || d.etfs > 0 || d.crypto > 0 || d.cash > 0
                  )

                  return (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {/* Total Value Chart */}
                      <div>
                        <div className="text-sm text-slate-400 mb-2">Total Portfolio Value</div>
                        <div className="h-56">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                              <defs>
                                <linearGradient id="totalGradient" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={isPositive ? '#10b981' : '#ef4444'} stopOpacity={0.3} />
                                  <stop offset="95%" stopColor={isPositive ? '#10b981' : '#ef4444'} stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                              <XAxis
                                dataKey="date"
                                tickFormatter={formatChartDate}
                                stroke="#64748b"
                                tick={{ fill: '#64748b', fontSize: 11 }}
                                tickLine={false}
                                axisLine={false}
                                interval="preserveStartEnd"
                              />
                              <YAxis
                                domain={['auto', 'auto']}
                                stroke="#64748b"
                                tick={{ fill: '#64748b', fontSize: 11 }}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(val) => formatCurrency(val)}
                                width={70}
                              />
                              <Tooltip content={<ChartTooltip />} />
                              <Area
                                type="monotone"
                                dataKey="total"
                                name="Total"
                                stroke={isPositive ? '#10b981' : '#ef4444'}
                                strokeWidth={2.5}
                                fill="url(#totalGradient)"
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Asset Type Breakdown Chart */}
                      {hasBreakdownData && (
                        <div>
                          <div className="text-sm text-slate-400 mb-2">Value by Asset Type</div>
                          <div className="h-56">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                <defs>
                                  <linearGradient id="stockGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                  </linearGradient>
                                  <linearGradient id="etfGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.15} />
                                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                                  </linearGradient>
                                  <linearGradient id="cryptoGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#f97316" stopOpacity={0.15} />
                                    <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                                  </linearGradient>
                                  <linearGradient id="cashGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                <XAxis
                                  dataKey="date"
                                  tickFormatter={formatChartDate}
                                  stroke="#64748b"
                                  tick={{ fill: '#64748b', fontSize: 11 }}
                                  tickLine={false}
                                  axisLine={false}
                                  interval="preserveStartEnd"
                                />
                                <YAxis
                                  domain={['auto', 'auto']}
                                  stroke="#64748b"
                                  tick={{ fill: '#64748b', fontSize: 11 }}
                                  tickLine={false}
                                  axisLine={false}
                                  tickFormatter={(val) => formatCurrency(val)}
                                  width={70}
                                />
                                <Tooltip content={<ChartTooltip />} />
                                <Legend
                                  iconType="line"
                                  wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
                                />
                                <Area
                                  type="monotone"
                                  dataKey="stocks"
                                  name="Stocks"
                                  stroke="#3b82f6"
                                  strokeWidth={1.5}
                                  fill="url(#stockGradient)"
                                  strokeDasharray="4 2"
                                />
                                <Area
                                  type="monotone"
                                  dataKey="etfs"
                                  name="ETFs"
                                  stroke="#a855f7"
                                  strokeWidth={1.5}
                                  fill="url(#etfGradient)"
                                  strokeDasharray="4 2"
                                />
                                <Area
                                  type="monotone"
                                  dataKey="crypto"
                                  name="Crypto"
                                  stroke="#f97316"
                                  strokeWidth={1.5}
                                  fill="url(#cryptoGradient)"
                                  strokeDasharray="4 2"
                                />
                                <Area
                                  type="monotone"
                                  dataKey="cash"
                                  name="Cash"
                                  stroke="#10b981"
                                  strokeWidth={1.5}
                                  fill="url(#cashGradient)"
                                  strokeDasharray="4 2"
                                />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })()}

                {/* Asset Type Breakdown */}
                <div>
                  <div className="text-sm text-slate-400 mb-3">Change by Asset Type</div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {(() => {
                      const PIE_COLORS = ['#3b82f6', '#a855f7', '#f97316', '#14b8a6', '#10b981', '#f43f5e', '#eab308', '#6366f1', '#ec4899', '#06b6d4']
                      return [
                        { key: 'stock', label: 'Stocks', color: 'blue', Icon: TrendingUp },
                        { key: 'etf', label: 'ETFs', color: 'purple', Icon: PieChart },
                        { key: 'crypto', label: 'Crypto', color: 'orange', Icon: DollarSign },
                        { key: 'custom', label: 'Miscellaneous', color: 'teal', Icon: Wallet },
                        { key: 'cash', label: 'Cash', color: 'emerald', Icon: Banknote },
                        { key: 'option', label: 'Options', color: 'rose', Icon: Target },
                      ].map(({ key, label, color, Icon }) => {
                      const typeData = periodData.byAssetType?.[key]
                      if (!typeData || (typeData.previousValue === 0 && typeData.currentValue === 0)) {
                        return null
                      }

                      const holdings = groupedHoldings[key] || []
                      const useName = key === 'cash' || key === 'custom'
                      const pieData = Object.values(holdings
                        .filter((h) => (h.currentValue || h.quantity * h.costBasis) > 0)
                        .reduce((acc, h) => {
                          const name = useName ? (h.accountName || h.ticker) : h.ticker
                          const value = h.currentValue || h.quantity * h.costBasis
                          acc[name] = acc[name] ? { name, value: acc[name].value + value } : { name, value }
                          return acc
                        }, {}))
                        .sort((a, b) => b.value - a.value)
                      const pieTotal = pieData.reduce((sum, d) => sum + d.value, 0)

                      return (
                        <div
                          key={key}
                          className={`bg-slate-900/50 rounded-lg p-4 border border-slate-700/50 ${pieData.length > 0 ? 'cursor-pointer hover:border-slate-600 transition-colors' : ''}`}
                          onClick={pieData.length > 0 ? () => setShowAssetBreakdown((prev) => !prev) : undefined}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <Icon className={`w-4 h-4 text-${color}-400`} />
                            <span className={`text-sm font-medium text-${color}-400`}>
                              {label}
                            </span>
                            {pieData.length > 0 && (
                              <span
                                className={`ml-auto text-xs px-2 py-0.5 rounded-full border transition-all ${
                                  showAssetBreakdown
                                    ? 'bg-blue-500/15 border-blue-500/40 text-blue-300'
                                    : 'bg-transparent border-slate-600 text-slate-400'
                                }`}
                              >
                                {showAssetBreakdown ? 'Hide' : 'Breakdown'}
                              </span>
                            )}
                          </div>
                          <div className={`text-xl font-bold ${getGainLossColor(typeData.change)}`}>
                            {formatPercent(typeData.changePercent)}
                          </div>
                          <div className={`text-sm ${getGainLossColor(typeData.change)}`}>
                            {formatCurrency(typeData.change)}
                          </div>
                          <div className="text-xs text-slate-500 mt-1">
                            {formatCurrency(typeData.previousValue)} &rarr; {formatCurrency(typeData.currentValue)}
                          </div>
                          {showAssetBreakdown && pieData.length > 0 && (
                            <div
                              className="mt-3 pt-3 border-t border-slate-700/50 cursor-pointer group"
                              onClick={() => setPieModalType(key)}
                              title="Click to expand"
                            >
                              <div className="text-[10px] text-slate-500 text-center mb-1 opacity-0 group-hover:opacity-100 transition-opacity">Click to expand</div>
                              <ResponsiveContainer width="100%" height={200}>
                                <RechartsPieChart>
                                  <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={40}
                                    outerRadius={75}
                                    paddingAngle={2}
                                    dataKey="value"
                                    label={({ name, percent }) =>
                                      `${name} ${(percent * 100).toFixed(0)}%`
                                    }
                                    labelLine={false}
                                  >
                                    {pieData.map((entry, index) => (
                                      <Cell
                                        key={`cell-${entry.name}`}
                                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                                      />
                                    ))}
                                  </Pie>
                                  <Tooltip
                                    content={({ active, payload }) => {
                                      if (!active || !payload?.length) return null
                                      const d = payload[0].payload
                                      return (
                                        <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 shadow-lg">
                                          <div className="text-sm font-medium text-white">{d.name}</div>
                                          <div className="text-xs text-slate-300">
                                            {formatCurrency(d.value)} &middot; {pieTotal > 0 ? ((d.value / pieTotal) * 100).toFixed(1) : 0}%
                                          </div>
                                        </div>
                                      )
                                    }}
                                  />
                                </RechartsPieChart>
                              </ResponsiveContainer>
                            </div>
                          )}
                        </div>
                      )
                    })
                    })()}
                  </div>
                </div>
              </div>
            )
          })()}
        </div>
      )}

      {/* Empty state */}
      {portfolio.holdings.length === 0 && (
        <div className="bg-slate-800 rounded-xl p-12 border border-slate-700 text-center">
          <Briefcase className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">No holdings yet</h2>
          <p className="text-slate-400 mb-6">
            Add your first holding to start tracking your portfolio performance.
          </p>
          <button
            onClick={openAddModal}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Add Your First Holding
          </button>
        </div>
      )}

      {/* Holdings by Asset Type */}
      {portfolio.holdings.length > 0 &&
        Object.entries(ASSET_TYPE_CONFIG).map(([assetType, config]) => {
          const holdings = groupedHoldings[assetType] || []
          if (holdings.length === 0) return null

          const isCollapsed = collapsedSections.has(assetType)
          const typeStats = summary?.byAssetType?.[assetType] || {}
          const activeFilter = sectionFilters[assetType]

          // Get unique accounts, tickers, and industries for filter options
          const accounts = [...new Set(holdings.map((h) => h.accountName))].sort()
          const tickers = [...new Set(holdings.map((h) => h.ticker))].sort()
          const industries = [...new Set(holdings.map((h) => h.industry).filter(Boolean))].sort()

          // Apply filter
          const filteredHoldings = activeFilter
            ? holdings.filter((h) => {
                if (activeFilter.type === 'account') return h.accountName === activeFilter.value
                if (activeFilter.type === 'industry') return h.industry === activeFilter.value
                return h.ticker === activeFilter.value
              })
            : holdings

          // Compute displayed stats from filtered holdings
          const displayStats = activeFilter
            ? (() => {
                const value = filteredHoldings.reduce((sum, h) => sum + (h.currentValue || 0), 0)
                const cost = filteredHoldings.reduce((sum, h) => sum + (h.quantity * h.costBasis || 0), 0)
                const gainLoss = value - cost
                const gainLossPercent = cost > 0 ? (gainLoss / cost) * 100 : 0
                return { value, gainLoss, gainLossPercent }
              })()
            : {
                ...typeStats,
                gainLossPercent: typeStats.cost > 0 ? (typeStats.gainLoss / typeStats.cost) * 100 : 0,
              }

          const setFilter = (type, value) => {
            setSectionFilters((prev) => {
              const current = prev[assetType]
              // Toggle off if same filter clicked again
              if (current?.type === type && current?.value === value) {
                const next = { ...prev }
                delete next[assetType]
                return next
              }
              return { ...prev, [assetType]: { type, value } }
            })
          }

          const clearFilter = () => {
            setSectionFilters((prev) => {
              const next = { ...prev }
              delete next[assetType]
              return next
            })
          }

          return (
            <div
              key={assetType}
              className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden"
            >
              {/* Section Header */}
              <button
                onClick={() => toggleSection(assetType)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isCollapsed ? (
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-slate-400" />
                  )}
                  <config.icon className={`w-5 h-5 text-${config.color}-500`} />
                  <span className="font-semibold text-lg">{config.label}</span>
                  <span className="text-sm text-slate-400 bg-slate-700 px-2 py-0.5 rounded-full">
                    {activeFilter ? `${filteredHoldings.length}/${holdings.length}` : holdings.length}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-sm text-slate-400">Value</div>
                    <div className="font-semibold">{formatCurrency(displayStats.value)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-slate-400">G/L</div>
                    <div className={`font-semibold ${getGainLossColor(displayStats.gainLoss)}`}>
                      {formatCurrency(displayStats.gainLoss)}
                      <span className="text-xs ml-1 opacity-75">
                        {formatPercent(displayStats.gainLossPercent)}
                      </span>
                    </div>
                  </div>
                </div>
              </button>

              {/* Filter Bar */}
              {!isCollapsed && (accounts.length > 1 || tickers.length > 1 || industries.length > 1) && (
                <div className="px-6 py-3 border-t border-slate-700 bg-slate-900/30 flex flex-wrap items-center gap-2">
                  <Filter className="w-4 h-4 text-slate-500 shrink-0" />

                  {/* Account filters */}
                  {accounts.length > 1 && (
                    <>
                      <span className="text-xs text-slate-500 uppercase tracking-wider">Account:</span>
                      {accounts.map((account) => (
                        <button
                          key={`acct-${account}`}
                          onClick={() => setFilter('account', account)}
                          className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                            activeFilter?.type === 'account' && activeFilter?.value === account
                              ? config.activeChip
                              : 'border-slate-600 text-slate-400 hover:border-slate-500 hover:text-slate-300'
                          }`}
                        >
                          {account}
                        </button>
                      ))}
                    </>
                  )}

                  {/* Divider */}
                  {accounts.length > 1 && (tickers.length > 1 || industries.length > 1) && (
                    <div className="w-px h-4 bg-slate-600 mx-1" />
                  )}

                  {/* Industry filters */}
                  {industries.length > 1 && (
                    <>
                      <span className="text-xs text-slate-500 uppercase tracking-wider">Industry:</span>
                      {industries.map((industry) => (
                        <button
                          key={`ind-${industry}`}
                          onClick={() => setFilter('industry', industry)}
                          className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                            activeFilter?.type === 'industry' && activeFilter?.value === industry
                              ? config.activeChip
                              : 'border-slate-600 text-slate-400 hover:border-slate-500 hover:text-slate-300'
                          }`}
                        >
                          {industry}
                        </button>
                      ))}
                    </>
                  )}

                  {/* Divider */}
                  {industries.length > 1 && tickers.length > 1 && (
                    <div className="w-px h-4 bg-slate-600 mx-1" />
                  )}

                  {/* Ticker filters */}
                  {tickers.length > 1 && (
                    <>
                      <span className="text-xs text-slate-500 uppercase tracking-wider">Ticker:</span>
                      {tickers.map((ticker) => (
                        <button
                          key={`tick-${ticker}`}
                          onClick={() => setFilter('ticker', ticker)}
                          className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                            activeFilter?.type === 'ticker' && activeFilter?.value === ticker
                              ? config.activeChip
                              : 'border-slate-600 text-slate-400 hover:border-slate-500 hover:text-slate-300'
                          }`}
                        >
                          {ticker}
                        </button>
                      ))}
                    </>
                  )}

                  {/* Clear filter */}
                  {activeFilter && (
                    <button
                      onClick={clearFilter}
                      className="px-2 py-1 text-xs rounded-full border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-1"
                    >
                      <X className="w-3 h-3" />
                      Clear
                    </button>
                  )}
                </div>
              )}

              {/* Options Table */}
              {!isCollapsed && assetType === 'option' && (
                <table className="w-full">
                  <thead>
                    <tr className="border-t border-slate-700 text-left bg-slate-900/50">
                      {[
                        { key: 'underlyingTicker', label: 'Underlying', align: 'left', px: 'px-6' },
                        { key: 'optionType', label: 'Type', align: 'left', px: 'px-4' },
                        { key: 'strikePrice', label: 'Strike', align: 'right', px: 'px-4' },
                        { key: 'expirationDate', label: 'Expiration', align: 'right', px: 'px-4' },
                        { key: 'quantity', label: 'Contracts', align: 'right', px: 'px-4' },
                        { key: 'costBasis', label: 'Premium', align: 'right', px: 'px-4' },
                        { key: 'currentPrice', label: 'Price', align: 'right', px: 'px-4' },
                        { key: 'currentValue', label: 'Value', align: 'right', px: 'px-4' },
                        { key: 'gainLossPercent', label: 'G/L', align: 'right', px: 'px-4' },
                        { key: 'accountName', label: 'Account', align: 'right', px: 'px-4' },
                      ].map((col) => (
                        <th
                          key={col.key}
                          onClick={() => handleSort(assetType, col.key)}
                          className={`${col.px} py-3 text-slate-400 font-medium text-sm ${col.align === 'right' ? 'text-right' : ''} cursor-pointer select-none group hover:text-slate-200 transition-colors`}
                        >
                          <span className={`inline-flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                            {col.label}
                            <SortIcon assetType={assetType} column={col.key} />
                          </span>
                        </th>
                      ))}
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {sortHoldings(filteredHoldings, assetType).map((holding) => (
                      <tr key={holding.id} className="transition-colors">
                        {/* Underlying */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-rose-500/10 flex items-center justify-center">
                              <Target className="w-5 h-5 text-rose-400" />
                            </div>
                            <div className="font-semibold">{holding.underlyingTicker || holding.ticker}</div>
                          </div>
                        </td>
                        {/* Type */}
                        <td className="px-4 py-4">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            holding.optionType === 'call'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}>
                            {holding.optionType === 'call' ? 'CALL' : 'PUT'}
                          </span>
                        </td>
                        {/* Strike */}
                        <td className="px-4 py-4 text-right font-medium">
                          {holding.strikePrice != null ? formatDollar(holding.strikePrice) : '-'}
                        </td>
                        {/* Expiration */}
                        <td className="px-4 py-4 text-right text-sm text-slate-300">
                          {holding.expirationDate || '-'}
                        </td>
                        {/* Contracts */}
                        <td className="px-4 py-4 text-right font-medium">
                          {holding.quantity}
                        </td>
                        {/* Premium */}
                        <td className="px-4 py-4 text-right">
                          {formatDollar(holding.costBasis)}
                        </td>
                        {/* Current Price */}
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {holding.currentPrice != null
                              ? formatDollar(holding.currentPrice)
                              : '-'}
                            {holding.livePrice && (
                              <span className="px-1 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 leading-none">
                                LIVE
                              </span>
                            )}
                          </div>
                        </td>
                        {/* Value */}
                        <td className="px-4 py-4 text-right font-semibold">
                          {formatCurrency(holding.currentValue)}
                        </td>
                        {/* G/L */}
                        <td className="px-4 py-4 text-right">
                          <div className={getGainLossColor(holding.gainLoss)}>
                            <div className="font-semibold">
                              {formatCurrency(holding.gainLoss)}
                            </div>
                            <div className="text-sm flex items-center justify-end gap-1">
                              {holding.gainLossPercent != null && holding.gainLossPercent >= 0 && (
                                <TrendingUp className="w-3 h-3" />
                              )}
                              {holding.gainLossPercent != null && holding.gainLossPercent < 0 && (
                                <TrendingDown className="w-3 h-3" />
                              )}
                              {formatPercent(holding.gainLossPercent)}
                            </div>
                          </div>
                        </td>
                        {/* Account */}
                        <td className="px-4 py-4 text-right text-sm text-slate-400">
                          {holding.accountName}
                        </td>
                        {/* Actions */}
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={(e) => openEditModal(holding, e)}
                              className="p-2 hover:bg-slate-600/50 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
                              title="Edit"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleRemove(holding.id, e)}
                              disabled={removingId === holding.id}
                              className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-slate-400 hover:text-red-400"
                              title="Remove"
                            >
                              {removingId === holding.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Trash2 className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {/* Cash Table */}
              {!isCollapsed && assetType === 'cash' && (
                <table className="w-full">
                  <thead>
                    <tr className="border-t border-slate-700 text-left bg-slate-900/50">
                      {[
                        { key: 'accountName', label: 'Account', align: 'left', px: 'px-6' },
                        { key: 'currentValue', label: 'Amount', align: 'right', px: 'px-4' },
                      ].map((col) => (
                        <th
                          key={col.key}
                          onClick={() => handleSort(assetType, col.key)}
                          className={`${col.px} py-3 text-slate-400 font-medium text-sm ${col.align === 'right' ? 'text-right' : ''} cursor-pointer select-none group hover:text-slate-200 transition-colors`}
                        >
                          <span className={`inline-flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                            {col.label}
                            <SortIcon assetType={assetType} column={col.key} />
                          </span>
                        </th>
                      ))}
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {sortHoldings(filteredHoldings, assetType).map((holding) => (
                      <tr key={holding.id} className="transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                              <Banknote className="w-5 h-5 text-emerald-400" />
                            </div>
                            <div className="font-semibold">{holding.accountName}</div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right text-lg font-semibold text-emerald-400">
                          {formatCurrency(holding.currentValue)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={(e) => openEditModal(holding, e)}
                              className="p-2 hover:bg-slate-600/50 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
                              title="Edit"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleRemove(holding.id, e)}
                              disabled={removingId === holding.id}
                              className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-slate-400 hover:text-red-400"
                              title="Remove"
                            >
                              {removingId === holding.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Trash2 className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {/* Standard Holdings Table */}
              {!isCollapsed && assetType !== 'cash' && assetType !== 'option' && (
                <table className="w-full">
                  <thead>
                    <tr className="border-t border-slate-700 text-left bg-slate-900/50">
                      {[
                        { key: 'ticker', label: 'Asset', align: 'left', px: 'px-6' },
                        ...(industries.length > 0 ? [{ key: 'industry', label: 'Industry', align: 'left', px: 'px-4' }] : []),
                        { key: 'quantity', label: 'Qty', align: 'right', px: 'px-4' },
                        { key: 'costBasis', label: 'Cost Basis', align: 'right', px: 'px-4' },
                        { key: 'currentPrice', label: 'Price', align: 'right', px: 'px-4' },
                        { key: 'currentValue', label: 'Value', align: 'right', px: 'px-4' },
                        { key: 'gainLossPercent', label: 'G/L', align: 'right', px: 'px-4' },
                        ...(assetType === 'stock' ? [{ key: 'nextEarningsDate', label: 'Earnings', align: 'right', px: 'px-4' }] : []),
                        { key: 'accountName', label: 'Account', align: 'right', px: 'px-4' },
                      ].map((col) => (
                        <th
                          key={col.key}
                          onClick={() => handleSort(assetType, col.key)}
                          className={`${col.px} py-3 text-slate-400 font-medium text-sm ${col.align === 'right' ? 'text-right' : ''} cursor-pointer select-none group hover:text-slate-200 transition-colors`}
                        >
                          <span className={`inline-flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                            {col.label}
                            <SortIcon assetType={assetType} column={col.key} />
                          </span>
                        </th>
                      ))}
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {sortHoldings(filteredHoldings, assetType).map((holding) => (
                      <tr
                        key={holding.id}
                        onClick={() =>
                          !['crypto', 'custom', 'cash', 'option'].includes(assetType) && navigate(`/analysis/${holding.ticker}`)
                        }
                        className={`${
                          !['crypto', 'custom', 'cash', 'option'].includes(assetType)
                            ? 'hover:bg-slate-700/30 cursor-pointer'
                            : ''
                        } transition-colors`}
                      >
                        {/* Asset */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            {holding.image ? (
                              <img
                                src={holding.image}
                                alt={holding.ticker}
                                className="w-10 h-10 rounded-lg object-contain bg-white p-1"
                                onError={(e) => {
                                  e.target.style.display = 'none'
                                }}
                              />
                            ) : (
                              <div className="w-10 h-10 rounded-lg bg-slate-700 flex items-center justify-center text-slate-400 text-sm font-bold">
                                {holding.ticker?.slice(0, 2)}
                              </div>
                            )}
                            <div>
                              <div className="font-semibold">{holding.ticker}</div>
                              <div className="text-sm text-slate-400 truncate max-w-[150px]">
                                {holding.name || holding.ticker}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Industry */}
                        {industries.length > 0 && (
                          <td className="px-4 py-4 text-sm text-slate-400 max-w-[140px] truncate">
                            {holding.industry || '-'}
                          </td>
                        )}

                        {/* Quantity */}
                        <td className="px-4 py-4 text-right font-medium">
                          {holding.quantity.toLocaleString(undefined, {
                            maximumFractionDigits: 6,
                          })}
                        </td>

                        {/* Cost Basis */}
                        <td className="px-4 py-4 text-right">
                          {formatDollar(holding.costBasis)}
                        </td>

                        {/* Current Price */}
                        <td className="px-4 py-4 text-right">
                          {formatDollar(holding.currentPrice)}
                        </td>

                        {/* Current Value */}
                        <td className="px-4 py-4 text-right font-semibold">
                          {formatCurrency(holding.currentValue)}
                        </td>

                        {/* Gain/Loss */}
                        <td className="px-4 py-4 text-right">
                          <div className={getGainLossColor(holding.gainLoss)}>
                            <div className="font-semibold">
                              {formatCurrency(holding.gainLoss)}
                            </div>
                            <div className="text-sm flex items-center justify-end gap-1">
                              {holding.gainLossPercent != null &&
                                holding.gainLossPercent >= 0 && (
                                  <TrendingUp className="w-3 h-3" />
                                )}
                              {holding.gainLossPercent != null &&
                                holding.gainLossPercent < 0 && (
                                  <TrendingDown className="w-3 h-3" />
                                )}
                              {formatPercent(holding.gainLossPercent)}
                            </div>
                          </div>
                        </td>

                        {/* Next Earnings (stocks only) */}
                        {assetType === 'stock' && (
                          <td className="px-4 py-4 text-right text-sm">
                            {holding.nextEarningsDate ? (() => {
                              const daysUntil = Math.ceil((new Date(holding.nextEarningsDate + 'T00:00:00') - new Date()) / (1000 * 60 * 60 * 24))
                              const dateLabel = new Date(holding.nextEarningsDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                              return (
                                <div className="flex items-center justify-end gap-1.5">
                                  <Calendar className="w-3 h-3 text-slate-500" />
                                  <span className={daysUntil <= 7 ? 'text-amber-400 font-medium' : 'text-slate-300'}>
                                    {dateLabel}
                                  </span>
                                  <span className={`text-xs ${daysUntil <= 7 ? 'text-amber-400/70' : 'text-slate-500'}`}>
                                    ({daysUntil}d)
                                  </span>
                                </div>
                              )
                            })() : (
                              <span className="text-slate-600">-</span>
                            )}
                          </td>
                        )}

                        {/* Account */}
                        <td className="px-4 py-4 text-right text-sm text-slate-400">
                          {holding.accountName}
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={(e) => openEditModal(holding, e)}
                              className="p-2 hover:bg-slate-600/50 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
                              title="Edit holding"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleRemove(holding.id, e)}
                              disabled={removingId === holding.id}
                              className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-slate-400 hover:text-red-400"
                              title="Remove holding"
                            >
                              {removingId === holding.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Trash2 className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )
        })}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold">
                {editingHolding
                  ? editingHolding.assetType === 'cash' ? 'Edit Cash'
                    : editingHolding.assetType === 'custom' ? 'Edit Miscellaneous'
                    : editingHolding.assetType === 'option' ? 'Edit Option'
                    : 'Edit Holding'
                  : addType === 'cash' ? 'Add Cash'
                    : addType === 'misc' ? 'Add Miscellaneous'
                    : addType === 'option' ? 'Add Option'
                    : 'Add Holding'}
              </h2>
              <button
                onClick={closeModal}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                  {formError}
                </div>
              )}

              {/* Type Toggle (only for new entries) */}
              {!editingHolding && (
                <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1">
                  <button
                    type="button"
                    onClick={() => setAddType('holding')}
                    className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                      addType === 'holding'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Holding
                  </button>
                  <button
                    type="button"
                    onClick={() => setAddType('cash')}
                    className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                      addType === 'cash'
                        ? 'bg-emerald-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Cash
                  </button>
                  <button
                    type="button"
                    onClick={() => setAddType('misc')}
                    className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                      addType === 'misc'
                        ? 'bg-teal-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Misc
                  </button>
                  <button
                    type="button"
                    onClick={() => setAddType('option')}
                    className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                      addType === 'option'
                        ? 'bg-rose-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Option
                  </button>
                </div>
              )}

              {/* Category (for misc) */}
              {(addType === 'misc' || editingHolding?.assetType === 'custom') && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Category
                  </label>
                  {editingHolding ? (
                    <div className="px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-300 opacity-50">
                      <span className="font-semibold">{formData.ticker}</span>
                    </div>
                  ) : (
                    <select
                      value={formData.ticker}
                      onChange={(e) => setFormData({ ...formData, ticker: e.target.value })}
                      className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-teal-500"
                    >
                      <option value="">Select category...</option>
                      {MISC_CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* Custom category name */}
              {addType === 'misc' && formData.ticker === 'Other' && !editingHolding && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Custom Category
                  </label>
                  <input
                    type="text"
                    value={formData.tickerName}
                    onChange={(e) => setFormData({ ...formData, tickerName: e.target.value })}
                    placeholder="Enter category name"
                    className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-teal-500"
                  />
                </div>
              )}

              {/* Option Fields */}
              {(addType === 'option' || editingHolding?.assetType === 'option') && (
                <>
                  {/* Underlying Ticker */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Underlying Ticker
                    </label>
                    <input
                      type="text"
                      value={formData.underlyingTicker}
                      onChange={(e) => setFormData({ ...formData, underlyingTicker: e.target.value.toUpperCase() })}
                      placeholder="e.g., AAPL"
                      className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-rose-500"
                    />
                  </div>

                  {/* Option Type (Call/Put toggle) */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Option Type
                    </label>
                    <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 border border-slate-600">
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, optionType: 'call' })}
                        className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                          formData.optionType === 'call'
                            ? 'bg-emerald-600 text-white'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Call
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, optionType: 'put' })}
                        className={`flex-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                          formData.optionType === 'put'
                            ? 'bg-red-600 text-white'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Put
                      </button>
                    </div>
                  </div>

                  {/* Strike Price */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Strike Price
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                      <input
                        type="number"
                        step="any"
                        value={formData.strikePrice}
                        onChange={(e) => setFormData({ ...formData, strikePrice: e.target.value })}
                        placeholder="e.g., 200"
                        className="w-full pl-8 pr-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-rose-500"
                      />
                    </div>
                  </div>

                  {/* Expiration Date */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Expiration Date
                    </label>
                    <input
                      type="date"
                      value={formData.expirationDate}
                      onChange={(e) => setFormData({ ...formData, expirationDate: e.target.value })}
                      className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-rose-500"
                    />
                  </div>

                  {/* Contracts */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Contracts
                    </label>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                      placeholder="e.g., 5"
                      className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-rose-500"
                    />
                  </div>

                  {/* Current Price (optional — for G/L calculation) */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Current Price <span className="text-slate-500 font-normal">(optional)</span>
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                      <input
                        type="number"
                        step="any"
                        value={formData.optionPrice}
                        onChange={(e) => setFormData({ ...formData, optionPrice: e.target.value })}
                        placeholder="e.g., 4.20"
                        className="w-full pl-8 pr-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-rose-500"
                      />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Leave blank to use premium as current value</p>
                  </div>
                </>
              )}

              {/* Ticker (not for cash, misc, or option) */}
              {addType === 'holding' && !(editingHolding?.assetType === 'cash') && !(editingHolding?.assetType === 'custom') && !(editingHolding?.assetType === 'option') && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Ticker Symbol
                </label>
                {editingHolding ? (
                  <div className="px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-300 opacity-50">
                    <span className="font-semibold">{formData.ticker}</span>
                    {formData.tickerName && (
                      <span className="text-slate-400 ml-2">{formData.tickerName}</span>
                    )}
                  </div>
                ) : formData.ticker ? (
                  <div className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg">
                    <span className="font-semibold text-blue-400">{formData.ticker}</span>
                    {formData.tickerName && (
                      <span className="text-slate-400">{formData.tickerName}</span>
                    )}
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, ticker: '', tickerName: '' })}
                      className="ml-auto p-0.5 hover:bg-slate-700 rounded transition-colors"
                    >
                      <X className="w-4 h-4 text-slate-400 hover:text-white" />
                    </button>
                  </div>
                ) : (
                  <TickerSearch
                    compact
                    placeholder="Search by symbol or company name..."
                    onSelect={(symbol, name) =>
                      setFormData({ ...formData, ticker: symbol, tickerName: name || '' })
                    }
                  />
                )}
              </div>
              )}

              {/* Quantity (not for cash, misc, or option — options have Contracts field above) */}
              {addType === 'holding' && !(editingHolding?.assetType === 'cash') && !(editingHolding?.assetType === 'custom') && !(editingHolding?.assetType === 'option') && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Quantity
                </label>
                <input
                  type="number"
                  step="any"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                  placeholder="e.g., 100"
                  className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>
              )}

              {/* Amount (for cash) / Cost Basis (for holdings) */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {addType === 'cash' || editingHolding?.assetType === 'cash'
                    ? 'Amount'
                    : addType === 'misc' || editingHolding?.assetType === 'custom'
                      ? 'Investment Amount'
                      : addType === 'option' || editingHolding?.assetType === 'option'
                        ? 'Premium per Contract'
                        : 'Cost Basis (per share/unit)'}
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                    $
                  </span>
                  <input
                    type="number"
                    step="any"
                    value={formData.costBasis}
                    onChange={(e) =>
                      setFormData({ ...formData, costBasis: e.target.value })
                    }
                    placeholder="e.g., 150.50"
                    className="w-full pl-8 pr-4 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Account */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Account
                </label>
                <select
                  value={formData.accountName}
                  onChange={(e) =>
                    setFormData({ ...formData, accountName: e.target.value })
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
              {formData.accountName === 'Other' && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Custom Account Name
                  </label>
                  <input
                    type="text"
                    value={formData.customAccount}
                    onChange={(e) =>
                      setFormData({ ...formData, customAccount: e.target.value })
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
                  onClick={closeModal}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingHolding ? 'Save Changes' : addType === 'cash' ? 'Add Cash' : addType === 'misc' ? 'Add Investment' : addType === 'option' ? 'Add Option' : 'Add Holding'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Pie Chart Expanded Modal */}
      {pieModalType && (() => {
        const ASSET_TYPE_META = {
          stock: { label: 'Stocks', color: 'blue' },
          etf: { label: 'ETFs', color: 'purple' },
          crypto: { label: 'Crypto', color: 'orange' },
          custom: { label: 'Miscellaneous', color: 'teal' },
          cash: { label: 'Cash', color: 'emerald' },
          option: { label: 'Options', color: 'rose' },
        }
        const PIE_COLORS = ['#3b82f6', '#a855f7', '#f97316', '#14b8a6', '#10b981', '#f43f5e', '#eab308', '#6366f1', '#ec4899', '#06b6d4']
        const meta = ASSET_TYPE_META[pieModalType] || { label: pieModalType, color: 'slate' }
        const holdings = groupedHoldings[pieModalType] || []
        const useName = pieModalType === 'cash' || pieModalType === 'custom'
        const modalPieData = Object.values(holdings
          .filter((h) => (h.currentValue || h.quantity * h.costBasis) > 0)
          .reduce((acc, h) => {
            const name = useName ? (h.accountName || h.ticker) : h.ticker
            const value = h.currentValue || h.quantity * h.costBasis
            acc[name] = acc[name] ? { name, value: acc[name].value + value } : { name, value }
            return acc
          }, {}))
          .sort((a, b) => b.value - a.value)
        const modalTotal = modalPieData.reduce((sum, d) => sum + d.value, 0)

        return (
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setPieModalType(null)}
          >
            <div
              className="bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-5 border-b border-slate-700">
                <h3 className={`text-lg font-semibold text-${meta.color}-400`}>
                  {meta.label} Breakdown
                </h3>
                <button
                  onClick={() => setPieModalType(null)}
                  className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>
              <div className="p-5">
                <ResponsiveContainer width="100%" height={320}>
                  <RechartsPieChart>
                    <Pie
                      data={modalPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={120}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                      labelLine={false}
                    >
                      {modalPieData.map((entry, index) => (
                        <Cell
                          key={`modal-cell-${entry.name}`}
                          fill={PIE_COLORS[index % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const d = payload[0].payload
                        return (
                          <div className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 shadow-lg">
                            <div className="text-sm font-medium text-white">{d.name}</div>
                            <div className="text-xs text-slate-300">
                              {formatCurrency(d.value)} &middot; {modalTotal > 0 ? ((d.value / modalTotal) * 100).toFixed(1) : 0}%
                            </div>
                          </div>
                        )
                      }}
                    />
                  </RechartsPieChart>
                </ResponsiveContainer>

                {/* Legend table */}
                <div className="mt-4 space-y-1.5">
                  {modalPieData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-3 text-sm">
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                      />
                      <span className="text-slate-300 flex-1">{entry.name}</span>
                      <span className="text-slate-400 tabular-nums">{formatCurrency(entry.value)}</span>
                      <span className="text-slate-500 tabular-nums w-14 text-right">
                        {modalTotal > 0 ? ((entry.value / modalTotal) * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
