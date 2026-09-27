"""Conversation Memory Module delegating to AIMemoryLayer."""

from backend.memory.ai_memory_layer import get_ai_memory_layer, AIMemoryLayer

class ConversationMemory:
    """Enterprise Conversation Memory."""
    def __init__(self, memory_layer: AIMemoryLayer | None = None) -> None:
        self.memory = memory_layer or get_ai_memory_layer()

    def add_turn(self, workspace_id: str, session_id: str, user_message: str, ai_response: str, intent: str | None = None) -> dict:
        return self.memory.record_turn(workspace_id, session_id, user_message, ai_response, intent)

    def get_history(self, workspace_id: str, session_id: str, limit: int = 10) -> list:
        return self.memory.get_conversation_history(workspace_id, session_id, limit)
