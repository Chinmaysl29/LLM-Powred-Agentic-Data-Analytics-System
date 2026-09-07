"""Phase 12.6.8 — Failover Engine.

Detects provider failures, triggers automatic transparent failovers to healthy backups,
and manages retry policies with health circuit breaking.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from backend.model_hub.base import BaseModelProvider, GenerationResult

logger = logging.getLogger(__name__)


class ModelFailoverEngine:
    """Circuit breaker and auto-failover orchestrator for model providers."""

    def __init__(
        self,
        providers: Dict[str, BaseModelProvider],
        failover_chain: Optional[List[str]] = None,
        max_retries_per_provider: int = 1,
    ) -> None:
        self.providers = providers
        self.failover_chain = failover_chain or list(providers.keys())
        self.max_retries = max_retries_per_provider
        self.consecutive_failures: Dict[str, int] = {p: 0 for p in self.providers}
        self.disabled_providers: set[str] = set()

    def mark_provider_down(self, provider_name: str, reason: str = "Unreachable") -> None:
        """Mark a provider down and disable it in the pool."""
        clean = provider_name.lower()
        self.disabled_providers.add(clean)
        logger.error("Provider '%s' marked DOWN. Reason: %s", clean, reason)

    def mark_provider_up(self, provider_name: str) -> None:
        """Restore provider status after successful health validation."""
        clean = provider_name.lower()
        self.disabled_providers.discard(clean)
        self.consecutive_failures[clean] = 0
        logger.info("Provider '%s' restored to HEALTHY status.", clean)

    def execute_with_failover(
        self,
        prompt: str,
        preferred_provider: str = "openai",
        simulate_failure_on: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Attempt execution with preferred provider; automatically failover on error."""
        chain = [preferred_provider] + [p for p in self.failover_chain if p != preferred_provider]

        last_exception: Optional[Exception] = None

        for provider_key in chain:
            clean_key = provider_key.lower()

            # Skip disabled providers
            if clean_key in self.disabled_providers:
                logger.warning("Skipping disabled provider '%s'", clean_key)
                continue

            provider = self.providers.get(clean_key)
            if not provider:
                continue

            # Attempt execution
            for attempt in range(self.max_retries + 1):
                try:
                    if simulate_failure_on and simulate_failure_on.lower() == clean_key:
                        raise ConnectionError(f"Simulated API outage for provider {clean_key}")

                    result = provider.generate(prompt=prompt, **kwargs)
                    self.consecutive_failures[clean_key] = 0
                    logger.info("Successfully executed generation via [%s] (failover resolved)", clean_key)
                    return result

                except Exception as exc:
                    self.consecutive_failures[clean_key] += 1
                    last_exception = exc
                    logger.warning(
                        "Attempt %d failed on [%s]: %s",
                        attempt + 1,
                        clean_key,
                        exc,
                    )
                    time.sleep(0.01)

            # Max retries exceeded for this provider -> mark down and fail over
            self.mark_provider_down(clean_key, str(last_exception))
            logger.info("Triggering automatic failover from [%s] to next candidate...", clean_key)

        raise RuntimeError(
            f"All providers in failover chain exhausted. Last error: {last_exception}"
        )
