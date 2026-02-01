import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

export default function EarningsTrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold mb-4">Revenue & EPS Trend</h3>
        <p className="text-slate-400">No trend data available</p>
      </div>
    )
  }

  // Transform data for chart (reverse to show oldest first)
  const chartData = [...data]
    .reverse()
    .map((item) => ({
      quarter: `${item.fiscal_year} ${item.fiscal_quarter}`,
      revenue: item.revenue ? item.revenue / 1_000_000_000 : 0, // Convert to billions
      eps: item.eps || 0,
    }))

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h3 className="text-lg font-semibold mb-4">Revenue & EPS Trend</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
          <XAxis
            dataKey="quarter"
            stroke="#94a3b8"
            tick={{ fontSize: 11 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            yAxisId="revenue"
            orientation="left"
            stroke="#3b82f6"
            tickFormatter={(val) => `$${val}B`}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            yAxisId="eps"
            orientation="right"
            stroke="#10b981"
            tickFormatter={(val) => `$${val}`}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #475569',
              borderRadius: '8px',
            }}
            formatter={(value, name) => {
              if (name === 'Revenue') return [`$${value.toFixed(2)}B`, name]
              return [`$${value.toFixed(2)}`, name]
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: 10 }}
            formatter={(value) => (
              <span className="text-slate-300 text-sm">{value}</span>
            )}
          />
          <Line
            yAxisId="revenue"
            type="monotone"
            dataKey="revenue"
            name="Revenue"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
          <Line
            yAxisId="eps"
            type="monotone"
            dataKey="eps"
            name="EPS"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: '#10b981', strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
