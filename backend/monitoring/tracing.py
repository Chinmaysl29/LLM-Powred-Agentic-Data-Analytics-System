"""Small OpenTelemetry-compatible tracing façade with safe local fallback."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from time import perf_counter
from typing import Generator
from uuid import uuid4

trace_id_context: ContextVar[str | None] = ContextVar("trace_id", default=None)


@dataclass
class TraceSpan:
    name: str
    trace_id: str
    parent_id: str | None = None
    span_id: str = field(default_factory=lambda: uuid4().hex)
    error: str | None = None
    duration_seconds: float | None = None


class Tracer:
    def __init__(self) -> None:
        self.spans: list[TraceSpan] = []

    @contextmanager
    def start_span(self, name: str, trace_id: str | None = None) -> Generator[TraceSpan, None, None]:
        inherited = trace_id_context.get()
        span = TraceSpan(name=name, trace_id=trace_id or inherited or uuid4().hex, parent_id=inherited)
        token = trace_id_context.set(span.trace_id)
        started = perf_counter()
        try:
            yield span
        except Exception as exc:
            span.error = str(exc)
            raise
        finally:
            span.duration_seconds = perf_counter() - started
            self.spans.append(span)
            trace_id_context.reset(token)


tracer = Tracer()
