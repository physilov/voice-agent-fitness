import httpx

from app.config import settings

# Nutrient IDs in the USDA FoodData Central schema
_NUTRIENT_IDS = {
    "calories": 1008,   # Energy (kcal)
    "protein_g": 1003,  # Protein
    "carbs_g": 1005,    # Carbohydrate, by difference
    "fat_g": 1004,      # Total lipid (fat)
    "fiber_g": 1079,    # Fiber, total dietary
}

# Prefer generic/foundation data over branded products for macros
_PREFERRED_DATA_TYPES = ["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"]


async def search_food(query: str, max_results: int = 5) -> list[dict]:
    """
    Search USDA FoodData Central and return up to max_results foods.

    Each result contains:
        name, data_type, per_100g {calories, protein_g, carbs_g, fat_g, fiber_g}

    Values are per 100 g of food. Returns [] on any error.
    """
    params = {
        "query": query,
        "api_key": settings.usda_api_key,
        "pageSize": 20,
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{settings.usda_base_url}/foods/search", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    foods = data.get("foods", [])

    # Sort so Foundation / SR Legacy come before Branded
    def _sort_key(f: dict) -> int:
        dt = f.get("dataType", "")
        try:
            return _PREFERRED_DATA_TYPES.index(dt)
        except ValueError:
            return len(_PREFERRED_DATA_TYPES)

    foods.sort(key=_sort_key)

    results = []
    for food in foods[:max_results]:
        nutrients_raw = food.get("foodNutrients", [])
        nutrient_map: dict[int, float] = {
            n["nutrientId"]: n.get("value", 0)
            for n in nutrients_raw
            if "nutrientId" in n and n.get("value") is not None
        }

        per_100g = {
            key: round(nutrient_map.get(nid, 0), 1)
            for key, nid in _NUTRIENT_IDS.items()
        }

        results.append({
            "name": food.get("description", query),
            "data_type": food.get("dataType", ""),
            "per_100g": per_100g,
        })

    return results
