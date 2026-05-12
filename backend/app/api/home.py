from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException
from app.core.ai_service import AIService
from app.models.member import Member
from app.models.family import Family
from app.schemas.common import ResponseWrapper
from app.services.member_service import MemberService

router = APIRouter(prefix="/home", tags=["首页"])


@router.get("/dashboard", response_model=ResponseWrapper[dict])
async def get_dashboard(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    family = await db.get(Family, member.family_id)
    if not family:
        raise NotFoundException("家庭不存在")

    member_cards = await MemberService.get_family_dashboard(db, family.id)

    # Generate real AI daily summary based on family health data
    ai_svc = AIService()
    ai_summary = await ai_svc.generate_family_summary(member_cards)

    return ResponseWrapper(
        data={
            "family": {
                "id": family.id,
                "name": family.name,
                "invite_code": family.invite_code,
            },
            "members": member_cards,
            "ai_summary": ai_summary,
        }
    )
