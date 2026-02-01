import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function PriceChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No price data available
      </div>
    )
  }

  // Sort data by date (oldest first) and format for chart
  const chartData = [...data]
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .map(item => ({
      date: item.date,
      price: item.close || item.adjClose,
      volume: item.volume,
    }))

  // Calculate price range for gradient
  const prices = chartData.map(d => d.price).filter(p => p)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceChange = chartData.length > 1
    ? chartData[chartData.length - 1].price - chartData[0].price
    : 0
  const isPositive = priceChange >= 0

  // Format date for tooltip
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  // Format date for X-axis (shorter)
  const formatXAxis = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      year: '2-digit'
    })
  }

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg">
          <p className="text-slate-400 text-xs mb-1">{formatDate(label)}</p>
          <p className="text-white font-semibold">
            ${payload[0].value?.toFixed(2)}
          </p>
          {payload[0].payload.volume && (
            <p className="text-slate-400 text-xs mt-1">
              Vol: {(payload[0].payload.volume / 1e6).toFixed(1)}M
            </p>
          )}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-slate-400">Period High: </span>
            <span className="font-medium text-emerald-400">${maxPrice.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-slate-400">Period Low: </span>
            <span className="font-medium text-red-400">${minPrice.toFixed(2)}</span>
          </div>
        </div>
        <div className={`font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{priceChange.toFixed(2)} ({((priceChange / chartData[0].price) * 100).toFixed(1)}%)
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={isPositive ? "#10b981" : "#ef4444"}
                  stopOpacity={0.3}
                />
                <stop
                  offset="95%"
                  stopColor={isPositive ? "#10b981" : "#ef4444"}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatXAxis}
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis
              domain={['auto', 'auto']}
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => `$${val}`}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="price"
              stroke={isPositive ? "#10b981" : "#ef4444"}
              strokeWidth={2}
              fill="url(#priceGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
