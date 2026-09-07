"""Comprehensive tests for Phase 4.1 Schema Reader.

Verifies:
1. Dynamic relational database schema inspection (tables, columns, datatypes, PKs).
2. Foreign key and cross-table relationship discovery.
3. Index extraction (unique and non-unique).
4. In-memory caching, TTL expiration, and cache invalidation.
5. Compact schema generation: [{'table': '...', 'columns': [...]}]
6. Prompt-ready markdown/DDL context formatting for downstream SQL agents.
7. SchemaReader interface in backend.sql_agent.schema_reader.
8. REST API endpoints for schema reading and cache management.
"""

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.postgres import get_db_session
from backend.app.repositories.schema_repository import SchemaRepository
from backend.app.schemas.schema_reader import DatabaseSchema
from backend.app.services.schema_reader_service import SchemaReaderService
from backend.main import app
from backend.sql_agent.schema_reader import SchemaReader


# ----------------------------------------------------------------------
# Test Fixtures & Schema Definition
# ----------------------------------------------------------------------
@pytest.fixture
def sqlite_engine():
    """Create in-memory SQLite engine with a realistic multi-table relational schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()

    customers = Table(
        "customers",
        metadata,
        Column("customer_id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("email", String(100), nullable=False),
        Column("city", String(50), nullable=True),
    )
    Index("ix_customers_email", customers.c.email, unique=True)

    orders = Table(
        "orders",
        metadata,
        Column("order_id", Integer, primary_key=True),
        Column("customer_id", Integer, ForeignKey("customers.customer_id"), nullable=False),
        Column("order_date", Date, nullable=False),
        Column("total_amount", Float, nullable=False),
        Column("status", String(20), nullable=False, default="completed"),
    )
    Index("ix_orders_customer_id", orders.c.customer_id)

    order_items = Table(
        "order_items",
        metadata,
        Column("item_id", Integer, primary_key=True),
        Column("order_id", Integer, ForeignKey("orders.order_id"), nullable=False),
        Column("product_name", String(100), nullable=False),
        Column("quantity", Integer, nullable=False, default=1),
        Column("unit_price", Float, nullable=False),
    )

    metadata.create_all(engine)
    return engine


@pytest.fixture
def schema_repository(sqlite_engine):
    return SchemaRepository(bind=sqlite_engine)


@pytest.fixture
def schema_service(schema_repository):
    return SchemaReaderService(schema_repository=schema_repository, cache_ttl_seconds=2)


# ----------------------------------------------------------------------
# 1. Dynamic Table and Column Extraction
# ----------------------------------------------------------------------
def test_schema_inspection_tables_and_columns(schema_repository: SchemaRepository):
    schema = schema_repository.inspect_schema()

    table_names = [t.table_name for t in schema.tables]
    assert "customers" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names

    # Verify Customers table
    cust_table = schema.get_table("customers")
    assert cust_table is not None
    assert "customer_id" in cust_table.primary_keys
    assert "customer_id" in cust_table.column_names
    assert "email" in cust_table.column_names

    email_col = next(c for c in cust_table.columns if c.name == "email")
    assert email_col.nullable is False
    assert "VARCHAR" in email_col.data_type.upper() or "TEXT" in email_col.data_type.upper() or "STRING" in email_col.data_type.upper()

    # Verify Orders table
    orders_table = schema.get_table("orders")
    assert orders_table is not None
    assert "order_id" in orders_table.primary_keys
    assert "total_amount" in orders_table.column_names


# ----------------------------------------------------------------------
# 2. Foreign Key & Relationship Discovery
# ----------------------------------------------------------------------
def test_foreign_keys_and_relationships(schema_repository: SchemaRepository):
    schema = schema_repository.inspect_schema()

    assert len(schema.relationships) >= 2

    # Relationship: orders -> customers
    orders_cust_rel = next(
        (r for r in schema.relationships if r.source_table == "orders" and r.target_table == "customers"),
        None,
    )
    assert orders_cust_rel is not None
    assert orders_cust_rel.source_columns == ["customer_id"]
    assert orders_cust_rel.target_columns == ["customer_id"]

    # Relationship: order_items -> orders
    items_orders_rel = next(
        (r for r in schema.relationships if r.source_table == "order_items" and r.target_table == "orders"),
        None,
    )
    assert items_orders_rel is not None
    assert items_orders_rel.source_columns == ["order_id"]
    assert items_orders_rel.target_columns == ["order_id"]


# ----------------------------------------------------------------------
# 3. Index Extraction
# ----------------------------------------------------------------------
def test_indexes_extraction(schema_repository: SchemaRepository):
    schema = schema_repository.inspect_schema()

    cust_table = schema.get_table("customers")
    assert cust_table is not None

    email_idx = next((idx for idx in cust_table.indexes if "email" in idx.columns), None)
    assert email_idx is not None
    assert email_idx.unique is True

    orders_table = schema.get_table("orders")
    assert orders_table is not None
    cust_id_idx = next((idx for idx in orders_table.indexes if "customer_id" in idx.columns), None)
    assert cust_id_idx is not None


# ----------------------------------------------------------------------
# 4. In-Memory Caching & TTL Expiration
# ----------------------------------------------------------------------
def test_caching_and_invalidation(schema_service: SchemaReaderService):
    # 1. Initial retrieval - not cached
    s1 = schema_service.get_schema()
    assert s1.metadata.is_cached is False

    # 2. Subsequent retrieval within TTL - served from cache
    s2 = schema_service.get_schema()
    assert s2.metadata.is_cached is True
    assert len(s2.tables) == len(s1.tables)

    # 3. Force refresh - cache bypassed
    s3 = schema_service.get_schema(force_refresh=True)
    assert s3.metadata.is_cached is False

    # 4. Invalidation
    schema_service.invalidate_cache()
    s4 = schema_service.get_schema()
    assert s4.metadata.is_cached is False

    # 5. TTL expiration
    s5 = schema_service.get_schema()
    assert s5.metadata.is_cached is True
    time.sleep(2.1)  # Cache TTL is 2s
    s6 = schema_service.get_schema()
    assert s6.metadata.is_cached is False


# ----------------------------------------------------------------------
# 5. Compact Table Schema Format
# ----------------------------------------------------------------------
def test_compact_tables_generation(schema_service: SchemaReaderService):
    compact = schema_service.get_compact_tables()
    assert isinstance(compact, list)
    assert len(compact) >= 3

    # Check structure conforms to required format: {"table": "...", "columns": [...]}
    sales_item = next((item for item in compact if item["table"] == "orders"), None)
    assert sales_item is not None
    assert "order_id" in sales_item["columns"]
    assert "customer_id" in sales_item["columns"]
    assert "total_amount" in sales_item["columns"]


# ----------------------------------------------------------------------
# 6. Prompt Context Formatting for LLM
# ----------------------------------------------------------------------
def test_prompt_context_formatting(schema_service: SchemaReaderService):
    prompt_ctx = schema_service.generate_prompt_context()

    assert "Database Schema" in prompt_ctx
    assert "Table `customers`" in prompt_ctx
    assert "Table `orders`" in prompt_ctx
    assert "customer_id" in prompt_ctx
    assert "Relationships:" in prompt_ctx
    assert "`orders.customer_id` -> `customers.customer_id`" in prompt_ctx

    # Filtered prompt context
    subset_ctx = schema_service.generate_prompt_context(table_names=["customers"])
    assert "Table `customers`" in subset_ctx
    assert "Table `orders`" not in subset_ctx


# ----------------------------------------------------------------------
# 7. Table Lookup
# ----------------------------------------------------------------------
def test_table_lookup(schema_service: SchemaReaderService):
    table = schema_service.get_table_schema("customers")
    assert table is not None
    assert table.table_name == "customers"

    # Case-insensitive lookup
    table_upper = schema_service.get_table_schema("CUSTOMERS")
    assert table_upper is not None
    assert table_upper.table_name == "customers"

    non_existent = schema_service.get_table_schema("non_existent_table")
    assert non_existent is None


# ----------------------------------------------------------------------
# 8. SQL Agent SchemaReader Facade Interface
# ----------------------------------------------------------------------
def test_sql_agent_schema_reader(sqlite_engine):
    reader = SchemaReader(bind=sqlite_engine)

    schema = reader.get_schema()
    assert isinstance(schema, DatabaseSchema)
    assert len(schema.tables) >= 3

    compact = reader.get_compact_tables()
    assert any(c["table"] == "orders" for c in compact)

    prompt_ctx = reader.to_prompt_context()
    assert "Table `orders`" in prompt_ctx

    table = reader.get_table("orders")
    assert table is not None
    assert "order_id" in table.primary_keys


# ----------------------------------------------------------------------
# 9. REST API Endpoints Tests
# ----------------------------------------------------------------------
def test_api_schema_endpoints(sqlite_engine):
    SessionLocal = sessionmaker(bind=sqlite_engine)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_db
    client = TestClient(app)

    # 1. GET /api/v1/schema
    resp = client.get("/api/v1/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "schema_data" in data
    assert len(data["schema_data"]["tables"]) >= 3

    # 2. GET /api/v1/schema/compact
    resp_compact = client.get("/api/v1/schema/compact")
    assert resp_compact.status_code == 200
    compact_data = resp_compact.json()
    assert isinstance(compact_data, list)
    assert any(t["table"] == "customers" for t in compact_data)

    # 3. GET /api/v1/schema/tables/customers
    resp_table = client.get("/api/v1/schema/tables/customers")
    assert resp_table.status_code == 200
    table_data = resp_table.json()
    assert table_data["table_name"] == "customers"
    assert "customer_id" in table_data["column_names"]

    # 4. GET /api/v1/schema/tables/unknown (404)
    resp_404 = client.get("/api/v1/schema/tables/unknown_table_xyz")
    assert resp_404.status_code == 404

    # 5. GET /api/v1/schema/prompt-context
    resp_prompt = client.get("/api/v1/schema/prompt-context")
    assert resp_prompt.status_code == 200
    assert "prompt_context" in resp_prompt.json()

    # 6. POST /api/v1/schema/refresh
    resp_refresh = client.post("/api/v1/schema/refresh")
    assert resp_refresh.status_code == 200
    assert resp_refresh.json()["status"] == "cache_invalidated"

    app.dependency_overrides.pop(get_db_session, None)
