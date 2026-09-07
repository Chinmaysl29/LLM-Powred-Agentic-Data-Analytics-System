# AI Data Analyst OS — Administrator Guide

## Roles & Permissions (RBAC)
The platform enforces strict role-based access control across four built-in tiers:

| Role | Permissions | Use Case |
| :--- | :--- | :--- |
| **Admin** | Full system access, user management, audit review, data deletion | Operations & Security Leads |
| **Analyst** | Upload datasets, run forecasts, execute SQL, generate recommendations, export reports | Business & Financial Analysts |
| **Viewer** | Read dashboards, view reports, browse published insights | Executives & Stakeholders |
| **Service** | Machine-to-machine API queries, telemetry ingestion | External integrations & pipelines |

---

## User Management Commands
Create or assign roles via CLI:
```bash
python -m backend.security.rbac --assign-role usr_102 --role analyst
```

---

## Audit Logs & Security Monitoring
Audit records are permanently preserved in PostgreSQL and formatted for SIEM ingestion:
- **Location**: Table `audit_logs`
- **Tracked Attributes**: `timestamp`, `user_id`, `client_ip`, `action`, `resource_id`, `status_code`, `latency_ms`

Query recent audit violations:
```sql
SELECT timestamp, user_id, action, client_ip 
FROM audit_logs 
WHERE status_code IN (401, 403) 
ORDER BY timestamp DESC LIMIT 50;
```

---

## Backup & Disaster Recovery Operations
Create manual snapshot:
```python
from backend.deployment.backup_recovery_manager import backup_recovery_manager
backup_recovery_manager.create_full_backup()
```

Verify snapshot checksums:
```python
backup_recovery_manager.verify_backup_integrity("backup_20260907_120000")
```
