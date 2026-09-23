"""Enterprise Intent Classification Service for AI Data Analyst OS.

Converts natural language user queries into structured intents with
confidence scoring, reasoning, and required downstream agent definitions.
"""

import json
import logging
import re
from typing import Any

from fastapi import Depends

from backend.app.core.exceptions import ValidationException
from backend.app.llm.provider import LLMProvider, get_llm_provider
from backend.app.schemas.intent import (
    IntentDefinition,
    IntentType,
    IntentClassificationResponse,
)

logger = logging.getLogger(__name__)


class IntentRegistry:
    """Extensible registry for registering and resolving supported intents."""

    def __init__(self) -> None:
        self._registry: dict[str, IntentDefinition] = {}
        self._bootstrap_core_intents()

    def register(self, definition: IntentDefinition) -> None:
        """Register or override an intent definition."""
        self._registry[definition.name] = definition
        logger.debug("Registered intent: %s", definition.name)

    def get(self, name: str) -> IntentDefinition | None:
        """Retrieve an intent definition by name."""
        return self._registry.get(name)

    def list_intents(self) -> list[IntentDefinition]:
        """List all currently registered intent definitions."""
        return list(self._registry.values())

    def get_prompt_descriptions(self) -> str:
        """Format registered intents for LLM system prompt instructions."""
        lines = []
        for item in self._registry.values():
            if item.name == IntentType.UNKNOWN.value:
                continue
            lines.append(f"- {item.name}: {item.description}")
        return "\n".join(lines)

    def match_heuristic(self, query: str) -> tuple[IntentDefinition | None, float, str]:
        """Evaluate deterministic regex and keyword matches for fast, robust routing.
        
        Returns:
            Tuple of (matched_intent, confidence, reasoning)
        """
        normalized = query.lower().strip()

        # 1. Regex Pattern Evaluation (Precision First)
        for definition in self._registry.values():
            for pattern in definition.patterns:
                if re.search(pattern, normalized, re.IGNORECASE):
                    reasoning = f"Matched strong semantic pattern '{pattern}' for {definition.name}"
                    return definition, 0.95, reasoning

        # 2. Keyword Scoring Evaluation
        best_match: IntentDefinition | None = None
        best_score = 0
        for definition in self._registry.values():
            score = sum(1 for kw in definition.keywords if kw in normalized)
            if score > best_score:
                best_score = score
                best_match = definition

        if best_match and best_score >= 1:
            confidence = min(0.85, 0.65 + (best_score * 0.1))
            reasoning = f"Matched {best_score} key terms for {best_match.name}"
            return best_match, confidence, reasoning

        return None, 0.0, "No heuristic match found"

    def _bootstrap_core_intents(self) -> None:
        """Initialize the standard 16 core intents + unknown."""
        core_definitions = [
            IntentDefinition(
                name=IntentType.TREND_ANALYSIS.value,
                description="Historical trends, time-series trajectory, sales/revenue evolution, changes over time",
                required_agents=["data_retrieval", "trend_analysis"],
                keywords=["trend", "trends", "over time", "trajectory", "growth", "decline", "historical", "seasonality", "by month", "by year"],
                patterns=[r"\b(revenue trends?|sales trends?|trends? over time|trend analysis|show .* trends?|growth trend)\b"],
                examples=["Show revenue trends", "What is the sales trend over the last 6 months?", "Analyze user sign-up trends over time"],
            ),
            IntentDefinition(
                name=IntentType.FORECASTING.value,
                description="Predicting future values, sales projections, next quarter/month forecasting",
                required_agents=["data_retrieval", "forecasting"],
                keywords=["predict", "prediction", "forecast", "forecasting", "projection", "next month", "next quarter", "next year", "future sales"],
                patterns=[r"\b(predict .* (next|future)|forecast|projections? for next|expected sales|future revenue)\b"],
                examples=["Predict sales for next quarter", "Forecast revenue for the next 6 months", "What will our churn be next year?"],
            ),
            IntentDefinition(
                name=IntentType.DATA_QUALITY.value,
                description="Checking duplicate records, missing values, nulls, schema validation, data hygiene",
                required_agents=["data_retrieval", "data_quality"],
                keywords=["duplicate", "duplicates", "missing", "null", "nulls", "data quality", "invalid", "data hygiene", "corrupted"],
                patterns=[r"\b(duplicate records?|find duplicates?|missing values?|check data quality|null counts?|missing data)\b"],
                examples=["Find duplicate records", "Are there any missing values in the customer table?", "Assess data quality"],
            ),
            IntentDefinition(
                name=IntentType.RANKING_ANALYSIS.value,
                description="Finding top or bottom performers, highest or lowest values, leaders, best or worst entities",
                required_agents=["data_retrieval", "ranking_analysis"],
                keywords=["top", "bottom", "highest", "lowest", "best", "worst", "rank", "ranking", "most", "least", "leaderboard"],
                patterns=[r"\b(highest (revenue|sales|profit|cost)|lowest (revenue|sales|cost)|top \d+|bottom \d+|which .* generated the highest|best performing|worst performing)\b"],
                examples=["Which product generated the highest revenue?", "Show the top 5 customers by sales", "Rank countries by order volume"],
            ),
            IntentDefinition(
                name=IntentType.DATASET_OVERVIEW.value,
                description="High-level dataset summary, columns, schema structure, row count, basic metadata",
                required_agents=["data_retrieval", "dataset_overview"],
                keywords=["overview", "summary", "summarize", "describe", "metadata", "schema", "dataset info", "columns", "what does this data contain"],
                patterns=[r"\b(dataset overview|summarize (this )?data(set)?|describe the dataset|show schema|what does this data contain)\b"],
                examples=["Show me a summary of this dataset", "What does this data contain?", "Describe the dataset schema"],
            ),
            IntentDefinition(
                name=IntentType.EDA_ANALYSIS.value,
                description="Exploratory data analysis, comprehensive profiling, deep-dive exploratory inspection",
                required_agents=["data_retrieval", "eda_agent"],
                keywords=["eda", "exploratory", "explore", "deep dive", "data patterns", "comprehensive analysis"],
                patterns=[r"\b(perform eda|exploratory data analysis|explore (the )?data)\b"],
                examples=["Perform exploratory analysis on customer churn", "Run an EDA on this dataset"],
            ),
            IntentDefinition(
                name=IntentType.COMPARISON_ANALYSIS.value,
                description="Comparing two or more segments, cohorts, categories, periods, or regional metrics",
                required_agents=["data_retrieval", "comparison_analysis"],
                keywords=["compare", "comparison", "versus", "vs", "difference between", "relative to", "benchmark against"],
                patterns=[r"\b(compare .* (with|to|and|vs)|comparison between|diff between)\b"],
                examples=["Compare Q1 sales with Q2 sales", "Compare regional performance across North and South", "Product A vs Product B"],
            ),
            IntentDefinition(
                name=IntentType.DISTRIBUTION_ANALYSIS.value,
                description="Frequency distributions, histograms, spread, skewness, percentiles, data dispersion",
                required_agents=["data_retrieval", "distribution_analysis"],
                keywords=["distribution", "spread", "histogram", "density", "skewness", "percentile", "variance", "frequency"],
                patterns=[r"\b(distribution of|show distribution|histogram of|spread of)\b"],
                examples=["Show the distribution of customer age", "Plot the income distribution", "What is the distribution of transaction values?"],
            ),
            IntentDefinition(
                name=IntentType.CORRELATION_ANALYSIS.value,
                description="Statistical correlations, relationships between metrics, covariance, dependency",
                required_agents=["data_retrieval", "correlation_analysis"],
                keywords=["correlation", "correlate", "correlated", "relationship between", "associated with", "covariance"],
                patterns=[r"\b(correlation between|is there a correlation|relationship between .* and)\b"],
                examples=["Is there a correlation between marketing spend and revenue?", "Show the correlation matrix", "Does price correlate with sales?"],
            ),
            IntentDefinition(
                name=IntentType.ANOMALY_DETECTION.value,
                description="Detecting outliers, unusual spikes, fraudulent transactions, unexpected variations",
                required_agents=["data_retrieval", "anomaly_detection"],
                keywords=["anomaly", "anomalies", "outlier", "outliers", "unusual", "spike", "abnormal", "unexpected jump"],
                patterns=[r"\b(find outliers?|detect anomalies?|unusual transactions?|abnormal spikes?)\b"],
                examples=["Find outliers in transaction amounts", "Detect anomalies in server response times", "Are there unusual spikes in revenue?"],
            ),
            IntentDefinition(
                name=IntentType.DASHBOARD_GENERATION.value,
                description="Building visual dashboards, KPI scorecards, multi-chart visual assemblies",
                required_agents=["data_retrieval", "dashboard_generation"],
                keywords=["dashboard", "scorecard", "visual board", "charts and graphs", "visual display", "kpi board"],
                patterns=[r"\b(create dashboard|generate dashboard|build a dashboard|kpi dashboard)\b"],
                examples=["Create a dashboard for executive KPIs", "Generate a sales dashboard", "Build an interactive dashboard"],
            ),
            IntentDefinition(
                name=IntentType.REPORT_GENERATION.value,
                description="Generating executive reports, structured written summaries, PDF/document outputs",
                required_agents=["data_retrieval", "report_generation"],
                keywords=["report", "executive summary", "briefing", "pdf report", "generate report", "compile report"],
                patterns=[r"\b(generate report|create (an? )?report|executive summary report|export report)\b"],
                examples=["Generate a monthly executive report", "Create a summary report for leadership", "Export analytical report"],
            ),
            IntentDefinition(
                name=IntentType.RECOMMENDATION_GENERATION.value,
                description="Actionable business recommendations, strategy suggestions, optimization steps",
                required_agents=["data_retrieval", "recommendation_generation"],
                keywords=["recommend", "recommendation", "recommendations", "suggest", "action items", "how to improve", "advice"],
                patterns=[r"\b(what (do you )?recommend|give me recommendations?|actionable recommendations?|suggestions to improve)\b"],
                examples=["What recommendations do you have to reduce churn?", "Suggest strategies to increase revenue", "Recommend optimizations"],
            ),
            IntentDefinition(
                name=IntentType.WHAT_IF_ANALYSIS.value,
                description="Simulations, hypothetical scenario testing, sensitivity modeling, parameter perturbations",
                required_agents=["data_retrieval", "what_if_analysis"],
                keywords=["what if", "scenario", "simulate", "hypothetical", "suppose we", "sensitivity", "what would happen"],
                patterns=[r"\b(what if we|scenario analysis|simulate the impact|what happens if)\b"],
                examples=["What if we increase prices by 10%?", "Simulate a 20% drop in advertising spend", "What happens if churn doubles?"],
            ),
            IntentDefinition(
                name=IntentType.SQL_QUERY.value,
                description="Executing direct SQL queries, table lookups, raw database extractions",
                required_agents=["data_retrieval", "sql_query"],
                keywords=["sql", "select", "query", "database query", "from table", "group by", "where clause"],
                patterns=[r"\b(select .* from|run sql query|write a sql query|execute sql)\b"],
                examples=["SELECT * FROM orders WHERE total > 100", "Write a SQL query to get active users by country", "Run SQL query on customers"],
            ),
            IntentDefinition(
                name=IntentType.RAG_QUERY.value,
                description="Searching documentation, domain knowledge retrieval, unstructured text Q&A",
                required_agents=["data_retrieval", "rag_query"],
                keywords=["documentation", "docs", "knowledge base", "handbook", "policy", "rag", "search documents"],
                patterns=[r"\b(search documentation|look up in docs|knowledge base search|what does the policy say)\b"],
                examples=["Search documentation for metric calculation rules", "Look up company refund policy", "What does the SLA manual say?"],
            ),
            IntentDefinition(
                name=IntentType.UNKNOWN.value,
                description="Unrecognized query, general greeting, or out-of-domain prompt",
                required_agents=[],
                keywords=["hello", "hi", "help", "who are you"],
                patterns=[r"^(hello|hi|hey|help)\b"],
                examples=["Hello", "Who created you?", "Random unparseable prompt"],
            ),
        ]

        for defn in core_definitions:
            self.register(defn)


class IntentClassificationService:
    """Enterprise-grade service to classify natural language queries into structured intents."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        registry: IntentRegistry | None = None,
    ) -> None:
        self._llm = llm
        self._registry = registry or IntentRegistry()

    @property
    def registry(self) -> IntentRegistry:
        """Return the underlying extensible intent registry."""
        return self._registry

    def _build_classification_prompt(self) -> str:
        """Construct a system prompt dynamically from the registered intents."""
        descriptions = self._registry.get_prompt_descriptions()
        return (
            "You are an expert AI Intent Classifier for an enterprise Data Analytics Operating System.\n"
            "Your job is to classify the user's natural language request into EXACTLY ONE of the supported intents:\n\n"
            f"{descriptions}\n"
            f"- {IntentType.UNKNOWN.value}: If the request does not match any analytical intent.\n\n"
            "Guidelines:\n"
            "1. Output valid JSON ONLY. Do not include markdown fences, backticks, or other text.\n"
            "2. Confidence must be a float between 0.0 and 1.0.\n"
            "3. Reasoning must be a concise explanation (1-2 sentences) of why this intent was selected.\n\n"
            "Required JSON Schema:\n"
            "{\n"
            '  "intent": "<intent_name>",\n'
            '  "confidence": <float_between_0_and_1>,\n'
            '  "reasoning": "<concise_explanation>"\n'
            "}"
        )

    def validate_query(self, query: str) -> str:
        """Validate input query string."""
        if query is None:
            raise ValidationException("Query cannot be None")
        cleaned = query.strip()
        if not cleaned:
            raise ValidationException("Query cannot be empty or whitespace")
        if len(cleaned) > 2000:
            raise ValidationException("Query exceeds maximum length of 2000 characters")
        return cleaned

    async def classify(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        dataset_id: str | None = None,
    ) -> IntentClassificationResponse:
        """Classify a user query using hybrid pattern matching and LLM intelligence."""
        cleaned_query = self.validate_query(query)

        # 1. Fast, High-Precision Heuristic Evaluation
        matched_intent, heuristic_conf, heuristic_reasoning = self._registry.match_heuristic(cleaned_query)

        # If high-confidence heuristic match is found and LLM is not provided, return immediately
        if matched_intent and heuristic_conf >= 0.90 and self._llm is None:
            logger.info(
                "Intent classified via heuristic query=%s intent=%s confidence=%.2f",
                cleaned_query[:50],
                matched_intent.name,
                heuristic_conf,
            )
            return IntentClassificationResponse(
                intent=matched_intent.name,
                confidence=round(heuristic_conf, 2),
                reasoning=heuristic_reasoning,
                required_agents=matched_intent.required_agents,
            )

        # 2. LLM Classification when provider is available
        if self._llm is not None:
            prompt = self._build_classification_prompt()
            message = f"User Request: {cleaned_query}"
            if dataset_id:
                message += f"\nDataset ID: {dataset_id}"
            if context:
                message += f"\nContext: {json.dumps(context)}"

            try:
                raw_response = await self._llm.chat_with_json(message=message, system_prompt=prompt)
                parsed = json.loads(raw_response)
                intent_name = str(parsed.get("intent", "")).lower().strip()
                confidence = float(parsed.get("confidence", 0.8))
                reasoning = str(parsed.get("reasoning", "LLM classified intent."))

                # Clamp confidence between 0.0 and 1.0
                confidence = max(0.0, min(1.0, confidence))

                intent_def = self._registry.get(intent_name)
                if not intent_def:
                    # If LLM returned unsupported intent, fallback to heuristic or unknown
                    logger.warning("LLM returned unknown intent '%s'; evaluating fallback", intent_name)
                    if matched_intent:
                        intent_def = matched_intent
                        confidence = heuristic_conf
                        reasoning = f"{heuristic_reasoning} (LLM returned unmapped: {intent_name})"
                    else:
                        intent_def = self._registry.get(IntentType.UNKNOWN.value)
                        confidence = 0.3
                        reasoning = f"Unmapped intent returned: {intent_name}"

                logger.info(
                    "Intent classified via LLM query=%s intent=%s confidence=%.2f",
                    cleaned_query[:50],
                    intent_def.name,
                    confidence,
                )
                return IntentClassificationResponse(
                    intent=intent_def.name,
                    confidence=round(confidence, 2),
                    reasoning=reasoning,
                    required_agents=intent_def.required_agents,
                )
            except Exception as exc:
                logger.warning(
                    "LLM intent classification failed: %s; falling back to heuristic",
                    exc,
                )

        # 3. Fallback to Heuristic Match if LLM was skipped or failed
        if matched_intent:
            logger.info(
                "Intent classified via fallback heuristic query=%s intent=%s confidence=%.2f",
                cleaned_query[:50],
                matched_intent.name,
                heuristic_conf,
            )
            return IntentClassificationResponse(
                intent=matched_intent.name,
                confidence=round(heuristic_conf, 2),
                reasoning=heuristic_reasoning,
                required_agents=matched_intent.required_agents,
            )

        # 4. Out of Domain / Unknown Default
        unknown_def = self._registry.get(IntentType.UNKNOWN.value) or IntentDefinition(
            name=IntentType.UNKNOWN.value,
            description="Unknown",
            required_agents=[],
        )
        return IntentClassificationResponse(
            intent=unknown_def.name,
            confidence=0.1,
            reasoning="Could not match query to any supported analytical intent.",
            required_agents=unknown_def.required_agents,
        )


def get_intent_classification_service() -> IntentClassificationService:
    """FastAPI dependency provider yielding configured IntentClassificationService."""
    try:
        llm = get_llm_provider()
    except Exception:
        llm = None
    return IntentClassificationService(llm=llm)
