"""Service for extracting and classifying dataset metadata using pandas."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends

from backend.app.core.exceptions import MetadataExtractionError
from backend.app.schemas.dataset_metadata import (
    ColumnMetadata,
    DatasetClassification,
    DatasetMetadataCreate,
)
from backend.app.services.storage_service import StorageService, get_storage_service

logger = logging.getLogger(__name__)


class MetadataExtractionService:
    """Service to analyze dataset files and extract structure/statistics."""

    def __init__(self, storage_service: StorageService) -> None:
        self.storage_service = storage_service

    def _load_dataframe(self, file_path: str, file_type: str) -> pd.DataFrame:
        """Load a file into a pandas DataFrame based on file_type."""
        absolute_path = self.storage_service.retrieve_file(file_path)
        
        try:
            if file_type == "csv":
                return pd.read_csv(absolute_path)
            elif file_type in {"xlsx", "xls"}:
                return pd.read_excel(absolute_path)
            elif file_type == "json":
                return pd.read_json(absolute_path)
            elif file_type == "pdf":
                return pd.DataFrame()
            else:
                raise MetadataExtractionError(f"Unsupported file type for extraction: {file_type}")
        except MetadataExtractionError:
            raise
        except Exception as exc:
            logger.error("Failed to parse file %s into DataFrame: %s", absolute_path, exc)
            raise MetadataExtractionError(f"Failed to parse dataset file: {exc}") from exc

    def _classify_columns(self, df: pd.DataFrame) -> DatasetClassification:
        """Classify columns into numeric, categorical, datetime, and boolean based on dtypes."""
        numeric = []
        categorical = []
        datetime_cols = []
        boolean = []

        for col in df.columns:
            dtype = df[col].dtype
            
            if pd.api.types.is_bool_dtype(dtype):
                boolean.append(col)
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                datetime_cols.append(col)
            elif pd.api.types.is_numeric_dtype(dtype):
                numeric.append(col)
            else:
                # Typically object or category dtypes
                categorical.append(col)
                
        return DatasetClassification(
            numeric=numeric,
            categorical=categorical,
            datetime=datetime_cols,
            boolean=boolean
        )

    def extract_metadata(self, dataset_id: str, file_path: str, file_type: str) -> DatasetMetadataCreate:
        """Extract all metadata for a given dataset file."""
        logger.info("Starting metadata extraction for dataset_id=%s file_type=%s", dataset_id, file_type)
        
        df = self._load_dataframe(file_path, file_type)
        
        row_count = int(df.shape[0])
        column_count = int(df.shape[1])
        column_names = df.columns.tolist()
        
        # Convert pandas dtypes to strings
        column_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Calculate column stats
        columns_metadata = []
        for col in column_names:
            null_count = int(df[col].isna().sum())
            null_percentage = float(null_count / row_count) if row_count > 0 else 0.0
            unique_count = int(df[col].nunique(dropna=True))
            
            columns_metadata.append(
                ColumnMetadata(
                    name=col,
                    type=str(df[col].dtype),
                    null_count=null_count,
                    null_percentage=null_percentage,
                    unique_count=unique_count
                )
            )
            
        classifications = self._classify_columns(df)
        
        logger.info(
            "Completed metadata extraction dataset_id=%s rows=%d cols=%d", 
            dataset_id, row_count, column_count
        )
        
        return DatasetMetadataCreate(
            dataset_id=dataset_id,
            row_count=row_count,
            column_count=column_count,
            column_names=column_names,
            column_types=column_types,
            columns_metadata=columns_metadata,
            classifications=classifications
        )


def get_metadata_extraction_service(
    storage_service: StorageService = Depends(get_storage_service),
) -> MetadataExtractionService:
    """FastAPI dependency yielding a MetadataExtractionService instance."""
    return MetadataExtractionService(storage_service=storage_service)
