"""Checklist alias module providing IntentService pointing to IntentClassificationService."""

from backend.app.services.intent_classification_service import (
    IntentClassificationService,
    IntentRegistry,
    get_intent_classification_service,
)

IntentService = IntentClassificationService
get_intent_service = get_intent_classification_service

__all__ = [
    "IntentService",
    "IntentClassificationService",
    "IntentRegistry",
    "get_intent_service",
    "get_intent_classification_service",
]
