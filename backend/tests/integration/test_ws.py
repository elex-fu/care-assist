"""WebSocket and ws.py integration tests."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_jwt
from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.ai_conversation import AIConversation
from fastapi import WebSocketDisconnect

from app.api.ws import (
    ConnectionManager,
    _get_member_from_token,
    _get_recent_indicators,
    _get_recent_reports,
    websocket_endpoint,
)


# ---------- ConnectionManager unit tests ----------

@pytest.mark.asyncio
class TestConnectionManager:
    async def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        await manager.connect(mock_ws, "user-1")
        assert "user-1" in manager.active_connections
        manager.disconnect("user-1")
        assert "user-1" not in manager.active_connections

    async def test_send_personal_message(self):
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        await manager.connect(mock_ws, "user-1")
        await manager.send_personal_message({"type": "test"}, "user-1")
        mock_ws.send_json.assert_awaited_once_with({"type": "test"})

    async def test_send_personal_message_to_disconnected(self):
        manager = ConnectionManager()
        # Should not raise
        await manager.send_personal_message({"type": "test"}, "no-user")

    async def test_broadcast(self):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, "user-1")
        await manager.connect(ws2, "user-2")
        await manager.broadcast({"type": "alert"})
        ws1.send_json.assert_awaited_once_with({"type": "alert"})
        ws2.send_json.assert_awaited_once_with({"type": "alert"})


# ---------- Helper function tests ----------

@pytest.mark.asyncio
class TestGetMemberFromToken:
    async def test_valid_access_token(self, db, test_creator):
        token = create_jwt(str(test_creator.id), token_type="access")
        result = await _get_member_from_token(token, db)
        assert result is not None
        assert result.id == test_creator.id

    async def test_invalid_token(self, db):
        result = await _get_member_from_token("bad-token", db)
        assert result is None

    async def test_refresh_token_returns_none(self, db, test_creator):
        token = create_jwt(str(test_creator.id), token_type="refresh")
        result = await _get_member_from_token(token, db)
        assert result is None

    async def test_nonexistent_member(self, db):
        token = create_jwt("nonexistent-id", token_type="access")
        result = await _get_member_from_token(token, db)
        assert result is None


@pytest.mark.asyncio
class TestGetRecentIndicators:
    async def test_returns_indicators(self, db, test_member):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            record_date=date(2024, 6, 15),
        ))
        await db.commit()

        result = await _get_recent_indicators(db, test_member.id)
        assert len(result) == 1
        assert result[0]["indicator_key"] == "systolic_bp"
        assert result[0]["value"] == 120.0

    async def test_empty_when_no_data(self, db, test_member):
        result = await _get_recent_indicators(db, test_member.id)
        assert result == []


@pytest.mark.asyncio
class TestGetRecentReports:
    async def test_returns_reports(self, db, test_member):
        db.add(Report(
            member_id=test_member.id,
            type="lab",
            hospital="测试医院",
            report_date=date(2024, 6, 15),
            ocr_status="completed",
            extracted_indicators=[{"key": "bp", "value": "120"}],
        ))
        await db.commit()

        result = await _get_recent_reports(db, test_member.id)
        assert len(result) == 1
        assert result[0]["type"] == "lab"
        assert result[0]["extracted_indicators"] == [{"key": "bp", "value": "120"}]

    async def test_empty_when_no_data(self, db, test_member):
        result = await _get_recent_reports(db, test_member.id)
        assert result == []


# ---------- WebSocket endpoint tests (direct function calls) ----------

@pytest.mark.asyncio
class TestWebSocketEndpointDirect:
    async def test_websocket_ping_pong(self, test_creator):
        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=[
            json.dumps({"type": "ping"}),
            WebSocketDisconnect(),
        ])

        with patch("app.api.ws._get_member_from_token", return_value=test_creator):
            await websocket_endpoint(mock_ws, token="any")

        calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
        assert {"type": "pong"} in calls

    async def test_websocket_invalid_json(self, test_creator):
        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=[
            "not json",
            WebSocketDisconnect(),
        ])

        with patch("app.api.ws._get_member_from_token", return_value=test_creator):
            await websocket_endpoint(mock_ws, token="any")

        calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
        assert any(c["type"] == "error" and "Invalid JSON" in c["message"] for c in calls)

    async def test_websocket_unknown_type(self, test_creator):
        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=[
            json.dumps({"type": "unknown_action"}),
            WebSocketDisconnect(),
        ])

        with patch("app.api.ws._get_member_from_token", return_value=test_creator):
            await websocket_endpoint(mock_ws, token="any")

        calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
        assert any(c["type"] == "error" and "Unknown message type" in c["message"] for c in calls)

    async def test_websocket_invalid_token(self):
        mock_ws = AsyncMock()
        await websocket_endpoint(mock_ws, token="invalid")
        mock_ws.close.assert_awaited_once_with(code=1008, reason="Invalid token")

    async def test_websocket_chat_missing_fields(self, test_creator):
        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=[
            json.dumps({"type": "chat", "conversation_id": "", "user_message": ""}),
            WebSocketDisconnect(),
        ])

        with patch("app.api.ws._get_member_from_token", return_value=test_creator):
            await websocket_endpoint(mock_ws, token="any")

        calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
        assert any(c["type"] == "chat_error" and "缺少对话ID或消息内容" in c["message"] for c in calls)


@pytest.mark.asyncio
class TestWebSocketChatFlowDirect:
    async def test_websocket_chat_unauthorized_conversation(self, db, test_creator, test_member):
        conv = AIConversation(
            id="conv-unauth",
            member_id=test_member.id,
            messages=[],
            page_context="home",
        )
        db.add(conv)
        await db.commit()

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=[
            json.dumps({
                "type": "chat",
                "conversation_id": "conv-unauth",
                "user_message": "你好",
            }),
            WebSocketDisconnect(),
        ])

        with patch("app.api.ws._get_member_from_token", return_value=test_creator):
            await websocket_endpoint(mock_ws, token="any")

        calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
        assert any(c["type"] == "chat_error" and "对话不存在或无权限" in c["message"] for c in calls)

    async def test_websocket_chat_success(self, db, test_creator):
        conv = AIConversation(
            id="conv-ok",
            member_id=test_creator.id,
            messages=[],
            page_context="home",
        )
        db.add(conv)
        await db.commit()

        mock_ws = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=[
            json.dumps({
                "type": "chat",
                "conversation_id": "conv-ok",
                "user_message": "你好",
            }),
            WebSocketDisconnect(),
        ])

        async def mock_stream(*args, **kwargs):
            yield "你好"
            yield "世界"

        with patch("app.api.ws._get_member_from_token", return_value=test_creator):
            with patch("app.api.ws.AIService.generate_reply_stream", mock_stream):
                await websocket_endpoint(mock_ws, token="any")

        calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
        assert any(c["type"] == "chat_chunk" and c["content"] == "你好" for c in calls)
        assert any(c["type"] == "chat_chunk" and c["content"] == "世界" for c in calls)
        assert any(c["type"] == "chat_done" for c in calls)

        # Verify DB was updated
        await db.refresh(conv)
        assert len(conv.messages) == 2
        assert conv.messages[0]["role"] == "user"
        assert conv.messages[1]["role"] == "assistant"
