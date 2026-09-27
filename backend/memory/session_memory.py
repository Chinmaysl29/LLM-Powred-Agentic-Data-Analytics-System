"""Session Memory Module delegating to AIMemoryLayer."""

from backend.memory.ai_memory_layer import get_ai_memory_layer, AIMemoryLayer

class SessionMemory:
    """Enterprise Session Memory."""
    def __init__(self, memory_layer: AIMemoryLayer | None = None) -> None:
        self.memory = memory_layer or get_ai_memory_layer()

    def get_session(self, workspace_id: str, session_id: str) -> dict:
        return self.memory._ensure_session(workspace_id, session_id)
