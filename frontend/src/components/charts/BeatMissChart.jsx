import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'

export default function BeatMissChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold mb-4">Earnings Surprises</h3>
        <p className="text-slate-400">No earnings surprise data available</p>
      </div>
    )
  }

  // Transform data for chart (reverse to show oldest first)
  const chartData = [...data]
    .reverse()
    .slice(-12)
    .map((item) => ({
      date: formatDate(item.date),
      surprise: item.eps_surprise_percent || 0,
      beat: item.beat_miss === 'BEAT',
      miss: item.beat_miss === 'MISS',
      actual: item.actual_eps,
      estimated: item.estimated_eps,
    }))

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h3 className="text-lg font-semibold mb-4">Earnings Surprise History</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
          <XAxis
            dataKey="date"
            stroke="#94a3b8"
            tick={{ fontSize: 11 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            stroke="#94a3b8"
            tickFormatter={(val) => `${val}%`}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #475569',
              borderRadius: '8px',
            }}
            formatter={(value, name) => [
              `${value.toFixed(2)}%`,
              'Surprise',
            ]}
            labelFormatter={(label) => `Quarter: ${label}`}
          />
          <ReferenceLine y={0} stroke="#64748b" />
          <Bar dataKey="surprise" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.beat ? '#10b981' : entry.miss ? '#ef4444' : '#f59e0b'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex justify-center gap-6 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span className="text-slate-400">Beat</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-red-500" />
          <span className="text-slate-400">Miss</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-yellow-500" />
          <span className="text-slate-400">Meet</span>
        </div>
      </div>
    </div>
  )
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  return `${date.getFullYear()} Q${Math.ceil((date.getMonth() + 1) / 3)}`
}
