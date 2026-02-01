import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function QuarterlyResultsTable({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold mb-4">Quarterly Results</h3>
        <p className="text-slate-400">No quarterly data available</p>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h3 className="text-lg font-semibold mb-4">Quarterly Results</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-700">
              <th className="text-left py-3 px-2">Quarter</th>
              <th className="text-right py-3 px-2">Revenue</th>
              <th className="text-right py-3 px-2">EPS</th>
              <th className="text-right py-3 px-2">Gross Margin</th>
              <th className="text-right py-3 px-2">Net Margin</th>
              <th className="text-right py-3 px-2">Rev Growth YoY</th>
              <th className="text-right py-3 px-2">EPS Growth YoY</th>
            </tr>
          </thead>
          <tbody>
            {data.map((quarter, index) => (
              <tr
                key={index}
                className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors"
              >
                <td className="py-3 px-2 font-medium">
                  {quarter.fiscal_year} {quarter.fiscal_quarter}
                </td>
                <td className="text-right py-3 px-2">
                  {formatCurrency(quarter.revenue)}
                </td>
                <td className="text-right py-3 px-2">
                  ${quarter.eps?.toFixed(2) || 'N/A'}
                </td>
                <td className="text-right py-3 px-2">
                  {quarter.gross_margin?.toFixed(1)}%
                </td>
                <td className="text-right py-3 px-2">
                  {quarter.net_margin?.toFixed(1)}%
                </td>
                <td className="text-right py-3 px-2">
                  <GrowthIndicator value={quarter.revenue_growth_yoy} />
                </td>
                <td className="text-right py-3 px-2">
                  <GrowthIndicator value={quarter.eps_growth_yoy} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function GrowthIndicator({ value }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-500">N/A</span>
  }

  const isPositive = value >= 0
  const Icon = isPositive ? TrendingUp : TrendingDown
  const colorClass = isPositive ? 'text-green-500' : 'text-red-500'

  return (
    <span className={`flex items-center justify-end ${colorClass}`}>
      <Icon className="h-3 w-3 mr-1" />
      {isPositive ? '+' : ''}
      {value.toFixed(1)}%
    </span>
  )
}

function formatCurrency(value) {
  if (!value) return 'N/A'
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`
  } else if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`
  }
  return `$${value.toLocaleString()}`
}
