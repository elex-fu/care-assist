import contextlib
import os
import shutil
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_service import AIService
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.indicator_engine import IndicatorEngine
from app.core.logging import get_logger
from app.core.ocr_service import get_ocr_service
from app.core.security import get_current_member, get_db
from app.models.indicator import IndicatorData
from app.models.member import Member
from app.models.reminder import Reminder
from app.models.report import Report
from app.schemas.common import ResponseWrapper
from app.schemas.report import (
    OCRResultItem,
    OCRTriggerOut,
    ReportAISummaryOut,
    ReportListOut,
    ReportOut,
)
from app.services.ocr_pipeline import run_ocr_pipeline

router = APIRouter(prefix="/reports", tags=["报告管理"])
logger = get_logger("app.api.reports")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads/reports"))


def _ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


def _save_upload(member_id: str, report_id: str, file: UploadFile) -> str:
    base = _ensure_upload_dir()
    dest_dir = base / member_id / report_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    original = file.filename or "upload.bin"
    suffix = Path(original).suffix
    filename = f"{uuid.uuid4().hex[:16]}{suffix}"
    dest_path = dest_dir / filename

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return str(dest_path)


@router.post("", response_model=ResponseWrapper[ReportOut])
async def create_report(
    member_id: str = Form(...),
    type: str = Form(...),
    hospital: str | None = Form(None),
    department: str | None = Form(None),
    report_date: str | None = Form(None),
    images: list[UploadFile] = File(default=[]),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    parsed_date = date.fromisoformat(report_date) if report_date else None

    report = Report(
        member_id=member_id,
        type=type,
        hospital=hospital,
        department=department,
        report_date=parsed_date,
        images=[],
        ocr_status="pending",
    )
    db.add(report)
    await db.flush()

    saved_urls = []
    for img in images:
        if img.filename:
            path = _save_upload(member_id, report.id, img)
            saved_urls.append(path)

    report.images = saved_urls
    await db.commit()
    await db.refresh(report)
    logger.info(
        f"Report created: id={report.id} member_id={member_id} type={type} "
        f"images={len(saved_urls)}"
    )
    return ResponseWrapper(data=ReportOut.model_validate(report))


@router.get("", response_model=ResponseWrapper[ReportListOut])
async def list_reports(
    member_id: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = (
        select(Report)
        .where(Report.member_id == member_id)
        .order_by(desc(Report.report_date), desc(Report.created_at))
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(
        data=ReportListOut(reports=[ReportOut.model_validate(r) for r in items])
    )


@router.get("/{report_id}", response_model=ResponseWrapper[ReportOut])
async def get_report(
    report_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if not report:
        raise NotFoundException("报告不存在")

    await _verify_member_in_family(report.member_id, current, db)

    return ResponseWrapper(data=ReportOut.model_validate(report))


@router.delete("/{report_id}", response_model=ResponseWrapper[dict])
async def delete_report(
    report_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if not report:
        raise NotFoundException("报告不存在")

    await _verify_member_in_family(report.member_id, current, db)

    # Clean up uploaded files
    with contextlib.suppress(Exception):
        for img_path in report.images or []:
            Path(img_path).unlink(missing_ok=True)
    # Try to remove empty dirs
    with contextlib.suppress(Exception):
        base = _ensure_upload_dir()
        member_dir = base / report.member_id
        if member_dir.exists():
            for sub in member_dir.iterdir():
                if sub.is_dir() and not any(sub.iterdir()):
                    sub.rmdir()
            if not any(member_dir.iterdir()):
                member_dir.rmdir()

    await db.delete(report)
    await db.commit()
    logger.info(f"Report deleted: id={report_id} member_id={report.member_id}")
    return ResponseWrapper(data={"deleted": True})


def _calculate_age_months(birth_date: date | None) -> int | None:
    if not birth_date:
        return None
    today = date.today()
    months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
    if today.day < birth_date.day:
        months -= 1
    return max(0, months)


def _indicator_threshold(indicator_key: str, age_months: int | None) -> dict:
    config = IndicatorEngine.THRESHOLDS.get(indicator_key, {})
    threshold = config.get("threshold", {})
    if age_months and "age_groups" in config:
        for group in config["age_groups"]:
            if age_months <= group["max_age_months"]:
                threshold = group
                break
    return threshold


@router.post("/{report_id}/ocr", response_model=ResponseWrapper[OCRTriggerOut])
async def trigger_ocr(
    report_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if not report:
        raise NotFoundException("报告不存在")

    await _verify_member_in_family(report.member_id, current, db)

    if not report.images:
        raise ForbiddenException("报告没有图片，无法执行OCR")

    # Prefer the modern OCR pipeline; fallback to legacy service on failure.
    extracted_items: list[OCRResultItem] = []
    try:
        pipeline_result = await run_ocr_pipeline(report.images)
        extracted_items = list(pipeline_result.extracted)
    except Exception as exc:
        logger.warning(f"OCR pipeline failed, falling back to legacy OCR: {exc}")

    if not extracted_items:
        logger.info("Pipeline returned no indicators, trying legacy OCR service")
        ocr_service = get_ocr_service()
        for img_path in report.images:
            try:
                legacy_items = await ocr_service.extract_indicators(img_path)
                for raw in legacy_items:
                    name = raw.get("indicator_name") or raw.get("name", "")
                    key = raw.get("indicator_key") or raw.get("key", "")
                    value = raw.get("value")
                    unit = raw.get("unit", "")
                    if value is None:
                        continue
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue
                    extracted_items.append(
                        OCRResultItem(
                            indicator_key=key or name,
                            indicator_name=name or key,
                            value=value,
                            unit=unit,
                            raw_text=raw.get("raw_text", ""),
                        )
                    )
            except Exception as exc:
                logger.warning(f"Legacy OCR failed for {img_path}: {exc}")

    # Deduplicate by indicator_key keeping the first occurrence.
    seen_keys: set[str] = set()
    deduplicated: list[OCRResultItem] = []
    for item in extracted_items:
        if item.indicator_key in seen_keys:
            continue
        seen_keys.add(item.indicator_key)
        deduplicated.append(item)
    extracted_items = deduplicated

    # Save extracted indicators to report
    report.extracted_indicators = [item.model_dump() for item in extracted_items]
    report.ocr_status = "completed"
    await db.commit()
    await db.refresh(report)

    # Create IndicatorData records with Decimal precision and thresholds.
    target = await db.get(Member, report.member_id)
    age_months = _calculate_age_months(target.birth_date if target else None)

    for item in extracted_items:
        status = IndicatorEngine.judge(item.value, item.indicator_key, age_months)
        deviation = IndicatorEngine.calculate_deviation(
            item.value, item.indicator_key, age_months
        )
        threshold = _indicator_threshold(item.indicator_key, age_months)
        indicator = IndicatorData(
            member_id=report.member_id,
            indicator_key=item.indicator_key,
            indicator_name=item.indicator_name,
            value=Decimal(str(item.value)),
            unit=item.unit,
            lower_limit=(
                Decimal(str(threshold.get("lower")))
                if threshold.get("lower") is not None
                else None
            ),
            upper_limit=(
                Decimal(str(threshold.get("upper")))
                if threshold.get("upper") is not None
                else None
            ),
            status=status,
            deviation_percent=Decimal(str(round(deviation, 4))),
            record_date=report.report_date or date.today(),
            source_report_id=report.id,
        )
        db.add(indicator)

    await db.commit()

    # Auto-create reminders for abnormal indicators identified by OCR
    for item in extracted_items:
        item_status = IndicatorEngine.judge(item.value, item.indicator_key, age_months)
        if item_status in ("high", "critical"):
            db.add(
                Reminder(
                    member_id=report.member_id,
                    type="checkup",
                    title=f"指标异常复查：{item.indicator_name}",
                    description=(
                        f"报告 OCR 识别到 {item.indicator_name} "
                        f"为 {item_status}，建议复查"
                    ),
                    scheduled_date=(report.report_date or date.today()) + timedelta(days=7),
                    status="pending",
                    related_report_id=report.id,
                    related_indicator=item.indicator_key,
                    priority="high",
                )
            )
    await db.commit()

    logger.info(
        f"OCR completed: report_id={report_id} extracted={len(extracted_items)} "
        f"indicators_created={len(extracted_items)}"
    )
    # Normalize pipeline/legacy OCR items to the response schema.
    schema_items = [OCRResultItem(**item.model_dump()) for item in extracted_items]
    return ResponseWrapper(
        data=OCRTriggerOut(
            report_id=report.id,
            ocr_status=report.ocr_status,
            extracted=schema_items,
        )
    )


@router.post("/{report_id}/ai-summary", response_model=ResponseWrapper[ReportAISummaryOut])
async def generate_ai_summary(
    report_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if not report:
        raise NotFoundException("报告不存在")

    target = await _verify_member_in_family(report.member_id, current, db)

    ai_svc = AIService()
    summary = await ai_svc.summarize_report(member=target, report=report)
    report.ai_summary = summary
    await db.commit()
    await db.refresh(report)

    logger.info(f"Report AI summary generated: report_id={report_id}")
    return ResponseWrapper(
        data=ReportAISummaryOut(
            id=report.id,
            ai_summary=report.ai_summary,
            updated_at=report.updated_at,
        )
    )
