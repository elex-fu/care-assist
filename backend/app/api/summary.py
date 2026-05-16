from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import ForbiddenException
from app.models.member import Member
from app.services.summary_service import SummaryService
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/summary", tags=["汇总"])


@router.get("/annual", response_model=ResponseWrapper[dict])
async def annual_summary(
    year: int | None = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if not member.family_id:
        raise ForbiddenException("用户未加入家庭")

    data = await SummaryService.get_annual_summary(db, member.family_id, year)
    return ResponseWrapper(data=data)
