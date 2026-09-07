"""
Phase 13.7 — Billing Platform
Enterprise monetization engine managing subscription tiers, compute credits metering,
token usage tracking, automated invoicing, and custom enterprise contracts.
"""

from typing import Dict, Any, List, Optional
import time
import uuid
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.operations.billing")


class SubscriptionTier(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class InvoiceRecord(BaseModel):
    invoice_id: str = Field(default_factory=lambda: f"inv-{uuid.uuid4().hex[:8]}")
    tenant_id: str
    amount_usd: float
    line_items: List[Dict[str, Any]]
    status: str = "PAID" # "DRAFT", "PAID", "VOID"
    issued_at: float = Field(default_factory=time.time)


class BillingPlatformEngine:
    """
    Manages tenant subscriptions, usage-based credit deduction,
    invoicing, and enterprise contract commitments.
    """

    TIER_PRICING = {
        SubscriptionTier.FREE: {"base_fee": 0.0, "monthly_credits": 1000},
        SubscriptionTier.PRO: {"base_fee": 499.0, "monthly_credits": 50000},
        SubscriptionTier.ENTERPRISE: {"base_fee": 2499.0, "monthly_credits": 500000}
    }

    def __init__(self):
        self._subscriptions: Dict[str, SubscriptionTier] = {}
        self._credit_balances: Dict[str, float] = {} # tenant_id -> credits
        self._invoices: List[InvoiceRecord] = []
        self._enterprise_contracts: Dict[str, Dict[str, Any]] = {}

    def create_subscription(self, tenant_id: str, tier: SubscriptionTier) -> Dict[str, Any]:
        """Establish subscription and assign initial monthly compute credits."""
        self._subscriptions[tenant_id] = tier
        initial_credits = self.TIER_PRICING[tier]["monthly_credits"]
        self._credit_balances[tenant_id] = float(initial_credits)

        logger.info("Created subscription for tenant %s: %s (%d credits)", tenant_id, tier.value, initial_credits)
        return {
            "tenant_id": tenant_id,
            "tier": tier.value,
            "monthly_fee_usd": self.TIER_PRICING[tier]["base_fee"],
            "initial_credits": initial_credits
        }

    def track_usage(self, tenant_id: str, compute_units: float, service_name: str) -> Dict[str, Any]:
        """Deduct credits according to consumption."""
        balance = self._credit_balances.get(tenant_id, 0.0)
        if balance < compute_units:
            return {
                "success": False,
                "error": "Insufficient credits",
                "remaining_credits": balance
            }

        self._credit_balances[tenant_id] = balance - compute_units
        return {
            "success": True,
            "tenant_id": tenant_id,
            "service": service_name,
            "units_consumed": compute_units,
            "remaining_credits": self._credit_balances[tenant_id]
        }

    def add_credits(self, tenant_id: str, credits: float) -> float:
        """Top-up credit wallet."""
        curr = self._credit_balances.get(tenant_id, 0.0)
        self._credit_balances[tenant_id] = curr + credits
        return self._credit_balances[tenant_id]

    def generate_invoice(self, tenant_id: str, additional_charges: float = 0.0) -> InvoiceRecord:
        """Generate monthly itemized invoice."""
        tier = self._subscriptions.get(tenant_id, SubscriptionTier.PRO)
        base_fee = self.TIER_PRICING[tier]["base_fee"]
        total = base_fee + additional_charges

        items = [
            {"description": f"AI Data Analyst OS ({tier.value} Subscription)", "amount": base_fee}
        ]
        if additional_charges > 0:
            items.append({"description": "Additional Compute Overages", "amount": additional_charges})

        inv = InvoiceRecord(tenant_id=tenant_id, amount_usd=total, line_items=items)
        self._invoices.append(inv)
        return inv

    def register_enterprise_contract(
        self,
        tenant_id: str,
        annual_contract_value: float,
        term_years: int = 3,
        discount_percentage: float = 20.0
    ) -> Dict[str, Any]:
        """Register negotiated enterprise master services agreement."""
        contract = {
            "contract_id": f"cnt-{uuid.uuid4().hex[:8]}",
            "tenant_id": tenant_id,
            "acv": annual_contract_value,
            "term_years": term_years,
            "discount_percentage": discount_percentage,
            "signed_at": time.time(),
            "status": "EXECUTED"
        }
        self._enterprise_contracts[tenant_id] = contract
        self.create_subscription(tenant_id, SubscriptionTier.ENTERPRISE)
        return contract
