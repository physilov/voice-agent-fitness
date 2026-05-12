from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.usda_food import search_food
from app.agent.tools import handle_tool_call
from app.db.models import User


_USDA_RESPONSE = {
    "foods": [
        {
            "fdcId": 171477,
            "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
            "dataType": "SR Legacy",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "value": 165.0, "unitName": "kcal"},
                {"nutrientId": 1003, "nutrientName": "Protein", "value": 31.02, "unitName": "g"},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "value": 0.0, "unitName": "g"},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "value": 3.57, "unitName": "g"},
                {"nutrientId": 1079, "nutrientName": "Fiber, total dietary", "value": 0.0, "unitName": "g"},
            ],
        },
        {
            "fdcId": 999999,
            "description": "Chicken Breast, Branded",
            "dataType": "Branded",
            "foodNutrients": [
                {"nutrientId": 1008, "value": 120.0},
                {"nutrientId": 1003, "value": 26.0},
                {"nutrientId": 1005, "value": 1.0},
                {"nutrientId": 1004, "value": 2.0},
            ],
        },
    ]
}


def _mock_httpx(json_data: dict):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = json_data

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


# ── search_food service ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_returns_macros_per_100g():
    with patch("app.services.usda_food.httpx.AsyncClient", return_value=_mock_httpx(_USDA_RESPONSE)):
        results = await search_food("chicken breast")

    assert len(results) == 2
    first = results[0]
    assert first["name"] == "Chicken, broilers or fryers, breast, meat only, cooked, roasted"
    assert first["per_100g"]["calories"] == 165.0
    assert first["per_100g"]["protein_g"] == 31.0
    assert first["per_100g"]["fat_g"] == 3.6


@pytest.mark.asyncio
async def test_foundation_sorted_before_branded():
    with patch("app.services.usda_food.httpx.AsyncClient", return_value=_mock_httpx(_USDA_RESPONSE)):
        results = await search_food("chicken breast")

    assert results[0]["data_type"] == "SR Legacy"
    assert results[1]["data_type"] == "Branded"


@pytest.mark.asyncio
async def test_returns_empty_list_on_http_error():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("timeout"))

    with patch("app.services.usda_food.httpx.AsyncClient", return_value=mock_client):
        results = await search_food("anything")

    assert results == []


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_foods():
    with patch("app.services.usda_food.httpx.AsyncClient", return_value=_mock_httpx({"foods": []})):
        results = await search_food("xyz123notafood")

    assert results == []


@pytest.mark.asyncio
async def test_respects_max_results():
    many_foods = {"foods": [_USDA_RESPONSE["foods"][0]] * 10}
    with patch("app.services.usda_food.httpx.AsyncClient", return_value=_mock_httpx(many_foods)):
        results = await search_food("chicken", max_results=3)

    assert len(results) == 3


# ── search_food tool handler ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_handler_returns_formatted_string():
    user = User(id="u1", phone_number="+1", onboarding_complete=True)
    db = AsyncMock()

    mock_results = [
        {
            "name": "Chicken breast, cooked",
            "data_type": "SR Legacy",
            "per_100g": {"calories": 165.0, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "fiber_g": 0.0},
        }
    ]

    with patch("app.agent.tools.usda_search_food", AsyncMock(return_value=mock_results)):
        result, ui = await handle_tool_call("search_food", {"query": "chicken breast"}, user, db)

    assert "165" in result
    assert "31.0" in result
    assert "USDA results" in result
    assert ui == []


@pytest.mark.asyncio
async def test_tool_handler_no_results_returns_fallback():
    user = User(id="u1", phone_number="+1", onboarding_complete=True)
    db = AsyncMock()

    with patch("app.agent.tools.usda_search_food", AsyncMock(return_value=[])):
        result, _ = await handle_tool_call("search_food", {"query": "unicorn meat"}, user, db)

    assert "No USDA data" in result
    assert "Estimate" in result
