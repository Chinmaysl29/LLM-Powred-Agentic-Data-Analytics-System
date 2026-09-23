"""Service for deeply profiling datasets and computing analytical statistics."""

import logging
from typing import Any
import pandas as pd
from fastapi import Depends

from backend.app.core.exceptions import DataProfilingError
from backend.app.schemas.dataset_profile import (
    CardinalityProfile,
    DatasetProfileCreate,
    MissingDataProfile,
    NumericProfile,
)
from backend.app.services.storage_service import StorageService, get_storage_service
from backend.app.services.metadata_extraction_service import MetadataExtractionService, get_metadata_extraction_service

logger = logging.getLogger(__name__)


class DataProfilingService:
    """Service to compute statistical profiles and analyze dataset contents."""

    def __init__(self, metadata_service: MetadataExtractionService) -> None:
        self.metadata_service = metadata_service

    def _calculate_missing_data(self, df: pd.DataFrame) -> MissingDataProfile:
        """Calculate missing data statistics across the dataset."""
        total_nulls = int(df.isna().sum().sum())
        total_cells = df.shape[0] * df.shape[1]
        null_percentage = float(total_nulls / total_cells) if total_cells > 0 else 0.0
        
        cols_with_missing = df.columns[df.isna().any()].tolist()
        
        return MissingDataProfile(
            null_count=total_nulls,
            null_percentage=null_percentage,
            columns_with_missing=cols_with_missing
        )

    def _calculate_cardinality(self, df: pd.DataFrame, row_count: int) -> CardinalityProfile:
        """Identify high and low cardinality columns."""
        high_cardinality = []
        low_cardinality = []

        for col in df.columns:
            unique_count = df[col].nunique(dropna=True)
            
            if row_count > 100 and unique_count / row_count > 0.5:
                high_cardinality.append(col)
            elif unique_count < 20:
                low_cardinality.append(col)

        return CardinalityProfile(
            high_cardinality_columns=high_cardinality,
            low_cardinality_columns=low_cardinality
        )

    def _calculate_numeric_profile(self, df: pd.DataFrame, numeric_cols: list[str]) -> dict[str, NumericProfile]:
        """Calculate detailed statistics for all numeric columns."""
        profile = {}
        
        for col in numeric_cols:
            series = df[col].dropna()
            if series.empty:
                continue
                
            # Mode can be multiple, take first
            modes = series.mode()
            mode_val = modes.iloc[0] if not modes.empty else None
            
            # Pandas calculates skew/kurtosis, replacing NaNs if calculation fails
            skewness = float(series.skew()) if len(series) >= 3 else 0.0
            kurtosis = float(series.kurt()) if len(series) >= 4 else 0.0

            profile[col] = NumericProfile(
                mean=float(series.mean()),
                median=float(series.median()),
                mode=mode_val,
                min=float(series.min()),
                max=float(series.max()),
                std=float(series.std(ddof=1)) if len(series) > 1 else 0.0,
                variance=float(series.var(ddof=1)) if len(series) > 1 else 0.0,
                p25=float(series.quantile(0.25)),
                p50=float(series.quantile(0.50)),
                p75=float(series.quantile(0.75)),
                skewness=skewness,
                kurtosis=kurtosis
            )
            
        return profile

    def generate_profile(self, dataset_id: str, file_path: str, file_type: str) -> DatasetProfileCreate:
        """Generate a complete statistical profile for a dataset file."""
        logger.info("Starting data profiling for dataset_id=%s", dataset_id)
        
        try:
            df = self.metadata_service._load_dataframe(file_path, file_type)
            row_count = df.shape[0]
            
            # 1. Duplicates
            duplicate_rows = int(df.duplicated().sum())
            duplicate_percentage = float(duplicate_rows / row_count) if row_count > 0 else 0.0
            
            # 2. Missing Data
            missing_data_profile = self._calculate_missing_data(df)
            
            # 3. Cardinality
            cardinality_profile = self._calculate_cardinality(df, row_count)
            
            # 4. Numeric Profile
            classifications = self.metadata_service._classify_columns(df)
            numeric_profile = self._calculate_numeric_profile(df, classifications.numeric)
            
            logger.info(
                "Completed data profiling dataset_id=%s duplicates=%d", 
                dataset_id, duplicate_rows
            )
            
            return DatasetProfileCreate(
                dataset_id=dataset_id,
                duplicate_rows=duplicate_rows,
                duplicate_percentage=duplicate_percentage,
                missing_data_profile=missing_data_profile,
                cardinality_profile=cardinality_profile,
                numeric_columns_profile=numeric_profile,
            )
        except Exception as exc:
            logger.error("Data profiling failed for dataset_id=%s: %s", dataset_id, exc)
            raise DataProfilingError(f"Failed to generate dataset profile: {exc}") from exc


def get_data_profiling_service(
    metadata_service: MetadataExtractionService = Depends(get_metadata_extraction_service),
) -> DataProfilingService:
    """FastAPI dependency yielding a DataProfilingService instance."""
    return DataProfilingService(metadata_service=metadata_service)
