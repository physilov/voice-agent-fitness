import type { NutritionData } from '../types'

function MacroBar({
  label,
  grams,
  color,
  total,
}: {
  label: string
  grams?: number
  color: string
  total: number
}) {
  if (grams == null) return null
  const pct = total > 0 ? Math.round((grams * 4) / (total) * 100) : 0
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-300">{grams}g</span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  )
}

export default function NutritionBreakdown({ data }: { data: NutritionData }) {
  return (
    <div className="mt-3 rounded-xl bg-gray-900 border border-gray-700 p-4 max-w-xs">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold text-white">{data.meal}</h3>
          <p className="text-xs text-gray-400">Nutrition breakdown</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-purple-400">{data.calories}</p>
          <p className="text-xs text-gray-400">kcal</p>
        </div>
      </div>

      <div className="space-y-3">
        <MacroBar label="Protein" grams={data.protein_g} color="bg-blue-500" total={data.calories} />
        <MacroBar label="Carbs" grams={data.carbs_g} color="bg-yellow-500" total={data.calories} />
        <MacroBar label="Fat" grams={data.fat_g} color="bg-red-500" total={data.calories} />
      </div>
    </div>
  )
}
