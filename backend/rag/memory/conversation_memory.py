"""Conversation Memory — Multi-turn session storage (Phase 5.9)."""

import uuid
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional

from backend.app.schemas.memory import ConversationSession, Message, MessageRole


class ConversationMemory:
    """Thread-safe in-memory conversation session store."""

    def __init__(self, max_window: int = 20) -> None:
        self.max_window = max_window
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = Lock()

    def create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        sid = session_id or str(uuid.uuid4())
        session = ConversationSession(session_id=sid)
        with self._lock:
            self._sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> ConversationSession:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ConversationSession(session_id=session_id)
            return self._sessions[session_id]

    def add_message(self, session_id: str, role: MessageRole, content: str) -> Message:
        session = self.get_or_create_session(session_id)
        message = Message(role=role, content=content)
        with self._lock:
            session.messages.append(message)
            # Apply sliding window trimming
            if len(session.messages) > self.max_window:
                session.messages = session.messages[-self.max_window:]
        return message

    def get_history(self, session_id: str) -> List[Message]:
        session = self.get_session(session_id)
        if session is None:
            return []
        return list(session.messages)

    def get_formatted_history(self, session_id: str) -> str:
        """Return conversation history as a formatted string for LLM context."""
        messages = self.get_history(session_id)
        if not messages:
            return ""
        lines = []
        for msg in messages:
            prefix = msg.role.value.capitalize()
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].messages = []

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())
