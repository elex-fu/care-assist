from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_service import AIService
from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.member import Member
from app.models.ai_conversation import AIConversation
from app.models.indicator import IndicatorData
from app.models.report import Report
from app.schemas.ai_conversation import (
    AIConversationCreate,
    AIConversationMessageRequest,
    AIConversationOut,
    AIConversationListOut,
    AIReplyOut,
)
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/ai-conversations", tags=["AI对话"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


async def _get_recent_indicators(db: AsyncSession, member_id: str, limit: int = 10):
    stmt = (
        select(IndicatorData)
        .where(IndicatorData.member_id == member_id)
        .order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "indicator_key": i.indicator_key,
            "indicator_name": i.indicator_name,
            "value": float(i.value),
            "unit": i.unit,
            "status": i.status,
            "record_date": str(i.record_date),
        }
        for i in items
    ]


async def _get_recent_reports(db: AsyncSession, member_id: str, limit: int = 5):
    stmt = (
        select(Report)
        .where(Report.member_id == member_id)
        .order_by(desc(Report.report_date), desc(Report.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "type": r.type,
            "ocr_status": r.ocr_status,
            "extracted_indicators": r.extracted_indicators or [],
        }
        for r in items
    ]


@router.post("", response_model=ResponseWrapper[AIConversationOut])
async def create_conversation(
    payload: AIConversationCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    conv = AIConversation(
        member_id=target.id,
        page_context=payload.page_context,
        messages=[],
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ResponseWrapper(data=AIConversationOut.model_validate(conv))


@router.get("", response_model=ResponseWrapper[list[AIConversationListOut]])
async def list_conversations(
    member_id: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = (
        select(AIConversation)
        .where(AIConversation.member_id == member_id)
        .order_by(desc(AIConversation.updated_at))
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    data = []
    for conv in items:
        msgs = conv.messages or []
        preview = ""
        if msgs:
            last = msgs[-1]
            preview = last.get("content", "")[:50]
        data.append(
            AIConversationListOut(
                id=conv.id,
                member_id=conv.member_id,
                page_context=conv.page_context,
                message_count=len(msgs),
                last_message_preview=preview,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )
    return ResponseWrapper(data=data)


@router.post("/{conversation_id}/messages", response_model=ResponseWrapper[AIReplyOut])
async def send_message(
    conversation_id: str,
    payload: AIConversationMessageRequest,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(AIConversation, conversation_id)
    if not conv:
        raise NotFoundException("对话不存在")

    target = await _verify_member_in_family(conv.member_id, current, db)

    # Append user message
    now = datetime.now(timezone.utc).isoformat()
    messages = list(conv.messages or [])
    messages.append({"role": "user", "content": payload.user_message, "timestamp": now})

    # Fetch context data
    recent_indicators = await _get_recent_indicators(db, target.id)
    recent_reports = await _get_recent_reports(db, target.id)

    # Build conversation history for AI service (exclude latest user message from history param)
    history = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]

    # Generate reply
    ai_svc = AIService()
    reply = await ai_svc.generate_reply(
        member=target,
        conversation_history=history,
        user_message=payload.user_message,
        page_context=conv.page_context,
        recent_indicators=recent_indicators if recent_indicators else None,
        recent_reports=recent_reports if recent_reports else None,
    )

    # Append assistant message
    messages.append({"role": "assistant", "content": reply, "timestamp": datetime.now(timezone.utc).isoformat()})
    conv.messages = messages
    await db.commit()
    await db.refresh(conv)

    return ResponseWrapper(
        data=AIReplyOut(
            conversation_id=conv.id,
            reply=reply,
            messages=conv.messages,
        )
    )


@router.delete("/{conversation_id}", response_model=ResponseWrapper[dict])
async def delete_conversation(
    conversation_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(AIConversation, conversation_id)
    if not conv:
        raise NotFoundException("对话不存在")

    await _verify_member_in_family(conv.member_id, current, db)

    await db.delete(conv)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})
