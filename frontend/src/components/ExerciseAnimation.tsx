import type { ExerciseAnimationData } from '../types'

export default function ExerciseAnimation({ data }: { data: ExerciseAnimationData }) {
  return (
    <div className="mt-3 rounded-xl overflow-hidden bg-gray-900 border border-gray-700 max-w-sm">
      {data.gif_url && (
        <img src={data.gif_url} alt={data.name} className="w-full object-cover" />
      )}
      <div className="p-4">
        <h3 className="font-semibold text-white capitalize mb-1">{data.name}</h3>
        {(data.target_muscle || data.body_part) && (
          <p className="text-xs text-gray-400 mb-3">
            {[data.body_part, data.target_muscle].filter(Boolean).join(' · ')}
          </p>
        )}
        {data.coaching_cues.length > 0 && (
          <ul className="space-y-1">
            {data.coaching_cues.map((cue, i) => (
              <li key={i} className="flex gap-2 text-sm text-gray-300">
                <span className="text-purple-400 font-bold shrink-0">{i + 1}.</span>
                {cue}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
