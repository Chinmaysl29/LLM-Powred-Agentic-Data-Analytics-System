"""Compatibility export for the enterprise Audit Log model."""

from backend.app.models.audit_entry import AuditEntry

AuditLog = AuditEntry

__all__ = ["AuditLog"]
