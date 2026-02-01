import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  AlertTriangle,
  Loader2,
  BarChart3,
  PieChart,
  Brain,
  History,
  ChevronUp,
  ChevronDown,
  ExternalLink,
  Building2,
  Users,
  Banknote,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  MessageSquare,
  Send,
} from 'lucide-react'
import { financialsApi, agentApi } from '../services/api'
import QuarterlyResultsTable from '../components/tables/QuarterlyResultsTable'
import BeatMissChart from '../components/charts/BeatMissChart'
import EarningsTrendChart from '../components/charts/EarningsTrendChart'
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

// Action Pill Component
function ActionPill({ label, icon: Icon, onClick, active, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all ${
        active
          ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
          : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-600 hover:bg-slate-700'
      } ${loading ? 'opacity-50 cursor-wait' : ''}`}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        Icon && <Icon className="w-4 h-4" />
      )}
      {label}
    </button>
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
  const [activeSection, setActiveSection] = useState(null)
  const [sectionData, setSectionData] = useState({})
  const [sectionLoading, setSectionLoading] = useState({})

  // AI Analysis
  const [aiAnalysis, setAiAnalysis] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiProgress, setAiProgress] = useState([])

  // Chat
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  // Load overview on mount
  useEffect(() => {
    loadOverview()
  }, [symbol])

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

  // Load section data on demand
  const loadSection = async (section) => {
    if (activeSection === section) {
      setActiveSection(null)
      return
    }

    setActiveSection(section)

    if (sectionData[section]) return // Already loaded

    setSectionLoading(prev => ({ ...prev, [section]: true }))

    try {
      let data
      switch (section) {
        case 'quarterly':
          const qRes = await financialsApi.getQuarterly(symbol, 5)
          data = qRes.data.quarters
          break
        case 'beatmiss':
          const bRes = await financialsApi.getSurprises(symbol, 12)
          data = bRes.data.surprises
          break
        case 'price':
          const pRes = await financialsApi.getPriceHistory(symbol, '1y')
          data = pRes.data.prices
          break
        default:
          data = null
      }
      setSectionData(prev => ({ ...prev, [section]: data }))
    } catch (err) {
      console.error(`Failed to load ${section}:`, err)
    } finally {
      setSectionLoading(prev => ({ ...prev, [section]: false }))
    }
  }

  // Load AI Analysis on demand
  const loadAiAnalysis = () => {
    if (aiAnalysis || aiLoading) return

    setAiLoading(true)
    setAiProgress([])

    const eventSource = agentApi.queryStream(
      symbol,
      'Provide a comprehensive analysis including key insights, concerns, and investment implications.',
      {
        onMessage: (update) => {
          setAiProgress(prev => [...prev, update])
          if (update.phase === 'complete' && update.result) {
            setAiAnalysis(update.result)
            setAiLoading(false)
          } else if (update.phase === 'error') {
            setAiLoading(false)
          }
        },
        onError: () => setAiLoading(false),
        onComplete: () => setAiLoading(false),
      }
    )
  }

  // Send chat message
  const sendChatMessage = async (e) => {
    e.preventDefault()
    if (!chatInput.trim() || chatLoading) return

    const question = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: question }])
    setChatLoading(true)

    try {
      const response = await agentApi.chat(symbol, question)
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.answer
      }])
    } catch (err) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.response?.data?.detail || 'Failed to get answer'}`
      }])
    } finally {
      setChatLoading(false)
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

  const { profile, price, latestQuarter, balanceSheet, cashFlow, earnings, revenuePillars } = overview

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-3">
            {profile.image && (
              <img src={profile.image} alt={symbol} className="w-12 h-12 rounded-lg" />
            )}
            <div>
              <h1 className="text-2xl font-bold">{profile.name}</h1>
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
          <div className={`flex items-center justify-end gap-1 ${
            price.change >= 0 ? 'text-emerald-400' : 'text-red-400'
          }`}>
            {price.change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            <span>${Math.abs(price.change || 0).toFixed(2)}</span>
            <span>({formatPercent(price.changePercent)})</span>
          </div>
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">Market Cap</span>
          <span className="float-right font-medium">{formatNumber(price.marketCap, 2)}</span>
        </div>
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">52W Range</span>
          <span className="float-right font-medium text-xs">{price.range52Week}</span>
        </div>
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">Beta</span>
          <span className="float-right font-medium">{price.beta?.toFixed(2)}</span>
        </div>
        <div className="bg-slate-800/50 rounded-lg px-4 py-2">
          <span className="text-slate-400">Employees</span>
          <span className="float-right font-medium">{parseInt(profile.employees || 0).toLocaleString()}</span>
        </div>
      </div>

      {/* Latest Quarter Section */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          Latest Quarter ({latestQuarter.period})
        </h2>

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

      {/* Revenue Pillars - Key Drivers */}
      {revenuePillars && (revenuePillars.products?.length > 0 || revenuePillars.geographies?.length > 0) && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-blue-500" />
            Revenue Drivers (FY{revenuePillars.products?.[0]?.fiscalYear || ''})
          </h2>

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

      {/* Action Pills */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold mb-4">Explore More</h2>
        <div className="flex flex-wrap gap-3">
          <ActionPill
            label="Quarterly Trends"
            icon={BarChart3}
            active={activeSection === 'quarterly'}
            loading={sectionLoading.quarterly}
            onClick={() => loadSection('quarterly')}
          />
          <ActionPill
            label="Beat/Miss History"
            icon={Target}
            active={activeSection === 'beatmiss'}
            loading={sectionLoading.beatmiss}
            onClick={() => loadSection('beatmiss')}
          />
          <ActionPill
            label="Price History"
            icon={TrendingUp}
            active={activeSection === 'price'}
            loading={sectionLoading.price}
            onClick={() => loadSection('price')}
          />
          <ActionPill
            label="AI Deep Analysis"
            icon={Brain}
            active={aiAnalysis !== null || aiLoading}
            loading={aiLoading}
            onClick={loadAiAnalysis}
          />
          <ActionPill
            label="Ask a Question"
            icon={MessageSquare}
            active={chatOpen}
            onClick={() => setChatOpen(!chatOpen)}
          />
        </div>

        {/* Expanded Section Content */}
        {activeSection === 'quarterly' && sectionData.quarterly && (
          <div className="mt-6">
            <QuarterlyResultsTable data={sectionData.quarterly} />
            <div className="mt-4">
              <EarningsTrendChart data={sectionData.quarterly} />
            </div>
          </div>
        )}

        {activeSection === 'beatmiss' && sectionData.beatmiss && (
          <div className="mt-6">
            <BeatMissChart data={sectionData.beatmiss} />
            <div className="mt-4 grid grid-cols-3 gap-4 text-center">
              <div className="bg-emerald-500/10 rounded-lg p-4 border border-emerald-500/30">
                <div className="text-2xl font-bold text-emerald-400">
                  {sectionData.beatmiss.filter(d => d.beat_miss === 'BEAT').length}
                </div>
                <div className="text-sm text-slate-400">Beats</div>
              </div>
              <div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/30">
                <div className="text-2xl font-bold text-yellow-400">
                  {sectionData.beatmiss.filter(d => d.beat_miss === 'MEET').length}
                </div>
                <div className="text-sm text-slate-400">Meets</div>
              </div>
              <div className="bg-red-500/10 rounded-lg p-4 border border-red-500/30">
                <div className="text-2xl font-bold text-red-400">
                  {sectionData.beatmiss.filter(d => d.beat_miss === 'MISS').length}
                </div>
                <div className="text-sm text-slate-400">Misses</div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'price' && sectionData.price && (
          <div className="mt-6">
            <PriceChart data={sectionData.price} />
          </div>
        )}

        {/* Chat Panel */}
        {chatOpen && (
          <div className="mt-6 bg-slate-900 rounded-xl border border-slate-600 overflow-hidden">
            <div className="p-4 border-b border-slate-700 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold">Ask anything about {symbol}</h3>
            </div>

            {/* Chat Messages */}
            <div className="h-64 overflow-y-auto p-4 space-y-3">
              {chatMessages.length === 0 && (
                <div className="text-center text-slate-500 py-8">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Ask any question about {symbol}'s financials</p>
                  <div className="mt-3 flex flex-wrap gap-2 justify-center">
                    {[
                      "What was iPhone revenue?",
                      "How much cash does the company have?",
                      "Did they beat earnings last quarter?",
                      "What's the revenue from China?",
                    ].map((q, i) => (
                      <button
                        key={i}
                        onClick={() => setChatInput(q)}
                        className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-full border border-slate-600"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-2 rounded-2xl ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 text-slate-200'
                    }`}
                  >
                    <ReactMarkdown className="text-sm">{msg.content}</ReactMarkdown>
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-slate-700 px-4 py-2 rounded-2xl">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <form onSubmit={sendChatMessage} className="p-3 border-t border-slate-700 flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={`Ask about ${symbol}...`}
                className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
                disabled={chatLoading}
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || chatLoading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}
      </div>

      {/* AI Analysis Section */}
      {aiLoading && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-500" />
            AI Analysis in Progress
          </h2>
          <div className="space-y-2">
            {aiProgress.map((p, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-slate-400">
                <div className={`w-2 h-2 rounded-full ${
                  p.phase === 'complete' ? 'bg-green-500' : 'bg-blue-500 animate-pulse'
                }`} />
                {p.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {aiAnalysis && (
        <div className="bg-slate-800 rounded-xl p-6 border border-purple-500/30">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-500" />
            AI Analysis (Qwen)
          </h2>
          <div className="ai-analysis">
            <ReactMarkdown>
              {aiAnalysis.synthesis || 'No analysis available'}
            </ReactMarkdown>
          </div>
        </div>
      )}

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
