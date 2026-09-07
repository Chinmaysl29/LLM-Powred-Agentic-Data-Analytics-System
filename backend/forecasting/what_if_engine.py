"""Phase 6.8 — What-If Analysis Engine Service.

Evaluates ad-hoc business changes (e.g. 'marketing +20%', 'price -5%')
using forecaster sensitivity elasticities, predicting business metric outcomes,
growth impact, and stated risk from prediction interval expansion.
"""

import logging
import re
from typing import Any

import numpy as np

from backend.app.schemas.forecasting import (
    DataPoint,
    UnifiedForecastOutput,
    WhatIfAnalysisInput,
    WhatIfAnalysisOutput,
)

logger = logging.getLogger(__name__)


class WhatIfAnalysisEngine:
    """Exploratory sensitivity engine predicting outcomes of single ad-hoc changes."""

    # Standard empirical business elasticities when specific model coefficients are absent
    DEFAULT_ELASTICITIES = {
        "marketing": 0.35,       # +10% marketing -> ~+3.5% revenue
        "ad_spend": 0.35,
        "advertising": 0.35,
        "price": -0.80,          # Price elasticity: +10% price -> -8% volume, net revenue impact
        "pricing": -0.80,
        "customer": 0.85,        # +10% customer volume -> ~+8.5% revenue
        "customers": 0.85,
        "users": 0.80,
        "demand": 0.95,          # +10% demand -> ~+9.5% revenue
        "inventory": 0.50,       # +10% inventory available -> ~+5% fulfillment/sales
        "stock": 0.50,
    }

    def __init__(self, custom_elasticities: dict[str, float] | None = None) -> None:
        self.elasticities = {**self.DEFAULT_ELASTICITIES, **(custom_elasticities or {})}

    def _parse_change_string(self, change_str: str) -> tuple[str, float]:
        """Parse natural language or structured change (e.g. 'marketing +20%', 'price -5%')."""
        clean_str = change_str.strip().lower()

        # Extract percentage or numeric multiplier
        pct_match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", clean_str)
        if pct_match:
            pct_val = float(pct_match.group(1)) / 100.0
        else:
            # Try plain number like '+0.20'
            num_match = re.search(r"([+-]?\d+(?:\.\d+)?)", clean_str)
            pct_val = float(num_match.group(1)) if num_match else 0.10

        # Identify driver domain
        driver_found = "generic"
        for driver in self.elasticities:
            if driver in clean_str:
                driver_found = driver
                break

        return driver_found, pct_val

    def analyze(
        self,
        what_if_input: WhatIfAnalysisInput,
    ) -> WhatIfAnalysisOutput:
        """Simulate single ad-hoc change and compute predicted revenue, growth, and risk."""
        change_str = what_if_input.input_change or getattr(what_if_input, "what_if_query", "") or ""
        driver, pct_change = self._parse_change_string(change_str)

        logger.info(
            "What-If analysis initiated for input_change='%s' (driver=%s, delta=%.2f%%)",
            change_str, driver, pct_change * 100
        )

        hist_data = what_if_input.historical_series or getattr(what_if_input, "series", None)

        # Baseline revenue estimation from base_forecast or historical series
        if what_if_input.base_forecast:
            base_fcast = what_if_input.base_forecast
            base_total = float(np.sum(base_fcast.forecast))
            base_intervals = [u - l for u, l in zip(base_fcast.upper_bound, base_fcast.lower_bound)]
            avg_base_interval = float(np.mean(base_intervals)) if base_intervals else (base_total * 0.10)

            # Check if model diagnostics provide feature importance for sensitivity tuning
            feature_imp = base_fcast.diagnostics.get("feature_importance", {})
            driver_weight = feature_imp.get(driver, self.elasticities.get(driver, 0.50))
        elif hist_data:
            hist_vals = [float(dp.value) for dp in hist_data]
            base_total = float(np.sum(hist_vals[-30:])) if len(hist_vals) >= 30 else float(np.sum(hist_vals))
            avg_base_interval = float(np.std(hist_vals)) * 2.0 if len(hist_vals) > 1 else base_total * 0.10
            driver_weight = self.elasticities.get(driver, 0.50)

        else:
            # Default baseline unit (e.g. 10M)
            base_total = 10_000_000.0
            avg_base_interval = 1_000_000.0
            driver_weight = self.elasticities.get(driver, 0.50)

        # Compute net expected growth rate
        if driver in ["price", "pricing"]:
            # Revenue = Price * Volume; where Volume = Volume_0 * (1 + price_elasticity * delta_price)
            # Net Revenue Factor = (1 + delta_price) * (1 + price_elasticity * delta_price)
            price_elasticity = self.elasticities.get("price", -0.80)
            vol_factor = 1.0 + (price_elasticity * pct_change)
            growth_rate = float(((1.0 + pct_change) * vol_factor) - 1.0)
        else:
            growth_rate = float(pct_change * driver_weight)

        predicted_revenue = float(round(base_total * (1.0 + growth_rate), 2))

        # Risk Definition: forecast interval width relative to baseline
        # Larger changes widen prediction intervals, increasing stated risk
        interval_expansion_factor = 1.0 + (abs(pct_change) * 0.75)
        new_interval_width = avg_base_interval * interval_expansion_factor
        # Risk metric defined as relative expansion: (new_width - base_width) / base_total
        predicted_risk = float(round((new_interval_width - avg_base_interval) / (base_total + 1e-8), 4))
        # Clamp to realistic bounded scale (0.00 to 1.00)
        predicted_risk = float(max(0.01, min(1.0, predicted_risk)))

        logger.info(
            "What-If analysis completed predicted_rev=%.2f growth=%.2f%% risk=%.4f",
            predicted_revenue, growth_rate * 100, predicted_risk
        )

        return WhatIfAnalysisOutput(
            input_change=change_str,
            predicted_revenue=predicted_revenue,
            predicted_growth=round(growth_rate, 4),
            predicted_risk=predicted_risk,
        )
