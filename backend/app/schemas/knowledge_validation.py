"""Schemas for Knowledge Validation (Phase 5.10)."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    """Individual claim verification result."""
    claim: str = Field(..., description="Extracted claim or assertion from the answer")
    is_grounded: bool = Field(..., description="True if claim is supported by retrieved context")
    supporting_source: Optional[str] = Field(default=None, description="Source citation supporting the claim")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Grounding confidence score")
    reason: Optional[str] = Field(default=None, description="Explanation of grounding decision")


class KnowledgeValidationResult(BaseModel):
    """Aggregate knowledge validation result for a RAG-generated answer."""
    is_valid: bool = Field(..., description="True if answer passes all critical checks")
    faithfulness_score: float = Field(..., ge=0.0, le=1.0, description="Proportion of grounded claims (0-1)")
    hallucinations_detected: bool = Field(..., description="True if any hallucinated claims found")
    checks: List[ValidationCheck] = Field(default_factory=list, description="Individual claim checks")
    warnings: List[str] = Field(default_factory=list, description="Non-critical validation warnings")
    answer_has_sources: bool = Field(default=True, description="True if answer cites at least one source")
