"""Task router component managing agent dispatching."""

from backend.app.services.agent_registry import AgentRegistry, BaseAgentRunner, DefaultAgentRunner

TaskRouter = AgentRegistry

__all__ = ["TaskRouter", "AgentRegistry", "BaseAgentRunner", "DefaultAgentRunner"]
