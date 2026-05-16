from datetime import date
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.member import Member
from app.services.export_service import export_excel, export_pdf
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/export", tags=["数据导出"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.get("/excel")
async def export_excel_endpoint(
    member_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)
    output = await export_excel(db, target, start_date, end_date)
    filename = f"{target.name}_health_data_{date.today()}.xlsx"
    encoded = quote(filename)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/pdf")
async def export_pdf_endpoint(
    member_id: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)
    output = await export_pdf(db, target)
    filename = f"{target.name}_health_report_{date.today()}.pdf"
    encoded = quote(filename)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
