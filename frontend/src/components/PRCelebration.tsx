import { Trophy } from 'lucide-react'
import type { PRCelebrationData } from '../types'

export default function PRCelebration({ data }: { data: PRCelebrationData }) {
  const improvement =
    data.previous_kg != null
      ? `+${(data.weight_kg - data.previous_kg).toFixed(1)} kg from ${data.previous_kg} kg`
      : 'First recorded lift!'

  return (
    <div className="mt-3 rounded-xl bg-gradient-to-br from-yellow-900/40 to-purple-900/40 border border-yellow-500/40 p-4 max-w-xs">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="text-yellow-400 shrink-0" size={20} />
        <span className="text-yellow-400 font-bold text-sm uppercase tracking-wider">
          New Personal Record!
        </span>
      </div>
      <p className="text-white font-semibold capitalize mb-1">{data.exercise}</p>
      <p className="text-3xl font-bold text-white">
        {data.weight_kg} kg
        <span className="text-lg font-normal text-gray-300 ml-2">× {data.reps} reps</span>
      </p>
      <p className="text-xs text-yellow-300/80 mt-2">{improvement}</p>
    </div>
  )
}
