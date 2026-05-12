import type { UIComponent } from '../types'
import ExerciseAnimation from './ExerciseAnimation'
import WorkoutPlanCard from './WorkoutPlanCard'
import ProgressChart from './ProgressChart'
import NutritionBreakdown from './NutritionBreakdown'
import PRCelebration from './PRCelebration'

export default function UIComponentRenderer({ component }: { component: UIComponent }) {
  switch (component.type) {
    case 'exercise_animation':
      return <ExerciseAnimation data={component.data as never} />
    case 'workout_plan_card':
      return <WorkoutPlanCard data={component.data as never} />
    case 'progress_chart':
      return <ProgressChart data={component.data as never} />
    case 'nutrition_breakdown':
      return <NutritionBreakdown data={component.data as never} />
    case 'pr_celebration':
      return <PRCelebration data={component.data as never} />
    default:
      return null
  }
}
