"""Phase 17.1 deterministic analytics and chat contracts."""

import asyncio

import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.natural_language_analytics import NaturalLanguageAnalyticsService


def test_count_aggregation_top_n_and_trend_queries():
    async def scenario():
        data = pd.DataFrame({"product": ["A", "A", "B", "C"], "region": ["North", "North", "South", "South"], "revenue": [10, 30, 20, 5], "sale_date": ["2026-01-01", "2026-02-01", "2026-01-05", "2026-02-05"]})
        service = NaturalLanguageAnalyticsService()
        assert "4" in (await service.analyze("count records", dataframe=data))["answer"]
        total = await service.analyze("total revenue by region", dataframe=data)
        assert total["data"][0]["region"] == "North"
        top = await service.analyze("top 2 products by revenue", dataframe=data)
        assert top["data"][0]["product"] == "A"
        trend = await service.analyze("revenue trend over time", dataframe=data)
        assert len(trend["data"]) == 2
    asyncio.run(scenario())


def test_chat_validation_and_dataset_requirement():
    with TestClient(create_app()) as client:
        invalid = client.post("/api/v1/chat", json={"message": ""})
        assert invalid.status_code == 422
        response = client.post("/api/v1/chat", json={"message": "What are the top products?"})
        assert response.status_code == 200
        assert response.json()["intent"] == "analytics"
        assert "dataset" in response.json()["answer"].lower()
