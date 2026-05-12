from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class AIConversationCreate(BaseModel):
    member_id: str
    page_context: str | None = None


class AIConversationMessageRequest(BaseModel):
    user_message: str


class AIConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    page_context: str | None
    messages: list[dict[str, Any]]
    created_at: Any
    updated_at: Any


class AIConversationListOut(BaseModel):
    id: str
    member_id: str
    page_context: str | None
    message_count: int
    last_message_preview: str
    created_at: Any
    updated_at: Any


class AIReplyOut(BaseModel):
    conversation_id: str
    reply: str
    messages: list[dict[str, Any]]
