import os
import shutil
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.ocr_service import get_ocr_service
from app.core.indicator_engine import IndicatorEngine
from app.models.member import Member
from app.models.report import Report
from app.models.indicator import IndicatorData
from app.schemas.report import ReportCreate, ReportOut, ReportListOut, OCRTriggerOut, OCRResultItem
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/reports", tags=["报告管理"])

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
    hospital: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    report_date: Optional[str] = Form(None),
    images: list[UploadFile] = File(default=[]),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)

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
    for img_path in report.images or []:
        try:
            Path(img_path).unlink(missing_ok=True)
        except Exception:
            pass
    # Try to remove empty dirs
    try:
        base = _ensure_upload_dir()
        member_dir = base / report.member_id
        if member_dir.exists():
            for sub in member_dir.iterdir():
                if sub.is_dir() and not any(sub.iterdir()):
                    sub.rmdir()
            if not any(member_dir.iterdir()):
                member_dir.rmdir()
    except Exception:
        pass

    await db.delete(report)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})


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

    ocr_service = get_ocr_service()
    all_extracted = []
    for img_path in report.images:
        items = await ocr_service.extract_indicators(img_path)
        all_extracted.extend(items)

    # Save extracted indicators to report
    report.extracted_indicators = all_extracted
    report.ocr_status = "completed"
    await db.commit()
    await db.refresh(report)

    # Also create IndicatorData records for each extracted indicator
    target = await db.get(Member, report.member_id)
    age_months = None
    if target and target.birth_date:
        today = date.today()
        age_months = (today.year - target.birth_date.year) * 12 + (today.month - target.birth_date.month)
        if today.day < target.birth_date.day:
            age_months -= 1
        age_months = max(0, age_months)

    for item in all_extracted:
        status = IndicatorEngine.judge(item["value"], item["indicator_key"], age_months)
        deviation = IndicatorEngine.calculate_deviation(
            item["value"], item["indicator_key"], age_months
        )
        indicator = IndicatorData(
            member_id=report.member_id,
            indicator_key=item["indicator_key"],
            indicator_name=item["indicator_name"],
            value=item["value"],
            unit=item["unit"],
            status=status,
            deviation_percent=round(deviation, 4),
            record_date=report.report_date or date.today(),
            source_report_id=report.id,
        )
        db.add(indicator)

    await db.commit()

    return ResponseWrapper(
        data=OCRTriggerOut(
            report_id=report.id,
            ocr_status=report.ocr_status,
            extracted=[OCRResultItem(**item) for item in all_extracted],
        )
    )
