"""Schemas for Conversation Memory (Phase 5.9)."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A single message in a conversation turn."""
    role: MessageRole = Field(..., description="Speaker role")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class ConversationSession(BaseModel):
    """Full multi-turn conversation session."""
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[Message] = Field(default_factory=list, description="Ordered message history")
    summary: Optional[str] = Field(default=None, description="Rolling summarization of older turns")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
