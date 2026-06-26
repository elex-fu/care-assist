from app.core.indicator_search import get_indicator_metadata, search_indicators


class TestIndicatorSearch:
    def test_search_by_name(self):
        results = search_indicators("收缩压")
        assert len(results) >= 1
        assert any(r.key == "systolic_bp" for r in results)

    def test_search_by_alias(self):
        results = search_indicators("SBP")
        assert any(r.key == "systolic_bp" for r in results)

    def test_search_by_key(self):
        results = search_indicators("fasting_glucose")
        assert any(r.key == "fasting_glucose" for r in results)

    def test_search_empty_query_returns_all(self):
        results = search_indicators("")
        assert len(results) == len(
            {r.key for r in results}
        )  # no duplicates
        assert len(results) >= 5

    def test_search_limit(self):
        results = search_indicators("压", limit=2)
        assert len(results) <= 2

    def test_search_no_match(self):
        results = search_indicators("不存在的指标")
        assert results == []

    def test_get_indicator_metadata(self):
        meta = get_indicator_metadata("systolic_bp")
        assert meta is not None
        assert meta.name == "收缩压"
        assert meta.unit == "mmHg"
        assert meta.ref_range is not None

    def test_ref_range_format(self):
        meta = get_indicator_metadata("fasting_glucose")
        assert meta is not None
        assert "3.9" in meta.ref_range and "6.1" in meta.ref_range
