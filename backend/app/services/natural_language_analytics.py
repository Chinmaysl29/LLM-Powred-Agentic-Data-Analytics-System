"""Deterministic, explainable natural-language analytics over an uploaded dataset.

This service deliberately executes dataframe operations rather than generated SQL.
Text-to-SQL is a separate Phase 17.2 concern, keeping Phase 17.1 safe and
useful for file-backed datasets.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from backend.app.services.data_retrieval_service import DataRetrievalService


@dataclass(frozen=True)
class AnalyticsRequest:
    operation: str
    metric: str | None
    dimension: str | None
    limit: int = 10


class NaturalLanguageAnalyticsService:
    """Parse a constrained analytics language into safe pandas aggregations."""

    def __init__(self, data_retrieval: DataRetrievalService | None = None) -> None:
        self._data_retrieval = data_retrieval

    @staticmethod
    def is_analytics_query(message: str) -> bool:
        words = {"show", "total", "sum", "average", "avg", "count", "top", "bottom", "highest", "lowest", "trend", "revenue", "sales", "profit", "by"}
        return bool(words.intersection(re.findall(r"[a-z]+", message.lower())))

    def parse(self, message: str, columns: list[str]) -> AnalyticsRequest:
        normalized = message.lower()
        operation = "sum"
        if re.search(r"\b(count|how many|number of)\b", normalized):
            operation = "count"
        elif re.search(r"\b(average|avg|mean)\b", normalized):
            operation = "average"
        elif re.search(r"\b(minimum|min|lowest)\b", normalized):
            operation = "min"
        elif re.search(r"\b(maximum|max|highest)\b", normalized):
            operation = "max"
        elif re.search(r"\b(bottom|least|worst)\b", normalized):
            operation = "bottom"
        elif re.search(r"\b(top|best|leading)\b", normalized):
            operation = "top"
        elif re.search(r"\b(trend|over time|growth|decline)\b", normalized):
            operation = "trend"

        metric = self._match_column(normalized, columns, after=r"(?:of|by|total|sum|average|avg|max|min|highest|lowest|top|bottom)\s+")
        dimension = self._match_column_after(normalized, columns, r"\bby\s+")
        if dimension == metric:
            dimension = None
        limit_match = re.search(r"\b(?:top|bottom)\s+(\d+)\b", normalized)
        return AnalyticsRequest(operation, metric, dimension, int(limit_match.group(1)) if limit_match else 10)

    @staticmethod
    def _match_column(message: str, columns: list[str], after: str) -> str | None:
        # Prefer column names following natural-language cues, then any clear
        # word-boundary mention. Matching only known columns prevents arbitrary
        # expression execution.
        candidates = sorted(columns, key=len, reverse=True)
        for column in candidates:
            expression = re.escape(column.lower()).replace(r"\ ", r"[ _-]?")
            if re.search(after + expression + r"\b", message) or re.search(r"\b" + expression + r"\b", message):
                return column
        return None

    @staticmethod
    def _match_column_after(message: str, columns: list[str], prefix: str) -> str | None:
        for column in sorted(columns, key=len, reverse=True):
            expression = re.escape(column.lower()).replace(r"\ ", r"[ _-]?")
            if re.search(prefix + expression + r"\b", message):
                return column
        return None

    async def analyze(self, message: str, dataset_id: str | None = None, dataframe: pd.DataFrame | None = None) -> dict[str, Any]:
        if dataframe is None:
            if not dataset_id or self._data_retrieval is None:
                return {"answer": "Select a dataset before requesting an analysis.", "data": [], "explanation": "Analytics needs a dataset context.", "actionable": []}
            dataframe, _ = await asyncio.to_thread(self._data_retrieval.load_dataframe, dataset_id)
        return await asyncio.to_thread(self._execute, message, dataframe)

    def _execute(self, message: str, dataframe: pd.DataFrame) -> dict[str, Any]:
        if dataframe.empty:
            return {"answer": "The selected dataset has no rows to analyze.", "data": [], "explanation": "No aggregation was run.", "actionable": []}
        request = self.parse(message, list(dataframe.columns))
        metric = request.metric or self._first_numeric(dataframe)
        if request.operation != "count" and metric is None:
            return {"answer": "I could not identify a numeric metric in the question or dataset.", "data": [], "explanation": "Try naming a numeric column such as revenue or sales.", "actionable": []}
        if metric is not None and metric not in dataframe.columns:
            return {"answer": f"I could not find the metric '{metric}' in this dataset.", "data": [], "explanation": "Use one of the dataset columns.", "actionable": []}

        if request.operation == "trend":
            return self._trend(dataframe, metric, request.dimension)
        if request.operation in {"top", "bottom"}:
            return self._ranking(dataframe, metric, request.dimension, request.operation, request.limit)
        return self._aggregate(dataframe, metric, request.dimension, request.operation)

    @staticmethod
    def _first_numeric(dataframe: pd.DataFrame) -> str | None:
        numeric = dataframe.select_dtypes(include="number").columns.tolist()
        return numeric[0] if numeric else None

    def _aggregate(self, dataframe: pd.DataFrame, metric: str | None, dimension: str | None, operation: str) -> dict[str, Any]:
        if operation == "count":
            series = dataframe.groupby(dimension).size() if dimension else len(dataframe)
        else:
            values = pd.to_numeric(dataframe[metric], errors="coerce")
            operation_fn = {"sum": "sum", "average": "mean", "min": "min", "max": "max"}.get(operation, "sum")
            series = values.groupby(dataframe[dimension]).agg(operation_fn) if dimension else getattr(values, operation_fn)()
        label = "records" if operation == "count" else metric
        if dimension:
            rows = [{dimension: str(index), label: self._number(value)} for index, value in series.sort_values(ascending=False).items()]
            answer = f"{operation.title()} {label} by {dimension}: " + "; ".join(f"{row[dimension]} = {row[label]}" for row in rows[:10]) + "."
        else:
            value = self._number(series)
            rows, answer = [{label: value}], f"The {operation} {label} is {value}."
        return {"answer": answer, "data": rows, "explanation": f"Calculated {operation} using {label}" + (f" grouped by {dimension}" if dimension else "") + ".", "actionable": []}

    def _ranking(self, dataframe: pd.DataFrame, metric: str | None, dimension: str | None, operation: str, limit: int) -> dict[str, Any]:
        group = dimension or self._first_categorical(dataframe, exclude=metric)
        if group is None:
            return {"answer": "I need a category such as product, customer, or region to rank results.", "data": [], "explanation": "No grouping column was identified.", "actionable": []}
        values = pd.to_numeric(dataframe[metric], errors="coerce") if metric else pd.Series(1, index=dataframe.index)
        ranked = values.groupby(dataframe[group]).sum().sort_values(ascending=operation == "bottom").head(limit)
        rows = [{group: str(index), metric or "count": self._number(value)} for index, value in ranked.items()]
        answer = f"{operation.title()} {len(rows)} {group} by {metric or 'count'}: " + "; ".join(f"{row[group]} ({row[metric or 'count']})" for row in rows) + "."
        return {"answer": answer, "data": rows, "explanation": f"Grouped records by {group}, summed {metric or 'records'}, and sorted {operation} first.", "actionable": [f"Focus on {rows[0][group]} first." ] if rows else []}

    def _trend(self, dataframe: pd.DataFrame, metric: str | None, date_column: str | None) -> dict[str, Any]:
        date_column = date_column or next((col for col in dataframe.columns if any(word in col.lower() for word in ("date", "month", "time", "year"))), None)
        if date_column is None:
            return {"answer": "I need a date or time column to analyze a trend.", "data": [], "explanation": "No temporal column was identified.", "actionable": []}
        dates = pd.to_datetime(dataframe[date_column], errors="coerce")
        values = pd.to_numeric(dataframe[metric], errors="coerce")
        trend = values.groupby(dates.dt.to_period("M")).sum().dropna()
        rows = [{date_column: str(index), metric: self._number(value)} for index, value in trend.items()]
        direction = "increased" if len(trend) > 1 and trend.iloc[-1] > trend.iloc[0] else "decreased" if len(trend) > 1 else "was stable"
        return {"answer": f"{metric.title()} {direction} across the available monthly periods.", "data": rows, "explanation": f"Aggregated {metric} by month from {date_column}.", "actionable": ["Review the latest period and investigate the main drivers."]}

    @staticmethod
    def _first_categorical(dataframe: pd.DataFrame, exclude: str | None = None) -> str | None:
        columns = [col for col in dataframe.columns if col != exclude and not pd.api.types.is_numeric_dtype(dataframe[col])]
        return columns[0] if columns else None

    @staticmethod
    def _number(value: Any) -> int | float:
        value = float(value)
        return int(value) if value.is_integer() else round(value, 2)


def get_natural_language_analytics_service() -> NaturalLanguageAnalyticsService:
    # The route injects file-backed retrieval when a database session exists;
    # this factory remains useful for dataframe-driven unit work.
    return NaturalLanguageAnalyticsService()
