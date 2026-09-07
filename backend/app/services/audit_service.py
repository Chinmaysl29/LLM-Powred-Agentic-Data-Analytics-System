"""Enterprise-facing audit service API, preserving the legacy service backend."""

from backend.app.services.audit_trail_service import AuditTrailService, audit_trail_service


class AuditService(AuditTrailService):
    log_event = AuditTrailService.record
    get_history = AuditTrailService.query
    search_events = AuditTrailService.query
    export_events = AuditTrailService.export


audit_service = audit_trail_service
