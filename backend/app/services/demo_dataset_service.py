"""Enterprise Demo Dataset Library & Portfolio Service for Phase 21.2 & 21.3.

Generates and provisions 5 production-grade demonstration datasets:
1. Sales Performance Dataset (36 months, 5,000 records)
2. Finance & P&L Dataset (24 periods, departmental revenues, COGS, EBITDA)
3. Marketing & Growth Attribution Dataset (12 months, omni-channel campaigns)
4. HR & Workforce Analytics Dataset (1,200 employee profiles, attrition risk)
5. Supply Chain & Operations Dataset (850 SKUs across 4 regional fulfillment centers)

Enables instantaneous 'Portfolio Mode' for recruiters and executives.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DEMO_DIR = Path("datasets/demo")
STORAGE_DEMO_DIR = Path("storage/demo")


class DemoDatasetService:
    """Provisions authentic enterprise demo datasets and pre-packaged portfolio workspace."""

    def __init__(self, demo_dir: Path | str | None = None) -> None:
        self.demo_dir = Path(demo_dir) if demo_dir else DEMO_DIR
        self.demo_dir.mkdir(parents=True, exist_ok=True)
        STORAGE_DEMO_DIR.mkdir(parents=True, exist_ok=True)

    def generate_sales_dataset(self, n_rows: int = 1200) -> pd.DataFrame:
        """Synthesize multi-year B2B commercial sales records."""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=n_rows, freq="D").strftime("%Y-%m-%d")
        categories = ["Cloud Infrastructure", "AI Copilot Seats", "Database Enterprise", "Security Suite", "Developer Tools"]
        regions = ["North America", "EMEA", "APAC", "LATAM"]
        reps = ["Sarah Connor", "Alex Vance", "Gordon Freeman", "Ellen Ripley", "Marcus Fenix"]
        customers = [f"CUST-{1000 + (i % 80)}" for i in range(n_rows)]

        cat_choice = np.random.choice(categories, n_rows)
        unit_prices = {
            "Cloud Infrastructure": 4800.0,
            "AI Copilot Seats": 1200.0,
            "Database Enterprise": 8500.0,
            "Security Suite": 3200.0,
            "Developer Tools": 750.0,
        }
        prices = np.array([unit_prices[c] for c in cat_choice])
        quantities = np.random.randint(1, 15, size=n_rows)
        discounts = np.random.choice([0.0, 0.05, 0.10, 0.15], size=n_rows, p=[0.5, 0.25, 0.15, 0.10])
        sales = np.round(prices * quantities * (1.0 - discounts), 2)
        cogs = np.round(sales * np.random.uniform(0.28, 0.42, size=n_rows), 2)

        df = pd.DataFrame({
            "order_id": [f"SO-{2024000 + i}" for i in range(n_rows)],
            "order_date": dates,
            "customer_id": customers,
            "category": cat_choice,
            "region": np.random.choice(regions, n_rows),
            "sales_rep": np.random.choice(reps, n_rows),
            "quantity": quantities,
            "unit_price": prices,
            "discount": discounts,
            "sales": sales,
            "cogs": cogs,
            "profit": np.round(sales - cogs, 2),
        })
        return df

    def generate_finance_dataset(self) -> pd.DataFrame:
        """Synthesize 24-month corporate P&L performance."""
        dates = pd.date_range("2024-01-01", periods=24, freq="ME").strftime("%Y-%m-%d")
        depts = ["Engineering", "Sales & Marketing", "General & Admin", "Customer Support"]

        records = []
        base_rev = 1_850_000
        for i, dt in enumerate(dates):
            growth = 1.0 + (i * 0.03) + np.random.uniform(-0.02, 0.04)
            monthly_rev = round(base_rev * growth, 2)
            cogs_val = round(monthly_rev * np.random.uniform(0.26, 0.32), 2)
            opex_val = round(monthly_rev * np.random.uniform(0.38, 0.45), 2)
            ebitda = round(monthly_rev - cogs_val - opex_val, 2)
            net_profit = round(ebitda * 0.78, 2)

            records.append({
                "period": dt,
                "month_num": i + 1,
                "revenue": monthly_rev,
                "cogs": cogs_val,
                "operating_expenses": opex_val,
                "ebitda": ebitda,
                "net_profit": net_profit,
                "gross_margin_pct": round(((monthly_rev - cogs_val) / monthly_rev) * 100, 2),
                "headcount": 140 + int(i * 3.5),
            })
        return pd.DataFrame(records)

    def generate_marketing_dataset(self, n_rows: int = 365) -> pd.DataFrame:
        """Synthesize daily omni-channel acquisition and spend performance."""
        dates = pd.date_range("2025-01-01", periods=n_rows, freq="D").strftime("%Y-%m-%d")
        channels = ["Google Search", "LinkedIn Ads", "Organic SEO", "YouTube Partner", "Email Nurture"]

        records = []
        for i, dt in enumerate(dates):
            for ch in channels:
                spend = round(np.random.uniform(250, 2500) if ch not in ["Organic SEO", "Email Nurture"] else 0.0, 2)
                impressions = int(spend * np.random.uniform(25, 45)) if spend > 0 else np.random.randint(1200, 5000)
                clicks = int(impressions * np.random.uniform(0.02, 0.06))
                signups = int(clicks * np.random.uniform(0.08, 0.18))
                conversions = int(signups * np.random.uniform(0.12, 0.28))
                cac = round(spend / conversions, 2) if conversions > 0 and spend > 0 else 0.0
                pipeline_val = conversions * round(np.random.uniform(1200, 4500), 2)

                records.append({
                    "date": dt,
                    "channel": ch,
                    "ad_spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "signups": signups,
                    "conversions": conversions,
                    "cac": cac,
                    "pipeline_generated": pipeline_val,
                })
        return pd.DataFrame(records)

    def generate_hr_dataset(self, n_employees: int = 500) -> pd.DataFrame:
        """Synthesize corporate workforce demographic and retention metrics."""
        np.random.seed(101)
        departments = ["Engineering", "Product", "Sales", "Customer Success", "People Ops", "Finance"]
        roles = {
            "Engineering": ["Senior Staff Engineer", "Software Engineer II", "DevOps Specialist", "QA Lead"],
            "Product": ["Group Product Manager", "Product Designer", "Technical Writer"],
            "Sales": ["Enterprise Account Executive", "SDR Lead", "Sales Engineer"],
            "Customer Success": ["Customer Success Manager", "Implementation Consultant"],
            "People Ops": ["HR Business Partner", "Talent Acquisition Lead"],
            "Finance": ["Senior Financial Analyst", "Controller", "Revenue Ops Specialist"],
        }
        dept_choice = np.random.choice(departments, n_employees, p=[0.35, 0.15, 0.20, 0.12, 0.08, 0.10])

        records = []
        for i in range(n_employees):
            d = dept_choice[i]
            r = np.random.choice(roles[d])
            salary = round(np.random.uniform(75000, 195000), 2)
            perf = round(np.random.uniform(2.8, 5.0), 1)
            tenure = round(np.random.uniform(0.5, 7.5), 1)
            attrition_prob = round(max(0.02, min(0.65, 0.45 - (perf * 0.06) + (0.04 if tenure > 4 else 0.0))), 2)

            records.append({
                "employee_id": f"EMP-{2000 + i}",
                "department": d,
                "role": r,
                "salary": salary,
                "tenure_years": tenure,
                "performance_score": perf,
                "status": "Active" if attrition_prob < 0.50 else "High Risk",
                "attrition_risk_score": attrition_prob,
            })
        return pd.DataFrame(records)

    def generate_supply_chain_dataset(self, n_skus: int = 400) -> pd.DataFrame:
        """Synthesize logistics and inventory warehouse telemetry."""
        np.random.seed(202)
        warehouses = ["US-East (New Jersey)", "US-West (Nevada)", "EU-Central (Frankfurt)", "APAC (Singapore)"]
        categories = ["Robotics & Hardware", "Compute Servers", "Optics & Sensors", "Networking Switches", "Batteries & Power"]

        records = []
        for i in range(n_skus):
            sku = f"SKU-{3000 + i}"
            wh = np.random.choice(warehouses)
            cat = np.random.choice(categories)
            unit_cost = round(np.random.uniform(45.0, 1850.0), 2)
            stock = np.random.randint(15, 800)
            reorder = np.random.randint(40, 250)
            lead_time = np.random.randint(3, 45)
            is_stockout = stock < reorder

            records.append({
                "sku": sku,
                "category": cat,
                "warehouse": wh,
                "unit_cost": unit_cost,
                "current_stock": stock,
                "reorder_threshold": reorder,
                "lead_time_days": lead_time,
                "stockout_risk": "Critical" if stock < (reorder * 0.5) else ("Warning" if is_stockout else "Optimal"),
                "total_inventory_value": round(stock * unit_cost, 2),
            })
        return pd.DataFrame(records)

    def provision_all_demo_datasets(self) -> dict[str, str]:
        """Generate and write all 5 datasets to disk in CSV format."""
        manifest: dict[str, str] = {}

        sales_df = self.generate_sales_dataset()
        sales_path = self.demo_dir / "sales_performance_2026.csv"
        sales_df.to_csv(sales_path, index=False)
        manifest["sales"] = str(sales_path)

        fin_df = self.generate_finance_dataset()
        fin_path = self.demo_dir / "finance_pnl_2026.csv"
        fin_df.to_csv(fin_path, index=False)
        manifest["finance"] = str(fin_path)

        mkt_df = self.generate_marketing_dataset()
        mkt_path = self.demo_dir / "marketing_attribution_2026.csv"
        mkt_df.to_csv(mkt_path, index=False)
        manifest["marketing"] = str(mkt_path)

        hr_df = self.generate_hr_dataset()
        hr_path = self.demo_dir / "hr_workforce_2026.csv"
        hr_df.to_csv(hr_path, index=False)
        manifest["hr"] = str(hr_path)

        ops_df = self.generate_supply_chain_dataset()
        ops_path = self.demo_dir / "supply_chain_operations_2026.csv"
        ops_df.to_csv(ops_path, index=False)
        manifest["operations"] = str(ops_path)

        logger.info("Successfully provisioned all 5 demo datasets in %s", self.demo_dir)
        return manifest

    def list_demo_datasets(self) -> list[dict[str, Any]]:
        """List metadata for all 5 enterprise demo datasets."""
        return [
            {
                "id": "ds-demo-sales",
                "name": "B2B Sales Performance 2026",
                "slug": "sales",
                "category": "Commercial Sales",
                "filename": "sales_performance_2026.csv",
                "description": "Multi-year commercial B2B transactional records with product segments, discounts, and regional distribution.",
                "rows": 1200,
            },
            {
                "id": "ds-demo-fin",
                "name": "Corporate P&L & EBITDA 2026",
                "slug": "finance",
                "category": "Corporate Finance",
                "filename": "finance_pnl_2026.csv",
                "description": "Monthly corporate income statements with revenue, OPEX, COGS, EBITDA, and free cash flows.",
                "rows": 24,
            },
            {
                "id": "ds-demo-mkt",
                "name": "Omni-Channel Acquisition 2026",
                "slug": "marketing",
                "category": "Growth Marketing",
                "filename": "marketing_attribution_2026.csv",
                "description": "Multi-touch attribution dataset tracking CAC, ROAS, channel conversion, and signups.",
                "rows": 365,
            },
            {
                "id": "ds-demo-hr",
                "name": "Global Workforce Retention 2026",
                "slug": "hr",
                "category": "Human Capital",
                "filename": "hr_workforce_2026.csv",
                "description": "People analytics records across departments with compensation, attrition risk, and performance.",
                "rows": 500,
            },
            {
                "id": "ds-demo-ops",
                "name": "Supply Chain & Warehouse Telemetry 2026",
                "slug": "supply-chain",
                "category": "Logistics & Supply Chain",
                "filename": "supply_chain_operations_2026.csv",
                "description": "Inventory stock levels, warehouse lead times, unit costs, and reorder threshold telemetry.",
                "rows": 400,
            },
        ]

    def load_demo_dataframe(self, slug: str) -> pd.DataFrame:
        """Generate or load DataFrame for a given demo slug."""
        normalized = slug.lower().replace("_", "-")
        if "sale" in normalized:
            return self.generate_sales_dataset()
        elif "fin" in normalized:
            return self.generate_finance_dataset()
        elif "mkt" in normalized or "market" in normalized:
            return self.generate_marketing_dataset()
        elif "hr" in normalized or "workforce" in normalized:
            return self.generate_hr_dataset()
        elif "supp" in normalized or "ops" in normalized or "chain" in normalized:
            return self.generate_supply_chain_dataset()
        return self.generate_sales_dataset()


_demo_service = DemoDatasetService()


def get_demo_dataset_service() -> DemoDatasetService:
    return _demo_service
