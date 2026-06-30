from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.report import Report
from app.schemas.ocr import OCRPipelineResult, OCRResultItem


@pytest.mark.asyncio
async def test_ocr_endpoint_auto_generates_ai_summary(auth_client, test_member, db):
    """After OCR succeeds, the report should have a generated AI summary."""
    report = Report(
        member_id=test_member.id,
        type="lab",
        images=["uploads/reports/demo.jpg"],
        ocr_status="pending",
        report_date=date(2024, 6, 15),
        extracted_indicators=[],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    fake_extracted = [
        OCRResultItem(
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=145,
            unit="mmHg",
            raw_text="收缩压 145 mmHg",
        )
    ]
    fake_pipeline_result = OCRPipelineResult(
        extracted=fake_extracted, raw_text="收缩压 145 mmHg", provider="kimi"
    )
    expected_summary = f"{test_member.name}的报告显示收缩压偏高，建议关注。"

    with patch(
        "app.api.reports.run_ocr_pipeline", new_callable=AsyncMock
    ) as mock_pipeline, patch(
        "app.api.reports.AIService.summarize_report", new_callable=AsyncMock
    ) as mock_summary:
        mock_pipeline.return_value = fake_pipeline_result
        mock_summary.return_value = expected_summary

        resp = await auth_client.post(f"/api/reports/{report.id}/ocr")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ocr_status"] == "completed"
    assert len(data["extracted"]) == 1
    mock_summary.assert_awaited_once()

    # Use a fresh GET request to verify the summary was persisted (test session
    # and API session are in different DB transactions).
    get_resp = await auth_client.get(f"/api/reports/{report.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["ai_summary"] == expected_summary


@pytest.mark.asyncio
async def test_ocr_endpoint_summary_failure_does_not_break_ocr(auth_client, test_member, db):
    """AI summary failure should be logged but not fail the OCR response."""
    report = Report(
        member_id=test_member.id,
        type="lab",
        images=["uploads/reports/demo.jpg"],
        ocr_status="pending",
        report_date=date(2024, 6, 15),
        extracted_indicators=[],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    fake_extracted = [
        OCRResultItem(
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=145,
            unit="mmHg",
            raw_text="收缩压 145 mmHg",
        )
    ]
    fake_pipeline_result = OCRPipelineResult(
        extracted=fake_extracted, raw_text="收缩压 145 mmHg", provider="kimi"
    )

    with patch(
        "app.api.reports.run_ocr_pipeline", new_callable=AsyncMock
    ) as mock_pipeline, patch(
        "app.api.reports.AIService.summarize_report", new_callable=AsyncMock
    ) as mock_summary:
        mock_pipeline.return_value = fake_pipeline_result
        mock_summary.side_effect = RuntimeError("AI service unavailable")

        resp = await auth_client.post(f"/api/reports/{report.id}/ocr")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ocr_status"] == "completed"
