import { useState } from 'react'
import type { WorkoutPlanData, WorkoutDay } from '../types'

function DayCard({ day, exercises }: { day: string; exercises: WorkoutDay[] }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2">{day}</p>
      <ul className="space-y-1">
        {exercises.map((ex, i) => (
          <li key={i} className="text-sm text-gray-300">
            <span className="text-white font-medium">{ex.exercise}</span>
            {' — '}
            {ex.sets}×{ex.reps}
            {ex.rest_seconds && (
              <span className="text-gray-500 text-xs ml-1">({ex.rest_seconds}s rest)</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function WorkoutPlanCard({ data }: { data: WorkoutPlanData }) {
  const weeks = Object.keys(data.plan).sort()
  const [activeWeek, setActiveWeek] = useState(weeks[0] ?? '')

  const days = activeWeek ? data.plan[activeWeek] : {}

  return (
    <div className="mt-3 rounded-xl bg-gray-900 border border-gray-700 p-4 max-w-lg">
      <h3 className="font-semibold text-white mb-3">{data.name}</h3>

      {/* Week tabs */}
      <div className="flex gap-2 flex-wrap mb-4">
        {weeks.map((w) => (
          <button
            key={w}
            onClick={() => setActiveWeek(w)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              activeWeek === w
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {w.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {Object.entries(days).map(([day, exercises]) => (
          <DayCard key={day} day={day} exercises={exercises as WorkoutDay[]} />
        ))}
      </div>
    </div>
  )
}
