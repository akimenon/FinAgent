import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, TrendingUp, BarChart3, Target } from 'lucide-react'
import StockSearch from '../components/search/StockSearch'

export default function Dashboard() {
  const navigate = useNavigate()
  const [recentSearches] = useState(['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META'])

  const handleSelectStock = (symbol) => {
    navigate(`/analysis/${symbol}`)
  }

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

      {/* Quick Access */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold mb-4">Popular Stocks</h3>
        <div className="flex flex-wrap gap-2">
          {recentSearches.map((symbol) => (
            <button
              key={symbol}
              onClick={() => handleSelectStock(symbol)}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
            >
              {symbol}
            </button>
          ))}
        </div>
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
