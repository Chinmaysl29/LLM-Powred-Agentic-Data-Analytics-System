"""
Phase 12.10.6 — Dashboard Plugin SDK
Developer interfaces for creating custom dashboard visualizations,
composite KPI cards, interactive heatmaps, and custom layout components.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import time
from pydantic import BaseModel, Field


class DashboardWidgetRender(BaseModel):
    widget_id: str
    title: str
    component_type: str # "react_custom_chart", "custom_kpi", "custom_table"
    rendered_payload: Dict[str, Any]
    width_units: int = 4 # grid column width (1..12)
    rendered_at: float = Field(default_factory=time.time)


class BaseDashboardWidgetPlugin(ABC):
    """
    Abstract Base Class for custom analytics dashboard widgets.
    """

    def __init__(self, widget_id: str, title: str, component_type: str = "react_custom_chart"):
        self.widget_id = widget_id
        self.title = title
        self.component_type = component_type

    @abstractmethod
    def render(self, input_data: Dict[str, Any]) -> DashboardWidgetRender:
        """Render widget visualization payload from live dataset."""
        pass

    def get_layout_spec(self) -> Dict[str, Any]:
        """Grid positioning rules."""
        return {
            "widget_id": self.widget_id,
            "min_width": 2,
            "default_width": 4,
            "resizable": True
        }
