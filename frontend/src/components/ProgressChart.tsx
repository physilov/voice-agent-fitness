import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import type { ProgressChartData } from '../types'

export default function ProgressChart({ data }: { data: ProgressChartData }) {
  // Bucket workout dates into weeks
  const buckets: Record<string, number> = {}
  data.workout_dates.forEach((iso) => {
    const d = new Date(iso)
    const week = `${d.getMonth() + 1}/${d.getDate()}`
    buckets[week] = (buckets[week] ?? 0) + 1
  })

  const chartData = Object.entries(buckets).map(([date, count]) => ({ date, count }))

  return (
    <div className="mt-3 rounded-xl bg-gray-900 border border-gray-700 p-4 max-w-lg">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-white">Workout Progress</h3>
        <span className="text-purple-400 font-bold">{data.workout_count} workouts</span>
      </div>
      <p className="text-xs text-gray-400 mb-3">Last {data.period_days} days</p>

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }}
              labelStyle={{ color: '#f3f4f6' }}
              itemStyle={{ color: '#a78bfa' }}
            />
            <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-sm text-gray-500 text-center py-8">No workouts logged yet</p>
      )}
    </div>
  )
}
