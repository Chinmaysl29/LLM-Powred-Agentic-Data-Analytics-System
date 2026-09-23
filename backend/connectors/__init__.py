"""Phase 12.4 — Connector Marketplace Package.

Exports base connector interfaces, registry, implementations (Databases, Storage,
CRMs, Warehouses), scheduler, and monitoring systems.
"""

from backend.connectors.base import (
    BaseConnector,
    ColumnInfo,
    ConnectorAuthError,
    ConnectorConnectionError,
    ConnectorError,
    ConnectorSyncError,
    FileInfo,
    HealthCheckResult,
    SchemaInfo,
    SyncResult,
    TableInfo,
    ValidationResult,
)
from backend.connectors.crm import (
    CRMConnector,
    HubSpotConnector,
    SalesforceConnector,
    ZohoCRMConnector,
)
from backend.connectors.database import (
    DatabaseConnector,
    MongoDBConnector,
    MySQLConnector,
    PostgresConnector,
    SQLiteConnector,
    SQLServerConnector,
)
from backend.connectors.monitoring import ConnectorMonitor, ConnectorTelemetry
from backend.connectors.registry import ConnectorRegistry
from backend.connectors.scheduler import (
    ConnectorScheduler,
    JobStatus,
    ScheduledJob,
    SyncFrequency,
)
from backend.connectors.storage import (
    AzureBlobConnector,
    CloudStorageConnector,
    GoogleDriveConnector,
    OneDriveConnector,
    S3Connector,
    SharePointConnector,
)
from backend.connectors.warehouse import (
    BigQueryConnector,
    DataWarehouseConnector,
    DatabricksConnector,
    RedshiftConnector,
    SnowflakeConnector,
)

__all__ = [
    "BaseConnector",
    "ConnectorError",
    "ConnectorAuthError",
    "ConnectorConnectionError",
    "ConnectorSyncError",
    "ColumnInfo",
    "TableInfo",
    "SchemaInfo",
    "FileInfo",
    "ValidationResult",
    "HealthCheckResult",
    "SyncResult",
    "ConnectorRegistry",
    "DatabaseConnector",
    "PostgresConnector",
    "MySQLConnector",
    "SQLServerConnector",
    "SQLiteConnector",
    "MongoDBConnector",
    "CloudStorageConnector",
    "GoogleDriveConnector",
    "OneDriveConnector",
    "SharePointConnector",
    "S3Connector",
    "AzureBlobConnector",
    "CRMConnector",
    "SalesforceConnector",
    "HubSpotConnector",
    "ZohoCRMConnector",
    "DataWarehouseConnector",
    "SnowflakeConnector",
    "BigQueryConnector",
    "RedshiftConnector",
    "DatabricksConnector",
    "ConnectorScheduler",
    "SyncFrequency",
    "JobStatus",
    "ScheduledJob",
    "ConnectorMonitor",
    "ConnectorTelemetry",
]
