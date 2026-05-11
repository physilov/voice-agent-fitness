from typing import Any
from pydantic import BaseModel


class UIComponent(BaseModel):
    type: str           # exercise_animation | workout_plan_card | progress_chart | nutrition_breakdown | pr_celebration
    data: dict[str, Any]


class AgentAction(BaseModel):
    type: str           # offer_form_check | schedule_reminder
    data: dict[str, Any] = {}


class CompoundResponse(BaseModel):
    text: str
    ui_components: list[UIComponent] = []
    actions: list[AgentAction] = []
