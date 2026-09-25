"""Unit tests for Phase 7.7 — Inventory Optimization Engine."""

import pytest
from backend.recommendations.inventory_recommendations import InventoryOptimizationEngine


def test_forecast_demand_exceeds_stock_generates_reorder_recommendation():
    """Test 1: Forecast demand exceeds stock -> Reorder recommendation."""
    engine = InventoryOptimizationEngine()
    inventory_data = {
        "sku": "PROD-ALPHA",
        "current_stock": 200.0,
        "forecasted_demand": 800.0,  # Stockout imminent
        "unit_cost": 40.0,
    }

    result = engine.analyze_inventory(inventory_data)

    assert isinstance(result.inventory_actions, list)
    assert len(result.inventory_actions) >= 1
    assert result.expected_inventory_savings > 0

    action = result.inventory_actions[0]
    assert action["type"] == "reorder"
    assert "Reorder Recommendation" in action["recommendation"]
    assert action["priority"] == "Critical"
    assert action["units_to_order"] >= 600.0


def test_overstocking_generates_destocking_action():
    """Test overstock detection and holding cost savings calculation."""
    engine = InventoryOptimizationEngine()
    inventory_data = {
        "sku": "PROD-BETA",
        "current_stock": 5000.0,
        "forecasted_demand": 1000.0,  # 5x overstock
        "unit_cost": 50.0,
    }

    result = engine.analyze_inventory(inventory_data)

    assert len(result.inventory_actions) >= 1
    action = result.inventory_actions[0]
    assert action["type"] == "destock"
    assert "Destocking" in action["recommendation"]
    assert action["expected_savings"] > 0


def test_reorder_point_calculation():
    """Test ROP formula (daily_demand * lead_time + safety_stock)."""
    engine = InventoryOptimizationEngine()
    # 20 units/day * 10 days + 50 safety stock = 250
    rop = engine.calculate_reorder_point(lead_time_days=10, daily_demand=20.0, safety_stock=50.0)
    assert rop == 250.0
