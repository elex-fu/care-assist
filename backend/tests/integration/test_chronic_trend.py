from datetime import date, timedelta

import pytest
from sqlalchemy import delete

from app.models.indicator import IndicatorData


@pytest.mark.asyncio
async def test_chronic_trend_returns_multiple_series(auth_client, test_member, db):
    """The chronic trend endpoint should return time series for all package indicators."""
    # Clean any existing data for this member.
    await db.execute(delete(IndicatorData).where(IndicatorData.member_id == test_member.id))
    await db.commit()

    base_date = date.today() - timedelta(days=20)
    records = [
        # Systolic BP: rising trend
        IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=125,
            unit="mmHg",
            status="normal",
            record_date=base_date,
        ),
        IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=138,
            unit="mmHg",
            status="high",
            record_date=base_date + timedelta(days=7),
        ),
        IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=145,
            unit="mmHg",
            status="high",
            record_date=base_date + timedelta(days=14),
        ),
        # Diastolic BP
        IndicatorData(
            member_id=test_member.id,
            indicator_key="diastolic_bp",
            indicator_name="舒张压",
            value=82,
            unit="mmHg",
            status="normal",
            record_date=base_date,
        ),
        IndicatorData(
            member_id=test_member.id,
            indicator_key="diastolic_bp",
            indicator_name="舒张压",
            value=88,
            unit="mmHg",
            status="normal",
            record_date=base_date + timedelta(days=7),
        ),
    ]
    for r in records:
        db.add(r)
    await db.commit()

    resp = await auth_client.get(
        f"/api/indicators/chronic/hypertension/trend?member_id={test_member.id}&days=30"
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["package"] == "hypertension"
    assert data["member_id"] == test_member.id
    assert len(data["series"]) == 2

    series_by_key = {s["indicator_key"]: s for s in data["series"]}
    assert "systolic_bp" in series_by_key
    assert "diastolic_bp" in series_by_key

    systolic = series_by_key["systolic_bp"]
    assert len(systolic["points"]) == 3
    assert [p["value"] for p in systolic["points"]] == [125.0, 138.0, 145.0]
    assert systolic["points"][0]["record_date"] == base_date.isoformat()
    assert systolic["trend_direction"] == "up"


@pytest.mark.asyncio
async def test_chronic_trend_unknown_package_returns_error(auth_client, test_member):
    resp = await auth_client.get(
        f"/api/indicators/chronic/unknown/trend?member_id={test_member.id}&days=30"
    )
    assert resp.status_code == 404
