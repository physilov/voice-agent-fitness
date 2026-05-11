import re

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ExerciseCache


class ExerciseDBService:
    def __init__(self):
        self._headers = {
            "X-RapidAPI-Key": settings.exercisedb_api_key,
            "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
        }

    def _normalize(self, name: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", name.lower().strip())

    async def get_exercise(self, db: AsyncSession, exercise_name: str) -> dict | None:
        normalized = self._normalize(exercise_name)

        result = await db.execute(
            select(ExerciseCache).where(ExerciseCache.name_normalized.contains(normalized))
        )
        cached = result.scalar_one_or_none()
        if cached:
            return self._to_dict(cached)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.exercisedb_base_url}/exercises/name/{exercise_name}",
                headers=self._headers,
                params={"limit": 1},
                timeout=10.0,
            )

        if response.status_code != 200 or not response.json():
            return None

        data = response.json()[0]
        exercise = ExerciseCache(
            id=data["id"],
            name=data["name"],
            name_normalized=self._normalize(data["name"]),
            gif_url=data["gifUrl"],
            target_muscle=data["target"],
            body_part=data["bodyPart"],
            equipment=data["equipment"],
            instructions=data.get("instructions", []),
        )
        db.add(exercise)
        await db.commit()
        return self._to_dict(exercise)

    def _to_dict(self, exercise: ExerciseCache) -> dict:
        return {
            "id": exercise.id,
            "name": exercise.name,
            "gif_url": exercise.gif_url,
            "target_muscle": exercise.target_muscle,
            "body_part": exercise.body_part,
            "equipment": exercise.equipment,
            "instructions": exercise.instructions,
        }


exercisedb_service = ExerciseDBService()
