import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, TrendingUp, TrendingDown, BarChart3, Target, Cpu, Car, Zap, ChevronDown, ChevronUp } from 'lucide-react'
import StockSearch from '../components/search/StockSearch'
import { companiesApi } from '../services/api'

export default function Dashboard() {
  const navigate = useNavigate()
  const [activeCategory, setActiveCategory] = useState('gainers')
  const [marketMovers, setMarketMovers] = useState({ gainers: [], losers: [] })
  const [sectorData, setSectorData] = useState({})
  const [loading, setLoading] = useState(true)
  const [sectorLoading, setSectorLoading] = useState(false)

  useEffect(() => {
    const fetchMarketMovers = async () => {
      try {
        const response = await companiesApi.getMarketMovers()
        setMarketMovers(response.data)
      } catch (error) {
        console.error('Failed to fetch market movers:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchMarketMovers()
  }, [])

  // Fetch sector data when switching to a sector category
  useEffect(() => {
    const fetchSectorData = async () => {
      if (['tech', 'semiconductors', 'ev'].includes(activeCategory) && !sectorData[activeCategory]) {
        setSectorLoading(true)
        try {
          const response = await companiesApi.getSectorStocks(activeCategory)
          setSectorData(prev => ({ ...prev, [activeCategory]: response.data.stocks }))
        } catch (error) {
          console.error(`Failed to fetch ${activeCategory} stocks:`, error)
        } finally {
          setSectorLoading(false)
        }
      }
    }
    fetchSectorData()
  }, [activeCategory])

  const handleSelectStock = (symbol) => {
    navigate(`/analysis/${symbol}`)
  }

  const categories = [
    { id: 'gainers', label: 'Top Gainers', icon: TrendingUp, color: 'emerald' },
    { id: 'losers', label: 'Top Losers', icon: TrendingDown, color: 'red' },
    { id: 'tech', label: 'Tech', icon: Zap, color: 'blue' },
    { id: 'semiconductors', label: 'Semiconductors', icon: Cpu, color: 'purple' },
    { id: 'ev', label: 'EV', icon: Car, color: 'amber' },
  ]

  const getStocksForCategory = (categoryId) => {
    if (categoryId === 'gainers') return marketMovers.gainers || []
    if (categoryId === 'losers') return marketMovers.losers || []
    return sectorData[categoryId] || []
  }

  const currentStocks = getStocksForCategory(activeCategory)
  const isLoading = (loading && ['gainers', 'losers'].includes(activeCategory)) ||
                    (sectorLoading && ['tech', 'semiconductors', 'ev'].includes(activeCategory))

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold mb-4">
          Multi-Agent Financial Analysis
        </h1>
        <p className="text-slate-400 text-lg mb-8 max-w-2xl mx-auto">
          Powered by Qwen AI agents that analyze quarterly results, track
          guidance accuracy, and provide actionable insights.
        </p>

        {/* Search */}
        <div className="max-w-xl mx-auto">
          <StockSearch onSelect={handleSelectStock} />
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <BarChart3 className="h-6 w-6 text-blue-500" />
            </div>
            <h3 className="text-lg font-semibold">Quarterly Analysis</h3>
          </div>
          <p className="text-slate-400">
            Deep dive into quarterly results with revenue, EPS, margins, and
            year-over-year growth trends.
          </p>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Target className="h-6 w-6 text-green-500" />
            </div>
            <h3 className="text-lg font-semibold">Beat/Miss Tracking</h3>
          </div>
          <p className="text-slate-400">
            Track how often companies beat, meet, or miss analyst estimates
            with historical patterns.
          </p>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <TrendingUp className="h-6 w-6 text-purple-500" />
            </div>
            <h3 className="text-lg font-semibold">AI-Powered Insights</h3>
          </div>
          <p className="text-slate-400">
            Get comprehensive analysis from specialized Qwen agents with
            actionable recommendations.
          </p>
        </div>
      </div>

      {/* Stock Categories */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold mb-4">Explore Stocks</h3>

        {/* Category Pills */}
        <div className="flex flex-wrap gap-2 mb-6">
          {categories.map((cat) => {
            const Icon = cat.icon
            const isActive = activeCategory === cat.id
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  isActive
                    ? `bg-${cat.color}-500/20 text-${cat.color}-400 border border-${cat.color}-500/50`
                    : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                }`}
                style={isActive ? {
                  backgroundColor: cat.color === 'emerald' ? 'rgba(16, 185, 129, 0.2)' :
                                   cat.color === 'red' ? 'rgba(239, 68, 68, 0.2)' :
                                   cat.color === 'blue' ? 'rgba(59, 130, 246, 0.2)' :
                                   cat.color === 'purple' ? 'rgba(168, 85, 247, 0.2)' :
                                   'rgba(245, 158, 11, 0.2)',
                  color: cat.color === 'emerald' ? '#34d399' :
                         cat.color === 'red' ? '#f87171' :
                         cat.color === 'blue' ? '#60a5fa' :
                         cat.color === 'purple' ? '#c084fc' :
                         '#fbbf24',
                  borderColor: cat.color === 'emerald' ? 'rgba(16, 185, 129, 0.5)' :
                               cat.color === 'red' ? 'rgba(239, 68, 68, 0.5)' :
                               cat.color === 'blue' ? 'rgba(59, 130, 246, 0.5)' :
                               cat.color === 'purple' ? 'rgba(168, 85, 247, 0.5)' :
                               'rgba(245, 158, 11, 0.5)',
                } : {}}
              >
                <Icon className="w-4 h-4" />
                {cat.label}
              </button>
            )
          })}
        </div>

        {/* Stock List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {currentStocks.slice(0, 10).map((stock, index) => (
              <button
                key={stock.symbol || index}
                onClick={() => handleSelectStock(stock.symbol)}
                className="bg-slate-700/50 hover:bg-slate-600 rounded-lg p-3 transition-colors text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{stock.symbol}</span>
                  {stock.price != null && (
                    <span className="text-sm text-slate-300">${stock.price.toFixed(2)}</span>
                  )}
                </div>
                {stock.changePercent != null && (
                  <div className={`text-sm flex items-center gap-1 mt-1 ${
                    stock.changePercent >= 0 ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {stock.changePercent >= 0 ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                    {Math.abs(stock.changePercent).toFixed(2)}%
                  </div>
                )}
                {stock.name && (
                  <div className="text-xs text-slate-400 truncate mt-1">
                    {stock.name.length > 18 ? stock.name.substring(0, 18) + '...' : stock.name}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}

        {currentStocks.length === 0 && !loading && (
          <div className="text-center text-slate-500 py-8">
            No stocks available for this category
          </div>
        )}
      </div>

      {/* Agent Architecture Info */}
      <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold mb-4">How It Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
          <div className="text-center p-4">
            <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
              <span className="text-blue-500 font-bold">1</span>
            </div>
            <p className="font-medium">Data Fetcher Agent</p>
            <p className="text-slate-400 text-xs mt-1">
              Retrieves financial data from FMP API
            </p>
          </div>
          <div className="text-center p-4">
            <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
              <span className="text-green-500 font-bold">2</span>
            </div>
            <p className="font-medium">Analysis Agent</p>
            <p className="text-slate-400 text-xs mt-1">
              Qwen analyzes trends and metrics
            </p>
          </div>
          <div className="text-center p-4">
            <div className="w-10 h-10 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
              <span className="text-yellow-500 font-bold">3</span>
            </div>
            <p className="font-medium">Guidance Tracker</p>
            <p className="text-slate-400 text-xs mt-1">
              Qwen tracks beat/miss patterns
            </p>
          </div>
          <div className="text-center p-4">
            <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
              <span className="text-purple-500 font-bold">4</span>
            </div>
            <p className="font-medium">Orchestrator</p>
            <p className="text-slate-400 text-xs mt-1">
              Synthesizes insights from all agents
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
