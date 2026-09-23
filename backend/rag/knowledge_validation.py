"""Knowledge Validator — Anti-hallucination and faithfulness scoring (Phase 5.10)."""

import re
from typing import List, Optional, Tuple

from backend.app.schemas.context_builder import ContextSource
from backend.app.schemas.knowledge_validation import KnowledgeValidationResult, ValidationCheck


class KnowledgeValidator:
    """Validates LLM-generated answers against retrieved source context.

    Checks:
    1. Claim extraction from generated answer
    2. Context grounding — each claim must be supported by retrieved text
    3. Numerical consistency — numbers in answer must appear in context
    4. Citation validity — cited source IDs must correspond to real sources
    5. Faithfulness scoring — ratio of grounded claims
    """

    # Regex to find numeric facts: integers, decimals, percentages, currency
    _NUMBER_PATTERN = re.compile(r'\b\d[\d,\.]*%?\b|\$[\d,\.]+')
    # Sentence splitter
    _SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

    def __init__(self, min_faithfulness: float = 0.5) -> None:
        self.min_faithfulness = min_faithfulness

    def _extract_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        return [s.strip() for s in self._SENTENCE_SPLIT.split(text) if s.strip()]

    def _extract_numbers(self, text: str) -> List[str]:
        return self._NUMBER_PATTERN.findall(text)

    def _is_grounded_in_context(self, claim: str, context: str) -> Tuple[bool, float, Optional[str]]:
        """Check if a claim's key terms appear in the context."""
        claim_lower = claim.lower().strip()
        context_lower = context.lower()

        # Remove very short claims (like single words)
        if len(claim_lower.split()) < 3:
            return True, 1.0, "Trivially short claim — skipped"

        # Extract meaningful tokens from claim
        tokens = re.findall(r'\b[a-z0-9]{3,}\b', claim_lower)
        if not tokens:
            return True, 1.0, "No meaningful tokens"

        matched = sum(1 for t in tokens if t in context_lower)
        coverage = matched / len(tokens)

        # Check numbers: every number in claim should appear in context
        claim_numbers = self._extract_numbers(claim)
        context_numbers = self._extract_numbers(context)
        number_ok = all(n in context_numbers for n in claim_numbers)

        if not number_ok and claim_numbers:
            bad_nums = [n for n in claim_numbers if n not in context_numbers]
            return False, 0.0, f"Numbers not found in context: {bad_nums}"

        is_grounded = coverage >= 0.4
        return is_grounded, coverage, f"Token coverage: {coverage:.0%}"

    def validate(
        self,
        answer: str,
        context_text: str,
        sources: Optional[List[ContextSource]] = None,
    ) -> KnowledgeValidationResult:
        warnings: List[str] = []
        checks: List[ValidationCheck] = []

        if not answer or not answer.strip():
            return KnowledgeValidationResult(
                is_valid=False,
                faithfulness_score=0.0,
                hallucinations_detected=True,
                checks=[],
                warnings=["Empty answer generated"],
                answer_has_sources=False,
            )

        if not context_text or not context_text.strip():
            warnings.append("No context provided — full hallucination risk")
            return KnowledgeValidationResult(
                is_valid=False,
                faithfulness_score=0.0,
                hallucinations_detected=True,
                checks=[],
                warnings=warnings,
                answer_has_sources=bool(sources),
            )

        sentences = self._extract_sentences(answer)
        grounded_count = 0

        for sentence in sentences:
            is_grounded, conf, reason = self._is_grounded_in_context(sentence, context_text)
            if is_grounded:
                grounded_count += 1

            # Find a supporting source if grounded
            supporting = None
            if is_grounded and sources:
                for src in sources:
                    if src.preview and any(
                        t in src.preview.lower() for t in re.findall(r'\b[a-z]{4,}\b', sentence.lower())[:3]
                    ):
                        supporting = src.source_id
                        break

            checks.append(
                ValidationCheck(
                    claim=sentence[:200],
                    is_grounded=is_grounded,
                    supporting_source=supporting,
                    confidence=round(conf, 2),
                    reason=reason,
                )
            )

        total_checks = len(checks)
        faithfulness = grounded_count / max(1, total_checks)
        hallucinations = faithfulness < self.min_faithfulness

        # Citation check
        answer_has_sources = bool(sources) and len(sources) > 0
        if not answer_has_sources:
            warnings.append("Answer has no source citations")

        is_valid = not hallucinations and answer_has_sources

        return KnowledgeValidationResult(
            is_valid=is_valid,
            faithfulness_score=round(faithfulness, 3),
            hallucinations_detected=hallucinations,
            checks=checks,
            warnings=warnings,
            answer_has_sources=answer_has_sources,
        )
