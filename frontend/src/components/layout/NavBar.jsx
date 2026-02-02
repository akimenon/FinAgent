import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, LayoutDashboard } from 'lucide-react'
import { companiesApi } from '../../services/api'

// Category colors for visual distinction
const categoryColors = {
  index: 'border-blue-500/30',
  etf: 'border-purple-500/30',
  crypto: 'border-orange-500/30',
  commodity: 'border-yellow-500/30',
}

export default function NavBar() {
  const [indices, setIndices] = useState([])

  useEffect(() => {
    loadIndices()
    // Refresh every 60 seconds
    const interval = setInterval(loadIndices, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadIndices = async () => {
    try {
      const response = await companiesApi.getMarketIndices()
      setIndices(response.data.indices || [])
    } catch (err) {
      console.error('Failed to load market indices:', err)
    }
  }

  const formatPrice = (price, category) => {
    if (!price) return '—'
    // Crypto and commodities show decimals, indices/ETFs don't need them
    if (category === 'crypto') {
      return price >= 1000
        ? price.toLocaleString(undefined, { maximumFractionDigits: 0 })
        : price.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
    if (category === 'commodity') {
      return price.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
    return price.toLocaleString(undefined, { maximumFractionDigits: 0 })
  }

  return (
    <nav className="bg-slate-800 border-b border-slate-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center space-x-2 flex-shrink-0">
            <TrendingUp className="h-8 w-8 text-blue-500" />
            <span className="text-xl font-bold hidden sm:inline">FinAgent</span>
          </Link>

          {/* Market Indicators - Scrollable */}
          <div className="flex-1 mx-4 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-1.5 justify-center">
              {indices.filter(idx => idx.price).map((idx) => (
                <div
                  key={idx.symbol}
                  className={`flex items-center gap-1.5 px-2 py-1 bg-slate-700/50 rounded-full text-xs border ${categoryColors[idx.category] || 'border-slate-600'}`}
                >
                  <span className="text-slate-300 font-medium">{idx.name}</span>
                  <span className="text-slate-400">
                    {formatPrice(idx.price, idx.category)}
                  </span>
                  {idx.changePercent !== null && (
                    <span
                      className={`flex items-center font-medium ${
                        idx.changePercent >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {idx.changePercent >= 0 ? (
                        <TrendingUp className="w-2.5 h-2.5" />
                      ) : (
                        <TrendingDown className="w-2.5 h-2.5" />
                      )}
                      {idx.changePercent >= 0 ? '+' : ''}
                      {idx.changePercent?.toFixed(2)}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center flex-shrink-0">
            <Link
              to="/"
              className="flex items-center space-x-1 px-3 py-2 rounded-md hover:bg-slate-700 transition-colors"
            >
              <LayoutDashboard className="h-4 w-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
