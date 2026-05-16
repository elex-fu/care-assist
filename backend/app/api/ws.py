import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_jwt
from app.core.ai_service import AIService
from app.core.exceptions import UnauthorizedException
from app.db.session import async_session
from app.models.member import Member
from app.models.ai_conversation import AIConversation
from app.models.indicator import IndicatorData
from app.models.report import Report
from sqlalchemy import select, desc
from datetime import datetime, timezone

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manage active WebSocket connections per user."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)


manager = ConnectionManager()


async def _get_member_from_token(token: str, db: AsyncSession) -> Optional[Member]:
    try:
        payload = decode_jwt(token)
    except (JWTError, UnauthorizedException):
        return None
    if payload.get("type") != "access":
        return None
    member_id = payload.get("sub")
    if not member_id:
        return None
    result = await db.execute(select(Member).where(Member.id == member_id))
    return result.scalar_one_or_none()


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


async def _handle_chat(websocket: WebSocket, member: Member, data: dict):
    """Handle AI chat message via WebSocket with streaming reply."""
    conversation_id = data.get("conversation_id")
    user_message = data.get("user_message", "").strip()

    if not conversation_id or not user_message:
        await websocket.send_json({
            "type": "chat_error",
            "message": "缺少对话ID或消息内容",
        })
        return

    async with async_session() as db:
        conv = await db.get(AIConversation, conversation_id)
        if not conv or conv.member_id != member.id:
            await websocket.send_json({
                "type": "chat_error",
                "message": "对话不存在或无权限",
            })
            return

        # Append user message
        now = datetime.now(timezone.utc).isoformat()
        messages = list(conv.messages or [])
        messages.append({"role": "user", "content": user_message, "timestamp": now})

        # Fetch context
        recent_indicators = await _get_recent_indicators(db, member.id)
        recent_reports = await _get_recent_reports(db, member.id)
        history = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]

        # Generate streaming reply
        ai_svc = AIService()
        reply_parts = []

        async for chunk in ai_svc.generate_reply_stream(
            member=member,
            conversation_history=history,
            user_message=user_message,
            page_context=conv.page_context,
            recent_indicators=recent_indicators if recent_indicators else None,
            recent_reports=recent_reports if recent_reports else None,
        ):
            reply_parts.append(chunk)
            await websocket.send_json({
                "type": "chat_chunk",
                "content": chunk,
            })

        # Send done
        await websocket.send_json({"type": "chat_done"})

        # Save full reply to DB
        full_reply = "".join(reply_parts)
        messages.append({
            "role": "assistant",
            "content": full_reply,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        conv.messages = messages
        await db.commit()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time communication."""
    async with async_session() as db:
        member = await _get_member_from_token(token, db)

    if not member:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await manager.connect(websocket, member.id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = data.get("type")
            if msg_type == "chat":
                await _handle_chat(websocket, member, data)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        manager.disconnect(member.id)
    except Exception:
        manager.disconnect(member.id)
