import { TrendingUp, TrendingDown } from 'lucide-react'

export default function StatCard({ title, value, subtitle, icon: Icon, trend }) {
  return (
    <div className="bg-slate-800 rounded-lg p-5 border border-slate-700">
      <div className="flex items-center justify-between mb-3">
        <span className="text-slate-400 text-sm">{title}</span>
        {Icon && (
          <Icon
            className={`h-5 w-5 ${
              trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-slate-400'
            }`}
          />
        )}
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      {subtitle && (
        <div
          className={`text-sm flex items-center ${
            trend === 'up'
              ? 'text-green-500'
              : trend === 'down'
              ? 'text-red-500'
              : 'text-slate-400'
          }`}
        >
          {trend === 'up' && <TrendingUp className="h-3 w-3 mr-1" />}
          {trend === 'down' && <TrendingDown className="h-3 w-3 mr-1" />}
          {subtitle}
        </div>
      )}
    </div>
  )
}
