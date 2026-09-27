"""Context Manager Module for multi-turn coreference resolution."""

from backend.memory.ai_memory_layer import get_ai_memory_layer, AIMemoryLayer

class ContextManager:
    """Enterprise Context Manager."""
    def __init__(self, memory_layer: AIMemoryLayer | None = None) -> None:
        self.memory = memory_layer or get_ai_memory_layer()

    def resolve_query(self, query: str, workspace_id: str, session_id: str) -> dict:
        return self.memory.resolve_contextual_query(query, workspace_id, session_id)
