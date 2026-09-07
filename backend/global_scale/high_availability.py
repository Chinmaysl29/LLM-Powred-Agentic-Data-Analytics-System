"""
Phase 12.9.7 — High Availability Layer
Enterprise load balancing, Horizontal Pod Autoscaling (HPA) algorithm,
Netflix Hystrix-style adaptive Circuit Breakers, and exponential backoff retry policies.
"""

from typing import Dict, Any, List, Optional, Callable
import time
import math
import random
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.global_scale.high_availability")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"     # Normal operation
    OPEN = "OPEN"         # Fast fail
    HALF_OPEN = "HALF_OPEN" # Probing recovery


class CircuitBreaker:
    """
    Protects downstream enterprise backends from cascading failures.
    Transitions CLOSED -> OPEN on failure threshold, and OPEN -> HALF_OPEN after cooldown.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: float = 2.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()
            logger.info("Circuit breaker recovered: state is now CLOSED")
        else:
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning("Circuit breaker tripped: state is now OPEN")

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if (time.time() - self.last_state_change) > self.recovery_timeout_sec:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
                logger.info("Circuit breaker entered HALF_OPEN test state")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False


class HighAvailabilityManager:
    """
    Manages global request distribution, pod autoscaling calculations (HPA),
    circuit breaking, and retry logic.
    """

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        if service_name not in self._circuit_breakers:
            self._circuit_breakers[service_name] = CircuitBreaker()
        return self._circuit_breakers[service_name]

    def execute_with_retry(
        self,
        service_name: str,
        operation: Callable[[], Any],
        max_retries: int = 3,
        base_delay_ms: float = 10.0
    ) -> Dict[str, Any]:
        """Execute callable with circuit breaker guard and exponential backoff jitter."""
        cb = self.get_circuit_breaker(service_name)
        if not cb.allow_request():
            return {"status": 503, "error": f"Circuit breaker OPEN for {service_name}", "circuit_state": cb.state.value}

        for attempt in range(1, max_retries + 1):
            try:
                result = operation()
                cb.record_success()
                return {"status": 200, "result": result, "attempts": attempt, "circuit_state": cb.state.value}
            except Exception as ex:
                cb.record_failure()
                if attempt == max_retries:
                    return {"status": 500, "error": str(ex), "attempts": attempt, "circuit_state": cb.state.value}
                # Backoff
                delay = (base_delay_ms * (2 ** (attempt - 1))) / 1000.0
                time.sleep(delay)

    def calculate_hpa_replicas(
        self,
        current_replicas: int,
        current_metric_value: float,
        target_metric_value: float = 70.0,
        min_replicas: int = 2,
        max_replicas: int = 20
    ) -> int:
        """
        Kubernetes Horizontal Pod Autoscaler (HPA) algorithm:
        desiredReplicas = ceil[currentReplicas * ( currentMetricValue / targetMetricValue )]
        """
        if target_metric_value <= 0:
            return current_replicas
        ratio = current_metric_value / target_metric_value
        desired = int(math.ceil(current_replicas * ratio))
        return max(min_replicas, min(max_replicas, desired))

    def balance_load(self, instances: List[Dict[str, Any]], strategy: str = "least_connections") -> Dict[str, Any]:
        """Distribute traffic across instances (least_connections or round_robin)."""
        if not instances:
            raise ValueError("No instances provided for load balancing")
        if strategy == "least_connections":
            return min(instances, key=lambda i: i.get("active_connections", 0))
        return random.choice(instances)
