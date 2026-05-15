export interface UIComponent {
  type:
    | 'exercise_animation'
    | 'workout_plan_card'
    | 'progress_chart'
    | 'nutrition_breakdown'
    | 'pr_celebration'
  data: Record<string, unknown>
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  ui_components: UIComponent[]
  image_url?: string
}

// ── Per-component data shapes ─────────────────────────────────────────────────

export interface ExerciseAnimationData {
  name: string
  gif_url: string
  target_muscle?: string
  body_part?: string
  equipment?: string
  instructions?: string[]
  coaching_cues: string[]
}

export interface WorkoutDay {
  exercise: string
  sets: number
  reps: number | string
  rest_seconds?: number
}

export interface WorkoutPlanData {
  name: string
  plan: Record<string, Record<string, WorkoutDay[]>>
}

export interface ProgressChartData {
  period_days: number
  workout_count: number
  workout_dates: string[]
}

export interface NutritionData {
  meal: string
  calories: number
  protein_g?: number
  carbs_g?: number
  fat_g?: number
}

export interface PRCelebrationData {
  exercise: string
  weight_kg: number
  reps: number
  previous_kg?: number
}
