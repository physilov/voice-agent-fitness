import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import type { WeightTrendData } from '../types'

export default function WeightTrendChart({ data }: { data: WeightTrendData }) {
  const { entries, period_days, start_weight, current_weight, change_kg } = data
  const isDown = change_kg < 0
  const color = isDown ? '#34d399' : '#f87171'
  const sign = change_kg > 0 ? '+' : ''

  return (
    <div className="mt-2 bg-gray-900 rounded-2xl p-4 border border-gray-700">
      <div className="flex items-baseline justify-between mb-3">
        <span className="text-sm font-medium text-gray-300">
          Weight — last {period_days} days
        </span>
        <span className={`text-sm font-semibold ${isDown ? 'text-emerald-400' : 'text-red-400'}`}>
          {sign}{change_kg} kg
        </span>
      </div>

      <div className="flex gap-6 mb-3 text-xs text-gray-400">
        <div>
          <div className="text-gray-500">Start</div>
          <div className="text-white font-medium">{start_weight} kg</div>
        </div>
        <div>
          <div className="text-gray-500">Current</div>
          <div className="text-white font-medium">{current_weight} kg</div>
        </div>
      </div>

      {entries.length > 1 ? (
        <ResponsiveContainer width="100%" height={140}>
          <LineChart data={entries} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="date"
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#9ca3af' }}
              itemStyle={{ color: color }}
              formatter={(v: number) => [`${v} kg`, 'Weight']}
            />
            <ReferenceLine y={start_weight} stroke="#374151" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="weight_kg"
              stroke={color}
              strokeWidth={2}
              dot={{ fill: color, r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-xs text-gray-500 text-center py-4">
          Log more weigh-ins to see a trend
        </p>
      )}
    </div>
  )
}
