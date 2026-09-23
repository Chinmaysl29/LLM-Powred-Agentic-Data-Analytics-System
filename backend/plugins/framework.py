"""
Phase 12.10.1 — Plugin Framework
Dynamic plugin loading, lifecycle state machine, semantic versioning checks,
dependency graph resolution, and structured logging.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import logging
import re
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.plugins.framework")


class PluginState(str, Enum):
    INITIALIZED = "INITIALIZED"
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    UNLOADED = "UNLOADED"
    ERROR = "ERROR"


class PluginMetadata(BaseModel):
    plugin_id: str
    plugin_name: str
    plugin_type: str # "agent", "connector", "workflow", "dashboard"
    version: str = "1.0.0"
    author: str = "Enterprise Developer"
    min_platform_version: str = "2.0.0"
    dependencies: List[str] = Field(default_factory=list)
    entry_point: Optional[str] = None
    description: str = ""


class PluginFramework:
    """
    Manages dynamic plugin lifecycle, semantic version validation,
    and dependency resolution for the AI Data Analyst OS platform.
    """

    PLATFORM_VERSION = "2.4.0"

    def __init__(self):
        self._plugins: Dict[str, PluginMetadata] = {}
        self._states: Dict[str, PluginState] = {}
        self._instances: Dict[str, Any] = {}

    def load_plugin(self, metadata: PluginMetadata, instance: Optional[Any] = None) -> bool:
        """Dynamically load and validate a plugin into the runtime."""
        # 1. Version Compatibility Check
        if not self.check_version_compatibility(metadata.min_platform_version, self.PLATFORM_VERSION):
            logger.error("Plugin %s requires platform version >= %s, current is %s",
                         metadata.plugin_id, metadata.min_platform_version, self.PLATFORM_VERSION)
            self._states[metadata.plugin_id] = PluginState.ERROR
            return False

        # 2. Check Dependencies
        for dep in metadata.dependencies:
            if dep not in self._plugins or self._states.get(dep) not in [PluginState.LOADED, PluginState.ACTIVE]:
                logger.warning("Unresolved dependency '%s' for plugin %s", dep, metadata.plugin_id)

        self._plugins[metadata.plugin_id] = metadata
        self._instances[metadata.plugin_id] = instance
        self._states[metadata.plugin_id] = PluginState.LOADED
        logger.info("Loaded plugin %s (v%s)", metadata.plugin_id, metadata.version)
        return True

    def activate_plugin(self, plugin_id: str) -> bool:
        """Activate a loaded plugin."""
        if self._states.get(plugin_id) not in [PluginState.LOADED, PluginState.DISABLED]:
            return False
        self._states[plugin_id] = PluginState.ACTIVE
        logger.info("Activated plugin %s", plugin_id)
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        """Deactivate an active plugin."""
        if self._states.get(plugin_id) != PluginState.ACTIVE:
            return False
        self._states[plugin_id] = PluginState.DISABLED
        logger.info("Disabled plugin %s", plugin_id)
        return True

    def unload_plugin(self, plugin_id: str) -> bool:
        """Safely detach and unload plugin from runtime."""
        if plugin_id not in self._plugins:
            return False
        self._states[plugin_id] = PluginState.UNLOADED
        if plugin_id in self._instances:
            del self._instances[plugin_id]
        logger.info("Unloaded plugin %s", plugin_id)
        return True

    def get_plugin_state(self, plugin_id: str) -> Optional[PluginState]:
        return self._states.get(plugin_id)

    @staticmethod
    def check_version_compatibility(required_version: str, current_version: str) -> bool:
        """Basic semantic version comparison (major.minor.patch)."""
        def parse_v(v: str) -> tuple[int, ...]:
            parts = re.findall(r"\d+", v)
            return tuple(int(p) for p in parts[:3])

        return parse_v(current_version) >= parse_v(required_version)
