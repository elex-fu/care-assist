import pytest


class TestIndicatorMetadata:
    async def test_metadata_requires_auth(self, client):
        resp = await client.get("/api/indicators/metadata?q=血压")
        assert resp.status_code == 401

    async def test_search_metadata_by_name(self, auth_client):
        resp = await auth_client.get("/api/indicators/metadata?q=血压")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert any(item["key"] in ("systolic_bp", "diastolic_bp") for item in data)

    async def test_search_metadata_by_alias(self, auth_client):
        resp = await auth_client.get("/api/indicators/metadata?q=SBP")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert any(item["key"] == "systolic_bp" for item in data)

    async def test_search_metadata_empty(self, auth_client):
        resp = await auth_client.get("/api/indicators/metadata?q=不存在的指标")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_search_metadata_limit(self, auth_client):
        resp = await auth_client.get("/api/indicators/metadata?q=&limit=3")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 3

    async def test_search_metadata_shape(self, auth_client):
        resp = await auth_client.get("/api/indicators/metadata?q=收缩压")
        assert resp.status_code == 200
        item = resp.json()["data"][0]
        assert item["key"] == "systolic_bp"
        assert item["name"] == "收缩压"
        assert item["unit"] == "mmHg"
        assert "aliases" in item
        assert "ref_range" in item
